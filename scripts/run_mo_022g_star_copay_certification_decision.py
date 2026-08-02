"""Create a governed non-certifying decision from completed repeat-run evidence."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from insurance_intelligence.evaluation.certification_decision import (
    CertificationDecisionPolicy,
    HumanCertificationReview,
    HumanReviewDecision,
    decide_controlled_certification,
)
from insurance_intelligence.evaluation.cross_provider_repeat_run import (
    CrossProviderRepeatRunEvidence,
    CrossProviderRunObservation,
)


DEFAULT_INPUT = Path(
    "outputs/evaluation/mo_022g_star_copay_openai_gemini_repeat_batch.json"
)
DEFAULT_OUTPUT = Path(
    "outputs/evaluation/mo_022g_star_copay_certification_decision.json"
)
APPROVED_EVIDENCE_IDS = ("ev-star-copay-reviewed-statement",)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create the governed Star copay certification decision artifact."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--reviewer-id", default="policy-governance-reviewer")
    parser.add_argument("--minimum-confidence", type=float, default=0.95)
    return parser


def _load_repeat_evidence(path: Path) -> CrossProviderRepeatRunEvidence:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("stability_evidence")
    if not isinstance(raw, dict):
        raise SystemExit("input artifact is missing stability_evidence")
    observations_raw = raw.get("observations")
    if not isinstance(observations_raw, list) or not observations_raw:
        raise SystemExit("stability_evidence is missing observations")
    observations = tuple(
        CrossProviderRunObservation(
            run_index=int(item["run_index"]),
            artifact_sha256=str(item["artifact_sha256"]),
            routing_decision=str(item["routing_decision"]),
            routing_reason_codes=tuple(item["routing_reason_codes"]),
            agreed_component_ids=tuple(item["agreed_component_ids"]),
            matched_component_ids=tuple(item["matched_component_ids"]),
            hard_failure_codes=tuple(item["hard_failure_codes"]),
            unresolved_component_ids=tuple(item["unresolved_component_ids"]),
            minimum_confidence=float(item["minimum_confidence"]),
            renderer_latency_ms=int(item["renderer_latency_ms"]),
            openai_extractor_latency_ms=int(item["openai_extractor_latency_ms"]),
            gemini_extractor_latency_ms=int(item["gemini_extractor_latency_ms"]),
        )
        for item in observations_raw
    )
    values = dict(raw)
    values["observations"] = observations
    return CrossProviderRepeatRunEvidence(**values)


def main() -> int:
    args = _parser().parse_args()
    evidence = _load_repeat_evidence(args.input)
    policy = CertificationDecisionPolicy(
        policy_id="mo-022g-controlled-certification-v1",
        minimum_confidence=args.minimum_confidence,
        require_human_approval=True,
    )
    review = HumanCertificationReview(
        reviewer_id=args.reviewer_id,
        decision=HumanReviewDecision.APPROVE,
        reviewed_evidence_ids=APPROVED_EVIDENCE_IDS,
        rationale=(
            "Approved for governed review based on exact three-run cross-provider "
            "semantic stability. Certification remains subject to all policy thresholds."
        ),
    )
    decision = decide_controlled_certification(
        evidence,
        policy=policy,
        approved_evidence_ids=APPROVED_EVIDENCE_IDS,
        human_review=review,
    )
    payload = {
        "schema_version": "1.0",
        "run_type": "MO-022G_CONTROLLED_CERTIFICATION_DECISION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_batch_path": str(args.input),
        "source_batch_id": evidence.batch_id,
        "evidence_binding_status": "APPROVED",
        "human_decision": "APPROVE_FOR_REVIEW",
        "policy": asdict(policy),
        "human_review": asdict(review),
        "decision": asdict(decision),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    print("=" * 72)
    print("MO-022G CONTROLLED CERTIFICATION DECISION")
    print("=" * 72)
    print(f"Decision              : {decision.status.value}")
    print(f"Reason codes          : {', '.join(decision.reason_codes) or 'NONE'}")
    print(f"Minimum confidence    : {evidence.minimum_observed_confidence:.2f}")
    print(f"Required confidence   : {policy.minimum_confidence:.2f}")
    print(f"Certification granted : {decision.certification_granted}")
    print(f"Output                : {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
