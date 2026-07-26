"""Generic pilot topic-profile contracts and registry alignment (P2.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from insurance_intelligence.contracts.reasoning_plan import DOMAIN_VALUES
from insurance_intelligence.contracts.topic_completeness import TopicDefinition
from insurance_intelligence.topic_completeness.registry import (
    TopicCompletenessRegistry,
    TopicCompletenessRegistryError,
)

SUPPORTED_PROFILE_CONTRACT_VERSION = "1.0"


class TopicProfileContractError(ValueError):
    """Raised when a topic profile is invalid or misaligned."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TopicProfileContractError(f"{label} must be a non-empty string")
    return value.strip()


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise TopicProfileContractError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class TopicProfile:
    contract_version: str
    profile_id: str
    profile_version: str
    domain: str
    topic_id: str
    topic_version: str
    required_component_ids: tuple[str, ...]
    optional_component_ids: tuple[str, ...]
    explanation_blocking_component_ids: tuple[str, ...]


@dataclass(frozen=True)
class TopicProfileValidationResult:
    profile_id: str
    profile_version: str
    topic_id: str
    topic_version: str
    valid: bool
    failures: tuple[str, ...]


def build_topic_profile(
    *,
    profile_id: str,
    profile_version: str,
    definition: TopicDefinition,
    required_component_ids: Sequence[str],
    optional_component_ids: Sequence[str] = (),
    explanation_blocking_component_ids: Sequence[str] | None = None,
    contract_version: str = SUPPORTED_PROFILE_CONTRACT_VERSION,
) -> TopicProfile:
    if contract_version != SUPPORTED_PROFILE_CONTRACT_VERSION:
        raise TopicProfileContractError(
            f"contract_version must be {SUPPORTED_PROFILE_CONTRACT_VERSION!r}"
        )
    if not isinstance(definition, TopicDefinition):
        raise TopicProfileContractError("definition must be a TopicDefinition")

    required = _unique(required_component_ids, "required_component_ids")
    optional = _unique(optional_component_ids, "optional_component_ids")
    if not required:
        raise TopicProfileContractError("required_component_ids must not be empty")
    overlap = set(required) & set(optional)
    if overlap:
        raise TopicProfileContractError(
            f"required and optional components must not overlap: {sorted(overlap)}"
        )

    definition_ids = {component.component_id for component in definition.components}
    profiled_ids = set(required) | set(optional)
    unknown = profiled_ids - definition_ids
    if unknown:
        raise TopicProfileContractError(
            f"profile references unknown topic components {sorted(unknown)}"
        )
    omitted = definition_ids - profiled_ids
    if omitted:
        raise TopicProfileContractError(
            f"profile must classify every registered topic component; omitted {sorted(omitted)}"
        )

    catalogue_required = {
        component.component_id for component in definition.components if component.required
    }
    weakened = catalogue_required - set(required)
    if weakened:
        raise TopicProfileContractError(
            f"profile cannot weaken registered required components {sorted(weakened)}"
        )

    blocking = (
        required
        if explanation_blocking_component_ids is None
        else _unique(
            explanation_blocking_component_ids,
            "explanation_blocking_component_ids",
        )
    )
    non_required_blockers = set(blocking) - set(required)
    if non_required_blockers:
        raise TopicProfileContractError(
            "explanation-blocking components must be required components; got "
            f"{sorted(non_required_blockers)}"
        )

    return TopicProfile(
        contract_version=contract_version,
        profile_id=_text(profile_id, "profile_id"),
        profile_version=_text(profile_version, "profile_version"),
        domain=definition.domain,
        topic_id=definition.topic_id,
        topic_version=definition.topic_version,
        required_component_ids=required,
        optional_component_ids=optional,
        explanation_blocking_component_ids=blocking,
    )


def validate_registered_topic_profile(
    *,
    profile: TopicProfile,
    registry: TopicCompletenessRegistry,
) -> TopicProfileValidationResult:
    if not isinstance(profile, TopicProfile):
        raise TopicProfileContractError("profile must be a TopicProfile")
    if not isinstance(registry, TopicCompletenessRegistry):
        raise TopicProfileContractError("registry must be a TopicCompletenessRegistry")
    if profile.domain not in DOMAIN_VALUES:
        raise TopicProfileContractError(
            f"profile domain must be one of {sorted(DOMAIN_VALUES)}"
        )

    failures: list[str] = []
    try:
        definition = registry.get(profile.topic_id, profile.topic_version)
    except TopicCompletenessRegistryError:
        failures.append(
            f"Registered topic not found: {profile.topic_id}@{profile.topic_version}"
        )
    else:
        if definition.domain != profile.domain:
            failures.append("Profile and registered topic domains do not match.")
        definition_ids = {component.component_id for component in definition.components}
        profile_ids = set(profile.required_component_ids) | set(
            profile.optional_component_ids
        )
        if profile_ids != definition_ids:
            failures.append("Profile component classification does not match registered topic.")
        catalogue_required = {
            component.component_id
            for component in definition.components
            if component.required
        }
        if not catalogue_required.issubset(profile.required_component_ids):
            failures.append("Profile weakens registered required components.")
        if not set(profile.explanation_blocking_component_ids).issubset(
            profile.required_component_ids
        ):
            failures.append("Explanation blockers are not all required components.")

    return TopicProfileValidationResult(
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        topic_id=profile.topic_id,
        topic_version=profile.topic_version,
        valid=not failures,
        failures=tuple(failures),
    )
