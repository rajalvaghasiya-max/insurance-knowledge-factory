from __future__ import annotations

from datetime import date

import pytest

from insurance_intelligence.generic_knowledge.benefit_limit_contracts import (
    BenefitIdentityReference,
    BenefitLimitMechanic,
    LimitKind,
    MonetaryAmount,
)
from insurance_intelligence.generic_knowledge.benefit_limit_applicability import (
    BandLookupStatus,
    BandSetValidationStatus,
    BenefitLimitApplicability,
    BenefitLimitApplicabilityCell,
    BenefitLimitApplicabilityError,
    SumInsuredBand,
    resolve_for_sum_insured,
    validate_band_set,
)
from insurance_intelligence.generic_knowledge.contracts import ApplicabilityKey, EvidenceReference


def _evidence(evidence_id: str) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        source_document_id="test",
        source_document_version="v1",
        source_hash_sha256="a" * 64,
        locator=evidence_id,
        authority_class="POLICY_WORDING",
    )


def _mechanic(amount: int, concept: str = "health:benefit:cataract") -> BenefitLimitMechanic:
    return BenefitLimitMechanic(
        benefit_identity=BenefitIdentityReference(
            concept_id=concept,
            alias_registry_version="v1",
            alias_registry_snapshot_id="snapshot",
        ),
        limit_kind=LimitKind.FIXED_CURRENCY,
        amount=MonetaryAmount(amount),
        core_evidence_references=(_evidence(f"core-{amount}"),),
        ontology_version="v1",
    )


def _app(policy_version: str = "v1", *, start: date | None = None, end: date | None = None, variant: str | None = None) -> ApplicabilityKey:
    return ApplicabilityKey(
        product_reference="product",
        policy_version=policy_version,
        variant=variant,
        effective_from=start,
        effective_to=end,
    )


def _cell(band: SumInsuredBand, amount: int, *, policy_version: str = "v1", start: date | None = None, end: date | None = None, variant: str | None = None) -> BenefitLimitApplicabilityCell:
    return BenefitLimitApplicabilityCell(
        mechanic=_mechanic(amount),
        applicability=BenefitLimitApplicability(
            base_applicability=_app(policy_version, start=start, end=end, variant=variant),
            sum_insured_band=band,
        ),
    )


def test_open_ended_and_explicit_unbounded_bands_are_valid_and_membership_is_deterministic() -> None:
    low = SumInsuredBand(upper_bound=500000)
    high = SumInsuredBand(lower_bound=500000, lower_inclusive=False)
    all_si = SumInsuredBand(explicit_unbounded=True)
    assert low.contains(500000) is True
    assert high.contains(500000) is False
    assert high.contains(500001) is True
    assert all_si.contains(1) is True


def test_accidental_unbounded_and_invalid_zero_width_or_reversed_bands_fail_closed() -> None:
    with pytest.raises(BenefitLimitApplicabilityError, match="explicit_unbounded"):
        SumInsuredBand()
    with pytest.raises(BenefitLimitApplicabilityError, match="lower_bound"):
        SumInsuredBand(lower_bound=600000, upper_bound=500000)
    with pytest.raises(BenefitLimitApplicabilityError, match="zero-width"):
        SumInsuredBand(lower_bound=500000, upper_bound=500000, lower_inclusive=False)


def test_single_point_inclusive_band_is_valid_and_boundary_overlap_is_exact() -> None:
    point = SumInsuredBand(lower_bound=500000, upper_bound=500000)
    low = SumInsuredBand(upper_bound=500000)
    high = SumInsuredBand(lower_bound=500000, lower_inclusive=False)
    assert point.contains(500000) is True
    assert point.overlaps(low) is True
    assert point.overlaps(high) is False


def test_adjacent_exclusive_boundary_is_non_overlapping_but_shared_inclusive_boundary_conflicts() -> None:
    low = SumInsuredBand(upper_bound=500000)
    high = SumInsuredBand(lower_bound=500000, lower_inclusive=False)
    shared = SumInsuredBand(lower_bound=500000)
    assert low.overlaps(high) is False
    assert low.overlaps(shared) is True


def test_same_benefit_non_overlapping_bands_are_valid_and_lookup_resolves_exactly_one() -> None:
    cells = (
        _cell(SumInsuredBand(upper_bound=500000), 25000),
        _cell(SumInsuredBand(lower_bound=500000, lower_inclusive=False), 40000),
    )
    assert validate_band_set(cells).status is BandSetValidationStatus.VALID
    result = resolve_for_sum_insured(cells, sum_insured=700000)
    assert result.status is BandLookupStatus.RESOLVED
    assert result.matched_cell == cells[1]


