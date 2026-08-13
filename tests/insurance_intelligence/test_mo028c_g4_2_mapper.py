from __future__ import annotations
from datetime import date
import pytest

from insurance_intelligence.generic_knowledge.benefit_limit_applicability import SumInsuredBand
from insurance_intelligence.generic_knowledge.benefit_limit_contracts import (
    CostSharingApplicability, CostSharingMechanicType, CostSharingOrdering,
    LimitKind, MonetaryAmount,
)
from insurance_intelligence.generic_knowledge.benefit_limit_mapper import BenefitLimitMapperError, map_benefit_limits
from insurance_intelligence.generic_knowledge.benefit_limit_reviewed_propositions import (
    DimensionEvidenceBinding, InteractionTargetMode, PropositionDimension,
    ReviewedBenefitLimitProposition, ReviewedCostSharingInteraction,
)
from insurance_intelligence.generic_knowledge.contracts import AccountingState, ApplicabilityKey, EvidenceReference
from insurance_intelligence.terminology.governed_concept_aliases import GovernedBenefitConceptResolver
from insurance_intelligence.terminology.mo028c_benefit_seed import build_mo028c_governed_alias_registry

AS_OF = date(2026, 8, 12)
BASE = ApplicabilityKey(product_reference="star_arogya_sanjeevani", policy_version="v1")

def _ev() -> EvidenceReference:
    return EvidenceReference("e", "wording", "v1", "a"*64, "benefit", "POLICY_WORDING")

def _bind(*dims: PropositionDimension) -> tuple[DimensionEvidenceBinding, ...]:
    return tuple(DimensionEvidenceBinding(d, ("e",), "review") for d in dims)

def _fixed(unit: str, label: str, amount: int, *, band: object | None = None, base: ApplicabilityKey = BASE) -> ReviewedBenefitLimitProposition:
    dims = [PropositionDimension.VALUE_KIND, PropositionDimension.BENEFIT_LABEL, PropositionDimension.AMOUNT]
    if band is not None:
        dims.append(PropositionDimension.SI_BAND)
    return ReviewedBenefitLimitProposition(
        unit, label, LimitKind.FIXED_CURRENCY, base, (_ev(),), _bind(*dims), "review",
        amount=MonetaryAmount(amount), sum_insured_band_payload=band,
    )

def _resolver() -> GovernedBenefitConceptResolver:
    return GovernedBenefitConceptResolver(build_mo028c_governed_alias_registry())

def _interaction(unit: str, targets: tuple[str, ...]) -> ReviewedCostSharingInteraction:
    return ReviewedCostSharingInteraction(
        normative_unit_id=unit,
        mechanic_type=CostSharingMechanicType.COPAY,
        applies=CostSharingApplicability.YES,
        ordering=CostSharingOrdering.UNKNOWN,
        target_mode=InteractionTargetMode.EXPLICIT_CONCEPT_SET,
        target_benefit_concept_ids=targets,
        evidence_references=(_ev(),),
        dimension_evidence_bindings=_bind(
            PropositionDimension.INTERACTION_APPLICABILITY,
            PropositionDimension.INTERACTION_ORDERING,
            PropositionDimension.INTERACTION_TARGET_SCOPE,
        ),
        review_decision_id="review",
        base_applicability=BASE,
    )

def test_fixed_maps_and_unknown_identity_defers_without_cell() -> None:
    batch = map_benefit_limits(
        (_fixed("road", "Road Ambulance", 2000), _fixed("unknown", "Unknown Benefit X", 1000)),
        (), resolver=_resolver(), as_of=AS_OF, ontology_version="v1",
    )
    assert batch.accounting_for("road").accounting_state is AccountingState.MAPPED
    assert batch.accounting_for("unknown").accounting_state is AccountingState.DEFERRED_WITH_REASON
    assert len(batch.cells) == 1

def test_unsupported_band_payload_is_not_yet_representable() -> None:
    batch = map_benefit_limits(
        (_fixed("u", "Cataract", 1000, band={"shared_pool": True}),), (),
        resolver=_resolver(), as_of=AS_OF, ontology_version="v1",
    )
    assert batch.accounting_for("u").accounting_state is AccountingState.NOT_YET_REPRESENTABLE

def test_non_overlapping_bands_map_but_overlap_conflicts_both_units() -> None:
    valid = (
        _fixed("low", "Cataract", 25000, band=SumInsuredBand(upper_bound=500000)),
        _fixed("high", "Cataract", 40000, band=SumInsuredBand(lower_bound=500000, lower_inclusive=False)),
    )
    batch = map_benefit_limits(valid, (), resolver=_resolver(), as_of=AS_OF, ontology_version="v1")
    assert all(batch.accounting_for(x).accounting_state is AccountingState.MAPPED for x in ("low","high"))

    conflict = (
        _fixed("a", "Cataract", 25000, band=SumInsuredBand(upper_bound=500000)),
        _fixed("b", "Cataract", 40000, band=SumInsuredBand(lower_bound=500000)),
    )
    batch2 = map_benefit_limits(conflict, (), resolver=_resolver(), as_of=AS_OF, ontology_version="v1")
    assert all(batch2.accounting_for(x).accounting_state is AccountingState.CONFLICTED for x in ("a","b"))

