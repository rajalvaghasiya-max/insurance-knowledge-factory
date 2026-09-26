from __future__ import annotations

from dataclasses import fields

from insurance_intelligence.contracts import reasoning as reasoning_contract
from insurance_intelligence.orchestration.intelligence_adapters import execute_intelligence_stage
from insurance_intelligence.orchestration.real_response_assembly import build_real_response_assembly_adapters
from tests.insurance_intelligence import test_d0_exact_boundary_fail_closed_human_answer as case_c


def test_typed_rule_rejection_contract_exists() -> None:
    execution_fields = {item.name for item in fields(reasoning_contract.RuleExecution)}
    result_fields = {
        item.name for item in fields(reasoning_contract.RequirementReasoningResult)
    }

    assert "rejection_kind" in execution_fields
    assert "rejection_kind" in result_fields
    assert {
        "MISSING_CUSTOMER_FACT",
        "SOURCE_DOES_NOT_ESTABLISH",
        "UNSUPPORTED_REASONING",
    } <= reasoning_contract.RULE_REJECTION_KINDS


def test_case_c_preserves_source_does_not_establish_without_changing_fail_closed() -> None:
    request = case_c._request()
    dependencies = case_c._dependencies(request)
    adapters = build_real_response_assembly_adapters(
        dependencies=dependencies,
        style_registry=case_c._styles(),
        response_registry=case_c._responses(),
    )

    prior = (request.knowledge_snapshot_id,)
    for sequence, adapter in enumerate(adapters, start=1):
        result = execute_intelligence_stage(
            request=request,
            adapter=adapter,
            sequence=sequence,
            input_ids=prior,
        )
        assert result.status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"}, (
            result.stage,
            result.failure.message if result.failure else result.limitations,
        )
        prior = tuple(item.output_id for item in result.outputs)

    reasoning = dependencies.store.get(f"{request.execution_id}:real:reasoning")

    assert not reasoning.findings
    assert reasoning.reasoning_status in {"NOT_REASONED", "PARTIALLY_REASONED"}
    assert any(
        item.status == "REJECTED"
        and item.rejection_kind == "SOURCE_DOES_NOT_ESTABLISH"
        for item in reasoning.rule_executions
    )
    assert any(
        item.rejection_kind == "SOURCE_DOES_NOT_ESTABLISH"
        for item in reasoning.requirement_results
    )
