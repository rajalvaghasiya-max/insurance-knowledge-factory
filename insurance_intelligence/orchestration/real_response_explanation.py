"""Generic extension of the proven real response path through authority-enforced explanation.

This module composes the existing real decision path with the existing
AuthorityEnforcedExplanationGenerator. Presentation policy is supplied as a dependency;
this orchestration layer does not invent product-specific explanation semantics.
It intentionally stops at EXPLANATION_AUTHORITY_ENFORCED.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict

from insurance_intelligence.authority_enforced_explanation import (
    AuthorityEnforcedExplanationGenerator,
)
from insurance_intelligence.contracts.authority_enforcement import AuthorityEnforcementResult
from insurance_intelligence.contracts.education_publication import EducationPublicationRecord
from insurance_intelligence.contracts.explanation import (
    ExplanationGeneratorOutput,
    build_output as build_explanation_output,
)
from insurance_intelligence.contracts.intent import IntentAnalyzerOutput
from insurance_intelligence.contracts.reasoning import ReasoningEngineOutput
from insurance_intelligence.explanation.registry import ExplanationStyleRegistry, TerminologyRegistry
from insurance_intelligence.orchestration.intelligence_adapters import (
    build_intelligence_stage_adapter,
    build_raw_intelligence_stage_output,
)
from insurance_intelligence.orchestration.real_response_decision import (
    build_real_response_decision_adapters,
)
from insurance_intelligence.orchestration.real_response_prefix import (
    RealResponsePrefixDependencies,
    RealResponsePrefixError,
)


def _output_id(execution_id: str, stage: str) -> str:
    return f"{execution_id}:real:{stage.lower()}"


EducationPublicationLookup = Callable[[object, IntentAnalyzerOutput], Sequence[EducationPublicationRecord]]


def build_real_response_explanation_adapters(
    *,
    dependencies: RealResponsePrefixDependencies,
    style_registry: ExplanationStyleRegistry,
    terminology_registry: TerminologyRegistry | None = None,
    education_publication_lookup: EducationPublicationLookup | None = None,
):
    """Build the proven real path plus canonical authority-enforced explanation."""
    if not isinstance(style_registry, ExplanationStyleRegistry):
        raise RealResponsePrefixError("style_registry must be ExplanationStyleRegistry")
    if terminology_registry is not None and not isinstance(terminology_registry, TerminologyRegistry):
        raise RealResponsePrefixError("terminology_registry must be TerminologyRegistry when provided")
    if education_publication_lookup is not None and not callable(education_publication_lookup):
        raise RealResponsePrefixError("education_publication_lookup must be callable when provided")

    prior = build_real_response_decision_adapters(dependencies=dependencies)

    def explanation(*, request, stage, input_ids, knowledge_snapshot_id):
        if stage != "EXPLANATION_AUTHORITY_ENFORCED":
            raise RealResponsePrefixError("explanation stage mismatch")
        authority_result = dependencies.store.get(
            _output_id(request.execution_id, "DECISION_GATE_AUTHORITY_ENFORCED"),
            expected_type=AuthorityEnforcementResult,
        )
        reasoning = dependencies.store.get(
            _output_id(request.execution_id, "REASONING"),
            expected_type=ReasoningEngineOutput,
        )
        findings_by_id = {finding.finding_id: finding for finding in reasoning.findings}
        intent_output = dependencies.store.get(
            _output_id(request.execution_id, "INTENT_ANALYSIS"),
            expected_type=IntentAnalyzerOutput,
        )
        education_publications = ()
        if education_publication_lookup is not None:
            resolved = tuple(education_publication_lookup(request, intent_output))
            if any(not isinstance(item, EducationPublicationRecord) for item in resolved):
                raise RealResponsePrefixError(
                    "education_publication_lookup must return EducationPublicationRecord values"
                )
            education_publications = resolved
        decision_output = authority_result.decision_output
        if decision_output is None:
            raise RealResponsePrefixError("authority-enforced decision omitted DecisionGateOutput")

        if decision_output.decision in {"APPROVED", "APPROVED_WITH_LIMITATIONS", "CLARIFICATION_REQUIRED"}:
            output = AuthorityEnforcedExplanationGenerator().generate(
                authority_result=authority_result,
                findings_by_id=findings_by_id,
                style_registry=style_registry,
                terminology_registry=terminology_registry,
                audience=request.audience,
                reading_level="SIMPLE",
                explanation_mode="PLAIN_LANGUAGE",
                communication_context=dict(request.customer_context),
                education_publications=education_publications,
            )
        else:
            limitations = tuple(
                dict.fromkeys(
                    (
                        *decision_output.limitations,
                        *reasoning.limitations,
                        *(issue.description for issue in decision_output.safety_issues),
                        *decision_output.human_review_reasons,
                        "The requested conclusion cannot be determined safely from the governed reasoning available.",
                    )
                )
            )
            output = build_explanation_output(
                request_id=request.execution_id,
                explanation_id=f"{request.execution_id}:withheld-explanation",
                audience=request.audience,
                reading_level="SIMPLE",
                explanation_mode="LIMITATION_NOTICE",
                sections=(),
                terminology_substitutions=(),
                fidelity_checks=(),
                fidelity_status="VERIFIED_WITH_LIMITATIONS",
                limitations=limitations,
                explanation_status="WITHHELD",
                confidence=decision_output.confidence,
                explanation_trace=(),
            )

        if not isinstance(output, ExplanationGeneratorOutput):
            raise RealResponsePrefixError("authority-enforced explanation did not return expected output")
        if output.explanation_status not in {"DRAFTED", "DRAFTED_WITH_LIMITATIONS", "CLARIFICATION_DRAFTED", "WITHHELD"}:
            raise RealResponsePrefixError(
                f"authority-enforced explanation blocked real path: {output.explanation_status}; {output.fidelity_status}"
            )

        output_id = _output_id(request.execution_id, stage)
        dependencies.store.put(output_id=output_id, value=output)
        evidence_ids = tuple(
            sorted({evidence_id for section in output.sections for evidence_id in section.evidence_ids})
        )
        return build_raw_intelligence_stage_output(
            execution_id=request.execution_id,
            stage=stage,
            knowledge_snapshot_id=knowledge_snapshot_id,
            output_id=output_id,
            output_type="explanation_generator_output",
            payload=asdict(output),
            limitations=output.limitations,
            evidence_ids=evidence_ids,
        )

    return prior + (
        build_intelligence_stage_adapter(
            stage="EXPLANATION_AUTHORITY_ENFORCED",
            capability=explanation,
        ),
    )


__all__ = ["EducationPublicationLookup", "build_real_response_explanation_adapters"]
