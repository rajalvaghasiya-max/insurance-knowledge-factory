"""Provider-backed semantic interpretation behind deterministic containment.

The provider is permitted to propose request meaning only. This module owns no
insurance facts and is intentionally disconnected from canonical orchestration.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping

from insurance_intelligence.contracts.semantic_interpretation import (
    INTERPRETATION_STATUSES,
    REQUEST_AUTHORITY_CLASSES,
    REQUESTED_OUTCOMES,
    ClarificationRoute,
    CompetingInterpretation,
    ConceptCandidate,
    FailedInterpretationAuditArtifact,
    GovernedSemanticInterpretation,
    InterpretationAuditArtifact,
    InterpreterProvenance,
    ScenarioFact,
    ValidatedGovernedSemanticInterpretation,
)
from insurance_intelligence.llm.provider import (
    LLMTextProvider,
    TextProviderInvocationResult,
    TextProviderRequest,
    invoke_text_provider,
)
from insurance_intelligence.semantic_interpretation.validator import (
    SemanticInterpretationValidationError,
    build_audit_artifact,
    build_clarification_route,
    build_failed_audit_artifact,
    validate_interpretation,
)

ADAPTER_VERSION = "gsi-provider-adapter-v2"
_PROVIDER_OUTPUT_KEYS = frozenset(
    {
        "interpretation_status",
        "confidence",
        "primary_intent",
        "requested_outcome",
        "governed_concept_candidates",
        "selected_concept_id",
        "requested_semantic_fact",
        "scenario_facts",
        "request_authority_class",
        "ambiguity_reasons",
        "competing_interpretations",
    }
)


class SemanticProviderOutputError(ValueError):
    """Raised when provider text cannot be converted to an untrusted proposal."""


@dataclass(frozen=True)
class GovernedInterpretationVocabulary:
    """Deterministic caller-owned vocabulary exposed to the interpreter."""

    concept_ids: tuple[str, ...]
    intent_ids: tuple[str, ...]
    semantic_fact_ids: tuple[str, ...]
    scenario_fact_names: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "concept_ids",
            "intent_ids",
            "semantic_fact_ids",
            "scenario_fact_names",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, tuple) or not values:
                raise ValueError(f"{field_name} must be a non-empty tuple")
            if not all(isinstance(value, str) and value.strip() for value in values):
                raise ValueError(f"{field_name} must contain non-empty strings")
            normalized = tuple(value.strip() for value in values)
            if len(normalized) != len(set(normalized)):
                raise ValueError(f"{field_name} must contain unique values")
            object.__setattr__(self, field_name, normalized)


@dataclass(frozen=True)
class SemanticInterpretationAttemptResult:
    status: str
    provider_invocation: TextProviderInvocationResult
    validated_interpretation: ValidatedGovernedSemanticInterpretation | None
    clarification_route: ClarificationRoute | None
    audit_artifact: InterpretationAuditArtifact | FailedInterpretationAuditArtifact

    def __post_init__(self) -> None:
        if self.status not in {"RESOLVED", "CLARIFICATION", "FAILED"}:
            raise ValueError("unsupported semantic interpretation attempt status")
        if self.status == "FAILED":
            if self.validated_interpretation is not None or self.clarification_route is not None:
                raise ValueError("FAILED attempt cannot expose validated or clarification output")
            if not isinstance(self.audit_artifact, FailedInterpretationAuditArtifact):
                raise ValueError("FAILED attempt requires failed audit artifact")
        elif self.status == "RESOLVED":
            if self.validated_interpretation is None or self.clarification_route is not None:
                raise ValueError("RESOLVED attempt requires only validated interpretation")
            if not isinstance(self.audit_artifact, InterpretationAuditArtifact):
                raise ValueError("RESOLVED attempt requires validated audit artifact")
        else:
            if self.validated_interpretation is None or self.clarification_route is None:
                raise ValueError("CLARIFICATION attempt requires validated interpretation and route")
            if not isinstance(self.audit_artifact, InterpretationAuditArtifact):
                raise ValueError("CLARIFICATION attempt requires validated audit artifact")


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise SemanticProviderOutputError(f"{label} must be an object")
    return value


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SemanticProviderOutputError(f"{label} must be null or non-empty text")
    return value.strip()


def _required_text(value: object, label: str) -> str:
    parsed = _optional_text(value, label)
    if parsed is None:
        raise SemanticProviderOutputError(f"{label} must be non-empty text")
    return parsed


def _required_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SemanticProviderOutputError(f"{label} must be numeric")
    return float(value)


def _text_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise SemanticProviderOutputError(f"{label} must be an array")
    return tuple(_required_text(item, f"{label}[]") for item in value)


def _ensure_governed(value: str | None, allowed: tuple[str, ...], label: str) -> None:
    if value is not None and value not in allowed:
        raise SemanticProviderOutputError(f"{label} is not in the caller-governed vocabulary")


def _nullable_enum(values: tuple[str, ...]) -> dict[str, object]:
    return {"type": ["string", "null"], "enum": [*values, None]}


def _semantic_response_schema(vocabulary: GovernedInterpretationVocabulary) -> dict[str, object]:
    """Build strict provider structure from deterministic governed domains only."""
    candidate = {
        "type": "object",
        "properties": {
            "concept_id": {"type": "string", "enum": list(vocabulary.concept_ids)},
            "confidence": {"type": "number"},
        },
        "required": ["concept_id", "confidence"],
        "additionalProperties": False,
    }
    scenario = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "enum": list(vocabulary.scenario_fact_names)},
            "value": {"type": "string"},
        },
        "required": ["name", "value"],
        "additionalProperties": False,
    }
    competing = {
        "type": "object",
        "properties": {
            "primary_intent": {"type": "string", "enum": list(vocabulary.intent_ids)},
            "requested_outcome": {"type": "string", "enum": sorted(REQUESTED_OUTCOMES)},
            "concept_id": _nullable_enum(vocabulary.concept_ids),
            "requested_semantic_fact": _nullable_enum(vocabulary.semantic_fact_ids),
            "confidence": {"type": "number"},
        },
        "required": [
            "primary_intent",
            "requested_outcome",
            "concept_id",
            "requested_semantic_fact",
            "confidence",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "interpretation_status": {"type": "string", "enum": sorted(INTERPRETATION_STATUSES)},
            "confidence": {"type": "number"},
            "primary_intent": _nullable_enum(vocabulary.intent_ids),
            "requested_outcome": _nullable_enum(tuple(sorted(REQUESTED_OUTCOMES))),
            "governed_concept_candidates": {"type": "array", "items": candidate},
            "selected_concept_id": _nullable_enum(vocabulary.concept_ids),
            "requested_semantic_fact": _nullable_enum(vocabulary.semantic_fact_ids),
            "scenario_facts": {"type": "array", "items": scenario},
            "request_authority_class": {"type": "string", "enum": sorted(REQUEST_AUTHORITY_CLASSES)},
            "ambiguity_reasons": {"type": "array", "items": {"type": "string"}},
            "competing_interpretations": {"type": "array", "items": competing},
        },
        "required": sorted(_PROVIDER_OUTPUT_KEYS),
        "additionalProperties": False,
    }


def build_semantic_text_request(
    *,
    request_id: str,
    user_text: str,
    vocabulary: GovernedInterpretationVocabulary,
    provider_name: str,
    model_name: str,
    timeout_seconds: float,
) -> TextProviderRequest:
    """Build a generic JSON-only interpretation request without domain examples."""
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("request_id must be non-empty")
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError("user_text must be non-empty")

    system_prompt = (
        "Map the user's language into request meaning only. You have zero insurance authority. "
        "Return exactly one JSON object and no prose. Use only IDs supplied in the governed "
        "vocabulary. Interpretation ambiguity means uncertainty about what the user means or "
        "which governed request mapping applies; missing policy wording, product-specific terms, "
        "or unknown downstream insurance truth do not by themselves make the language ambiguous. "
        "If interpretation_status is RESOLVED, ambiguity_reasons and competing_interpretations "
        "must both be empty. If material request-meaning ambiguity remains, use AMBIGUOUS or "
        "UNRESOLVED instead of RESOLVED, set selected_concept_id and requested_semantic_fact to "
        "null, and provide explicit ambiguity_reasons; AMBIGUOUS requires at least two competing "
        "interpretations. Each scenario fact name may appear at most once; when multiple user "
        "details map to the same governed scenario fact name, merge those details into one value. "
        "Do not decide policy truth, coverage, claim admissibility, claim approval, claim rejection, "
        "payment, non-payment, suitability, or recommendation truth. Do not emit provenance or "
        "any confidence threshold."
    )
    payload = {
        "request_id": request_id.strip(),
        "user_text": user_text.strip(),
        "governed_vocabulary": {
            "concept_ids": list(vocabulary.concept_ids),
            "intent_ids": list(vocabulary.intent_ids),
            "semantic_fact_ids": list(vocabulary.semantic_fact_ids),
            "scenario_fact_names": list(vocabulary.scenario_fact_names),
        },
        "required_output_fields": sorted(_PROVIDER_OUTPUT_KEYS),
    }
    return TextProviderRequest(
        provider_request_id=_stable_id(
            "gsi-provider-request", request_id.strip(), _sha256_text(user_text.strip())
        ),
        provider_name=provider_name,
        model_name=model_name,
        system_prompt=system_prompt,
        user_prompt=json.dumps(payload, sort_keys=True, ensure_ascii=False),
        timeout_seconds=timeout_seconds,
        response_schema_name="governed_semantic_interpretation",
        response_json_schema=json.dumps(
            _semantic_response_schema(vocabulary),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ),
    )


def parse_provider_interpretation(
    *,
    output_text: str,
    request_id: str,
    vocabulary: GovernedInterpretationVocabulary,
    provenance: InterpreterProvenance,
) -> GovernedSemanticInterpretation:
    """Parse provider JSON into an untrusted proposal and reject invented vocabulary."""
    try:
        raw = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise SemanticProviderOutputError("provider output must be valid JSON") from exc
    root = _require_mapping(raw, "provider output")
    keys = frozenset(root)
    if keys != _PROVIDER_OUTPUT_KEYS:
        missing = sorted(_PROVIDER_OUTPUT_KEYS - keys)
        extra = sorted(keys - _PROVIDER_OUTPUT_KEYS)
        raise SemanticProviderOutputError(
            f"provider output keys must match schema; missing={missing} extra={extra}"
        )

    primary_intent = _optional_text(root["primary_intent"], "primary_intent")
    _ensure_governed(primary_intent, vocabulary.intent_ids, "primary_intent")
    selected_concept_id = _optional_text(root["selected_concept_id"], "selected_concept_id")
    _ensure_governed(selected_concept_id, vocabulary.concept_ids, "selected_concept_id")
    requested_semantic_fact = _optional_text(
        root["requested_semantic_fact"], "requested_semantic_fact"
    )
    _ensure_governed(requested_semantic_fact, vocabulary.semantic_fact_ids, "requested_semantic_fact")

    raw_candidates = root["governed_concept_candidates"]
    if not isinstance(raw_candidates, list):
        raise SemanticProviderOutputError("governed_concept_candidates must be an array")
    candidates: list[ConceptCandidate] = []
    for index, item in enumerate(raw_candidates):
        candidate = _require_mapping(item, f"governed_concept_candidates[{index}]")
        if frozenset(candidate) != {"concept_id", "confidence"}:
            raise SemanticProviderOutputError("concept candidate keys must be concept_id/confidence")
        concept_id = _required_text(candidate["concept_id"], "candidate.concept_id")
        _ensure_governed(concept_id, vocabulary.concept_ids, "candidate.concept_id")
        candidates.append(ConceptCandidate(concept_id=concept_id, confidence=_required_number(candidate["confidence"], "candidate.confidence")))

    raw_scenario = root["scenario_facts"]
    if not isinstance(raw_scenario, list):
        raise SemanticProviderOutputError("scenario_facts must be an array")
    scenario_facts: list[ScenarioFact] = []
    for index, item in enumerate(raw_scenario):
        fact = _require_mapping(item, f"scenario_facts[{index}]")
        if frozenset(fact) != {"name", "value"}:
            raise SemanticProviderOutputError("scenario fact keys must be name/value")
        name = _required_text(fact["name"], "scenario_fact.name")
        _ensure_governed(name, vocabulary.scenario_fact_names, "scenario_fact.name")
        scenario_facts.append(ScenarioFact(name=name, value=_required_text(fact["value"], "scenario_fact.value")))

    raw_competing = root["competing_interpretations"]
    if not isinstance(raw_competing, list):
        raise SemanticProviderOutputError("competing_interpretations must be an array")
    competing: list[CompetingInterpretation] = []
    expected_competing_keys = {"primary_intent", "requested_outcome", "concept_id", "requested_semantic_fact", "confidence"}
    for index, item in enumerate(raw_competing):
        alternative = _require_mapping(item, f"competing_interpretations[{index}]")
        if frozenset(alternative) != expected_competing_keys:
            raise SemanticProviderOutputError("competing interpretation keys do not match schema")
        alt_intent = _required_text(alternative["primary_intent"], "competing.primary_intent")
        _ensure_governed(alt_intent, vocabulary.intent_ids, "competing.primary_intent")
        alt_concept = _optional_text(alternative["concept_id"], "competing.concept_id")
        _ensure_governed(alt_concept, vocabulary.concept_ids, "competing.concept_id")
        alt_fact = _optional_text(alternative["requested_semantic_fact"], "competing.requested_semantic_fact")
        _ensure_governed(alt_fact, vocabulary.semantic_fact_ids, "competing.requested_semantic_fact")
        competing.append(
            CompetingInterpretation(
                primary_intent=alt_intent,
                requested_outcome=_required_text(alternative["requested_outcome"], "competing.requested_outcome"),
                concept_id=alt_concept,
                requested_semantic_fact=alt_fact,
                confidence=_required_number(alternative["confidence"], "competing.confidence"),
            )
        )

    return GovernedSemanticInterpretation(
        contract_version="1.0",
        request_id=request_id,
        interpretation_status=_required_text(root["interpretation_status"], "interpretation_status"),
        confidence=_required_number(root["confidence"], "confidence"),
        primary_intent=primary_intent,
        requested_outcome=_optional_text(root["requested_outcome"], "requested_outcome"),
        governed_concept_candidates=tuple(candidates),
        selected_concept_id=selected_concept_id,
        requested_semantic_fact=requested_semantic_fact,
        scenario_facts=tuple(scenario_facts),
        request_authority_class=_required_text(root["request_authority_class"], "request_authority_class"),
        ambiguity_reasons=_text_list(root["ambiguity_reasons"], "ambiguity_reasons"),
        competing_interpretations=tuple(competing),
        provenance=provenance,
    )


def interpret_with_provider(
    *,
    request_id: str,
    user_text: str,
    vocabulary: GovernedInterpretationVocabulary,
    provider: LLMTextProvider,
    model_name: str,
    config_id: str,
    interpreter_version: str = ADAPTER_VERSION,
    timeout_seconds: float = 15.0,
    execution_id: str,
    created_at: str,
) -> SemanticInterpretationAttemptResult:
    """Run one provider attempt and contain every exit behind deterministic artifacts."""
    input_sha256 = _sha256_text(user_text.strip())
    provenance = InterpreterProvenance(
        interpreter_version=interpreter_version,
        model_name=model_name,
        config_id=config_id,
        input_sha256=input_sha256,
    )
    request = build_semantic_text_request(
        request_id=request_id,
        user_text=user_text,
        vocabulary=vocabulary,
        provider_name=provider.provider_name,
        model_name=model_name,
        timeout_seconds=timeout_seconds,
    )
    invocation = invoke_text_provider(provider, request)
    artifact_id = _stable_id("gsi-audit", execution_id, request_id, invocation.invocation_id)

    if invocation.response.status != "SUCCEEDED":
        audit = build_failed_audit_artifact(
            artifact_id=artifact_id,
            execution_id=execution_id,
            request_id=request_id,
            provenance=provenance,
            failure_code=invocation.normalized_failure or invocation.response.status,
            failure_detail=invocation.response.error_message or "provider invocation failed",
            created_at=created_at,
        )
        return SemanticInterpretationAttemptResult(
            status="FAILED",
            provider_invocation=invocation,
            validated_interpretation=None,
            clarification_route=None,
            audit_artifact=audit,
        )

    output_text = invocation.response.output_text or ""
    output_hash = _sha256_text(output_text)
    try:
        proposal = parse_provider_interpretation(
            output_text=output_text,
            request_id=request_id,
            vocabulary=vocabulary,
            provenance=provenance,
        )
    except (SemanticProviderOutputError, TypeError, ValueError) as exc:
        audit = build_failed_audit_artifact(
            artifact_id=artifact_id,
            execution_id=execution_id,
            request_id=request_id,
            provenance=provenance,
            provider_output_sha256=output_hash,
            failure_code="MALFORMED_PROVIDER_OUTPUT",
            failure_detail=str(exc) or type(exc).__name__,
            created_at=created_at,
        )
        return SemanticInterpretationAttemptResult(
            status="FAILED",
            provider_invocation=invocation,
            validated_interpretation=None,
            clarification_route=None,
            audit_artifact=audit,
        )

    try:
        validated = validate_interpretation(proposal)
    except SemanticInterpretationValidationError as exc:
        audit = build_failed_audit_artifact(
            artifact_id=artifact_id,
            execution_id=execution_id,
            request_id=request_id,
            provenance=provenance,
            proposed_interpretation=proposal,
            provider_output_sha256=output_hash,
            failure_code="VALIDATOR_REJECTED",
            failure_detail=str(exc) or type(exc).__name__,
            created_at=created_at,
        )
        return SemanticInterpretationAttemptResult(
            status="FAILED",
            provider_invocation=invocation,
            validated_interpretation=None,
            clarification_route=None,
            audit_artifact=audit,
        )

    audit = build_audit_artifact(
        artifact_id=artifact_id,
        execution_id=execution_id,
        validated=validated,
        created_at=created_at,
    )
    if proposal.interpretation_status == "RESOLVED":
        return SemanticInterpretationAttemptResult(
            status="RESOLVED",
            provider_invocation=invocation,
            validated_interpretation=validated,
            clarification_route=None,
            audit_artifact=audit,
        )
    clarification = build_clarification_route(validated)
    return SemanticInterpretationAttemptResult(
        status="CLARIFICATION",
        provider_invocation=invocation,
        validated_interpretation=validated,
        clarification_route=clarification,
        audit_artifact=audit,
    )
