"""Deterministic MO-028C.G4.2 benefit-limit mapper with complete accounting."""
from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import date
from typing import Mapping

from insurance_intelligence.generic_knowledge.benefit_limit_applicability import (
    BandSetValidation, BandSetValidationStatus, BenefitLimitApplicability,
    BenefitLimitApplicabilityCell, SumInsuredBand, validate_band_set,
)
from insurance_intelligence.generic_knowledge.benefit_limit_contracts import (
    BenefitIdentityReference, BenefitLimitContractError, BenefitLimitMechanic,
    CostSharingInteractionRule,
)
from insurance_intelligence.generic_knowledge.benefit_limit_reviewed_propositions import (
    InteractionTargetMode, PropositionDimension, ReviewedBenefitLimitProposition,
    ReviewedCostSharingInteraction,
)
from insurance_intelligence.generic_knowledge.contracts import AccountingState, EvidenceReference
from insurance_intelligence.terminology.governed_concept_aliases import (
    BenefitConceptIdentityStatus, GovernedBenefitConceptResolver,
)

class BenefitLimitMapperError(ValueError):
    pass

@dataclass(frozen=True)
class BenefitLimitAccountingRecord:
    normative_unit_id: str
    accounting_state: AccountingState
    reason_codes: tuple[str, ...]
    concept_id: str | None = None
    cell_indexes: tuple[int, ...] = ()

@dataclass(frozen=True)
class BenefitLimitMappingBatch:
    cells: tuple[BenefitLimitApplicabilityCell, ...]
    accounting_records: tuple[BenefitLimitAccountingRecord, ...]
    validation_findings: tuple[BandSetValidation, ...]

    def accounting_for(self, normative_unit_id: str) -> BenefitLimitAccountingRecord:
        found = tuple(x for x in self.accounting_records if x.normative_unit_id == normative_unit_id)
        if len(found) != 1:
            raise BenefitLimitMapperError(f"expected one accounting record for {normative_unit_id}")
        return found[0]


def _ev(p: ReviewedBenefitLimitProposition, dims: tuple[PropositionDimension, ...]) -> tuple[EvidenceReference, ...]:
    by_id = {e.evidence_id: e for e in p.evidence_references}
    ids = {eid for b in p.dimension_evidence_bindings if b.dimension in set(dims) for eid in b.evidence_ids}
    return tuple(by_id[eid] for eid in sorted(ids))


def _mechanic(p: ReviewedBenefitLimitProposition, *, concept_id: str, registry_version: str, snapshot_id: str, ontology_version: str) -> BenefitLimitMechanic:
    return BenefitLimitMechanic(
        benefit_identity=BenefitIdentityReference(concept_id, registry_version, snapshot_id),
        limit_kind=p.limit_kind,
        ontology_version=ontology_version,
        core_evidence_references=_ev(p, (
            PropositionDimension.VALUE_KIND, PropositionDimension.BENEFIT_LABEL,
            PropositionDimension.AMOUNT, PropositionDimension.PERCENTAGE,
            PropositionDimension.PERCENTAGE_BASIS,
        )),
        amount=p.amount, percentage=p.percentage, percentage_basis=p.percentage_basis,
        floor_amount=p.floor_amount, ceiling_amount=p.ceiling_amount,
        time_scope=p.time_scope, event_scope=p.event_scope,
        scope_evidence_references=_ev(p, (PropositionDimension.TIME_SCOPE, PropositionDimension.EVENT_SCOPE)),
        bound_evidence_references=_ev(p, (PropositionDimension.FLOOR, PropositionDimension.CEILING)),
    )


def _group_key(cell: BenefitLimitApplicabilityCell) -> tuple[object, ...]:
    a = cell.applicability.base_applicability
    return (cell.mechanic.benefit_identity.concept_id, a.product_reference, a.variant, a.zone, a.optional_cover_state)


