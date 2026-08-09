"""Controlled deterministic evaluation pack for MO-024H.

The pack evaluates the governed terminology chain through the orchestration gate.
It records only deterministic READY/BLOCKED outcomes and never invokes fuzzy
matching, semantic inference, ranking, recommendation, or LLM services.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256

from insurance_intelligence.orchestration.star_comprehensive_terminology import (
    build_star_comprehensive_terminology_gate,
)
from insurance_intelligence.orchestration.terminology_gate import (
    TerminologyOrchestrationRequest,
)

STAR_VARIANT = "pv_star_health_star_comprehensive_shahlip26044v092526"


@dataclass(frozen=True)
class TerminologyEvaluationCase:
    case_id: str
    text: str
    insurer_id: str | None
    product_id: str | None
    product_variant_id: str | None
    expected_status: str
    expected_reason_codes: tuple[str, ...] = ()
    expected_concept_family_id: str | None = None


@dataclass(frozen=True)
class TerminologyEvaluationObservation:
    case_id: str
    status: str
    may_advance: bool
    reason_codes: tuple[str, ...]
    missing_context: tuple[str, ...]
    candidate_term_ids: tuple[str, ...]
    canonical_concept_family_id: str | None
    product_term_implementation_id: str | None
    fingerprint: str


@dataclass(frozen=True)
class TerminologyEvaluationReport:
    evaluation_id: str
    as_of: date
    observations: tuple[TerminologyEvaluationObservation, ...]

    @property
    def passed(self) -> bool:
        return all(
            observation.status in {"READY", "BLOCKED"}
            for observation in self.observations
        )


CONTROLLED_TERMINOLOGY_CASES = (
    TerminologyEvaluationCase(
        case_id="direct_canonical_term",
        text="Co-payment",
        insurer_id="star_health",
        product_id="star_comprehensive",
        product_variant_id=STAR_VARIANT,
        expected_status="READY",
        expected_concept_family_id="health:cost_sharing:copayment",
    ),
    TerminologyEvaluationCase(
        case_id="exact_alias_copay",
        text="Copay",
        insurer_id="star_health",
        product_id="star_comprehensive",
        product_variant_id=STAR_VARIANT,
        expected_status="READY",
        expected_concept_family_id="health:cost_sharing:copayment",
    ),
    TerminologyEvaluationCase(
        case_id="exact_alias_co_payment",
        text="Co payment",
        insurer_id="star_health",
        product_id="star_comprehensive",
        product_variant_id=STAR_VARIANT,
        expected_status="READY",
        expected_concept_family_id="health:cost_sharing:copayment",
    ),
    TerminologyEvaluationCase(
        case_id="missing_variant_context",
        text="Copay",
        insurer_id="star_health",
        product_id="star_comprehensive",
        product_variant_id=None,
        expected_status="BLOCKED",
        expected_reason_codes=("MISSING_REQUIRED_PRODUCT_CONTEXT",),
    ),
    TerminologyEvaluationCase(
        case_id="wrong_product_context",
        text="Copay",
        insurer_id="star_health",
        product_id="another_product",
        product_variant_id=STAR_VARIANT,
        expected_status="BLOCKED",
        expected_reason_codes=("NO_GOVERNED_MATCH_FOR_CONTEXT",),
    ),
    TerminologyEvaluationCase(
        case_id="unknown_punctuation_variant",
        text="co/pay",
        insurer_id="star_health",
        product_id="star_comprehensive",
        product_variant_id=STAR_VARIANT,
        expected_status="BLOCKED",
        expected_reason_codes=("NO_GOVERNED_TERM_OR_ALIAS_MATCH",),
    ),
)


def _fingerprint(*parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return sha256(payload.encode("utf-8")).hexdigest()


def run_controlled_terminology_evaluation(
    *,
    as_of: date,
    cases: tuple[TerminologyEvaluationCase, ...] = CONTROLLED_TERMINOLOGY_CASES,
) -> TerminologyEvaluationReport:
    """Run the controlled pack and fail if an observed outcome diverges."""
    gate = build_star_comprehensive_terminology_gate()
    observations = []
    for case in cases:
        result = gate.evaluate(
            TerminologyOrchestrationRequest(
                request_id=f"eval:{case.case_id}",
                text=case.text,
                insurer_id=case.insurer_id,
                product_id=case.product_id,
                product_variant_id=case.product_variant_id,
            ),
            as_of=as_of,
        )
        concept_id = result.canonical_context.get("canonical_concept_family_id")
        implementation_id = result.canonical_context.get(
            "product_term_implementation_id"
        )
        if result.status != case.expected_status:
            raise AssertionError(
                f"{case.case_id}: expected {case.expected_status}, got {result.status}"
            )
        if result.reason_codes != case.expected_reason_codes:
            raise AssertionError(
                f"{case.case_id}: expected reasons {case.expected_reason_codes}, "
                f"got {result.reason_codes}"
            )
        if concept_id != case.expected_concept_family_id:
            raise AssertionError(
                f"{case.case_id}: expected concept {case.expected_concept_family_id}, "
                f"got {concept_id}"
            )
        if result.status == "BLOCKED" and result.may_advance:
            raise AssertionError(f"{case.case_id}: blocked result may not advance")
        observations.append(
            TerminologyEvaluationObservation(
                case_id=case.case_id,
                status=result.status,
                may_advance=result.may_advance,
                reason_codes=result.reason_codes,
                missing_context=result.missing_context,
                candidate_term_ids=result.candidate_term_ids,
                canonical_concept_family_id=concept_id,
                product_term_implementation_id=implementation_id,
                fingerprint=_fingerprint(
                    case.case_id,
                    result.status,
                    result.may_advance,
                    result.reason_codes,
                    result.missing_context,
                    result.candidate_term_ids,
                    concept_id,
                    implementation_id,
                ),
            )
        )
    observations_tuple = tuple(observations)
    evaluation_id = "term-eval-" + _fingerprint(
        as_of.isoformat(),
        *(observation.fingerprint for observation in observations_tuple),
    )[:20]
    return TerminologyEvaluationReport(
        evaluation_id=evaluation_id,
        as_of=as_of,
        observations=observations_tuple,
    )


__all__ = [
    "CONTROLLED_TERMINOLOGY_CASES",
    "STAR_VARIANT",
    "TerminologyEvaluationCase",
    "TerminologyEvaluationObservation",
    "TerminologyEvaluationReport",
    "run_controlled_terminology_evaluation",
]
