from __future__ import annotations

from datetime import date

import pytest

from insurance_intelligence.generic_knowledge.contracts import (
    AccountingState,
    ApplicabilityKey,
    EvidenceReference,
    NormativeUnit,
    NormativeUnitKind,
    PublicationBlockerCode,
    RelationshipFact,
    RelationshipType,
    SemanticFact,
)
from insurance_intelligence.generic_knowledge.normative_inventory import (
    InventoryAccountingDecision,
    InventoryReviewStatus,
    NormativeInventory,
    NormativeInventoryError,
    account_normative_inventory,
)


def _app(*, optional_cover_state: str | None = None) -> ApplicabilityKey:
    return ApplicabilityKey(
        product_reference="pv_demo_product",
        policy_version="v1",
        optional_cover_state=optional_cover_state,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
    )


def _evidence(evidence_id: str = "ev_1") -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        source_document_id="doc_1",
        source_document_version="docv_1",
        source_hash_sha256="abc123",
        locator="page:10",
        authority_class="POLICY_WORDING",
    )


def _unit(
    unit_id: str = "nu_1",
    *,
    kind: NormativeUnitKind = NormativeUnitKind.CONDITION,
    applicability: ApplicabilityKey | None = None,
    evidence: EvidenceReference | None = None,
) -> NormativeUnit:
    return NormativeUnit(
        normative_unit_id=unit_id,
        concept="waiting_periods",
        kind=kind,
        text_sha256=f"hash_{unit_id}",
        excerpt="Normative waiting-period clause",
        applicability=applicability or _app(),
        evidence=evidence or _evidence(),
        materially_affects=("duration",),
    )


def _inventory(*units: NormativeUnit) -> NormativeInventory:
    return NormativeInventory(
        concept="waiting_periods",
        inventory_method="independent_high_recall_v1",
        inventory_version="1.0",
        review_status=InventoryReviewStatus.REVIEWED,
        units=units or (_unit(),),
    )


def test_missing_accounting_decision_becomes_material_blocking_residue() -> None:
    result = account_normative_inventory(_inventory(_unit()), decisions=())

    assert result.publishable is False
    assert len(result.residues) == 1
    assert result.residues[0].accounting_state is AccountingState.DEFERRED_WITH_REASON
    assert result.residues[0].material is True
    assert result.blockers[0].code is PublicationBlockerCode.MATERIAL_RESIDUE
    assert result.blockers[0].applicability == _app()


def test_mapped_semantic_fact_accounts_unit_without_residue() -> None:
    unit = _unit()
    fact = SemanticFact(
        fact_id="fact_1",
        concept="waiting_periods",
        semantic_type="INITIAL_WAITING_PERIOD",
        value={"duration_value": 30, "duration_unit": "DAYS"},
        applicability=unit.applicability,
        evidence_ids=(unit.evidence.evidence_id,),
        ontology_version="wp_v1",
    )
    decision = InventoryAccountingDecision(
        normative_unit_id=unit.normative_unit_id,
        accounting_state=AccountingState.MAPPED,
        reason="mapped to governed waiting-period fact",
        semantic_fact_ids=(fact.fact_id,),
    )

    result = account_normative_inventory(
        _inventory(unit), decisions=(decision,), semantic_facts=(fact,)
    )

    assert result.publishable is True
    assert result.residues == ()
    assert result.blockers == ()
    assert result.telemetry.accounted_unit_count == 1
    assert result.telemetry.state_counts[AccountingState.MAPPED] == 1


def test_relationship_mapping_accounts_benefit_scoped_waiver() -> None:
    unit = _unit(kind=NormativeUnitKind.RELATIONSHIP)
    relationship = RelationshipFact(
        relationship_id="rel_1",
        source_concept="chronic_care",
        relationship_type=RelationshipType.WAIVES,
        target_concept="waiting_periods",
        condition={"scope": "listed chronic conditions"},
        applicability=unit.applicability,
        evidence_ids=(unit.evidence.evidence_id,),
        ontology_version="rel_v1",
    )
    decision = InventoryAccountingDecision(
        normative_unit_id=unit.normative_unit_id,
        accounting_state=AccountingState.MAPPED_AS_RELATIONSHIP,
        reason="benefit-scoped waiver represented as relationship",
        relationship_fact_ids=(relationship.relationship_id,),
    )

    result = account_normative_inventory(
        _inventory(unit),
        decisions=(decision,),
        relationship_facts=(relationship,),
    )

    assert result.publishable is True
    assert result.telemetry.state_counts[AccountingState.MAPPED_AS_RELATIONSHIP] == 1


def test_not_yet_representable_blocks_only_affected_applicability_unit() -> None:
    base = _unit("nu_base", applicability=_app(optional_cover_state="OFF"))
    optional = _unit("nu_optional", applicability=_app(optional_cover_state="ON"))
    decisions = (
        InventoryAccountingDecision(
            normative_unit_id="nu_base",
            accounting_state=AccountingState.EXPLICITLY_NON_APPLICABLE,
            reason="base unit does not apply when optional cover is off",
        ),
        InventoryAccountingDecision(
            normative_unit_id="nu_optional",
            accounting_state=AccountingState.NOT_YET_REPRESENTABLE,
            reason="novel suspension mechanic is not in ontology",
        ),
    )

    result = account_normative_inventory(_inventory(base, optional), decisions=decisions)

    assert len(result.blockers) == 1
    assert result.blockers[0].code is PublicationBlockerCode.NOT_YET_REPRESENTABLE
    assert result.blockers[0].applicability.optional_cover_state == "ON"


