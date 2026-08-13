"""Deterministic MO-028C.G4.2 benefit-limit mapper and residue accounting.

Consumes only reviewed, source-sufficient propositions. It performs no prose parsing,
fuzzy inference, product-specific branching, claim calculation, comparison, or publication.
Every input normative unit receives exactly one final accounting outcome.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Mapping

from insurance_intelligence.generic_knowledge.benefit_limit_applicability import (
    BandSetValidation,
    BandSetValidationStatus,
    BenefitLimitApplicability,
    BenefitLimitApplicabilityCell,
    SumInsuredBand,
    validate_band_set,
)
from insurance_intelligence.generic_knowledge.benefit_limit_contracts import (
    BenefitIdentityReference,
    BenefitLimitContractError,
    BenefitLimitMechanic,
    CostSharingInteractionRule,
)
from insurance_intelligence.generic_knowledge.benefit_limit_reviewed_propositions import (
    InteractionTargetMode,
    PropositionDimension,
    ReviewedBenefitLimitProposition,
    ReviewedCostSharingInteraction,
)
from insurance_intelligence.generic_knowledge.contracts import (
    AccountingState,
    EvidenceReference,
)
from insurance_intelligence.terminology.governed_concept_aliases import (
    BenefitConceptIdentityStatus,
    GovernedBenefitConceptResolver,
)


class BenefitLimitMapperError(ValueError):
    """Raised when the mapping batch itself violates identity/accounting invariants."""


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

    def __post_init__(self) -> None:
        ids = tuple(item.normative_unit_id for item in self.accounting_records)
        if len(ids) != len(set(ids)):
            raise BenefitLimitMapperError("each normative_unit_id must have exactly one accounting record")

    def accounting_for(self, normative_unit_id: str) -> BenefitLimitAccountingRecord:
        matches = tuple(item for item in self.accounting_records if item.normative_unit_id == normative_unit_id)
        if len(matches) != 1:
            raise BenefitLimitMapperError(f"expected one accounting record for {normative_unit_id}")
        return matches[0]


def _evidence_for_dimensions(
    proposition: ReviewedBenefitLimitProposition,
    dimensions: tuple[PropositionDimension, ...],
) -> tuple[EvidenceReference, ...]:
    evidence_by_id = {item.evidence_id: item for item in proposition.evidence_references}
    ids: set[str] = set()
    wanted = set(dimensions)
    for binding in proposition.dimension_evidence_bindings:
        if binding.dimension in wanted:
            ids.update(binding.evidence_ids)
    return tuple(evidence_by_id[item] for item in sorted(ids))


def _build_mechanic(
    proposition: ReviewedBenefitLimitProposition,
    *,
    concept_id: str,
    alias_registry_version: str,
    alias_registry_snapshot_id: str,
    ontology_version: str,
) -> BenefitLimitMechanic:
    core = _evidence_for_dimensions(
        proposition,
        (
            PropositionDimension.VALUE_KIND,
            PropositionDimension.BENEFIT_LABEL,
            PropositionDimension.AMOUNT,
            PropositionDimension.PERCENTAGE,
            PropositionDimension.PERCENTAGE_BASIS,
        ),
    )
    scope = _evidence_for_dimensions(
        proposition,
        (PropositionDimension.TIME_SCOPE, PropositionDimension.EVENT_SCOPE),
    )
    bounds = _evidence_for_dimensions(
        proposition,
        (PropositionDimension.FLOOR, PropositionDimension.CEILING),
    )
    return BenefitLimitMechanic(
        benefit_identity=BenefitIdentityReference(
            concept_id=concept_id,
            alias_registry_version=alias_registry_version,
            alias_registry_snapshot_id=alias_registry_snapshot_id,
        ),
        limit_kind=proposition.limit_kind,
        ontology_version=ontology_version,
        core_evidence_references=core,
        amount=proposition.amount,
        percentage=proposition.percentage,
        percentage_basis=proposition.percentage_basis,
        floor_amount=proposition.floor_amount,
        ceiling_amount=proposition.ceiling_amount,
        time_scope=proposition.time_scope,
        event_scope=proposition.event_scope,
        scope_evidence_references=scope,
        bound_evidence_references=bounds,
    )


def _same_base_scope(left: object, right: object) -> bool:
    return left == right


def _group_key(cell: BenefitLimitApplicabilityCell) -> tuple[object, ...]:
    app = cell.applicability.base_applicability
    return (
        cell.mechanic.benefit_identity.concept_id,
        app.product_reference,
        app.variant,
        app.zone,
        app.optional_cover_state,
    )


def map_benefit_limits(
    propositions: tuple[ReviewedBenefitLimitProposition, ...],
    interactions: tuple[ReviewedCostSharingInteraction, ...],
    *,
    resolver: GovernedBenefitConceptResolver,
    as_of: date,
    ontology_version: str,
    governed_product_scopes: Mapping[str, tuple[str, ...]] | None = None,
) -> BenefitLimitMappingBatch:
    """Map reviewed propositions and finalize one accounting record per input unit."""
    governed_product_scopes = governed_product_scopes or {}
    all_ids = tuple(
        [item.normative_unit_id for item in propositions]
        + [item.normative_unit_id for item in interactions]
    )
    if len(all_ids) != len(set(all_ids)):
        raise BenefitLimitMapperError("duplicate normative_unit_id in mapping batch")

    cells: list[BenefitLimitApplicabilityCell] = []
    cell_source_ids: list[str] = []
    accounting: dict[str, BenefitLimitAccountingRecord] = {}

    for proposition in sorted(propositions, key=lambda item: item.normative_unit_id):
        identity = resolver.resolve(proposition.raw_benefit_label, as_of=as_of)
        if identity.status is BenefitConceptIdentityStatus.AMBIGUOUS:
            accounting[proposition.normative_unit_id] = BenefitLimitAccountingRecord(
                proposition.normative_unit_id,
                AccountingState.DEFERRED_WITH_REASON,
                ("BENEFIT_IDENTITY_AMBIGUOUS",),
            )
            continue
        if identity.status is BenefitConceptIdentityStatus.NOT_FOUND:
            accounting[proposition.normative_unit_id] = BenefitLimitAccountingRecord(
                proposition.normative_unit_id,
                AccountingState.DEFERRED_WITH_REASON,
                ("BENEFIT_IDENTITY_NOT_FOUND",),
            )
            continue
        if identity.status is not BenefitConceptIdentityStatus.RESOLVED or identity.concept_id is None:
            accounting[proposition.normative_unit_id] = BenefitLimitAccountingRecord(
                proposition.normative_unit_id,
                AccountingState.CONFLICTED,
                ("INVALID_BENEFIT_IDENTITY_INPUT",),
            )
            continue

        if proposition.sum_insured_band_payload is not None and not isinstance(
            proposition.sum_insured_band_payload, SumInsuredBand
        ):
            accounting[proposition.normative_unit_id] = BenefitLimitAccountingRecord(
                proposition.normative_unit_id,
                AccountingState.NOT_YET_REPRESENTABLE,
                ("UNSUPPORTED_TYPED_SI_BAND_PAYLOAD",),
                identity.concept_id,
            )
            continue

        try:
            mechanic = _build_mechanic(
                proposition,
                concept_id=identity.concept_id,
                alias_registry_version=identity.alias_registry_version,
                alias_registry_snapshot_id=identity.alias_registry_snapshot_id,
                ontology_version=ontology_version,
            )
            cell = BenefitLimitApplicabilityCell(
                mechanic=mechanic,
                applicability=BenefitLimitApplicability(
                    base_applicability=proposition.base_applicability,
                    sum_insured_band=proposition.sum_insured_band_payload,
                ),
            )
        except (BenefitLimitContractError, ValueError):
            accounting[proposition.normative_unit_id] = BenefitLimitAccountingRecord(
                proposition.normative_unit_id,
                AccountingState.CONFLICTED,
                ("INVALID_REVIEWED_SEMANTIC_SHAPE",),
                identity.concept_id,
            )
            continue

        cells.append(cell)
        cell_source_ids.append(proposition.normative_unit_id)
        accounting[proposition.normative_unit_id] = BenefitLimitAccountingRecord(
            proposition.normative_unit_id,
            AccountingState.MAPPED,
            ("SEMANTIC_CELL_MAPPED",),
            identity.concept_id,
            (len(cells) - 1,),
        )

    # Attach reviewed interaction semantics only when the full declared target set is resolvable.
    for interaction in sorted(interactions, key=lambda item: item.normative_unit_id):
        if interaction.target_mode is InteractionTargetMode.EXPLICIT_CONCEPT_SET:
            target_ids = interaction.target_benefit_concept_ids
        else:
            scope_id = interaction.governed_product_scope_id or ""
            target_ids = tuple(governed_product_scopes.get(scope_id, ()))
            if not target_ids:
                accounting[interaction.normative_unit_id] = BenefitLimitAccountingRecord(
                    interaction.normative_unit_id,
                    AccountingState.DEFERRED_WITH_REASON,
                    ("GOVERNED_PRODUCT_SCOPE_UNRESOLVED",),
                )
                continue

        matches_by_target: dict[str, tuple[int, ...]] = {}
        for target_id in target_ids:
            indexes = tuple(
                index
                for index, cell in enumerate(cells)
                if cell.mechanic.benefit_identity.concept_id == target_id
                and _same_base_scope(
                    cell.applicability.base_applicability,
                    interaction.base_applicability,
                )
            )
            matches_by_target[target_id] = indexes

        if any(not indexes for indexes in matches_by_target.values()):
            accounting[interaction.normative_unit_id] = BenefitLimitAccountingRecord(
                interaction.normative_unit_id,
                AccountingState.DEFERRED_WITH_REASON,
                ("INTERACTION_TARGET_UNRESOLVED",),
            )
            continue

        rule = CostSharingInteractionRule(
            mechanic_type=interaction.mechanic_type,
            applies=interaction.applies,
            ordering=interaction.ordering,
            evidence_references=interaction.evidence_references,
        )
        affected: set[int] = set()
        conflict = False
        for indexes in matches_by_target.values():
            for index in indexes:
                mechanic = cells[index].mechanic
                if any(existing.mechanic_type is rule.mechanic_type for existing in mechanic.cost_sharing_interactions):
                    conflict = True
                    break
                cells[index] = replace(
                    cells[index],
                    mechanic=replace(
                        mechanic,
                        cost_sharing_interactions=mechanic.cost_sharing_interactions + (rule,),
                    ),
                )
                affected.add(index)
            if conflict:
                break
        if conflict:
            accounting[interaction.normative_unit_id] = BenefitLimitAccountingRecord(
                interaction.normative_unit_id,
                AccountingState.CONFLICTED,
                ("DUPLICATE_INTERACTION_MECHANIC",),
            )
        else:
            accounting[interaction.normative_unit_id] = BenefitLimitAccountingRecord(
                interaction.normative_unit_id,
                AccountingState.MAPPED_AS_RELATIONSHIP,
                ("INTERACTION_ATTACHED_TO_EXPLICIT_TARGETS",),
                cell_indexes=tuple(sorted(affected)),
            )

    # Set-level band validation can overturn provisional MAPPED states.
    findings: list[BandSetValidation] = []
    groups: dict[tuple[object, ...], list[int]] = {}
    for index, cell in enumerate(cells):
        groups.setdefault(_group_key(cell), []).append(index)

    for key in sorted(groups, key=lambda value: tuple("" if item is None else str(item) for item in value)):
        indexes = tuple(groups[key])
        finding = validate_band_set(tuple(cells[index] for index in indexes))
        findings.append(finding)
        if finding.status is BandSetValidationStatus.VALID:
            continue
        affected_global = tuple(indexes[local] for local in finding.conflicting_cell_indexes)
        if finding.status is BandSetValidationStatus.OVERLAP_REDUNDANT:
            reason = "SI_BAND_OVERLAP_REDUNDANT"
        elif finding.status is BandSetValidationStatus.OVERLAP_CONTRADICTORY:
            reason = "SI_BAND_OVERLAP_CONTRADICTORY"
        else:
            reason = "TEMPORAL_CONFLICT_DEFERRED"
        for global_index in affected_global:
            source_id = cell_source_ids[global_index]
            current = accounting[source_id]
            accounting[source_id] = BenefitLimitAccountingRecord(
                source_id,
                AccountingState.CONFLICTED,
                (reason,),
                current.concept_id,
                current.cell_indexes,
            )

    if set(accounting) != set(all_ids):
        missing = tuple(sorted(set(all_ids) - set(accounting)))
        raise BenefitLimitMapperError(
            "mapping batch failed complete accounting: " + ", ".join(missing)
        )

    records = tuple(accounting[item] for item in sorted(accounting))
    return BenefitLimitMappingBatch(
        cells=tuple(cells),
        accounting_records=records,
        validation_findings=tuple(findings),
    )


__all__ = [
    "BenefitLimitAccountingRecord",
    "BenefitLimitMapperError",
    "BenefitLimitMappingBatch",
    "map_benefit_limits",
]
