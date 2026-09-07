"""Generic extension of the proven real response path through deterministic response assembly.

This module composes the existing real explanation path with the existing
Response Assembler. Response format policy is supplied as a dependency; this
orchestration layer does not invent product-specific answer semantics.
It intentionally stops at RESPONSE_ASSEMBLY.
"""
from __future__ import annotations

from dataclasses import asdict

from insurance_intelligence.contracts.authority_enforcement import AuthorityEnforcementResult
from insurance_intelligence.contracts.explanation import ExplanationGeneratorOutput
from insurance_intelligence.contracts.response import (
    ResponseAssemblerOutput,
    build_input as build_response_input,
)
from insurance_intelligence.orchestration.intelligence_adapters import (
    build_intelligence_stage_adapter,
    build_raw_intelligence_stage_output,
)
from insurance_intelligence.orchestration.real_response_explanation import (
    build_real_response_explanation_adapters,
)
from insurance_intelligence.orchestration.real_response_prefix import (
    RealResponsePrefixDependencies,
    RealResponsePrefixError,
)
from insurance_intelligence.explanation.registry import ExplanationStyleRegistry, TerminologyRegistry
from insurance_intelligence.response.registry import ResponseFormatRegistry
from insurance_intelligence.response.service import assemble_response


def _output_id(execution_id: str, stage: str) -> str:
    return f"{execution_id}:real:{stage.lower()}"


def build_real_response_assembly_adapters(
    *,
    dependencies: RealResponsePrefixDependencies,
    style_registry: ExplanationStyleRegistry,
    response_registry: ResponseFormatRegistry,
    terminology_registry: TerminologyRegistry | None = None,
    response_format: str = "STANDARD",
):
    """Build the proven real path plus canonical deterministic response assembly."""
    if not isinstance(response_registry, ResponseFormatRegistry):
        raise RealResponsePrefixError("response_registry must be ResponseFormatRegistry")

    prior = build_real_response_explanation_adapters(
        dependencies=dependencies,
        style_registry=style_registry,
        terminology_registry=terminology_registry,
    )

    def response_assembly(*, request, stage, input_ids, knowledge_snapshot_id):
        if stage != "RESPONSE_ASSEMBLY":
            raise RealResponsePrefixError("response assembly stage mismatch")

        authority_result = dependencies.store.get(
            _output_id(request.execution_id, "DECISION_GATE_AUTHORITY_ENFORCED"),
            expected_type=AuthorityEnforcementResult,
        )
        decision_output = authority_result.decision_output
        if decision_output is None:
            raise RealResponsePrefixError("authority-enforced decision omitted decision output")

        explanation_output = dependencies.store.get(
            _output_id(request.execution_id, "EXPLANATION_AUTHORITY_ENFORCED"),
            expected_type=ExplanationGeneratorOutput,
        )
        assembler_input = build_response_input(
            request_id=request.execution_id,
            decision_output=decision_output,
            explanation_output=explanation_output,
            response_format=response_format,
            assembly_context=dict(request.customer_context),
        )
        output = assemble_response(assembler_input, response_registry)
        if not isinstance(output, ResponseAssemblerOutput):
            raise RealResponsePrefixError("response assembler did not return expected output")
        if output.response_status not in {"ANSWER", "ANSWER_WITH_LIMITATIONS"}:
            raise RealResponsePrefixError(
                f"response assembly blocked real path: {output.response_status}"
            )
        if not output.direct_answer:
            raise RealResponsePrefixError("response assembly omitted deterministic direct answer")

        output_id = _output_id(request.execution_id, stage)
        dependencies.store.put(output_id=output_id, value=output)
        evidence_ids = tuple(sorted({item.source_id for item in output.evidence_references}))
        return build_raw_intelligence_stage_output(
            execution_id=request.execution_id,
            stage=stage,
            knowledge_snapshot_id=knowledge_snapshot_id,
            output_id=output_id,
            output_type="response_assembler_output",
            payload=asdict(output),
            limitations=output.limitations,
            evidence_ids=evidence_ids,
        )

    return prior + (
        build_intelligence_stage_adapter(stage="RESPONSE_ASSEMBLY", capability=response_assembly),
    )


__all__ = ["build_real_response_assembly_adapters"]
