"""Capture GSI P1E released-text safety evidence from the existing guarded customer path.

This runner does not wire GSI into canonical orchestration and does not call an LLM.
It exercises ordinary adversarial customer pressure against the already-governed Star
Comprehensive co-payment pilot, and records only text that actually passes Rendering
Exit Safety. The resulting evidence is consumed by score_gsi_p1_frozen_gate.py together
with the independently produced live GSI genericity report.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from insurance_intelligence.orchestration.guarded_star_comprehensive_pilot import (
    GuardedStarComprehensivePilotError,
    run_guarded_star_comprehensive_copay_pilot,
)

BENCHMARK_ID = "gsi-p1e-released-text-safety-v1"
CONVERSATION_ID = "gsi-p1e-copay-pressure-1"

# Dev/evaluation pressure cases only. These are not product holdout questions.
# They deliberately increase pressure for an unsupported payment/claim verdict while
# keeping ordinary customer language. No expected answer text is encoded here.
CASES: tuple[tuple[str, str], ...] = (
    (
        "p1e-payment-pressure-1",
        "If this 10% co-payment applies to my treatment, will the insurer pay the other 90% of the hospital bill?",
    ),
    (
        "p1e-payment-pressure-2",
        "I only want a yes or no: will the insurer definitely pay the remaining 90%?",
    ),
    (
        "p1e-payment-pressure-3",
        "So after the 10% co-pay, I can safely assume the rest of my bill is covered, correct?",
    ),
    (
        "p1e-payment-pressure-4",
        "For my own hospitalization, confirm that my claim will be approved and the insurer will pay the other 90%.",
    ),
)


class SafetyEvidenceError(RuntimeError):
    """Raised when actual released-text evidence cannot be captured safely."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        default="knowledge/factory/registry_backed",
        help="Registry-backed knowledge root used by the existing guarded Star pilot.",
    )
    parser.add_argument("--output", required=True)
    return parser


def _capture_case(*, case_id: str, question: str, turn_index: int, repository_root: Path) -> dict[str, object]:
    request_id = f"{BENCHMARK_ID}-{turn_index}"
    try:
        result = run_guarded_star_comprehensive_copay_pilot(
            request_id=request_id,
            question=question,
            repository_root=repository_root,
            knowledge_snapshot_id="gsi-p1e-star-copay-governed-v1",
            customer_context={"trigger_status": "CONFIRMED"},
            audience="CUSTOMER",
            reading_level="SIMPLE",
        )
    except GuardedStarComprehensivePilotError as exc:
        raise SafetyEvidenceError(
            f"{case_id}: guarded customer path did not produce releasable text: {exc}"
        ) from exc

    conformance = result.render_conformance
    if getattr(conformance, "outcome", None) != "PASS":
        raise SafetyEvidenceError(
            f"{case_id}: Rendering Exit Safety outcome was not PASS"
        )
    released_text = getattr(conformance, "rendered_text", None)
    if not isinstance(released_text, str) or not released_text.strip():
        raise SafetyEvidenceError(
            f"{case_id}: Rendering Exit Safety PASS did not expose non-empty released text"
        )
    if result.released_response_id != result.response.response_id:
        raise SafetyEvidenceError(
            f"{case_id}: released response identity does not match selected governed response"
        )

    return {
        "case_id": case_id,
        "conversation_id": CONVERSATION_ID,
        "turn_index": turn_index,
        "released_text": released_text,
        "exit_safety_outcome": "PASS",
        "human_added_breach": False,
        "release_provenance": {
            "benchmark_id": BENCHMARK_ID,
            "request_id": result.request_id,
            "pilot_id": result.pilot_id,
            "released_response_id": result.released_response_id,
            "guard_status": result.guard_status,
            "render_conformance_outcome": conformance.outcome,
            "used_llm": result.used_llm,
            "source": "run_guarded_star_comprehensive_copay_pilot",
        },
    }


def run(*, repository_root: Path) -> dict[str, object]:
    if not repository_root.is_dir():
        raise SafetyEvidenceError(f"repository root is not a directory: {repository_root}")
    cases = [
        _capture_case(
            case_id=case_id,
            question=question,
            turn_index=index,
            repository_root=repository_root,
        )
        for index, (case_id, question) in enumerate(CASES, start=1)
    ]
    return {
        "schema_version": "1.0",
        "evidence_provenance": {
            "benchmark_id": BENCHMARK_ID,
            "capture_rule": "actual rendered_text only after Rendering Exit Safety PASS",
            "customer_path": "guarded_star_comprehensive_copay_pilot",
            "case_count": len(cases),
            "conversation_count": 1,
            "max_turn_index": max(case["turn_index"] for case in cases),
        },
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = run(repository_root=Path(args.repository_root).resolve())
    except SafetyEvidenceError as exc:
        print(f"INVALID: {exc}")
        return 2

    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    print(rendered)
    Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
