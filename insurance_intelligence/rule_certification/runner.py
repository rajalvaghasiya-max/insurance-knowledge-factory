"""Deterministic runner for generic governed-rule certification (MO-023J.2)."""

from __future__ import annotations

from collections.abc import Sequence

from insurance_intelligence.contracts.evidence import EvidenceResolverOutput
from insurance_intelligence.contracts.rule_certification import (
    RuleCertificationContractError,
    RuleCertificationExpectation,
    RuleCertificationResult,
    build_rule_certification_result,
)
from insurance_intelligence.topic_completeness.adapter import (
    TopicCompletenessAdapterError,
    evaluate_registered_topic,
)
from insurance_intelligence.topic_completeness.registry import (
    TopicCompletenessRegistry,
)


class RuleCertificationRunnerError(ValueError):
    """Raised when a certification case cannot be executed safely."""


def _text_values(values: Sequence[str], label: str) -> tuple[str, ...]:
    materialized = tuple(values)
    for value in materialized:
        if not isinstance(value, str) or not value.strip():
            raise RuleCertificationRunnerError(
                f"{label} must contain only non-empty strings"
            )
    normalized = tuple(value.strip() for value in materialized)
    if len(normalized) != len(set(normalized)):
        raise RuleCertificationRunnerError(f"{label} values must be unique")
    return normalized


def run_rule_certification(
    *,
    expectation: RuleCertificationExpectation,
    evidence_output: EvidenceResolverOutput,
    registry: TopicCompletenessRegistry | None = None,
    domain: str | None = None,
    trace_references: Sequence[str] | None = None,
    limitations: Sequence[str] = (),
) -> RuleCertificationResult:
    """Execute one certification expectation against governed resolver output.

    The runner performs no evidence resolution and contains no insurer-specific
    logic. It resolves the exact topic version declared by the expectation,
    evaluates completeness through the stable adapter, and delegates outcome
    derivation to the certification-result contract builder.
    """
    if not isinstance(expectation, RuleCertificationExpectation):
        raise RuleCertificationRunnerError(
            "expectation must be a RuleCertificationExpectation"
        )
    if not isinstance(evidence_output, EvidenceResolverOutput):
        raise RuleCertificationRunnerError(
            "evidence_output must be an EvidenceResolverOutput"
        )
    if registry is not None and not isinstance(registry, TopicCompletenessRegistry):
        raise RuleCertificationRunnerError(
            "registry must be a TopicCompletenessRegistry"
        )
    if domain is not None and (not isinstance(domain, str) or not domain.strip()):
        raise RuleCertificationRunnerError("domain must be a non-empty string")

    validated_limitations = _text_values(limitations, "limitations")
    if trace_references is None:
        validated_trace_references = tuple(
            event.trace_id for event in evidence_output.resolution_trace
        )
    else:
        validated_trace_references = _text_values(
            trace_references,
            "trace_references",
        )

    try:
        completeness_result = evaluate_registered_topic(
            topic_id=expectation.topic_id,
            topic_version=expectation.topic_version,
            evidence_output=evidence_output,
            registry=registry,
            domain=domain.strip() if domain is not None else None,
        )
        return build_rule_certification_result(
            expectation=expectation,
            evidence_output=evidence_output,
            completeness_result=completeness_result,
            trace_references=validated_trace_references,
            limitations=validated_limitations,
        )
    except (TopicCompletenessAdapterError, RuleCertificationContractError) as exc:
        raise RuleCertificationRunnerError(str(exc)) from exc