def test_cross_version_temporal_uncertainty_conflicts() -> None:
    v1 = ApplicabilityKey(product_reference="star_arogya_sanjeevani", policy_version="v1", effective_from=date(2025,1,1))
    v2 = ApplicabilityKey(product_reference="star_arogya_sanjeevani", policy_version="v2", effective_from=date(2025,7,1))
    props = (
        _fixed("a", "Cataract", 25000, band=SumInsuredBand(upper_bound=500000), base=v1),
        _fixed("b", "Cataract", 40000, band=SumInsuredBand(upper_bound=500000), base=v2),
    )
    batch = map_benefit_limits(props, (), resolver=_resolver(), as_of=AS_OF, ontology_version="v1")
    assert batch.accounting_for("a").reason_codes == ("TEMPORAL_CONFLICT_DEFERRED",)
    assert batch.accounting_for("b").reason_codes == ("TEMPORAL_CONFLICT_DEFERRED",)

def test_interaction_attaches_all_or_none() -> None:
    p = _fixed("road", "Road Ambulance", 2000)
    good = _interaction("copay", ("health:benefit:road_ambulance",))
    batch = map_benefit_limits((p,), (good,), resolver=_resolver(), as_of=AS_OF, ontology_version="v1")
    assert batch.accounting_for("copay").accounting_state is AccountingState.MAPPED_AS_RELATIONSHIP
    assert len(batch.cells[0].mechanic.cost_sharing_interactions) == 1

    bad = _interaction(
        "copay2", ("health:benefit:road_ambulance","health:benefit:cataract")
    )
    batch2 = map_benefit_limits((p,), (bad,), resolver=_resolver(), as_of=AS_OF, ontology_version="v1")
    assert batch2.accounting_for("copay2").accounting_state is AccountingState.DEFERRED_WITH_REASON
    assert batch2.cells[0].mechanic.cost_sharing_interactions == ()

def test_product_wide_scope_requires_governed_scope_and_can_map() -> None:
    p = _fixed("road", "Road Ambulance", 2000)
    it = ReviewedCostSharingInteraction(
        normative_unit_id="copay",
        mechanic_type=CostSharingMechanicType.COPAY,
        applies=CostSharingApplicability.YES,
        ordering=CostSharingOrdering.UNKNOWN,
        target_mode=InteractionTargetMode.PRODUCT_WIDE_GOVERNED_SCOPE,
        evidence_references=(_ev(),),
        dimension_evidence_bindings=_bind(
            PropositionDimension.INTERACTION_APPLICABILITY,
            PropositionDimension.INTERACTION_ORDERING,
            PropositionDimension.INTERACTION_TARGET_SCOPE,
        ),
        review_decision_id="review", base_applicability=BASE,
        governed_product_scope_id="scope1",
    )
    blocked = map_benefit_limits((p,), (it,), resolver=_resolver(), as_of=AS_OF, ontology_version="v1")
    assert blocked.accounting_for("copay").accounting_state is AccountingState.DEFERRED_WITH_REASON
    mapped = map_benefit_limits(
        (p,), (it,), resolver=_resolver(), as_of=AS_OF, ontology_version="v1",
        governed_product_scopes={"scope1": ("health:benefit:road_ambulance",)},
    )
    assert mapped.accounting_for("copay").accounting_state is AccountingState.MAPPED_AS_RELATIONSHIP

def test_duplicate_ids_fail_batch_and_order_is_deterministic() -> None:
    p = _fixed("same", "Road Ambulance", 2000)
    with pytest.raises(BenefitLimitMapperError, match="duplicate normative_unit_id"):
        map_benefit_limits((p,p), (), resolver=_resolver(), as_of=AS_OF, ontology_version="v1")

    a = _fixed("a", "Cataract", 25000, band=SumInsuredBand(upper_bound=500000))
    b = _fixed("b", "Cataract", 40000, band=SumInsuredBand(lower_bound=500000, lower_inclusive=False))
    left = map_benefit_limits((a,b), (), resolver=_resolver(), as_of=AS_OF, ontology_version="v1")
    right = map_benefit_limits((b,a), (), resolver=_resolver(), as_of=AS_OF, ontology_version="v1")
    assert left.accounting_records == right.accounting_records

# Note: the mapper may emit cells that are later blocked by accounting.
# Certification is zero silent residue, not zero residue or zero candidates.
