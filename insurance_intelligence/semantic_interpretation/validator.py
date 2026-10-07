"""Deterministic validation for untrusted semantic-interpretation proposals."""
from __future__ import annotations

import re
from datetime import datetime

from insurance_intelligence.contracts.semantic_interpretation import (
    FAILURE_ORIGINS,
    INTERPRETATION_STATUSES,
    REQUEST_AUTHORITY_CLASSES,
    REQUESTED_OUTCOMES,
    SUPPORTED_CONTRACT_VERSION,
    ClarificationRoute,
    FailureAttribution,
    GovernedSemanticInterpretation,
    InterpretationAuditArtifact,
    ValidatedGovernedSemanticInterpretation,
)

VALIDATOR_VERSION = "1.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SemanticInterpretationValidationError(ValueError):
    """Raised when an interpreter proposal violates the containment contract."""


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SemanticInterpretationValidationError(f"{label} must be a non-empty string")
    return value


def _confidence(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SemanticInterpretationValidationError(f"{label} must be numeric")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise SemanticInterpretationValidationError(f"{label} must be between 0 and 1")
    return number


def _validate_provenance(interpretation: GovernedSemanticInterpretation) -> None:
    provenance = interpretation.provenance
    _nonempty(provenance.interpreter_version, "provenance.interpreter_version")
    _nonempty(provenance.model_name, "provenance.model_name")
    _nonempty(provenance.config_id, "provenance.config_id")
    if not isinstance(provenance.input_sha256, str) or not _SHA256_RE.fullmatch(
        provenance.input_sha256
    ):
        raise SemanticInterpretationValidationError(
            "provenance.input_sha256 must be a lowercase SHA-256 hex digest"
        )


def validate_interpretation(
    interpretation: GovernedSemanticInterpretation,
) -> ValidatedGovernedSemanticInterpretation:
    """Validate an untrusted proposal and return the only downstream-safe marker."""
    if not isinstance(interpretation, GovernedSemanticInterpretation):
        raise SemanticInterpretationValidationError(
            "interpretation must be a GovernedSemanticInterpretation"
        )
    if interpretation.contract_version != SUPPORTED_CONTRACT_VERSION:
        raise SemanticInterpretationValidationError(
            f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}"
        )
    _nonempty(interpretation.request_id, "request_id")
    if interpretation.interpretation_status not in INTERPRETATION_STATUSES:
        raise SemanticInterpretationValidationError("unsupported interpretation_status")
    confidence = _confidence(interpretation.confidence, "confidence")
    threshold = _confidence(interpretation.resolution_threshold, "resolution_threshold")
    if threshold <= 0.0:
        raise SemanticInterpretationValidationError("resolution_threshold must be greater than 0")
    if interpretation.request_authority_class not in REQUEST_AUTHORITY_CLASSES:
        raise SemanticInterpretationValidationError("unsupported request_authority_class")

    candidates = interpretation.governed_concept_candidates
    candidate_ids: list[str] = []
    candidate_confidences: dict[str, float] = {}
    for candidate in candidates:
        concept_id = _nonempty(candidate.concept_id, "governed_concept_candidates[].concept_id")
        if concept_id in candidate_confidences:
            raise SemanticInterpretationValidationError("governed concept candidate IDs must be unique")
        candidate_ids.append(concept_id)
        candidate_confidences[concept_id] = _confidence(
            candidate.confidence, "governed_concept_candidates[].confidence"
        )

    scenario_names: set[str] = set()
    for fact in interpretation.scenario_facts:
        name = _nonempty(fact.name, "scenario_facts[].name")
        _nonempty(fact.value, "scenario_facts[].value")
        if name in scenario_names:
            raise SemanticInterpretationValidationError("scenario fact names must be unique")
        scenario_names.add(name)

    for reason in interpretation.ambiguity_reasons:
        _nonempty(reason, "ambiguity_reasons[]")
    for competing in interpretation.competing_interpretations:
        _nonempty(competing.primary_intent, "competing_interpretations[].primary_intent")
        if competing.requested_outcome not in REQUESTED_OUTCOMES:
            raise SemanticInterpretationValidationError(
                "competing interpretation requested_outcome is outside the executable domain"
            )
        if competing.concept_id is not None:
            _nonempty(competing.concept_id, "competing_interpretations[].concept_id")
        if competing.requested_semantic_fact is not None:
            _nonempty(
                competing.requested_semantic_fact,
                "competing_interpretations[].requested_semantic_fact",
            )
        _confidence(competing.confidence, "competing_interpretations[].confidence")

    _validate_provenance(interpretation)

    if interpretation.interpretation_status == "RESOLVED":
        if confidence < threshold:
            raise SemanticInterpretationValidationError(
                "RESOLVED confidence cannot be below resolution_threshold"
            )
        _nonempty(interpretation.primary_intent, "primary_intent")
        if interpretation.requested_outcome not in REQUESTED_OUTCOMES:
            raise SemanticInterpretationValidationError(
                "requested_outcome is outside the executable domain"
            )
        selected = _nonempty(interpretation.selected_concept_id, "selected_concept_id")
        _nonempty(interpretation.requested_semantic_fact, "requested_semantic_fact")
        if selected not in candidate_confidences:
            raise SemanticInterpretationValidationError(
                "selected_concept_id must reference a governed concept candidate"
            )
        if candidate_confidences[selected] < threshold:
            raise SemanticInterpretationValidationError(
                "selected concept confidence cannot be below resolution_threshold"
            )
        if interpretation.ambiguity_reasons or interpretation.competing_interpretations:
            raise SemanticInterpretationValidationError(
                "RESOLVED interpretation cannot retain ambiguity or competing interpretations"
            )
    else:
        if interpretation.selected_concept_id is not None:
            raise SemanticInterpretationValidationError(
                "AMBIGUOUS/UNRESOLVED interpretation cannot select a concept"
            )
        if interpretation.requested_semantic_fact is not None:
            raise SemanticInterpretationValidationError(
                "AMBIGUOUS/UNRESOLVED interpretation cannot request an executable semantic fact"
            )
        if not interpretation.ambiguity_reasons:
            raise SemanticInterpretationValidationError(
                "AMBIGUOUS/UNRESOLVED interpretation requires an explicit reason"
            )
        if interpretation.requested_outcome is not None and interpretation.requested_outcome not in REQUESTED_OUTCOMES:
            raise SemanticInterpretationValidationError(
                "requested_outcome is outside the executable domain"
            )
        if interpretation.primary_intent is not None:
            _nonempty(interpretation.primary_intent, "primary_intent")
        if interpretation.interpretation_status == "AMBIGUOUS" and len(
            interpretation.competing_interpretations
        ) < 2:
            raise SemanticInterpretationValidationError(
                "AMBIGUOUS interpretation requires at least two competing interpretations"
            )

    return ValidatedGovernedSemanticInterpretation(
        interpretation=interpretation,
        validator_version=VALIDATOR_VERSION,
    )


