from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from insurance_intelligence.benefits.contracts import (
    BenefitAvailability,
    BenefitConcept,
    BenefitContractError,
    BenefitEvidenceReference,
    BenefitImplementationType,
    BenefitMechanic,
    MechanicValueType,
    ProductBenefitImplementation,
    PublicationStatus,
    ReviewStatus,
)


AS_OF = date(2026, 7, 31)
SHA = "a" * 64


def _evidence() -> BenefitEvidenceReference:
    return BenefitEvidenceReference(
        evidence_reference_id="evidence:star:restore:policy-wording",
        source_document_id="document:star-comprehensive:policy-wording",
        source_sha256=SHA,
        authority_type="POLICY_WORDING",
        evidence_locator="page 22",
        canonical_fact_id="cfact_restore_1",
        governed_fact_id="gfact_restore_1",
        review_decision_id="review_restore_1",
    )


def _concept(**overrides: object) -> BenefitConcept:
    values = {
        "concept_id": "health:coverage_capacity:restoration_benefit",
        "canonical_name": "Restoration of sum insured",
        "definition": "Replenishment of available sum insured under governed product conditions.",
        "benefit_family": "coverage_capacity",
        "allowed_mechanic_dimensions": (
            "restoration_count",
            "exhaustion_requirement",
            "same_claim_use",
        ),
        "review_status": ReviewStatus.APPROVED,
        "publication_status": PublicationStatus.PUBLISHED,
        "effective_from": date(2026, 1, 1),
    }
    values.update(overrides)
    return BenefitConcept(**values)


def _implementation(**overrides: object) -> ProductBenefitImplementation:
    evidence = _evidence()
    values = {
        "implementation_id": "implementation:star:star-comprehensive:restoration",
        "concept_id": "health:coverage_capacity:restoration_benefit",
        "insurer_id": "star_health",
        "product_id": "star_comprehensive",
        "product_variant_id": "pv_star_health_star_comprehensive_shahlip26044v092526",
        "marketing_name": "Automatic Restoration",
        "availability": BenefitAvailability.INCLUDED,
        "implementation_type": BenefitImplementationType.BUILT_IN,
        "mechanics": (
            BenefitMechanic(
                dimension_id="restoration_count",
                value_type=MechanicValueType.INTEGER,
                value=1,
                evidence_reference_ids=(evidence.evidence_reference_id,),
            ),
            BenefitMechanic(
                dimension_id="exhaustion_requirement",
                value_type=MechanicValueType.ENUM,
                value="FULL_EXHAUSTION",
                evidence_reference_ids=(evidence.evidence_reference_id,),
            ),
            BenefitMechanic(
                dimension_id="same_claim_use",
                value_type=MechanicValueType.BOOLEAN,
                value=False,
                evidence_reference_ids=(evidence.evidence_reference_id,),
            ),
        ),
        "evidence_references": (evidence,),
        "behaviour_signature_id": "ga_star_restore_once_after_full_exhaustion_v1",
        "conditions": ("Base sum insured must be exhausted.",),
        "limitations": ("Use is subject to the governed policy wording.",),
        "exclusions": (),
        "review_status": ReviewStatus.APPROVED,
        "publication_status": PublicationStatus.PUBLISHED,
        "effective_from": date(2026, 1, 1),
    }
    values.update(overrides)
    return ProductBenefitImplementation(**values)


def test_governed_concept_and_implementation_validate_together() -> None:
    concept = _concept()
    implementation = _implementation()

    implementation.validate_against(concept)

    assert concept.is_governed_for_use is True
    assert implementation.is_governed_for_use is True
    assert concept.is_active(AS_OF) is True
    assert implementation.is_active(AS_OF) is True


def test_mechanics_preserve_typed_dimensions_and_evidence_lineage() -> None:
    implementation = _implementation()

    assert implementation.mechanics[0].dimension_id == "restoration_count"
    assert implementation.mechanics[0].value == 1
    assert implementation.mechanics[0].evidence_reference_ids == (
        "evidence:star:restore:policy-wording",
    )
    assert implementation.evidence_references[0].canonical_fact_id == "cfact_restore_1"


def test_contracts_are_immutable() -> None:
    concept = _concept()
    implementation = _implementation()

    with pytest.raises(FrozenInstanceError):
        concept.canonical_name = "Changed"
    with pytest.raises(FrozenInstanceError):
        implementation.marketing_name = "Changed"
    with pytest.raises(TypeError):
        implementation.mechanics[0].applicability["scope"] = "changed"


def test_unknown_mechanic_dimension_is_rejected_against_concept() -> None:
    evidence = _evidence()
    implementation = _implementation(
        mechanics=(
            BenefitMechanic(
                dimension_id="carry_forward",
                value_type=MechanicValueType.BOOLEAN,
                value=False,
                evidence_reference_ids=(evidence.evidence_reference_id,),
            ),
        )
    )

    with pytest.raises(BenefitContractError, match="not allowed"):
        implementation.validate_against(_concept())


def test_unknown_evidence_reference_is_rejected() -> None:
    with pytest.raises(BenefitContractError, match="unknown evidence"):
        _implementation(
            mechanics=(
                BenefitMechanic(
                    dimension_id="restoration_count",
                    value_type=MechanicValueType.INTEGER,
                    value=1,
                    evidence_reference_ids=("evidence:missing",),
                ),
            )
        )


def test_evidence_requires_governed_lineage_identifier() -> None:
    with pytest.raises(BenefitContractError, match="governed lineage"):
        BenefitEvidenceReference(
            evidence_reference_id="evidence:no-lineage",
            source_document_id="document:test",
            source_sha256=SHA,
            authority_type="POLICY_WORDING",
            evidence_locator="page 1",
        )


def test_invalid_typed_mechanic_value_is_rejected() -> None:
    with pytest.raises(BenefitContractError, match="BOOLEAN"):
        BenefitMechanic(
            dimension_id="same_claim_use",
            value_type=MechanicValueType.BOOLEAN,
            value="no",
            evidence_reference_ids=("evidence:test",),
        )


def test_not_available_requires_not_applicable_implementation_type() -> None:
    with pytest.raises(BenefitContractError, match="NOT_APPLICABLE"):
        _implementation(
            availability=BenefitAvailability.NOT_AVAILABLE,
            implementation_type=BenefitImplementationType.BUILT_IN,
        )


def test_unpublished_or_unapproved_records_are_not_governed_for_use() -> None:
    assert _concept(publication_status=PublicationStatus.NOT_PUBLISHED).is_governed_for_use is False
    assert _implementation(review_status=ReviewStatus.REVIEWED).is_governed_for_use is False


def test_effective_date_range_is_fail_closed() -> None:
    concept = _concept(effective_to=date(2026, 6, 30))
    implementation = _implementation(effective_to=date(2026, 6, 30))

    assert concept.is_active(AS_OF) is False
    assert implementation.is_active(AS_OF) is False


def test_invalid_effective_date_range_is_rejected() -> None:
    with pytest.raises(BenefitContractError, match="effective_to"):
        _concept(effective_from=date(2026, 7, 1), effective_to=date(2026, 6, 30))


def test_duplicate_mechanic_dimensions_are_rejected() -> None:
    evidence = _evidence()
    mechanic = BenefitMechanic(
        dimension_id="restoration_count",
        value_type=MechanicValueType.INTEGER,
        value=1,
        evidence_reference_ids=(evidence.evidence_reference_id,),
    )
    with pytest.raises(BenefitContractError, match="duplicate dimension"):
        _implementation(mechanics=(mechanic, mechanic))
