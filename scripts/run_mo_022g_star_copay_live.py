"""Run one governed MO-022G live certification case for Star conditional copayment.

The script performs exactly one renderer call and one extractor call, then applies
the deterministic semantic fidelity gate. Generated artifacts are written locally
under outputs/evaluation and are not certification decisions by themselves.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from insurance_intelligence.contracts.semantic_fidelity import (
    CanonicalSemanticComponent,
    ExplanationSemanticContract,
    FidelityRoutingPolicy,
    SemanticAttribute,
    SemanticKind,
    SemanticRiskTier,
)
from insurance_intelligence.llm.openai_component_locked import (
    OpenAIComponentLockedProvider,
    OpenAIComponentLockedResult,
)


SECTIONS = (
    "II.1", "II.2", "II.3", "II.4", "II.5", "II.6", "II.7",
    "II.8", "II.9", "II.10", "II.11", "II.15", "II.25",
)
DEFAULT_OUTPUT = Path("outputs/evaluation/mo_022g_star_copay_live.json")


def _component(
    component_id: str,
    kind: SemanticKind,
    risk_tier: SemanticRiskTier,
    **attributes: object,
) -> CanonicalSemanticComponent:
    return CanonicalSemanticComponent(
        component_id=component_id,
        kind=kind,
        risk_tier=risk_tier,
        attributes=tuple(
            SemanticAttribute(name=name, value=value) for name, value in attributes.items()
        ),
        evidence_ids=("ev-star-copay-reviewed-statement",),
    )


def build_star_copay_contract() -> ExplanationSemanticContract:
    """Build the governed canonical contract used by the live certification case."""
    return ExplanationSemanticContract(
        contract_id="contract-star-comprehensive-conditional-copay-v1",
        contract_version="1.0.0",
        rule_family="CONDITIONAL_COPAYMENT",
        components=(
            _component(
                "entry-age-trigger",
                SemanticKind.TRIGGER,
                SemanticRiskTier.RULE_LOGIC,
                subject="insured_person",
                attribute="age_at_entry",
                operator=">=",
                value=61,
            ),
            _component(
                "copay-effect",
                SemanticKind.EFFECT,
                SemanticRiskTier.EXACT_VALUE,
                effect_type="copayment",
                percentage=10,
                claim_scope="each_and_every_claim",
            ),
            _component(
                "continuous-renewal-exception",
                SemanticKind.EXCEPTION,
                SemanticRiskTier.RULE_LOGIC,
                age_operator="<",
                age_value=61,
                continuous_renewal=True,
                policy_break=False,
                logical_operator="AND",
            ),
            _component(
                "applicability-scope",
                SemanticKind.APPLICABILITY_SCOPE,
                SemanticRiskTier.EXACT_VALUE,
                mode="exact_set",
                sections=SECTIONS,
            ),
        ),
        approved_finding_ids=("finding-star-conditional-copay",),
        prohibited_operations=(
            "ADD_FACT",
            "REMOVE_FACT",
            "INFER_FACT",
            "GENERALISE_SCOPE",
            "NARROW_SCOPE",
            "CHANGE_NUMBER",
            "CHANGE_OPERATOR",
            "CHANGE_CERTAINTY",
        ),
    )


def build_live_policy() -> FidelityRoutingPolicy:
    return FidelityRoutingPolicy(
        policy_id="mo-022g-live-certification-v1",
        minimum_confidence=0.95,
        minimum_extractor_agreement=0.95,
        require_certified_rule_family=True,
    )


def result_payload(result: OpenAIComponentLockedResult) -> dict[str, object]:
    outcome = result.outcome
    return {
        "schema_version": "1.0",
        "run_type": "MO-022G_CONTROLLED_LIVE_CERTIFICATION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "certification_effect": "NONE",
        "renderer_trace": asdict(result.rendering_trace),
        "extractor_trace": asdict(result.extraction_trace),
        "semantic_report": asdict(outcome.fidelity_report),
        "routing_result": asdict(outcome.routing_result),
        "human_review_packet": (
            asdict(outcome.human_review_packet)
            if outcome.human_review_packet is not None
            else None
        ),
        "verified_explanation": (
            asdict(outcome.verified_explanation)
            if outcome.verified_explanation is not None
            else None
        ),
    }


def write_result(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one governed MO-022G Star copayment live certification case."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audience", default="customer")
    parser.add_argument("--reading-level", default="plain_language")
    return parser


def main() -> int:
    args = _parser().parse_args()
    provider = OpenAIComponentLockedProvider.from_environment()
    result = provider.evaluate(
        build_star_copay_contract(),
        audience=args.audience,
        reading_level=args.reading_level,
        policy=build_live_policy(),
        certification=None,
    )
    payload = result_payload(result)
    write_result(args.output, payload)

    routing = result.outcome.routing_result
    print("=" * 72)
    print("MO-022G STAR COPAY CONTROLLED LIVE RUN")
    print("=" * 72)
    print(f"Routing decision : {routing.decision.value}")
    print(f"Reason codes     : {', '.join(routing.reason_codes)}")
    print(f"Renderer latency : {result.rendering_trace.latency_ms} ms")
    print(f"Extractor latency: {result.extraction_trace.latency_ms} ms")
    print(f"Output            : {args.output}")
    print("Certification     : NOT GRANTED BY THIS RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
