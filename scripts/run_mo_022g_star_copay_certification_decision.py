"""Create governed certification policy views from completed repeat-run evidence.

This command is replay-only: it consumes persisted repeat-run evidence and never
invokes an LLM provider. It emits the legacy threshold-required v1 view and the
deterministic-proof-primary v2 view from the exact same governed evidence.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from insurance_intelligence.evaluation.certification_decision import (
    CertificationConfidenceMode,
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
        description="Create governed Star copay certification policy views from persisted evidence."
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


def _policies(minimum_confidence: float) -> tuple[CertificationDecisionPolicy, CertificationDecisionPolicy]:
    return (
        CertificationDecisionPolicy(
            policy_id="mo-022g-controlled-certification-v1",
            minimum_confidence=minimum_confidence,
            require_human_approval=True,
            confidence_mode=CertificationConfidenceMode.THRESHOLD_REQUIRED,
        ),
        CertificationDecisionPolicy(
            policy_id="mo-022g-controlled-certification-v2-deterministic-proof-primary",
            minimum_confidence=minimum_confidence,
            require_human_approval=True,
            confidence_mode=CertificationConfidenceMode.DETERMINISTIC_PROOF_PRIMARY,
        ),
    )


def main() -> int:
    args = _parser().parse_args()
    evidence = _load_repeat_evidence(args.input)
    policy_v1, policy_v2 = _policies(args.minimum_confidence)
    review = HumanCertificationReview(
        reviewer_id=args.reviewer_id,
        decision=HumanReviewDecision.APPROVE,
        reviewed_evidence_ids=APPROVED_EVIDENCE_IDS,
        rationale=(
            "Approved for governed certification review based on exact three-run cross-provider "
            "semantic stability. Each policy view remains subject to its own fail-closed gates."
        ),
    )
    decision_v1 = decide_controlled_certification(
        evidence,
        policy=policy_v1,
        approved_evidence_ids=APPROVED_EVIDENCE_IDS,
        human_review=review,
    )
    decision_v2 = decide_controlled_certification(
        evidence,
        policy=policy_v2,
        approved_evidence_ids=APPROVED_EVIDENCE_IDS,
        human_review=review,
    )
    payload = {
        "schema_version": "2.0",
        "run_type": "MO-022G_CONTROLLED_CERTIFICATION_DECISION_REPLAY",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_batch_path": str(args.input),
        "source_batch_id": evidence.batch_id,
        "provider_calls_performed": 0,
        "replay_source": "PERSISTED_REPEAT_RUN_EVIDENCE",
        "evidence_binding_status": "APPROVED",
        "human_decision": "APPROVE_FOR_CERTIFICATION_REVIEW",
        "human_review": asdict(review),
        "policies": {
            "v1_threshold_required": asdict(policy_v1),
            "v2_deterministic_proof_primary": asdict(policy_v2),
        },
        "decisions": {
            "v1_threshold_required": asdict(decision_v1),
            "v2_deterministic_proof_primary": asdict(decision_v2),
        },
        # Backward-compatible aliases for consumers that expect the original v1 fields.
        "policy": asdict(policy_v1),
        "decision": asdict(decision_v1),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    print("=" * 72)
    print("MO-022G CONTROLLED CERTIFICATION DECISION REPLAY")
    print("=" * 72)
    print(f"Source batch          : {evidence.batch_id}")
    print("Provider calls        : 0")
    print(f"Minimum confidence    : {evidence.minimum_observed_confidence:.2f}")
    print(f"Required confidence   : {args.minimum_confidence:.2f}")
    print(f"V1 threshold-required : {decision_v1.status.value}")
    print(f"V1 reason codes       : {', '.join(decision_v1.reason_codes) or 'NONE'}")
    print(f"V2 proof-primary      : {decision_v2.status.value}")
    print(f"V2 reason codes       : {', '.join(decision_v2.reason_codes) or 'NONE'}")
    print(f"V2 certification      : {decision_v2.certification_granted}")
    print(f"Output                : {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
