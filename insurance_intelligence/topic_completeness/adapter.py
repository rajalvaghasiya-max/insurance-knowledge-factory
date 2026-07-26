"""Stable integration adapter for generic topic completeness (MO-023I.5)."""

from __future__ import annotations

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
) -> TopicCompletenessResult:
    """Resolve a registered topic and evaluate it against governed evidence.

    A new default registry is created when ``registry`` is omitted. The adapter
    performs lookup and boundary validation only; it does not mutate registry,
    definition, or resolver output state.
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

    try:
        return evaluate_topic_completeness(
            definition=definition,
            evidence_output=evidence_output,
        )
    except (TopicCompletenessEvaluationError, ValueError, TypeError) as exc:
        raise TopicCompletenessAdapterError(str(exc)) from exc
