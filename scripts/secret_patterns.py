"""Shared secret-detection patterns and scanner.

Used by .githooks/pre-commit and the Cursor hooks under .cursor/hooks/.

Design goals
------------
- High-precision, low-noise: only flag strings that look like real provider
  keys, tokens, or private-key blocks. The 40-character generic base64 pattern
  is gated on nearby AWS/Azure secret context to keep false positives down.
- Skip obvious placeholders (``example``, ``placeholder``, ``changeme``,
  ``your_``, ``replace_``, ``<your_...>``, ``demo``, ``fake``, ``dummy``,
  ``redacted``, ``xxxxx``, ``sample``, ``test_``).
- Skip the project's intentional dev-only Postgres password
  ``rag:rag_dev_password`` (used by docker-compose and CI only).

The module exposes :func:`find_secrets`, which returns a list of
:class:`Finding` objects.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence


_PLACEHOLDER_VALUE_RE = re.compile(
    r"(?i)(example|placeholder|changeme|replace[-_]|your[-_]|<your|<replace|"
    r"demo|fake|dummy|redacted|xxxxx|sample|test_|driver://user:pass)"
)
_PLACEHOLDER_CONTEXT_RE = re.compile(
    r"(?i)(placeholder|changeme|replace[-_]|your[-_]|<your|<replace|"
    r"redacted|xxxxx|driver://user:pass)"
)

DEV_ALLOWLIST = (
    "rag:rag_dev_password",
    "postgres:postgres@",
)


@dataclass(frozen=True)
class Pattern:
    name: str
    regex: "re.Pattern[str]"
    description: str
    requires_context: bool = False
    context_keywords: tuple = ()


PATTERNS: Sequence[Pattern] = (
    Pattern(
        "AWS_ACCESS_KEY_ID",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "AWS access key id",
    ),
    Pattern(
        "AWS_TEMP_ACCESS_KEY",
        re.compile(r"\bASIA[0-9A-Z]{16}\b"),
        "AWS temporary access key",
    ),
    Pattern(
        "AWS_SECRET_ACCESS_KEY",
        re.compile(r"\b[A-Za-z0-9/+=]{40}\b"),
        "AWS secret access key (context-gated)",
        requires_context=True,
        context_keywords=("aws_secret", "secret_access_key", "bedrock_secret"),
    ),
    Pattern(
        "OPENAI_API_KEY",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
        "OpenAI API key",
    ),
    Pattern(
        "ANTHROPIC_API_KEY",
        re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
        "Anthropic API key",
    ),
    Pattern(
        "GROQ_API_KEY",
        re.compile(r"\bgsk_[A-Za-z0-9]{30,}\b"),
        "Groq API key",
    ),
    Pattern(
        "HF_TOKEN",
        re.compile(r"\bhf_[A-Za-z0-9]{30,}\b"),
        "Hugging Face token",
    ),
    Pattern(
        "GITHUB_PAT",
        re.compile(r"\bgh[oprsu]_[A-Za-z0-9]{30,}\b"),
        "GitHub personal access token",
    ),
    Pattern(
        "GOOGLE_API_KEY",
        re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
        "Google API key",
    ),
    Pattern(
        "SLACK_TOKEN",
        re.compile(r"\bxox[bpoars]-[0-9A-Za-z-]{10,}\b"),
        "Slack token",
    ),
    Pattern(
        "JWT",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}\b"
        ),
        "JWT (JSON Web Token)",
    ),
    Pattern(
        "PRIVATE_KEY_BLOCK",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP |ENCRYPTED )?PRIVATE KEY-----"
        ),
        "PEM private key block",
    ),
    Pattern(
        "AZURE_STORAGE_CONN",
        re.compile(r"DefaultEndpointsProtocol=https;AccountName="),
        "Azure storage connection string",
    ),
    Pattern(
        "BASIC_AUTH_URL",
        re.compile(r"\b[a-z]+://[A-Za-z0-9._%-]+:[^\s/@<>'\"]+@"),
        "Basic-auth URL with embedded credentials",
    ),
)


@dataclass(frozen=True)
class Finding:
    name: str
    description: str
    match: str
    line_no: int
    line_excerpt: str


def _is_placeholder(match: str, context: str) -> bool:
    if _PLACEHOLDER_VALUE_RE.search(match) or _PLACEHOLDER_CONTEXT_RE.search(context):
        return True
    return any(allowed in match or allowed in context for allowed in DEV_ALLOWLIST)


def find_secrets(text: str, *, extra_allowlist: Iterable[str] = ()) -> List[Finding]:
    """Return a list of :class:`Finding` results for ``text``.

    ``extra_allowlist`` extends :data:`DEV_ALLOWLIST` for callers that want to
    suppress additional well-known dev/test values.
    """

    allowlist = tuple(DEV_ALLOWLIST) + tuple(extra_allowlist)
    findings: List[Finding] = []

    line_starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(i + 1)

    def _line_info(pos: int):
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        line_no = lo + 1
        start = line_starts[lo]
        end = text.find("\n", start)
        line = text[start: end if end != -1 else None]
        return line_no, line.strip()[:200]

    for pat in PATTERNS:
        for m in pat.regex.finditer(text):
            matched = m.group(0)
            context = text[max(0, m.start() - 80): m.end() + 40]
            # Do not flag the scanner's own regex definitions when this file
            # is staged or audited.
            if "re.compile" in context:
                continue
            if pat.requires_context:
                lowered = context.lower()
                if not any(k in lowered for k in pat.context_keywords):
                    continue
            if _PLACEHOLDER_VALUE_RE.search(matched) or _PLACEHOLDER_CONTEXT_RE.search(context):
                continue
            if any(allowed in matched or allowed in context for allowed in allowlist):
                continue
            line_no, line_excerpt = _line_info(m.start())
            findings.append(
                Finding(
                    name=pat.name,
                    description=pat.description,
                    match=matched if len(matched) <= 80 else matched[:77] + "...",
                    line_no=line_no,
                    line_excerpt=line_excerpt,
                )
            )

    return findings


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: secret_patterns.py <file> [file ...]", file=sys.stderr)
        sys.exit(2)
    overall = 0
    for path in sys.argv[1:]:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        for f in find_secrets(text):
            overall += 1
            print(
                f"{path}:{f.line_no}: {f.name} ({f.description}) :: {f.match}"
            )
    if overall:
        print(f"\n{overall} potential secret(s) detected.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
