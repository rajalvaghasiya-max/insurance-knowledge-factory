"""MO-028C.G3 typed sum-insured applicability for benefit limits."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from insurance_intelligence.generic_knowledge.contracts import ApplicabilityKey
from insurance_intelligence.generic_knowledge.benefit_limit_contracts import BenefitLimitMechanic


class BenefitLimitApplicabilityError(ValueError):
    pass


class BandSetValidationStatus(str, Enum):
    VALID = "VALID"
    OVERLAP_REDUNDANT = "OVERLAP_REDUNDANT"
    OVERLAP_CONTRADICTORY = "OVERLAP_CONTRADICTORY"
    CONFLICT_DEFERRED_TEMPORAL = "CONFLICT_DEFERRED_TEMPORAL"


class BandLookupStatus(str, Enum):
    RESOLVED = "RESOLVED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"


def _inr(value: object, field_name: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BenefitLimitApplicabilityError(f"{field_name} must be an integer INR value")
    if positive and value <= 0:
        raise BenefitLimitApplicabilityError(f"{field_name} must be > 0")
    if not positive and value < 0:
        raise BenefitLimitApplicabilityError(f"{field_name} must be >= 0")
    return value


@dataclass(frozen=True)
class SumInsuredBand:
    lower_bound: int | None = None
    upper_bound: int | None = None
    lower_inclusive: bool = True
    upper_inclusive: bool = True
    currency: str = "INR"
    explicit_unbounded: bool = False

    def __post_init__(self) -> None:
        if self.currency != "INR":
            raise BenefitLimitApplicabilityError("G3 supports INR-only bands")
        if type(self.lower_inclusive) is not bool or type(self.upper_inclusive) is not bool:
            raise BenefitLimitApplicabilityError("band inclusivity flags must be boolean")
        if type(self.explicit_unbounded) is not bool:
            raise BenefitLimitApplicabilityError("explicit_unbounded must be boolean")
        if self.lower_bound is not None:
            object.__setattr__(self, "lower_bound", _inr(self.lower_bound, "lower_bound"))
        if self.upper_bound is not None:
            object.__setattr__(self, "upper_bound", _inr(self.upper_bound, "upper_bound"))
        if self.lower_bound is None and self.upper_bound is None:
            if not self.explicit_unbounded:
                raise BenefitLimitApplicabilityError("fully unbounded band requires explicit_unbounded=True")
            return
        if self.explicit_unbounded:
            raise BenefitLimitApplicabilityError("explicit_unbounded requires both bounds absent")
        if self.lower_bound is not None and self.upper_bound is not None:
            if self.lower_bound > self.upper_bound:
                raise BenefitLimitApplicabilityError("lower_bound cannot exceed upper_bound")
            if self.lower_bound == self.upper_bound and not (self.lower_inclusive and self.upper_inclusive):
                raise BenefitLimitApplicabilityError("zero-width band requires both boundaries inclusive")

    def contains(self, sum_insured: int) -> bool:
        value = _inr(sum_insured, "sum_insured", positive=True)
        if self.lower_bound is not None:
            if value < self.lower_bound or (value == self.lower_bound and not self.lower_inclusive):
                return False
        if self.upper_bound is not None:
            if value > self.upper_bound or (value == self.upper_bound and not self.upper_inclusive):
                return False
        return True

    def overlaps(self, other: "SumInsuredBand") -> bool:
        if self.upper_bound is not None and other.lower_bound is not None:
            if self.upper_bound < other.lower_bound:
                return False
            if self.upper_bound == other.lower_bound and not (self.upper_inclusive and other.lower_inclusive):
                return False
        if other.upper_bound is not None and self.lower_bound is not None:
            if other.upper_bound < self.lower_bound:
                return False
            if other.upper_bound == self.lower_bound and not (other.upper_inclusive and self.lower_inclusive):
                return False
        return True


@dataclass(frozen=True)
class BenefitLimitApplicability:
    base_applicability: ApplicabilityKey
    sum_insured_band: SumInsuredBand | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.base_applicability, ApplicabilityKey):
            raise BenefitLimitApplicabilityError("base_applicability must be ApplicabilityKey")
        if self.base_applicability.sum_insured_band is not None:
            raise BenefitLimitApplicabilityError("base_applicability.sum_insured_band must be None")
        if self.sum_insured_band is not None and not isinstance(self.sum_insured_band, SumInsuredBand):
            raise BenefitLimitApplicabilityError("sum_insured_band must be SumInsuredBand or None")


@dataclass(frozen=True)
class BenefitLimitApplicabilityCell:
    mechanic: BenefitLimitMechanic
    applicability: BenefitLimitApplicability


@dataclass(frozen=True)
class BandSetValidation:
    status: BandSetValidationStatus
    conflicting_cell_indexes: tuple[int, ...] = ()
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class BandLookupResult:
    status: BandLookupStatus
    matched_cell: BenefitLimitApplicabilityCell | None
    matching_cell_indexes: tuple[int, ...]
    reason_codes: tuple[str, ...]


def _base_without_version(app: ApplicabilityKey) -> tuple[object, ...]:
    return (app.product_reference, app.variant, app.zone, app.optional_cover_state)


def _provably_disjoint(app1: ApplicabilityKey, app2: ApplicabilityKey) -> bool:
    if app1.effective_to is not None and app2.effective_from is not None and app1.effective_to < app2.effective_from:
        return True
    if app2.effective_to is not None and app1.effective_from is not None and app2.effective_to < app1.effective_from:
        return True
    return False


def validate_band_set(cells: Iterable[BenefitLimitApplicabilityCell]) -> BandSetValidation:
    items = tuple(cells)
    redundant: set[int] = set()
    contradictory: set[int] = set()
    deferred: set[int] = set()
    for i, left in enumerate(items):
        for j in range(i + 1, len(items)):
            right = items[j]
            if left.mechanic.benefit_identity.concept_id != right.mechanic.benefit_identity.concept_id:
                continue
            lb, rb = left.applicability.sum_insured_band, right.applicability.sum_insured_band
            if lb is None or rb is None or not lb.overlaps(rb):
                continue
            la, ra = left.applicability.base_applicability, right.applicability.base_applicability
            if la == ra:
                (redundant if left.mechanic == right.mechanic else contradictory).update((i, j))
                continue
            if _base_without_version(la) == _base_without_version(ra) and la.policy_version != ra.policy_version and not _provably_disjoint(la, ra):
                deferred.update((i, j))
    if contradictory:
        return BandSetValidation(BandSetValidationStatus.OVERLAP_CONTRADICTORY, tuple(sorted(contradictory)), ("OVERLAPPING_BANDS_DIFFERENT_MECHANICS",))
    if deferred:
        return BandSetValidation(BandSetValidationStatus.CONFLICT_DEFERRED_TEMPORAL, tuple(sorted(deferred)), ("CROSS_VERSION_TEMPORAL_DISJOINTNESS_NOT_PROVEN",))
    if redundant:
        return BandSetValidation(BandSetValidationStatus.OVERLAP_REDUNDANT, tuple(sorted(redundant)), ("OVERLAPPING_BANDS_IDENTICAL_MECHANICS",))
    return BandSetValidation(BandSetValidationStatus.VALID)


def resolve_for_sum_insured(cells: Iterable[BenefitLimitApplicabilityCell], *, sum_insured: int) -> BandLookupResult:
    items = tuple(cells)
    _inr(sum_insured, "sum_insured", positive=True)
    matches = tuple((i, cell) for i, cell in enumerate(items) if cell.applicability.sum_insured_band is None or cell.applicability.sum_insured_band.contains(sum_insured))
    if not matches:
        return BandLookupResult(BandLookupStatus.NOT_FOUND, None, (), ("NO_MATCHING_SUM_INSURED_BAND",))
    if len(matches) > 1:
        return BandLookupResult(BandLookupStatus.CONFLICT, None, tuple(i for i, _ in matches), ("MULTIPLE_MATCHING_SUM_INSURED_BANDS",))
    index, cell = matches[0]
    return BandLookupResult(BandLookupStatus.RESOLVED, cell, (index,), ("EXACT_SUM_INSURED_BAND_MATCH",))
