from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    DecisionRole,
)
from insurance_intelligence.decision_support.decision_projection import (
    DecisionProjectionStatus,
    project_decision_support,
)
from insurance_intelligence.decision_support.decision_sufficiency import (
    DecisionSufficiencyStatus,
    ProductDecisionEvidence,
    evaluate_decision_sufficiency,
)
from insurance_intelligence.decision_support.dimension_alignment import (
    DimensionAlignmentStatus,
    align_assessment_to_customer_priority,
)


G2_PATH = Path(
    "docs/architecture/AR_3_0_G2_STAR_COMPREHENSIVE_DELIVERY_NEWBORN_ATOMIC_MAPPING.json"
)
G4_PATH = Path(
    "docs/architecture/AR_3_0_G4_STAR_COMPREHENSIVE_COMPARISON_READINESS_PRESSURE.json"
)
G5_PATH = Path(
    "docs/architecture/AR_3_0_G5_STAR_COMPREHENSIVE_EDUCATION_DECISION_SUPPORT_PRESSURE.json"
)

STAR = "star_health:star_comprehensive"
CONTROL = "control_insurer:control_product"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assessment(
    product: str,
    *,
    status: AssessmentStatus,
    band: AssessmentBand | None,
) -> BenefitAssessment:
    limitations = ()
    policy_id = "policy:delivery_newborn_limit_values:v1"
    policy_version = "1.0"
    if status is AssessmentStatus.NOT_SCORABLE:
        limitations = ("Governed delivery/newborn limit values remain unresolved.",)
        policy_id = None
        policy_version = None
    return BenefitAssessment(
        assessment_id=f"assessment:{product}:delivery_newborn_limit_values",
        implementation_id=f"implementation:{product}:delivery_newborn_limit_values",
        concept_id="health:delivery_newborn_limit_values",
        dimension_id="delivery_newborn_limit_values",
        decision_role=DecisionRole.CORE_PROTECTION,
        status=status,
        assessment_band=band,
        assessment_policy_id=policy_id,
        assessment_policy_version=policy_version,
        summary="Delivery/newborn limit-value assessment.",
        practical_meaning="Whether exact governed delivery/newborn limit values are available.",
        source_mechanic_ids=("mechanic:delivery_newborn_limit_values",),
        evidence_reference_ids=(f"evidence:{product}:delivery_newborn_limit_values",),
        limitations=limitations,
    )


def _alignment(product: str, *, unresolved: bool):
    assessment = _assessment(
        product,
        status=(AssessmentStatus.NOT_SCORABLE if unresolved else AssessmentStatus.ASSESSED),
        band=(None if unresolved else AssessmentBand.STRONG),
    )
    return align_assessment_to_customer_priority(
        finding_id=f"finding:{product}:delivery_newborn_limit_values",
        product_reference=product,
        assessment=assessment,
        customer_priority=None,
    )


def test_g5_is_bound_to_certified_g2_and_g4_pressure_artifacts() -> None:
    g5 = _load(G5_PATH)

    assert G2_PATH.exists()
    assert G4_PATH.exists()
    assert g5["source_g2_path"] == G2_PATH.as_posix()
    assert g5["source_g4_path"] == G4_PATH.as_posix()
    assert g5["product_reference"] == STAR
    assert g5["comparison_subject"] == "delivery_newborn"


def test_g5_education_projection_explains_known_mechanics_without_inventing_limit_values() -> None:
    g2 = _load(G2_PATH)
    g5 = _load(G5_PATH)

    known = " ".join(g5["education_projection"]["known_mechanics"]).casefold()
    propositions = " ".join(
        unit["proposition"] for unit in g2["atomic_normative_units"]
    ).casefold()

    assert g5["education_projection"]["permitted"] is True
    assert "24-month waiting period" in known
    assert "fresh 24-month waiting-period cycle" in known
    assert "pre-hospitalization" in known
    assert "post-hospitalization" in known
    assert "hospital cash benefit" in known
    assert "exact values remain unresolved" in known
    assert "24-month waiting period" in propositions
    assert "hospital cash benefit" in propositions


def test_g5_carries_material_g4_unknowns_into_explicit_user_facing_limitations() -> None:
    g4 = _load(G4_PATH)
    g5 = _load(G5_PATH)

    assert g4["readiness_assessment"]["material_residue_present"] is True
    assert g4["readiness_assessment"]["comparison_ready"] is False
    limitations = " ".join(g5["education_projection"]["required_limitations"]).casefold()
    assert "per-delivery table values" in limitations
    assert "new born liability table values" in limitations
    assert "completeness is not established" in limitations


def test_material_star_product_unknown_blocks_real_decision_sufficiency_path() -> None:
    left_unknown = _alignment(STAR, unresolved=True)
    right_known = _alignment(CONTROL, unresolved=False)
    left = ProductDecisionEvidence(product_reference=STAR, alignments=(left_unknown,))
    right = ProductDecisionEvidence(product_reference=CONTROL, alignments=(right_known,))

    sufficiency = evaluate_decision_sufficiency(
        decision_id="ar30g5:star-delivery-newborn-limit-unknown",
        left=left,
        right=right,
    )

    assert left_unknown.status is DimensionAlignmentStatus.UNRESOLVED
    assert sufficiency.status is DecisionSufficiencyStatus.BLOCKED_BY_PRODUCT_UNKNOWN
    assert sufficiency.blocking_reference_ids == (left_unknown.finding_id,)


def test_product_unknown_projects_as_action_required_and_preserves_unresolved_finding() -> None:
    left_unknown = _alignment(STAR, unresolved=True)
    right_known = _alignment(CONTROL, unresolved=False)
    left = ProductDecisionEvidence(product_reference=STAR, alignments=(left_unknown,))
    right = ProductDecisionEvidence(product_reference=CONTROL, alignments=(right_known,))
    sufficiency = evaluate_decision_sufficiency(
        decision_id="ar30g5:sufficiency",
        left=left,
        right=right,
    )

    projection = project_decision_support(
        projection_id="ar30g5:projection",
        sufficiency=sufficiency,
        left=left,
        right=right,
    )

    assert projection.status is DecisionProjectionStatus.ACTION_REQUIRED
    assert projection.left.unresolved_findings == (left_unknown,)
    assert projection.blocking_reference_ids == (left_unknown.finding_id,)
    lower = projection.decision_boundary.casefold()
    assert "does not choose" in lower
    assert "user decides" in lower


def test_g5_forbids_false_completeness_and_does_not_require_product_specific_logic() -> None:
    g5 = _load(G5_PATH)
    prohibited = {item.casefold() for item in g5["education_projection"]["prohibited_claims"]}
    result = g5["architecture_result"]
    guardrails = " ".join(g5["guardrails"]).casefold()

    assert {
        "complete section coverage",
        "comparison-ready status",
        "winner",
        "ranking",
        "recommendation",
        "net product direction",
    }.issubset(prohibited)
    assert result["new_generic_contract_required"] is False
    assert result["star_specific_runtime_logic_required"] is False
    assert result["existing_decision_sufficiency_contract_sufficient"] is True
    assert result["existing_education_first_projection_contract_sufficient"] is True
    assert "action_required" in guardrails
    assert "no unresolved limit value may be inferred" in guardrails
