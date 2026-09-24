from __future__ import annotations

from pathlib import Path

from insurance_intelligence.contracts.education_publication import (
    CUSTOMER_EDUCATION,
    EDUCATION_PUBLICATION_STATUS,
    EducationExample,
    EducationPublicationRecord,
)
from insurance_intelligence.contracts.explanation import (
    build_practical_illustration_profile,
    build_section,
)
from insurance_intelligence.contracts.reasoning import build_finding
from insurance_intelligence.contracts.response import build_section as build_response_section
from insurance_intelligence.contracts.semantic import build_governed_semantic_attribute
from insurance_intelligence.explanation.education import (
    render_practical_illustration_sections,
)


def _education(concept_id: str = "benefit_hold_period") -> EducationPublicationRecord:
    return EducationPublicationRecord(
        contract_version="1.0",
        publication_id="education-benefit-hold-period",
        publication_status=EDUCATION_PUBLICATION_STATUS,
        allowed_uses=(CUSTOMER_EDUCATION,),
        concept_id=concept_id,
        canonical_name="Benefit Hold Period",
        definition="A reviewed generic definition.",
        plain_language_explanation="A reviewed plain explanation.",
        practical_implication="A product rule may restrict a related event for a period.",
        examples=(
            EducationExample(
                scenario="A generic reviewed scenario.",
                result="A generic reviewed result.",
                boundary="Illustrative only.",
            ),
        ),
        limitations=("Generic education only.",),
        product_specific_boundary="Product mechanics require governed product evidence.",
        customer_document_boundary="Customer facts require applicable documents.",
        evidence_references=("education-evidence-1",),
        source_asset_id="meaning-benefit-hold",
        source_asset_digest="a" * 64,
        source_governed_record_id="gconcept-benefit-hold",
        source_knowledge_version="1.0",
        review_decision_id="review-benefit-hold",
        publication_authority="PolicyScna education publication authority",
        publication_receipt_id="education_receipt_1234567890abcdef1234",
    )


def _finding(*, duration: int = 12, unit: str = "MONTHS"):
    evidence_id = "product-evidence-duration"
    return build_finding(
        finding_id="finding-duration",
        requirement_id="requirement-duration",
        finding_type="DOCUMENTED_FACT",
        subject="generic:product",
        predicate="documents",
        object_or_effect=f"The governed duration is {duration} {unit}.",
        scope="generic:product",
        finding_status="SUPPORTED",
        derivation_type="DIRECT_FACT",
        rule_id="direct_documented_fact_v1",
        rule_version="1.0",
        evidence_ids=(evidence_id,),
        semantic_attributes=(
            build_governed_semantic_attribute(
                key="duration_value",
                value=str(duration),
                evidence_references=(evidence_id,),
            ),
            build_governed_semantic_attribute(
                key="duration_unit",
                value=unit,
                evidence_references=(evidence_id,),
            ),
            build_governed_semantic_attribute(
                key="answer_role",
                value="PRIMARY",
                evidence_references=(evidence_id,),
            ),
        ),
        confidence=1.0,
    )


def _profile(*, before: int = 4, after: int = 18):
    return build_practical_illustration_profile(
        profile_id="profile-benefit-hold-v1",
        concept_id="benefit_hold_period",
        duration_unit="MONTHS",
        before_probe_value=before,
        after_probe_value=after,
        related_condition="Condition Alpha",
        unrelated_condition="Condition Beta",
        during_wait_template=(
            "At month {before_probe_value}, the restriction for {related_condition} "
            "is still within the {duration_value} {duration_unit_lower} period"
        ),
        unrelated_condition_template=(
            "The restriction for {related_condition} does not by itself block "
            "{unrelated_condition}; other product terms still apply"
        ),
        after_wait_template=(
            "At month {after_probe_value}, the {duration_value} {duration_unit_lower} "
            "restriction has been completed for {related_condition} on that basis; "
            "other product terms still apply"
        ),
        boundary_text=(
            "This is an illustration using reviewed probe values, not a claim-payment promise"
        ),
    )


def test_practical_illustration_contract_supports_dual_governed_lineage() -> None:
    section = build_section(
        section_id="illustration-1",
        section_type="PRACTICAL_ILLUSTRATION",
        status="DRAFTED",
        text="Illustrative governed product scenario.",
        approved_finding_ids=("finding-duration",),
        evidence_ids=("evidence-duration",),
        education_publication_ids=("education-benefit-hold-period",),
    )

    assert section.approved_finding_ids == ("finding-duration",)
    assert section.evidence_ids == ("evidence-duration",)
    assert section.education_publication_ids == ("education-benefit-hold-period",)


def test_generic_composer_uses_typed_duration_and_reviewed_profile_without_topic_branch() -> None:
    finding = _finding()
    sections = render_practical_illustration_sections(
        request_id="request-1",
        profiles=(_profile(),),
        publications=(_education(),),
        approved_finding_ids=(finding.finding_id,),
        findings_by_id={finding.finding_id: finding},
    )

    assert len(sections) == 1
    section = sections[0]
    assert section.section_type == "PRACTICAL_ILLUSTRATION"
    assert section.approved_finding_ids == (finding.finding_id,)
    assert section.evidence_ids == finding.evidence_ids
    assert section.education_publication_ids == ("education-benefit-hold-period",)
    assert "month 4" in section.text
    assert "12 months" in section.text
    assert "month 18" in section.text
    assert "Condition Alpha" in section.text
    assert "Condition Beta" in section.text


def test_generic_composer_omits_when_reviewed_probes_do_not_bracket_duration() -> None:
    finding = _finding(duration=12)
    sections = render_practical_illustration_sections(
        request_id="request-1",
        profiles=(_profile(before=12, after=18),),
        publications=(_education(),),
        approved_finding_ids=(finding.finding_id,),
        findings_by_id={finding.finding_id: finding},
    )

    assert sections == ()


def test_response_contract_preserves_practical_illustration_dual_lineage() -> None:
    section = build_response_section(
        section_id="response-illustration-1",
        section_type="PRACTICAL_ILLUSTRATION",
        status="INCLUDED",
        text="Illustrative governed product scenario.",
        explanation_section_ids=("illustration-1",),
        approved_finding_ids=("finding-duration",),
        evidence_reference_ids=("ref-duration",),
        education_publication_ids=("education-benefit-hold-period",),
    )

    assert section.section_type == "PRACTICAL_ILLUSTRATION"
    assert section.education_publication_ids == ("education-benefit-hold-period",)


def test_runtime_composer_contains_no_case_a_product_or_example_constants() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "insurance_intelligence/explanation/education.py"
    ).read_text(encoding="utf-8").lower()

    for forbidden in ("star comprehensive", "pre_existing_disease", "ear condition", "dengue"):
        assert forbidden not in source
