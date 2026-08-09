from __future__ import annotations

from datetime import date

import pytest

from insurance_intelligence.generic_knowledge.contracts import (
    AccountingState,
    ApplicabilityKey,
    EvidenceReference,
    GenericKnowledgeContractError,
    NormativeUnit,
    NormativeUnitKind,
    PublicationBlockerCode,
    RelationshipFact,
    RelationshipType,
    ResidueRecord,
    SemanticFact,
    blocker_for_residue,
)


def _applicability() -> ApplicabilityKey:
    return ApplicabilityKey(
        product_reference="pv_example_product_v1",
        policy_version="v1",
        variant="base",
        zone="all",
        sum_insured_band="all",
        optional_cover_state="base",
        effective_from=date(2026, 1, 1),
    )


def _evidence() -> EvidenceReference:
    return EvidenceReference(
        evidence_id="ev_1",
        source_document_id="doc_1",
        source_document_version="docver_1",
        source_hash_sha256="abc123",
        locator="page:10",
        authority_class="POLICY_WORDING",
    )


def test_applicability_is_product_data_not_product_logic() -> None:
    key = _applicability()
    assert key.product_reference == "pv_example_product_v1"
    assert key.effective_from == date(2026, 1, 1)


def test_applicability_rejects_invalid_date_range() -> None:
    with pytest.raises(GenericKnowledgeContractError):
        ApplicabilityKey(
            product_reference="pv_example_product_v1",
            effective_from=date(2026, 2, 1),
            effective_to=date(2026, 1, 1),
        )


def test_normative_unit_requires_source_anchored_material_consequence() -> None:
    unit = NormativeUnit(
        normative_unit_id="nu_1",
        concept="waiting_periods",
        kind=NormativeUnitKind.EXCEPTION,
        text_sha256="hash",
        excerpt="PED waiting period does not apply to this benefit.",
        applicability=_applicability(),
        evidence=_evidence(),
        materially_affects=("waiver", "applicability"),
    )
    assert "waiver" in unit.materially_affects


def test_normative_unit_rejects_empty_materiality() -> None:
    with pytest.raises(GenericKnowledgeContractError):
        NormativeUnit(
            normative_unit_id="nu_1",
            concept="waiting_periods",
            kind=NormativeUnitKind.CONDITION,
            text_sha256="hash",
            excerpt="text",
            applicability=_applicability(),
            evidence=_evidence(),
            materially_affects=(),
        )


def test_semantic_fact_is_generic_and_evidence_backed() -> None:
    fact = SemanticFact(
        fact_id="fact_1",
        concept="waiting_periods",
        semantic_type="PRE_EXISTING_DISEASE",
        value={"duration_value": 36, "duration_unit": "MONTHS"},
        applicability=_applicability(),
        evidence_ids=("ev_1",),
        ontology_version="waiting_periods_v1",
    )
    assert fact.value["duration_value"] == 36


def test_relationship_fact_governs_benefit_scoped_waiver() -> None:
    relationship = RelationshipFact(
        relationship_id="rel_1",
        source_concept="chronic_care",
        relationship_type=RelationshipType.WAIVES,
        target_concept="waiting_periods.PRE_EXISTING_DISEASE",
        condition={"listed_conditions_only": True},
        applicability=_applicability(),
        evidence_ids=("ev_1",),
        ontology_version="relationships_v1",
    )
    assert relationship.relationship_type is RelationshipType.WAIVES
    assert relationship.condition["listed_conditions_only"] is True


def test_material_not_yet_representable_residue_blocks_only_its_applicability_unit() -> None:
    residue = ResidueRecord(
        residue_id="res_1",
        normative_unit_id="nu_1",
        concept="waiting_periods.SPECIFIC_DISEASE_PROCEDURE",
        applicability=_applicability(),
        accounting_state=AccountingState.NOT_YET_REPRESENTABLE,
        reason="Source contains a conditional carve-out the ontology cannot yet represent.",
        material=True,
    )
    blocker = blocker_for_residue(residue)
    assert blocker is not None
    assert blocker.code is PublicationBlockerCode.NOT_YET_REPRESENTABLE
    assert blocker.applicability == residue.applicability
    assert blocker.normative_unit_ids == ("nu_1",)


def test_conflicted_material_residue_maps_to_authority_conflict_blocker() -> None:
    residue = ResidueRecord(
        residue_id="res_2",
        normative_unit_id="nu_2",
        concept="waiting_periods.PRE_EXISTING_DISEASE",
        applicability=_applicability(),
        accounting_state=AccountingState.CONFLICTED,
        reason="Equal-authority sources disagree.",
        material=True,
    )
    blocker = blocker_for_residue(residue)
    assert blocker is not None
    assert blocker.code is PublicationBlockerCode.AUTHORITY_CONFLICT


def test_fully_mapped_material_unit_does_not_block_publication() -> None:
    residue = ResidueRecord(
        residue_id="res_3",
        normative_unit_id="nu_3",
        concept="waiting_periods.INITIAL",
        applicability=_applicability(),
        accounting_state=AccountingState.MAPPED,
        reason="Mapped to governed semantic fact.",
        material=True,
    )
    assert blocker_for_residue(residue) is None


def test_non_material_deferred_unit_does_not_block_publication() -> None:
    residue = ResidueRecord(
        residue_id="res_4",
        normative_unit_id="nu_4",
        concept="waiting_periods",
        applicability=_applicability(),
        accounting_state=AccountingState.DEFERRED_WITH_REASON,
        reason="Editorial explanatory text, not normative insurance content.",
        material=False,
    )
    assert blocker_for_residue(residue) is None


def test_empty_product_reference_fails_closed() -> None:
    with pytest.raises(GenericKnowledgeContractError):
        ApplicabilityKey(product_reference="   ")
