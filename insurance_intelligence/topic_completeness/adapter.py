"""Stable integration adapter for generic topic completeness (MO-023I.5)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from insurance_intelligence.contracts.evidence import EvidenceResolverOutput
from insurance_intelligence.contracts.topic_completeness import TopicCompletenessResult
from insurance_intelligence.topic_completeness.catalogue import (
    build_default_topic_registry,
)
from insurance_intelligence.topic_completeness.evaluator import (
    TopicCompletenessEvaluationError,
    evaluate_topic_completeness,
)
from insurance_intelligence.topic_completeness.registry import (
    TopicCompletenessRegistry,
    TopicCompletenessRegistryError,
)

if TYPE_CHECKING:
    from insurance_intelligence.contracts.topic_profile import TopicProfile


class TopicCompletenessAdapterError(ValueError):
    """Raised when adapter input, lookup, or evaluation is invalid."""


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TopicCompletenessAdapterError(f"{label} must be a non-empty string")
    return value.strip()


def evaluate_registered_topic(
    *,
    topic_id: str,
    evidence_output: EvidenceResolverOutput,
    registry: TopicCompletenessRegistry | None = None,
    topic_version: str | None = None,
    domain: str | None = None,
    profile: TopicProfile | None = None,
) -> TopicCompletenessResult:
    """Resolve a registered topic and evaluate it against governed evidence.

    A new default registry is created when ``registry`` is omitted. When a
    validated ``TopicProfile`` is supplied, its required/optional classification
    is applied only for this evaluation. The registered generic topic definition
    is never mutated.
    """
    validated_topic_id = _required_text(topic_id, "topic_id")
    validated_version = (
        _required_text(topic_version, "topic_version")
        if topic_version is not None
        else None
    )
    validated_domain = (
        _required_text(domain, "domain") if domain is not None else None
    )

    if not isinstance(evidence_output, EvidenceResolverOutput):
        raise TopicCompletenessAdapterError(
            "evidence_output must be an EvidenceResolverOutput"
        )
    if registry is None:
        resolved_registry = build_default_topic_registry()
    elif isinstance(registry, TopicCompletenessRegistry):
        resolved_registry = registry
    else:
        raise TopicCompletenessAdapterError(
            "registry must be a TopicCompletenessRegistry"
        )

    try:
        definition = resolved_registry.get(
            validated_topic_id,
            validated_version,
        )
    except TopicCompletenessRegistryError as exc:
        raise TopicCompletenessAdapterError(str(exc)) from exc

    if validated_domain is not None and definition.domain != validated_domain:
        raise TopicCompletenessAdapterError(
            "requested domain does not match registered topic definition: "
            f"{validated_domain!r} != {definition.domain!r}"
        )

    if profile is not None:
        from insurance_intelligence.contracts.topic_profile import (
            TopicProfile,
            TopicProfileContractError,
            validate_registered_topic_profile,
        )

        if not isinstance(profile, TopicProfile):
            raise TopicCompletenessAdapterError("profile must be a TopicProfile")
        if profile.topic_id != definition.topic_id or profile.topic_version != definition.topic_version:
            raise TopicCompletenessAdapterError(
                "profile topic identity does not match requested registered topic"
            )
        if validated_domain is not None and profile.domain != validated_domain:
            raise TopicCompletenessAdapterError(
                "profile domain does not match requested domain"
            )
        try:
            validation = validate_registered_topic_profile(
                profile=profile,
                registry=resolved_registry,
            )
        except TopicProfileContractError as exc:
            raise TopicCompletenessAdapterError(str(exc)) from exc
        if not validation.valid:
            raise TopicCompletenessAdapterError(
                "profile is not valid for the registered topic: "
                + "; ".join(validation.failures)
            )
        required_ids = set(profile.required_component_ids)
        definition = replace(
            definition,
            components=tuple(
                replace(component, required=component.component_id in required_ids)
                for component in definition.components
            ),
        )

    try:
        return evaluate_topic_completeness(
            definition=definition,
            evidence_output=evidence_output,
        )
    except (TopicCompletenessEvaluationError, ValueError, TypeError) as exc:
        raise TopicCompletenessAdapterError(str(exc)) from exc