def test_conflicted_unit_yields_authority_conflict_blocker() -> None:
    unit = _unit()
    decision = InventoryAccountingDecision(
        normative_unit_id=unit.normative_unit_id,
        accounting_state=AccountingState.CONFLICTED,
        reason="two equal-authority clauses disagree",
    )

    result = account_normative_inventory(_inventory(unit), decisions=(decision,))

    assert result.blockers[0].code is PublicationBlockerCode.AUTHORITY_CONFLICT


def test_explicit_non_applicability_is_accounted_without_residue() -> None:
    unit = _unit()
    decision = InventoryAccountingDecision(
        normative_unit_id=unit.normative_unit_id,
        accounting_state=AccountingState.EXPLICITLY_NON_APPLICABLE,
        reason="review confirmed clause applies to another benefit only",
    )

    result = account_normative_inventory(_inventory(unit), decisions=(decision,))

    assert result.publishable is True
    assert result.residues == ()


def test_mapped_fact_must_retain_normative_unit_evidence() -> None:
    unit = _unit()
    fact = SemanticFact(
        fact_id="fact_1",
        concept="waiting_periods",
        semantic_type="INITIAL_WAITING_PERIOD",
        value={"duration_value": 30},
        applicability=unit.applicability,
        evidence_ids=("different_evidence",),
        ontology_version="wp_v1",
    )
    decision = InventoryAccountingDecision(
        normative_unit_id=unit.normative_unit_id,
        accounting_state=AccountingState.MAPPED,
        reason="mapped",
        semantic_fact_ids=(fact.fact_id,),
    )

    with pytest.raises(NormativeInventoryError, match="retain the normative unit evidence"):
        account_normative_inventory(
            _inventory(unit), decisions=(decision,), semantic_facts=(fact,)
        )


def test_mapped_fact_must_match_applicability() -> None:
    unit = _unit(applicability=_app(optional_cover_state="OFF"))
    fact = SemanticFact(
        fact_id="fact_1",
        concept="waiting_periods",
        semantic_type="INITIAL_WAITING_PERIOD",
        value={"duration_value": 30},
        applicability=_app(optional_cover_state="ON"),
        evidence_ids=(unit.evidence.evidence_id,),
        ontology_version="wp_v1",
    )
    decision = InventoryAccountingDecision(
        normative_unit_id=unit.normative_unit_id,
        accounting_state=AccountingState.MAPPED,
        reason="mapped",
        semantic_fact_ids=(fact.fact_id,),
    )

    with pytest.raises(NormativeInventoryError, match="applicability must match"):
        account_normative_inventory(
            _inventory(unit), decisions=(decision,), semantic_facts=(fact,)
        )


def test_unknown_semantic_reference_fails_closed() -> None:
    unit = _unit()
    decision = InventoryAccountingDecision(
        normative_unit_id=unit.normative_unit_id,
        accounting_state=AccountingState.MAPPED,
        reason="mapped",
        semantic_fact_ids=("missing_fact",),
    )

    with pytest.raises(NormativeInventoryError, match="unknown semantic fact"):
        account_normative_inventory(_inventory(unit), decisions=(decision,))


def test_inventory_rejects_duplicate_normative_unit_ids() -> None:
    with pytest.raises(NormativeInventoryError, match="duplicate normative_unit_id"):
        _inventory(_unit("same"), _unit("same", evidence=_evidence("ev_2")))


def test_telemetry_records_residue_states_from_first_run() -> None:
    mapped = _unit("nu_mapped", evidence=_evidence("ev_mapped"))
    unresolved = _unit("nu_unresolved", evidence=_evidence("ev_unresolved"))
    fact = SemanticFact(
        fact_id="fact_mapped",
        concept="waiting_periods",
        semantic_type="PED",
        value={"duration_value": 36, "duration_unit": "MONTHS"},
        applicability=mapped.applicability,
        evidence_ids=(mapped.evidence.evidence_id,),
        ontology_version="wp_v1",
    )
    decisions = (
        InventoryAccountingDecision(
            normative_unit_id=mapped.normative_unit_id,
            accounting_state=AccountingState.MAPPED,
            reason="mapped",
            semantic_fact_ids=(fact.fact_id,),
        ),
        InventoryAccountingDecision(
            normative_unit_id=unresolved.normative_unit_id,
            accounting_state=AccountingState.NOT_YET_REPRESENTABLE,
            reason="ontology gap",
        ),
    )

    result = account_normative_inventory(
        _inventory(mapped, unresolved),
        decisions=decisions,
        semantic_facts=(fact,),
    )

    assert result.telemetry.normative_unit_count == 2
    assert result.telemetry.accounted_unit_count == 2
    assert result.telemetry.residue_count == 1
    assert result.telemetry.blocking_residue_count == 1
    assert result.telemetry.state_counts[AccountingState.MAPPED] == 1
    assert result.telemetry.state_counts[AccountingState.NOT_YET_REPRESENTABLE] == 1
