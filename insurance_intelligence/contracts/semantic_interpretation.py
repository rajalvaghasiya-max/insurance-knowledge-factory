"""Typed contracts for the Governed Semantic Interpreter containment boundary.

This module deliberately contains no model/provider invocation and no insurance
truth. It only represents a proposed interpretation and the deterministic
artifacts that may be produced after validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

SUPPORTED_CONTRACT_VERSION = "1.0"
INTERPRETATION_STATUSES = frozenset({"RESOLVED", "AMBIGUOUS", "UNRESOLVED"})
REQUESTED_OUTCOMES = frozenset(
    {
        "POLICY_FACT_EXPLANATION",
        "INSURANCE_MECHANICS_EXPLANATION",
        "POLICY_FACT_COMPARISON",
        "CONTEXTUAL_POLICY_EXPLANATION",
        "ADVISORY_DECISION_SUPPORT",
    }
)
REQUEST_AUTHORITY_CLASSES = frozenset({"ASSERTIVE", "ADVISORY", "MIXED", "UNRESOLVED"})
FAILURE_ORIGINS = frozenset(
    {"INTERPRETATION", "DOWNSTREAM_GOVERNANCE", "CUSTOMER_QUALITY", "NONE"}
)


@dataclass(frozen=True)
class ConceptCandidate:
    concept_id: str
    confidence: float


@dataclass(frozen=True)
class ScenarioFact:
    name: str
    value: str


@dataclass(frozen=True)
class CompetingInterpretation:
    primary_intent: str
    requested_outcome: str
    concept_id: str | None
    requested_semantic_fact: str | None
    confidence: float


@dataclass(frozen=True)
class InterpreterProvenance:
    interpreter_version: str
    model_name: str
    config_id: str
    input_sha256: str


@dataclass(frozen=True)
class GovernedSemanticInterpretation:
    """Untrusted interpreter proposal. Never pass this directly to orchestration.

    Deliberately does not contain a resolution threshold. The probabilistic
    interpreter may report confidence, but it may never choose the safety bar
    used to admit its own output.
    """

    contract_version: str
    request_id: str
    interpretation_status: str
    confidence: float
    primary_intent: str | None
    requested_outcome: str | None
    governed_concept_candidates: tuple[ConceptCandidate, ...]
    selected_concept_id: str | None
    requested_semantic_fact: str | None
    scenario_facts: tuple[ScenarioFact, ...]
    request_authority_class: str
    ambiguity_reasons: tuple[str, ...]
    competing_interpretations: tuple[CompetingInterpretation, ...]
    provenance: InterpreterProvenance


@dataclass(frozen=True)
class ValidatedGovernedSemanticInterpretation:
    """Marker returned only by the deterministic validator."""

    interpretation: GovernedSemanticInterpretation
    validator_version: str
    resolution_threshold_applied: float


@dataclass(frozen=True)
class ClarificationRoute:
    contract_version: str
    request_id: str
    interpretation_status: str
    clarification_required: bool
    reason_codes: tuple[str, ...]
    candidate_concept_ids: tuple[str, ...]


@dataclass(frozen=True)
class FailureAttribution:
    origin: str
    code: str
    detail: str


@dataclass(frozen=True)
class InterpretationAuditArtifact:
    contract_version: str
    artifact_id: str
    execution_id: str
    request_id: str
    validated_interpretation: ValidatedGovernedSemanticInterpretation
    failure_attribution: FailureAttribution
    created_at: str


def audit_artifact_as_dict(artifact: InterpretationAuditArtifact) -> Mapping[str, object]:
    """Return a JSON-serializable audit record without losing typed provenance."""
    from dataclasses import asdict

    return asdict(artifact)