def test_lookup_gap_is_not_found_with_no_nearest_or_adjacent_inheritance() -> None:
    cells = (
        _cell(SumInsuredBand(upper_bound=500000), 25000),
        _cell(SumInsuredBand(lower_bound=1000000, lower_inclusive=False), 50000),
    )
    result = resolve_for_sum_insured(cells, sum_insured=700000)
    assert result.status is BandLookupStatus.NOT_FOUND
    assert result.matched_cell is None


def test_overlapping_different_mechanics_are_contradictory_and_lookup_never_first_matches() -> None:
    cells = (
        _cell(SumInsuredBand(upper_bound=1000000), 40000),
        _cell(SumInsuredBand(lower_bound=1000000), 50000),
    )
    validation = validate_band_set(cells)
    assert validation.status is BandSetValidationStatus.OVERLAP_CONTRADICTORY
    result = resolve_for_sum_insured(cells, sum_insured=1000000)
    assert result.status is BandLookupStatus.CONFLICT
    assert result.matched_cell is None


def test_overlapping_identical_mechanics_are_redundant_but_still_blocking() -> None:
    mechanic = _mechanic(40000)
    cells = (
        BenefitLimitApplicabilityCell(mechanic, BenefitLimitApplicability(_app(), SumInsuredBand(upper_bound=1000000))),
        BenefitLimitApplicabilityCell(mechanic, BenefitLimitApplicability(_app(), SumInsuredBand(lower_bound=1000000))),
    )
    assert validate_band_set(cells).status is BandSetValidationStatus.OVERLAP_REDUNDANT


def test_different_variant_does_not_conflict() -> None:
    cells = (
        _cell(SumInsuredBand(upper_bound=1000000), 40000, variant="A"),
        _cell(SumInsuredBand(upper_bound=1000000), 50000, variant="B"),
    )
    assert validate_band_set(cells).status is BandSetValidationStatus.VALID


def test_cross_version_temporal_uncertainty_fails_closed_but_disjoint_versions_pass() -> None:
    uncertain = (
        _cell(SumInsuredBand(upper_bound=1000000), 40000, policy_version="v1", start=date(2025, 1, 1)),
        _cell(SumInsuredBand(upper_bound=1000000), 50000, policy_version="v2", start=date(2025, 7, 1)),
    )
    assert validate_band_set(uncertain).status is BandSetValidationStatus.CONFLICT_DEFERRED_TEMPORAL
    disjoint = (
        _cell(SumInsuredBand(upper_bound=1000000), 40000, policy_version="v1", start=date(2025, 1, 1), end=date(2025, 12, 31)),
        _cell(SumInsuredBand(upper_bound=1000000), 50000, policy_version="v2", start=date(2026, 1, 1)),
    )
    assert validate_band_set(disjoint).status is BandSetValidationStatus.VALID


def test_typed_band_and_legacy_string_band_cannot_coexist() -> None:
    base = ApplicabilityKey(product_reference="product", sum_insured_band="5-10L")
    with pytest.raises(BenefitLimitApplicabilityError, match="sum_insured_band must be None"):
        BenefitLimitApplicability(base, SumInsuredBand(upper_bound=1000000))


def test_sum_insured_lookup_requires_positive_integer_inr() -> None:
    band = SumInsuredBand(upper_bound=1000000)
    with pytest.raises(BenefitLimitApplicabilityError, match="> 0"):
        band.contains(0)
    with pytest.raises(BenefitLimitApplicabilityError, match="integer"):
        band.contains(1.5)  # type: ignore[arg-type]


def test_input_order_does_not_change_validation_semantics() -> None:
    a = _cell(SumInsuredBand(upper_bound=1000000), 40000)
    b = _cell(SumInsuredBand(lower_bound=1000000), 50000)
    assert validate_band_set((a, b)).status is BandSetValidationStatus.OVERLAP_CONTRADICTORY
    assert validate_band_set((b, a)).status is BandSetValidationStatus.OVERLAP_CONTRADICTORY


def test_si_band_applicability_does_not_change_mechanic_si_linkage() -> None:
    fixed = _cell(SumInsuredBand(lower_bound=500000, upper_bound=1000000), 40000)
    assert fixed.mechanic.is_si_linked is False


def test_unbounded_default_band_plus_specific_band_conflicts_without_override_semantics() -> None:
    cells = (
        _cell(SumInsuredBand(explicit_unbounded=True), 50000),
        _cell(SumInsuredBand(upper_bound=500000), 25000),
    )
    assert validate_band_set(cells).status is BandSetValidationStatus.OVERLAP_CONTRADICTORY
