from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from insurance_intelligence.generic_knowledge.benefit_limit_contracts import (
    CostSharingApplicability,
    CostSharingMechanicType,
    CostSharingOrdering,
    EventScope,
    LimitKind,
    MonetaryAmount,
    PercentageBasis,
    TimeScope,
)
from insurance_intelligence.generic_knowledge.benefit_limit_mapper import map_benefit_limits
from insurance_intelligence.generic_knowledge.benefit_limit_reviewed_propositions import (
    DimensionEvidenceBinding,
    InteractionTargetMode,
    PropositionDimension,
    ReviewedBenefitLimitProposition,
    ReviewedCostSharingInteraction,
)
from insurance_intelligence.generic_knowledge.contracts import AccountingState, ApplicabilityKey, EvidenceReference
from insurance_intelligence.terminology.governed_concept_aliases import GovernedBenefitConceptResolver
from insurance_intelligence.terminology.mo028c_benefit_seed import build_mo028c_governed_alias_registry

ARTIFACT = Path("docs/architecture/MO_028C_G5_STAR_AROGYA_REVIEWED_BENEFIT_LIMIT_MAPPING.json")
AS_OF = date(2026, 8, 12)


def _load() -> dict[str, object]:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _evidence(data: dict[str, object], row: dict[str, object]) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=str(row["evidence_id"]),
        source_document_id=str(data["source_document_id"]),
        source_document_version=str(data["source_document_version"]),
        source_hash_sha256="a" * 64,
        locator=str(row["locator"]),
        authority_class="POLICY_WORDING",
    )


def _base(data: dict[str, object]) -> ApplicabilityKey:
    return ApplicabilityKey(
        product_reference=str(data["product_reference"]),
        policy_version=str(data["policy_version"]),
    )


def _bindings(evidence_id: str, dimensions: list[PropositionDimension]) -> tuple[DimensionEvidenceBinding, ...]:
    return tuple(
        DimensionEvidenceBinding(
            dimension=dimension,
            evidence_ids=(evidence_id,),
            review_decision_id="MO_028C_G5_STAR_AROGYA_REVIEW",
        )
        for dimension in dimensions
    )


def _propositions(data: dict[str, object]) -> tuple[ReviewedBenefitLimitProposition, ...]:
    values: list[ReviewedBenefitLimitProposition] = []
    for row in data["limit_propositions"]:
        evidence = _evidence(data, row)
        dimensions = [PropositionDimension.VALUE_KIND, PropositionDimension.BENEFIT_LABEL]
        kwargs: dict[str, object] = {}
        if "amount" in row:
            kwargs["amount"] = MonetaryAmount(row["amount"])
            dimensions.append(PropositionDimension.AMOUNT)
        if "percentage" in row:
            kwargs["percentage"] = row["percentage"]
            dimensions.append(PropositionDimension.PERCENTAGE)
        if "percentage_basis" in row:
            kwargs["percentage_basis"] = PercentageBasis(row["percentage_basis"])
            dimensions.append(PropositionDimension.PERCENTAGE_BASIS)
        if "ceiling_amount" in row:
            kwargs["ceiling_amount"] = MonetaryAmount(row["ceiling_amount"])
            dimensions.append(PropositionDimension.CEILING)
        if "time_scope" in row:
            kwargs["time_scope"] = TimeScope(row["time_scope"])
            dimensions.append(PropositionDimension.TIME_SCOPE)
        if "event_scope" in row:
            kwargs["event_scope"] = EventScope(row["event_scope"])
            dimensions.append(PropositionDimension.EVENT_SCOPE)
        values.append(
            ReviewedBenefitLimitProposition(
                normative_unit_id=str(row["normative_unit_id"]),
                raw_benefit_label=str(row["raw_benefit_label"]),
                limit_kind=LimitKind(row["limit_kind"]),
                base_applicability=_base(data),
                evidence_references=(evidence,),
                dimension_evidence_bindings=_bindings(evidence.evidence_id, dimensions),
                review_decision_id="MO_028C_G5_STAR_AROGYA_REVIEW",
                **kwargs,
            )
        )
    return tuple(values)


