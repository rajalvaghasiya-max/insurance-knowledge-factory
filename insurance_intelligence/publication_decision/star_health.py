"""Star Comprehensive publication-decision pilot records (P2.3)."""

from __future__ import annotations

from insurance_intelligence.contracts.publication_decision import (
    PublicationDecisionResult,
    build_publication_decision_input,
)
from insurance_intelligence.publication_decision.evaluator import (
    evaluate_publication_decision,
)
from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.rule_certification.star_health import (
    build_star_comprehensive_conditional_copayment_case,
)
from insurance_intelligence.rule_certification.star_health_bariatric_surgery import (
    build_star_comprehensive_bariatric_surgery_case,
)
from insurance_intelligence.rule_certification.star_health_room_rent import (
    build_star_comprehensive_room_rent_case,
)

DECISION_AUTHORITY = "P2.3 governed publication decision authority"


def _certify(case, trace_reference: str):
    return run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
        trace_references=(trace_reference,),
    )


def build_star_conditional_copayment_publication_decision() -> PublicationDecisionResult:
    case = build_star_comprehensive_conditional_copayment_case()
    certification = _certify(
        case,
        "certification:star_comprehensive_conditional_copayment",
    )
    decision_input = build_publication_decision_input(
        decision_id="publication-decision:star-comprehensive:conditional-copayment",
        governed_subject_reference=certification.governed_subject_reference,
        certification_result=certification,
        requested_status="WITHHOLD",
        decision_reasons=(
            "The governed binding remains explicitly bound_not_published.",
            "Publication is withheld until that governance boundary is resolved by a later authority.",
        ),
        limitations=certification.limitations,
        evidence_trace_references=(
            "evidence:star-comprehensive-copayment:obligation_value",
            "evidence:star-comprehensive-copayment:trigger_condition",
            "evidence:star-comprehensive-copayment:applicability_scope",
            "evidence:star-comprehensive-copayment:exception_condition",
            "evidence:star-comprehensive-copayment:calculation_basis",
        ),
        decision_authority=DECISION_AUTHORITY,
    )
    return evaluate_publication_decision(decision_input)


def build_star_room_rent_publication_decision() -> PublicationDecisionResult:
    case = build_star_comprehensive_room_rent_case()
    certification = _certify(case, "certification:star_comprehensive_room_rent")
    decision_input = build_publication_decision_input(
        decision_id="publication-decision:star-comprehensive:room-rent",
        governed_subject_reference=certification.governed_subject_reference,
        certification_result=certification,
        requested_status="PUBLISH",
        decision_reasons=(
            "The governed rule certification passed with complete required semantics.",
            "Registered primary policy-wording evidence and lineage are preserved.",
        ),
        limitations=certification.limitations,
        evidence_trace_references=(
            "evidence:star-comprehensive-room-rent:covered_subject",
            "evidence:star-comprehensive-room-rent:limit_value",
            "evidence:star-comprehensive-room-rent:limit_basis",
            "evidence:star-comprehensive-room-rent:applicability_scope",
            "evidence:star-comprehensive-room-rent:excess_consequence",
        ),
        decision_authority=DECISION_AUTHORITY,
    )
    return evaluate_publication_decision(decision_input)


def build_star_bariatric_surgery_publication_decision() -> PublicationDecisionResult:
    case = build_star_comprehensive_bariatric_surgery_case()
    certification = _certify(
        case,
        "certification:star_comprehensive_bariatric_surgery",
    )
    decision_input = build_publication_decision_input(
        decision_id="publication-decision:star-comprehensive:bariatric-surgery",
        governed_subject_reference=certification.governed_subject_reference,
        certification_result=certification,
        requested_status="PUBLISH",
        decision_reasons=(
            "The governed rule certification passed with complete eligibility and consequence semantics.",
            "Registered primary policy-wording evidence and lineage are preserved.",
        ),
        limitations=certification.limitations,
        evidence_trace_references=(
            "evidence:star-comprehensive-bariatric:eligibility_criteria",
            "evidence:star-comprehensive-bariatric:applicability_scope",
            "evidence:star-comprehensive-bariatric:eligible_consequence",
            "evidence:star-comprehensive-bariatric:ineligible_consequence",
            "evidence:star-comprehensive-bariatric:exception_condition",
        ),
        decision_authority=DECISION_AUTHORITY,
    )
    return evaluate_publication_decision(decision_input)


def build_all_star_publication_decisions() -> tuple[PublicationDecisionResult, ...]:
    """Return all bounded P2.3 Star pilot decisions in stable order."""
    return (
        build_star_conditional_copayment_publication_decision(),
        build_star_room_rent_publication_decision(),
        build_star_bariatric_surgery_publication_decision(),
    )
