"""Authenticated Policy Schedule value resolution for MO-028B.G11.C4.

C4 is a value-only trust boundary. A governed document-class gate and authenticated field binding
must already exist before an instance value may resolve a certified semantic domain. Documents
capable of changing contractual semantics (endorsements/riders) are deliberately rejected from
this path and must route to semantic governance instead.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Hashable

from insurance_intelligence.generic_knowledge.duration_normalization import (
    DurationNormalizationError,
    DurationUnit,
    normalize_duration,
)
from insurance_intelligence.generic_knowledge.resolution_status import (
    ComputedResolution,
    InstanceAvailability,
    ResolutionInputs,
    ResolutionStatus,
    ReviewState,
    SourceState,
    ValidationState,
    ValueSource,
    compute_resolution_status,
)


class ScheduleResolutionError(ValueError):
    """Raised when C4 contracts are structurally invalid."""


class InstanceDocumentClass(str, Enum):
    POLICY_WORDING = "POLICY_WORDING"
    SCHEDULE = "SCHEDULE"
    ENDORSEMENT = "ENDORSEMENT"
    RIDER = "RIDER"
    CERTIFICATE = "CERTIFICATE"


class BindingReviewState(str, Enum):
    APPROVED = "APPROVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ScheduleTelemetryCode(str, Enum):
    DOMAIN_MEMBERSHIP_REJECTED = "DOMAIN_MEMBERSHIP_REJECTED"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScheduleResolutionError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(value: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ScheduleResolutionError(f"{field_name} must be a tuple")
    normalized = tuple(_text(item, f"{field_name}[]") for item in value)
    if not normalized:
        raise ScheduleResolutionError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ScheduleResolutionError(f"{field_name} must not contain duplicates")
    return normalized


@dataclass(frozen=True)
class WaitingPeriodSelectionDomain:
    semantic_fact_id: str
    resolution_cell_identity: Hashable
    allowed_values: tuple[int, ...]
    canonical_unit: DurationUnit
    semantic_evidence_ids: tuple[str, ...]
    ontology_version: str
    domain_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "semantic_fact_id", _text(self.semantic_fact_id, "semantic_fact_id"))
        object.__setattr__(self, "ontology_version", _text(self.ontology_version, "ontology_version"))
        object.__setattr__(self, "domain_version", _text(self.domain_version, "domain_version"))
        try:
            hash(self.resolution_cell_identity)
        except TypeError as exc:
            raise ScheduleResolutionError("resolution_cell_identity must be hashable") from exc
        if not isinstance(self.allowed_values, tuple) or not self.allowed_values:
            raise ScheduleResolutionError("allowed_values must be a non-empty tuple")
        if any(type(value) is not int or value < 0 for value in self.allowed_values):
            raise ScheduleResolutionError("allowed_values must contain non-negative integers")
        if len(set(self.allowed_values)) != len(self.allowed_values):
            raise ScheduleResolutionError("allowed_values must not contain duplicates")
        if not isinstance(self.canonical_unit, DurationUnit):
            raise ScheduleResolutionError("canonical_unit must be DurationUnit")
        object.__setattr__(
            self, "semantic_evidence_ids", _text_tuple(self.semantic_evidence_ids, "semantic_evidence_ids")
        )


@dataclass(frozen=True)
class GovernedBindingProvenance:
    binding_id: str
    binding_method: str
    bound_semantic_fact_id: str
    semantic_domain_version: str
    source_document_id: str
    source_document_version: str
    source_document_hash: str
    document_class: InstanceDocumentClass
    review_state: BindingReviewState

    def __post_init__(self) -> None:
        for field_name in (
            "binding_id",
            "binding_method",
            "bound_semantic_fact_id",
            "semantic_domain_version",
            "source_document_id",
            "source_document_version",
            "source_document_hash",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if not isinstance(self.document_class, InstanceDocumentClass):
            raise ScheduleResolutionError("document_class must be InstanceDocumentClass")
        if not isinstance(self.review_state, BindingReviewState):
            raise ScheduleResolutionError("review_state must be BindingReviewState")


@dataclass(frozen=True)
class WaitingPeriodInstanceSelection:
    selection_id: str
    policy_instance_reference: str
    instance_document_id: str
    instance_document_version: str
    instance_document_hash: str
    document_class: InstanceDocumentClass
    binding_provenance_id: str
    semantic_fact_id: str
    resolution_cell_identity: Hashable
    selected_value: int
    selected_unit: DurationUnit
    instance_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "selection_id",
            "policy_instance_reference",
            "instance_document_id",
            "instance_document_version",
            "instance_document_hash",
            "binding_provenance_id",
            "semantic_fact_id",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if not isinstance(self.document_class, InstanceDocumentClass):
            raise ScheduleResolutionError("document_class must be InstanceDocumentClass")
        try:
            hash(self.resolution_cell_identity)
        except TypeError as exc:
            raise ScheduleResolutionError("resolution_cell_identity must be hashable") from exc
        if type(self.selected_value) is not int or self.selected_value < 0:
            raise ScheduleResolutionError("selected_value must be a non-negative integer")
        if not isinstance(self.selected_unit, DurationUnit):
            raise ScheduleResolutionError("selected_unit must be DurationUnit")
        object.__setattr__(
            self, "instance_evidence_ids", _text_tuple(self.instance_evidence_ids, "instance_evidence_ids")
        )


@dataclass(frozen=True)
class ScheduleResolutionTelemetry:
    code: ScheduleTelemetryCode
    semantic_fact_id: str
    policy_instance_reference: str
    selected_value: int
    selected_unit: DurationUnit


@dataclass(frozen=True)
class ResolvedWaitingPeriodSelection:
    semantic_fact_id: str
    policy_instance_reference: str
    resolution_cell_identity: Hashable
    selected_value: int | None
    selected_unit: DurationUnit | None
    semantic_evidence_ids: tuple[str, ...]
    instance_evidence_ids: tuple[str, ...]
    instance_document_class: InstanceDocumentClass | None
    binding_provenance_id: str | None
    ontology_version: str
    domain_version: str
    instance_document_id: str | None
    instance_document_version: str | None
    instance_document_hash: str | None
    resolution: ComputedResolution
    telemetry: tuple[ScheduleResolutionTelemetry, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.resolution, ComputedResolution):
            raise ScheduleResolutionError("resolution must be ComputedResolution")
        if self.resolution.status is ResolutionStatus.RESOLVED:
            if self.selected_value is None or self.selected_unit is None:
                raise ScheduleResolutionError("resolved selection requires selected value and unit")
            if self.instance_document_class is not InstanceDocumentClass.SCHEDULE:
                raise ScheduleResolutionError("resolved C4 selection requires SCHEDULE document class")
            if self.binding_provenance_id is None:
                raise ScheduleResolutionError("resolved C4 selection requires binding provenance")
            if not self.instance_evidence_ids:
                raise ScheduleResolutionError("resolved C4 selection requires instance evidence")
        if not self.semantic_evidence_ids:
            raise ScheduleResolutionError("semantic evidence must not be empty")


@dataclass(frozen=True)
class ScheduleResolutionRequest:
    domain: WaitingPeriodSelectionDomain
    selection: WaitingPeriodInstanceSelection | None
    binding: GovernedBindingProvenance | None
    instance_source_stale: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.domain, WaitingPeriodSelectionDomain):
            raise ScheduleResolutionError("domain must be WaitingPeriodSelectionDomain")
        if self.selection is not None and not isinstance(self.selection, WaitingPeriodInstanceSelection):
            raise ScheduleResolutionError("selection must be WaitingPeriodInstanceSelection or None")
        if self.binding is not None and not isinstance(self.binding, GovernedBindingProvenance):
            raise ScheduleResolutionError("binding must be GovernedBindingProvenance or None")
        if type(self.instance_source_stale) is not bool:
            raise ScheduleResolutionError("instance_source_stale must be boolean")


def _resolution(*, review: ReviewState = ReviewState.APPROVED, source: SourceState = SourceState.CURRENT, validation: ValidationState = ValidationState.VALID, instance_available: bool = True) -> ComputedResolution:
    return compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=(
                InstanceAvailability.AVAILABLE if instance_available else InstanceAvailability.MISSING
            ),
            review_state=review,
            source_state=source,
            validation_state=validation,
        )
    )


def _unresolved_result(
    domain: WaitingPeriodSelectionDomain,
    *,
    resolution: ComputedResolution,
    selection: WaitingPeriodInstanceSelection | None = None,
    binding: GovernedBindingProvenance | None = None,
    telemetry: tuple[ScheduleResolutionTelemetry, ...] = (),
) -> ResolvedWaitingPeriodSelection:
    return ResolvedWaitingPeriodSelection(
        semantic_fact_id=domain.semantic_fact_id,
        policy_instance_reference=(selection.policy_instance_reference if selection else "UNBOUND_POLICY_INSTANCE"),
        resolution_cell_identity=domain.resolution_cell_identity,
        selected_value=None,
        selected_unit=None,
        semantic_evidence_ids=domain.semantic_evidence_ids,
        instance_evidence_ids=(selection.instance_evidence_ids if selection else ()),
        instance_document_class=(selection.document_class if selection else None),
        binding_provenance_id=(binding.binding_id if binding else None),
        ontology_version=domain.ontology_version,
        domain_version=domain.domain_version,
        instance_document_id=(selection.instance_document_id if selection else None),
        instance_document_version=(selection.instance_document_version if selection else None),
        instance_document_hash=(selection.instance_document_hash if selection else None),
        resolution=resolution,
        telemetry=telemetry,
    )


def resolve_schedule_selection(request: ScheduleResolutionRequest) -> ResolvedWaitingPeriodSelection:
    """Resolve one authenticated SCHEDULE selection against one certified semantic domain."""
    if not isinstance(request, ScheduleResolutionRequest):
        raise ScheduleResolutionError("request must be ScheduleResolutionRequest")
    domain = request.domain
    selection = request.selection
    binding = request.binding

    if selection is None:
        return _unresolved_result(domain, resolution=_resolution(instance_available=False))

    # Document-class gate: semantic-authority documents never enter the value-only resolver.
    if selection.document_class is not InstanceDocumentClass.SCHEDULE:
        return _unresolved_result(
            domain,
            selection=selection,
            binding=binding,
            resolution=_resolution(review=ReviewState.REVIEW_REQUIRED),
        )

    if binding is None or binding.review_state is not BindingReviewState.APPROVED:
        return _unresolved_result(
            domain,
            selection=selection,
            binding=binding,
            resolution=_resolution(review=ReviewState.REVIEW_REQUIRED),
        )

    binding_matches = (
        binding.binding_id == selection.binding_provenance_id
        and binding.document_class is InstanceDocumentClass.SCHEDULE
        and binding.document_class is selection.document_class
        and binding.bound_semantic_fact_id == domain.semantic_fact_id
        and binding.bound_semantic_fact_id == selection.semantic_fact_id
        and binding.semantic_domain_version == domain.domain_version
        and binding.source_document_id == selection.instance_document_id
        and binding.source_document_version == selection.instance_document_version
        and binding.source_document_hash == selection.instance_document_hash
        and selection.resolution_cell_identity == domain.resolution_cell_identity
    )
    if not binding_matches:
        return _unresolved_result(
            domain,
            selection=selection,
            binding=binding,
            resolution=_resolution(validation=ValidationState.CONFLICT),
        )

    if request.instance_source_stale:
        return _unresolved_result(
            domain,
            selection=selection,
            binding=binding,
            resolution=_resolution(source=SourceState.STALE),
        )

    try:
        normalized = normalize_duration(
            selection.selected_value,
            selection.selected_unit,
            domain.canonical_unit,
        )
    except DurationNormalizationError:
        return _unresolved_result(
            domain,
            selection=selection,
            binding=binding,
            resolution=_resolution(validation=ValidationState.CONFLICT),
        )

    if normalized.value not in domain.allowed_values:
        telemetry = (
            ScheduleResolutionTelemetry(
                code=ScheduleTelemetryCode.DOMAIN_MEMBERSHIP_REJECTED,
                semantic_fact_id=domain.semantic_fact_id,
                policy_instance_reference=selection.policy_instance_reference,
                selected_value=selection.selected_value,
                selected_unit=selection.selected_unit,
            ),
        )
        return _unresolved_result(
            domain,
            selection=selection,
            binding=binding,
            resolution=_resolution(validation=ValidationState.CONFLICT),
            telemetry=telemetry,
        )

    return ResolvedWaitingPeriodSelection(
        semantic_fact_id=domain.semantic_fact_id,
        policy_instance_reference=selection.policy_instance_reference,
        resolution_cell_identity=domain.resolution_cell_identity,
        selected_value=normalized.value,
        selected_unit=domain.canonical_unit,
        semantic_evidence_ids=domain.semantic_evidence_ids,
        instance_evidence_ids=selection.instance_evidence_ids,
        instance_document_class=selection.document_class,
        binding_provenance_id=binding.binding_id,
        ontology_version=domain.ontology_version,
        domain_version=domain.domain_version,
        instance_document_id=selection.instance_document_id,
        instance_document_version=selection.instance_document_version,
        instance_document_hash=selection.instance_document_hash,
        resolution=_resolution(),
    )


__all__ = [
    "BindingReviewState",
    "GovernedBindingProvenance",
    "InstanceDocumentClass",
    "ResolvedWaitingPeriodSelection",
    "ScheduleResolutionError",
    "ScheduleResolutionRequest",
    "ScheduleResolutionTelemetry",
    "ScheduleTelemetryCode",
    "WaitingPeriodInstanceSelection",
    "WaitingPeriodSelectionDomain",
    "resolve_schedule_selection",
]