def _interactions(data: dict[str, object]) -> tuple[ReviewedCostSharingInteraction, ...]:
    values: list[ReviewedCostSharingInteraction] = []
    for row in data["interactions"]:
        evidence = _evidence(data, row)
        dimensions = [
            PropositionDimension.INTERACTION_APPLICABILITY,
            PropositionDimension.INTERACTION_TARGET_SCOPE,
        ]
        if row["applies"] == "YES":
            dimensions.append(PropositionDimension.INTERACTION_ORDERING)
        values.append(
            ReviewedCostSharingInteraction(
                normative_unit_id=str(row["normative_unit_id"]),
                mechanic_type=CostSharingMechanicType(row["mechanic_type"]),
                applies=CostSharingApplicability(row["applies"]),
                ordering=CostSharingOrdering(row["ordering"]),
                target_mode=InteractionTargetMode(row["target_mode"]),
                evidence_references=(evidence,),
                dimension_evidence_bindings=_bindings(evidence.evidence_id, dimensions),
                review_decision_id="MO_028C_G5_STAR_AROGYA_REVIEW",
                base_applicability=_base(data),
                target_benefit_concept_ids=tuple(row.get("target_benefit_concept_ids", ())),
                governed_product_scope_id=row.get("governed_product_scope_id"),
            )
        )
    return tuple(values)


def _batch():
    data = _load()
    resolver = GovernedBenefitConceptResolver(build_mo028c_governed_alias_registry())
    scope = data["governed_product_scope"]
    return data, map_benefit_limits(
        _propositions(data),
        _interactions(data),
        resolver=resolver,
        as_of=AS_OF,
        ontology_version=str(data["ontology_version"]),
        governed_product_scopes={str(scope["scope_id"]): tuple(scope["benefit_concept_ids"])},
    )


def test_all_eight_real_source_units_receive_exactly_one_final_accounting_outcome() -> None:
    data, batch = _batch()
    records = batch.accounting_records
    assert len(records) == data["expected_accounting"]["atomic_unit_count"] == 8
    assert len({record.normative_unit_id for record in records}) == 8
    assert sum(record.accounting_state is AccountingState.MAPPED for record in records) == 6
    assert sum(record.accounting_state is AccountingState.MAPPED_AS_RELATIONSHIP for record in records) == 2
    assert all(record.accounting_state in (AccountingState.MAPPED, AccountingState.MAPPED_AS_RELATIONSHIP) for record in records)


def test_policy_period_is_preserved_and_not_coerced_to_policy_year() -> None:
    _, batch = _batch()
    modern = next(cell for cell in batch.cells if cell.mechanic.benefit_identity.concept_id == "health:benefit:modern_treatment_group")
    assert modern.mechanic.time_scope is TimeScope.PER_POLICY_PERIOD
    assert modern.mechanic.time_scope is not TimeScope.PER_POLICY_YEAR


def test_product_wide_copay_attaches_to_every_governed_limit_benefit_and_blocks_equivalence() -> None:
    data, batch = _batch()
    expected = set(data["governed_product_scope"]["benefit_concept_ids"])
    observed: set[str] = set()
    for cell in batch.cells:
        concept_id = cell.mechanic.benefit_identity.concept_id
        copays = tuple(rule for rule in cell.mechanic.cost_sharing_interactions if rule.mechanic_type is CostSharingMechanicType.COPAY)
        assert len(copays) == 1
        assert copays[0].ordering is CostSharingOrdering.UNKNOWN
        assert cell.mechanic.equivalence_ready is False
        observed.add(concept_id)
    assert observed == expected


def test_proportionate_deduction_is_attached_only_to_room_and_icu() -> None:
    _, batch = _batch()
    targets = {
        cell.mechanic.benefit_identity.concept_id
        for cell in batch.cells
        if any(rule.mechanic_type is CostSharingMechanicType.PROPORTIONATE_DEDUCTION for rule in cell.mechanic.cost_sharing_interactions)
    }
    assert targets == {"health:benefit:room_rent", "health:benefit:icu"}


def test_g5_real_mapping_has_zero_silent_residue_without_product_specific_runtime_logic() -> None:
    data, batch = _batch()
    expected = data["expected_accounting"]
    assert expected["zero_silent_residue"] is True
    assert expected["residue_units"] == 0
    assert len(batch.cells) == expected["mapped_limit_units"] == 6
    assert all(finding.status.value == "VALID" for finding in batch.validation_findings)
