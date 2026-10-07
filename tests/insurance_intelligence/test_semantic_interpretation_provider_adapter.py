from __future__ import annotations

import inspect
import json

from insurance_intelligence.contracts.semantic_interpretation import (
    FailedInterpretationAuditArtifact,
    InterpretationAuditArtifact,
)
from insurance_intelligence.llm.provider import DeterministicFakeTextProvider
from insurance_intelligence.semantic_interpretation import provider_adapter
from insurance_intelligence.semantic_interpretation.provider_adapter import (
    GovernedInterpretationVocabulary,
    build_semantic_text_request,
    interpret_with_provider,
)


def vocabulary(*, concept: str = "concept_alpha") -> GovernedInterpretationVocabulary:
    return GovernedInterpretationVocabulary(
        concept_ids=(concept, "concept_beta"),
        intent_ids=("understand_policy_term", "understand_policy_effect"),
        semantic_fact_ids=("definition", "applicability", "consequence"),
        scenario_fact_names=("customer_age", "declared_condition"),
    )


def resolved_output(*, concept: str = "concept_alpha", outcome: str = "POLICY_FACT_EXPLANATION") -> str:
    return json.dumps(
        {
            "interpretation_status": "RESOLVED",
            "confidence": 0.94,
            "primary_intent": "understand_policy_term",
            "requested_outcome": outcome,
            "governed_concept_candidates": [
                {"concept_id": concept, "confidence": 0.95}
            ],
            "selected_concept_id": concept,
            "requested_semantic_fact": "definition",
            "scenario_facts": [],
            "request_authority_class": "ASSERTIVE",
            "ambiguity_reasons": [],
            "competing_interpretations": [],
        }
    )


def ambiguous_output() -> str:
    return json.dumps(
        {
            "interpretation_status": "AMBIGUOUS",
            "confidence": 0.61,
            "primary_intent": "understand_policy_effect",
            "requested_outcome": None,
            "governed_concept_candidates": [
                {"concept_id": "concept_alpha", "confidence": 0.61},
                {"concept_id": "concept_beta", "confidence": 0.59},
            ],
            "selected_concept_id": None,
            "requested_semantic_fact": None,
            "scenario_facts": [],
            "request_authority_class": "ASSERTIVE",
            "ambiguity_reasons": ["multiple governed concepts remain plausible"],
            "competing_interpretations": [
                {
                    "primary_intent": "understand_policy_effect",
                    "requested_outcome": "POLICY_FACT_EXPLANATION",
                    "concept_id": "concept_alpha",
                    "requested_semantic_fact": "consequence",
                    "confidence": 0.61,
                },
                {
                    "primary_intent": "understand_policy_effect",
                    "requested_outcome": "POLICY_FACT_EXPLANATION",
                    "concept_id": "concept_beta",
                    "requested_semantic_fact": "applicability",
                    "confidence": 0.59,
                },
            ],
        }
    )


def run(provider: DeterministicFakeTextProvider, *, vocab: GovernedInterpretationVocabulary | None = None):
    return interpret_with_provider(
        request_id="request-p1a",
        user_text="Please explain what this term means for me.",
        vocabulary=vocab or vocabulary(),
        provider=provider,
        model_name="test-model",
        config_id="p1a-test-config",
        execution_id="execution-p1a",
        created_at="2026-10-07T17:30:00Z",
    )


def test_shared_text_provider_is_invoked_exactly_once_and_only_validated_output_is_exposed() -> None:
    provider = DeterministicFakeTextProvider(output_text=resolved_output())
    result = run(provider)
    assert provider.call_count == 1
    assert result.status == "RESOLVED"
    assert result.validated_interpretation is not None
    assert result.validated_interpretation.interpretation.selected_concept_id == "concept_alpha"
    assert isinstance(result.audit_artifact, InterpretationAuditArtifact)


