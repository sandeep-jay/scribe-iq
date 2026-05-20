#!/usr/bin/env python3
"""Cursor hook: beforeShellExecution.

Ask before running shell commands that look like they could leak secrets,
e.g. dumping .env / .aws / .ssh / .netrc files, dumping environment
variables, curl with embedded provider keys or URL token queries, git
--no-verify, force pushes, openssl on private keys, etc.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _scanner_loader import load_scanner


def _allow() -> None:
    print(json.dumps({"permission": "allow"}))
    sys.exit(0)


def _ask(reasons: list[str]) -> None:
    msg = "; ".join(sorted(set(reasons)))
    print(json.dumps({
        "permission": "ask",
        "user_message": f"Cursor security hook flagged this command: {msg}. Confirm it is safe before running.",
        "agent_message": f"Local security hook flagged this command as potentially secret-leaking: {msg}.",
    }))
    sys.exit(0)


# Sensitive file substrings the agent should ask before reading/copying.
SENSITIVE_PATHS = (
    (r"\.env(?:\b|\.[^\s/]*)",                       "reads a .env file"),
    (r"\.aws/credentials",                             "reads AWS credentials"),
    (r"\.aws/config",                                  "reads AWS config"),
    (r"\.ssh/id_[A-Za-z0-9_-]+",                       "reads an SSH private key"),
    (r"\.ssh/identity",                                "reads an SSH identity"),
    (r"\.netrc",                                       "reads a .netrc credentials file"),
    (r"\.npmrc",                                       "reads a .npmrc (may contain tokens)"),
    (r"\.pypirc",                                      "reads a .pypirc (may contain tokens)"),
    (r"\.docker/config\.json",                         "reads docker auth config"),
    (r"\.kube/config",                                 "reads kubeconfig"),
    (r"\.gnupg/[^\s]*",                                "reads GnuPG keys"),
    (r"gcloud/application_default_credentials\.json",  "reads gcloud ADC"),
)

READ_CMDS = ("cat", "less", "more", "head", "tail", "bat", "view", "xclip", "pbcopy")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        _allow()
    command = str(payload.get("command", ""))
    if not command.strip():
        _allow()

    risky: list[tuple[re.Pattern[str], str]] = []
    for cmd in READ_CMDS:
        for path_re, label in SENSITIVE_PATHS:
            risky.append((re.compile(rf"\b{cmd}\s+[^\s|;&]*{path_re}"), label))
    risky.extend([
        (re.compile(r"\bprintenv\b"),                                          "dumps environment variables"),
        (re.compile(r"\benv\s*\|\s*grep"),                                     "dumps environment variables"),
        (re.compile(r"--no-verify\b"),                                         "bypasses git hooks"),
        (re.compile(r"git\s+push\s+(?:--force\b|-f\b|.*--force-with-lease)"), "force-pushes (could overwrite remote history)"),
        (re.compile(r"\baws\s+configure\s+(?:set\s+)?aws_secret_access_key"),  "writes an AWS secret"),
        (re.compile(r"\bgh\s+auth\s+token\b"),                                 "prints a GitHub token"),
        (re.compile(r"[?&](?:token|api_key|apikey|access_token|auth)=[^\s&]+"), "passes a credential as a URL query"),
        (re.compile(r"\bopenssl\s+(?:rsa|ec|pkcs8|pkey)\s+-in\b"),              "reads/derives a private key"),
        (re.compile(r"\bscp\s+[^\s]+\s+[^\s]+@"),                              "scp to remote (verify destination)"),
    ])

    reasons: list[str] = []
    for pat, why in risky:
        if pat.search(command):
            reasons.append(why)

    mod = load_scanner()
    if mod is not None:
        for f in mod.find_secrets(command):
            reasons.append(f"contains a {f.description} literal")

    if reasons:
        _ask(reasons)
    _allow()


if __name__ == "__main__":
    main()