def map_benefit_limits(
    propositions: tuple[ReviewedBenefitLimitProposition, ...],
    interactions: tuple[ReviewedCostSharingInteraction, ...],
    *, resolver: GovernedBenefitConceptResolver, as_of: date, ontology_version: str,
    governed_product_scopes: Mapping[str, tuple[str, ...]] | None = None,
) -> BenefitLimitMappingBatch:
    scopes = governed_product_scopes or {}
    all_ids = tuple([p.normative_unit_id for p in propositions] + [i.normative_unit_id for i in interactions])
    if len(all_ids) != len(set(all_ids)):
        raise BenefitLimitMapperError("duplicate normative_unit_id in mapping batch")

    cells: list[BenefitLimitApplicabilityCell] = []
    source_ids: list[str] = []
    acc: dict[str, BenefitLimitAccountingRecord] = {}

    for p in sorted(propositions, key=lambda x: x.normative_unit_id):
        r = resolver.resolve(p.raw_benefit_label, as_of=as_of)
        if r.status is BenefitConceptIdentityStatus.AMBIGUOUS:
            acc[p.normative_unit_id] = BenefitLimitAccountingRecord(p.normative_unit_id, AccountingState.DEFERRED_WITH_REASON, ("BENEFIT_IDENTITY_AMBIGUOUS",))
            continue
        if r.status is BenefitConceptIdentityStatus.NOT_FOUND:
            acc[p.normative_unit_id] = BenefitLimitAccountingRecord(p.normative_unit_id, AccountingState.DEFERRED_WITH_REASON, ("BENEFIT_IDENTITY_NOT_FOUND",))
            continue
        if r.status is not BenefitConceptIdentityStatus.RESOLVED or r.concept_id is None:
            acc[p.normative_unit_id] = BenefitLimitAccountingRecord(p.normative_unit_id, AccountingState.CONFLICTED, ("INVALID_BENEFIT_IDENTITY_INPUT",))
            continue
        band = p.sum_insured_band_payload
        if band is not None and not isinstance(band, SumInsuredBand):
            acc[p.normative_unit_id] = BenefitLimitAccountingRecord(p.normative_unit_id, AccountingState.NOT_YET_REPRESENTABLE, ("UNSUPPORTED_TYPED_SI_BAND_PAYLOAD",), r.concept_id)
            continue
        try:
            m = _mechanic(p, concept_id=r.concept_id, registry_version=r.alias_registry_version, snapshot_id=r.alias_registry_snapshot_id, ontology_version=ontology_version)
            cell = BenefitLimitApplicabilityCell(m, BenefitLimitApplicability(p.base_applicability, band))
        except (BenefitLimitContractError, ValueError):
            acc[p.normative_unit_id] = BenefitLimitAccountingRecord(p.normative_unit_id, AccountingState.CONFLICTED, ("INVALID_REVIEWED_SEMANTIC_SHAPE",), r.concept_id)
            continue
        idx = len(cells)
        cells.append(cell); source_ids.append(p.normative_unit_id)
        acc[p.normative_unit_id] = BenefitLimitAccountingRecord(p.normative_unit_id, AccountingState.MAPPED, ("SEMANTIC_CELL_MAPPED",), r.concept_id, (idx,))

    for it in sorted(interactions, key=lambda x: x.normative_unit_id):
        if it.target_mode is InteractionTargetMode.EXPLICIT_CONCEPT_SET:
            targets = it.target_benefit_concept_ids
        else:
            targets = tuple(scopes.get(it.governed_product_scope_id or "", ()))
            if not targets:
                acc[it.normative_unit_id] = BenefitLimitAccountingRecord(it.normative_unit_id, AccountingState.DEFERRED_WITH_REASON, ("GOVERNED_PRODUCT_SCOPE_UNRESOLVED",))
                continue
        by_target = {
            t: tuple(idx for idx, cell in enumerate(cells)
                     if cell.mechanic.benefit_identity.concept_id == t
                     and cell.applicability.base_applicability == it.base_applicability)
            for t in targets
        }
        if any(not indexes for indexes in by_target.values()):
            acc[it.normative_unit_id] = BenefitLimitAccountingRecord(it.normative_unit_id, AccountingState.DEFERRED_WITH_REASON, ("INTERACTION_TARGET_UNRESOLVED",))
            continue
        rule = CostSharingInteractionRule(it.mechanic_type, it.applies, it.ordering, it.evidence_references)
        affected = tuple(sorted({idx for indexes in by_target.values() for idx in indexes}))
        # Atomic preflight: never partially attach a conflicting interaction.
        if any(any(old.mechanic_type is rule.mechanic_type for old in cells[idx].mechanic.cost_sharing_interactions) for idx in affected):
            acc[it.normative_unit_id] = BenefitLimitAccountingRecord(it.normative_unit_id, AccountingState.CONFLICTED, ("DUPLICATE_INTERACTION_MECHANIC",))
            continue
        for idx in affected:
            m = cells[idx].mechanic
            cells[idx] = replace(cells[idx], mechanic=replace(m, cost_sharing_interactions=m.cost_sharing_interactions + (rule,)))
        acc[it.normative_unit_id] = BenefitLimitAccountingRecord(it.normative_unit_id, AccountingState.MAPPED_AS_RELATIONSHIP, ("INTERACTION_ATTACHED_TO_REVIEWED_TARGETS",), cell_indexes=affected)

    findings: list[BandSetValidation] = []
    groups: dict[tuple[object, ...], list[int]] = {}
    for idx, cell in enumerate(cells):
        groups.setdefault(_group_key(cell), []).append(idx)
    for key in sorted(groups, key=lambda k: tuple("" if x is None else str(x) for x in k)):
        indexes = tuple(groups[key])
        f = validate_band_set(tuple(cells[idx] for idx in indexes)); findings.append(f)
        if f.status is BandSetValidationStatus.VALID:
            continue
        reason = {
            BandSetValidationStatus.OVERLAP_REDUNDANT: "SI_BAND_OVERLAP_REDUNDANT",
            BandSetValidationStatus.OVERLAP_CONTRADICTORY: "SI_BAND_OVERLAP_CONTRADICTORY",
            BandSetValidationStatus.CONFLICT_DEFERRED_TEMPORAL: "TEMPORAL_CONFLICT_DEFERRED",
        }[f.status]
        for local_idx in f.conflicting_cell_indexes:
            idx = indexes[local_idx]; source_id = source_ids[idx]; old = acc[source_id]
            acc[source_id] = BenefitLimitAccountingRecord(source_id, AccountingState.CONFLICTED, (reason,), old.concept_id, old.cell_indexes)

    if set(acc) != set(all_ids):
        raise BenefitLimitMapperError("mapping batch failed complete accounting")
    return BenefitLimitMappingBatch(tuple(cells), tuple(acc[k] for k in sorted(acc)), tuple(findings))

__all__ = ["BenefitLimitAccountingRecord", "BenefitLimitMapperError", "BenefitLimitMappingBatch", "map_benefit_limits"]