def test_prompt_schema_does_not_expose_resolution_threshold_field() -> None:
    request = build_semantic_text_request(
        request_id="request-schema",
        user_text="Explain this.",
        vocabulary=vocabulary(),
        provider_name="deterministic_text_fake",
        model_name="test-model",
        timeout_seconds=5.0,
    )
    payload = json.loads(request.user_prompt)
    assert "resolution_threshold" not in payload["required_output_fields"]
    assert "provenance" not in payload["required_output_fields"]


def test_provider_cannot_invent_governed_concept_id() -> None:
    provider = DeterministicFakeTextProvider(output_text=resolved_output(concept="invented_concept"))
    result = run(provider)
    assert result.status == "FAILED"
    assert result.validated_interpretation is None
    assert isinstance(result.audit_artifact, FailedInterpretationAuditArtifact)
    assert result.audit_artifact.failure_attribution.code == "MALFORMED_PROVIDER_OUTPUT"


def test_prohibited_claim_outcome_reaches_deterministic_validator_and_fails_closed() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=resolved_output(outcome="CLAIM_PAYMENT_OUTCOME")
    )
    result = run(provider)
    assert result.status == "FAILED"
    assert isinstance(result.audit_artifact, FailedInterpretationAuditArtifact)
    assert result.audit_artifact.failure_attribution.code == "VALIDATOR_REJECTED"
    assert result.audit_artifact.proposed_interpretation is not None
    assert result.audit_artifact.proposed_interpretation.requested_outcome == "CLAIM_PAYMENT_OUTCOME"


def test_provider_cannot_smuggle_threshold_or_provenance_fields() -> None:
    raw = json.loads(resolved_output())
    raw["resolution_threshold"] = 0.01
    raw["provenance"] = {"model_name": "provider-controlled"}
    provider = DeterministicFakeTextProvider(output_text=json.dumps(raw))
    result = run(provider)
    assert result.status == "FAILED"
    assert isinstance(result.audit_artifact, FailedInterpretationAuditArtifact)
    assert result.audit_artifact.failure_attribution.code == "MALFORMED_PROVIDER_OUTPUT"


def test_timeout_is_audited_without_proposal_or_validated_marker() -> None:
    provider = DeterministicFakeTextProvider(failure="TIMEOUT")
    result = run(provider)
    assert provider.call_count == 1
    assert result.status == "FAILED"
    assert isinstance(result.audit_artifact, FailedInterpretationAuditArtifact)
    assert result.audit_artifact.proposed_interpretation is None
    assert result.audit_artifact.provider_output_sha256 is None
    assert result.audit_artifact.failure_attribution.origin == "INTERPRETATION"


def test_malformed_json_is_audited_by_output_hash() -> None:
    provider = DeterministicFakeTextProvider(output_text="{not-json")
    result = run(provider)
    assert result.status == "FAILED"
    assert isinstance(result.audit_artifact, FailedInterpretationAuditArtifact)
    assert result.audit_artifact.provider_output_sha256 is not None
    assert result.audit_artifact.failure_attribution.code == "MALFORMED_PROVIDER_OUTPUT"


def test_ambiguous_validated_output_routes_to_clarification_not_execution() -> None:
    provider = DeterministicFakeTextProvider(output_text=ambiguous_output())
    result = run(provider)
    assert result.status == "CLARIFICATION"
    assert result.validated_interpretation is not None
    assert result.clarification_route is not None
    assert result.clarification_route.clarification_required is True
    assert isinstance(result.audit_artifact, InterpretationAuditArtifact)


def test_arbitrary_caller_governed_concept_uses_same_generic_path() -> None:
    concept = "novel_governed_concept_xyz"
    provider = DeterministicFakeTextProvider(output_text=resolved_output(concept=concept))
    result = run(provider, vocab=vocabulary(concept=concept))
    assert result.status == "RESOLVED"
    assert result.validated_interpretation is not None
    assert result.validated_interpretation.interpretation.selected_concept_id == concept


def test_held_back_concept_has_no_source_specific_branch_or_example() -> None:
    source = inspect.getsource(provider_adapter).lower()
    assert "restoration" not in source