def build_clarification_route(
    validated: ValidatedGovernedSemanticInterpretation,
) -> ClarificationRoute:
    interpretation = validated.interpretation
    if interpretation.interpretation_status == "RESOLVED":
        raise SemanticInterpretationValidationError(
            "RESOLVED interpretation must not be routed to clarification"
        )
    return ClarificationRoute(
        contract_version=SUPPORTED_CONTRACT_VERSION,
        request_id=interpretation.request_id,
        interpretation_status=interpretation.interpretation_status,
        clarification_required=True,
        reason_codes=interpretation.ambiguity_reasons,
        candidate_concept_ids=tuple(
            candidate.concept_id for candidate in interpretation.governed_concept_candidates
        ),
    )


def build_audit_artifact(
    *,
    artifact_id: str,
    execution_id: str,
    validated: ValidatedGovernedSemanticInterpretation,
    failure_origin: str = "NONE",
    failure_code: str = "SUCCESS",
    failure_detail: str = "validated interpretation",
    created_at: str,
) -> InterpretationAuditArtifact:
    if failure_origin not in FAILURE_ORIGINS:
        raise SemanticInterpretationValidationError("unsupported failure_origin")
    timestamp = _nonempty(created_at, "created_at")
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SemanticInterpretationValidationError("created_at must be ISO-8601") from exc
    interpretation = validated.interpretation
    return InterpretationAuditArtifact(
        contract_version=SUPPORTED_CONTRACT_VERSION,
        artifact_id=_nonempty(artifact_id, "artifact_id"),
        execution_id=_nonempty(execution_id, "execution_id"),
        request_id=interpretation.request_id,
        validated_interpretation=validated,
        failure_attribution=FailureAttribution(
            origin=failure_origin,
            code=_nonempty(failure_code, "failure_code"),
            detail=_nonempty(failure_detail, "failure_detail"),
        ),
        created_at=timestamp,
    )
