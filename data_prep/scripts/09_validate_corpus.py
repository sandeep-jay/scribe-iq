"""
09_validate_corpus.py — validate assembled ``clinical_corpus_v2`` JSONL invariants.

Run::

  python data_prep/scripts/09_validate_corpus.py [-v|--verbose]

Writes ``audit_report.md`` beside the corpus. Use ``-v`` for DEBUG checkpoints about
which input shards exist on disk (boolean flags only — no PHI).
"""
from __future__ import annotations


import argparse
import sys
from pathlib import Path as _Path

_DP_ROOT = _Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))


from collections import Counter
from pathlib import Path

import logging

from utils.cli_logging import add_logging_arguments, configure_cli_logging, logging_args_from_ns
from utils.io_utils import load_jsonl

log = logging.getLogger(__name__)


def _load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    return list(load_jsonl(path))


REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "data/clinical_corpus_v2"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate clinical_corpus_v2 JSONL bundle.")
    add_logging_arguments(parser)
    ns = parser.parse_args()
    configure_cli_logging(**logging_args_from_ns(ns))

    log.info("corpus_validate_started corpus_dir=%s", CORPUS)
    log.debug(
        "corpus_validate_inputs_present patients=%s encounters=%s notes=%s dialogues=%s",
        (CORPUS / "patients.jsonl").is_file(),
        (CORPUS / "encounters.jsonl").is_file(),
        (CORPUS / "notes.jsonl").is_file(),
        (CORPUS / "dialogues.jsonl").is_file(),
    )
    patients = list(load_jsonl(CORPUS / "patients.jsonl"))
    encounters = list(load_jsonl(CORPUS / "encounters.jsonl"))
    notes = list(load_jsonl(CORPUS / "notes.jsonl"))
    dialogues = list(load_jsonl(CORPUS / "dialogues.jsonl"))
    conditions = _load_jsonl(CORPUS / "conditions.jsonl")
    medications = _load_jsonl(CORPUS / "medications.jsonl")

    patient_ids = {p["patient_id"] for p in patients}
    encounter_ids = {e["encounter_id"] for e in encounters}
    issues: list[str] = []
    warnings: list[str] = []

    for e in encounters:
        if e["patient_id"] not in patient_ids:
            issues.append(f"Encounter {e['encounter_id']} orphaned patient_id")
    for n in notes:
        if n["encounter_id"] not in encounter_ids:
            issues.append(f"Note {n['note_id']} orphaned encounter_id")
        if not n.get("note_text") or len(n["note_text"].split()) < 30:
            issues.append(f"Note {n['note_id']} empty or too short")
    for d in dialogues:
        if d["encounter_id"] not in encounter_ids:
            issues.append(f"Dialogue {d['dialogue_id']} orphaned encounter_id")

    showcase_enc_ids = {e["encounter_id"] for e in encounters if e.get("is_showcase")}
    dialogue_enc_ids = {d["encounter_id"] for d in dialogues}
    aci_dialogue_ids = {d["encounter_id"] for d in dialogues if "aci" in str(d.get("source", "")).lower()}
    showcase_with_dlg = showcase_enc_ids & dialogue_enc_ids
    showcase_aci_dlg = showcase_enc_ids & aci_dialogue_ids
    showcase_no_dlg = showcase_enc_ids - dialogue_enc_ids

    for enc_id in showcase_no_dlg:
        warnings.append(f"Showcase encounter {enc_id} has no dialogue")

    specialty_dist = Counter(p["primary_specialty"] for p in patients)
    source_dist = Counter(n["reference_source"] for n in notes)
    score_vals = [e["match_score"] for e in encounters]
    avg_score = sum(score_vals) / len(score_vals) if score_vals else 0.0

    log.info("=" * 55)
    log.info("CORPUS AUDIT")
    log.info("=" * 55)
    log.info("\nSCALE")
    log.info(f"  Patients:      {len(patients)}")
    log.info(f"  Encounters:    {len(encounters)}")
    log.info(f"  Notes:         {len(notes)}")
    log.info(f"  Dialogues:     {len(dialogues)}")
    log.info(f"  Conditions:    {len(conditions)}")
    log.info(f"  Medications:   {len(medications)}")
    log.info("\nSHOWCASE")
    log.info(f"  Total showcase:             {len(showcase_enc_ids)}")
    log.info(f"  Showcase with any dialogue: {len(showcase_with_dlg)}")
    log.info(f"  Showcase with ACI dialogue: {len(showcase_aci_dlg)}")
    log.info(f"  Showcase with no dialogue:  {len(showcase_no_dlg)}")
    log.info("\nSPECIALTY DISTRIBUTION")
    for spec, count in sorted(specialty_dist.items(), key=lambda x: -x[1]):
        log.info(f"  {spec:<30} {count}")
    log.info("\nNOTE SOURCES")
    for src, count in sorted(source_dist.items(), key=lambda x: -x[1]):
        log.info(f"  {src:<20} {count}")
    log.info("\nMATCH QUALITY")
    if score_vals:
        log.info(
            f"  Average: {avg_score:.3f}  Min: {min(score_vals):.3f}  Max: {max(score_vals):.3f}"
        )
    if issues:
        log.warning("corpus_validate_issues_found count=%s", len(issues))
    log.info("\nISSUES")
    if issues:
        for i in issues:
            log.info(f"  ✗ {i}")
    else:
        log.info("  (none)")
    log.info("\nWARNINGS")
    if warnings:
        for w in warnings:
            log.info(f"  ⚠ {w}")
    else:
        log.info("  (none)")

    report_lines = [
        "# Scribe-IQ Corpus Audit Report\n",
        "## Scale\n",
        f"| Patients | {len(patients)} |\n",
        f"| Encounters | {len(encounters)} |\n",
        f"| Notes | {len(notes)} |\n",
        f"| Dialogues | {len(dialogues)} |\n",
        "## Showcase\n",
        f"| Total showcase | {len(showcase_enc_ids)} |\n",
        f"| With ACI dialogue | {len(showcase_aci_dlg)} |\n",
        f"| With any dialogue | {len(showcase_with_dlg)} |\n",
        f"| No dialogue | {len(showcase_no_dlg)} |\n",
        "## Issues\n",
        "None\n" if not issues else "\n".join(f"- {i}" for i in issues) + "\n",
        "## Warnings\n",
        "None\n" if not warnings else "\n".join(f"- {w}" for w in warnings) + "\n",
    ]
    (CORPUS / "audit_report.md").write_text("".join(report_lines), encoding="utf-8")
    log.info(f"\n✓ audit_report.md → {CORPUS}")
    log.info(
        "corpus_validate_succeeded issues=%s warnings=%s patients=%s",
        len(issues),
        len(warnings),
        len(patients),
    )


if __name__ == "__main__":
    main()
