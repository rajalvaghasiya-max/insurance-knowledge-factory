from __future__ import annotations

from knowledge_domains.health.concept_knowledge.governed_concept_to_meaning_asset import (
    GovernedConceptToMeaningAssetAdapter,
)
from knowledge_domains.health.concept_knowledge.governed_generic_concept_record import (
    GovernedGenericConceptRecordContract,
)


def _governed_waiting_period_record() -> dict:
    """Third-concept fixture: all education meaning is supplied as governed data."""
    return GovernedGenericConceptRecordContract.create_record(
        concept_id="waiting_period",
        concept_name="Waiting Period",
        domain="health_insurance",
        definition=(
            "A waiting period is a policy-defined period during which a specified "
            "coverage restriction applies to the relevant illness, treatment, or benefit."
        ),
        plain_language_explanation=(
            "Some parts of a health policy do not become available immediately. "
            "The applicable policy wording determines what is restricted, for how long, "
            "when the period starts, and which exceptions or continuity rules apply."
        ),
        practical_implication=(
            "A customer must identify the specific waiting-period clause that applies "
            "before deciding whether that restriction affects a particular situation."
        ),
        simple_example={
            "scenario": (
                "A policy contains a waiting-period clause for a specified condition."
            ),
            "illustration": (
                "During the applicable period, that waiting-period restriction can still "
                "apply to the specified condition."
            ),
            "boundary": (
                "Illustrative only. This does not determine claim approval, claim payment, "
                "or an exact calendar boundary unless those facts are separately governed."
            ),
        },
        common_misunderstandings=[
            (
                "A waiting period does not mean every claim under the policy is blocked "
                "during that period."
            ),
            (
                "Completing one waiting period does not establish that every other policy "
                "condition or exclusion has been satisfied."
            ),
        ],
        limitations=[
            (
                "This generic concept record does not state any insurer-specific or "
                "product-specific waiting-period duration."
            ),
            (
                "It does not determine customer-specific eligibility, claim approval, "
                "claim payment, or an exact boundary convention."
            ),
        ],
        product_specific_boundary=(
            "Duration, start basis, affected condition or benefit, exceptions, continuity "
            "credit, and other mechanics must come from governed product knowledge."
        ),
        customer_document_boundary=(
            "Customer-specific selections, policy dates, continuity history, endorsements, "
            "and schedule-dependent terms must be verified from applicable customer documents."
        ),
        related_concepts=[
            "initial_waiting_period",
            "pre_existing_disease_waiting_period",
            "specified_disease_waiting_period",
            "continuity_benefit",
        ],
        source_evidence=[
            {
                "evidence_id": "waiting_period_generic_education_fixture_v1",
                "source_type": "approved_training_material",
                "source_title": "Reviewed generic waiting-period education fixture",
                "publisher": "PolicyScna test governance",
                "source_locator": "test://waiting-period-generic-education",
                "source_sha256": "b" * 64,
                "evidence_text": (
                    "Reviewed generic education evidence for waiting-period concept "
                    "falsification only."
                ),
                "evidence_scope": "generic_insurance_concept",
            }
        ],
        review_decision={
            "review_decision_id": "review_waiting_period_genericity_falsification_v1",
            "decision": "approve_for_governed_generic_concept_creation",
            "reviewer_identity": "test-reviewer",
            "reviewed_at": "2026-09-20T00:00:00Z",
            "rationale": (
                "Approved only as a governed third-concept fixture to falsify whether "
                "the education adapter is data-driven rather than concept-branch driven."
            ),
        },
        knowledge_version="falsification-v1",
        created_by="test",
        created_at="2026-09-20T00:00:00Z",
        factory_signature={
            "factory": "PolicyScna Knowledge Factory",
            "engine_version": "0.2",
            "rules_version": "governed_generic_concept_rules_v0.2",
            "schema_version": "0.2",
            "deterministic": True,
        },
    )


def test_third_governed_concept_reaches_meaning_asset_without_adapter_tuning() -> None:
    """A governed third concept must not require a new concept_id runtime branch."""
    record = _governed_waiting_period_record()

    asset = GovernedConceptToMeaningAssetAdapter.build(record)

    assert asset["concept_id"] == "waiting_period"
    assert asset["canonical_name"] == "Waiting Period"
    assert asset["core_meaning"] == record["definition"]
    assert asset["functional_behaviour"] == record["plain_language_explanation"]
    assert asset["business_purpose"] == record["practical_implication"]
    assert asset["evidence_refs"] == [
        "waiting_period_generic_education_fixture_v1"
    ]
    assert asset["policy_examples"]
    assert asset["policy_examples"][0]["source_example"] == record["simple_example"]

    rendered = str(asset["policy_examples"]).lower()
    assert "claim approval" in rendered
    assert "claim payment" in rendered
    assert "exact calendar boundary" in rendered
