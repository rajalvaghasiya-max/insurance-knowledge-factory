from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.full_cycle import (
    KNOWLEDGE_BUILD_STAGE_ORDER,
    build_orchestration_request,
    build_product_scope,
)
from insurance_intelligence.orchestration.knowledge_adapters import (
    KnowledgeAdapterError,
    RawKnowledgeStageOutput,
    build_knowledge_stage_adapter,
    build_raw_knowledge_stage_output,
    deterministic_fake_capability,
    execute_knowledge_adapter_chain,
    execute_knowledge_stage,
)


def request(mode: str = "KNOWLEDGE_BUILD"):
    return build_orchestration_request(
        execution_id="exec-023b",
        mode=mode,
        product_scope=build_product_scope(domain="health", insurer_id="star", product_id="comprehensive"),
        force_refresh=mode == "KNOWLEDGE_REFRESH",
        question="Explain co-payment" if mode == "FULL_CYCLE_CERTIFICATION" else None,
        audience="customer" if mode == "FULL_CYCLE_CERTIFICATION" else None,
    )


def adapters():
    return tuple(
        build_knowledge_stage_adapter(stage=stage, capability=deterministic_fake_capability(output_type=f"{stage.lower()}_receipt"))
        for stage in KNOWLEDGE_BUILD_STAGE_ORDER
    )


def test_raw_output_requires_payload():
    with pytest.raises(KnowledgeAdapterError):
        build_raw_knowledge_stage_output(output_id="x", output_type="y", payload={})


def test_raw_output_is_immutable():
    value = build_raw_knowledge_stage_output(output_id="x", output_type="y", payload={"a": 1})
    with pytest.raises(FrozenInstanceError):
        value.output_id = "z"  # type: ignore[misc]


def test_raw_output_rejects_non_json_payload():
    with pytest.raises(KnowledgeAdapterError):
        build_raw_knowledge_stage_output(output_id="x", output_type="y", payload={"bad": object()})


def test_adapter_requires_governed_stage():
    with pytest.raises(KnowledgeAdapterError):
        build_knowledge_stage_adapter(stage="UNKNOWN", capability=lambda **_: None)


def test_adapter_requires_callable():
    with pytest.raises(KnowledgeAdapterError):
        build_knowledge_stage_adapter(stage="DISCOVERY", capability=None)  # type: ignore[arg-type]


def test_fake_capability_is_deterministic():
    cap = deterministic_fake_capability(output_type="receipt")
    first = cap(request=request(), stage="DISCOVERY", input_ids=())
    second = cap(request=request(), stage="DISCOVERY", input_ids=())
    assert first == second


def test_stage_success_normalises_digest():
    result = execute_knowledge_stage(request=request(), adapter=adapters()[0], sequence=1)
    assert result.status == "SUCCEEDED"
    assert len(result.outputs[0].content_digest) == 64


def test_stage_preserves_input_ids():
    result = execute_knowledge_stage(request=request(), adapter=adapters()[1], sequence=2, input_ids=("prior",))
    assert result.input_ids == ("prior",)


def test_stage_with_limitations_is_visible():
    adapter = build_knowledge_stage_adapter(
        stage="DISCOVERY", capability=deterministic_fake_capability(output_type="receipt", limitations=("partial source scope",))
    )
    result = execute_knowledge_stage(request=request(), adapter=adapter, sequence=1)
    assert result.status == "SUCCEEDED_WITH_LIMITATIONS"
    assert result.limitations == ("partial source scope",)


def test_stage_rejects_wrong_sequence():
    with pytest.raises(KnowledgeAdapterError):
        execute_knowledge_stage(request=request(), adapter=adapters()[0], sequence=2)


def test_stage_rejects_response_mode():
    response_request = build_orchestration_request(
        execution_id="response", mode="INTELLIGENCE_RESPONSE",
        product_scope=build_product_scope(domain="health", insurer_id="star", product_id="comprehensive"),
        question="q", audience="customer", knowledge_snapshot_id="snapshot-1"
    )
    with pytest.raises(KnowledgeAdapterError):
        execute_knowledge_stage(request=response_request, adapter=adapters()[0], sequence=1)


def test_capability_exception_becomes_failed_result():
    def boom(**_):
        raise RuntimeError("offline failure")
    adapter = build_knowledge_stage_adapter(stage="DISCOVERY", capability=boom)
    result = execute_knowledge_stage(request=request(), adapter=adapter, sequence=1)
    assert result.status == "FAILED"
    assert result.failure.failure_kind == "STAGE_ERROR"


def test_invalid_capability_output_fails_closed():
    adapter = build_knowledge_stage_adapter(stage="DISCOVERY", capability=lambda **_: {"bad": True})
    result = execute_knowledge_stage(request=request(), adapter=adapter, sequence=1)
    assert result.status == "FAILED"


def test_chain_requires_exact_order():
    with pytest.raises(KnowledgeAdapterError):
        execute_knowledge_adapter_chain(request=request(), adapters=tuple(reversed(adapters())))


def test_chain_rejects_duplicate_stage():
    values = list(adapters())
    values[-1] = values[0]
    with pytest.raises(KnowledgeAdapterError):
        execute_knowledge_adapter_chain(request=request(), adapters=values)


def test_chain_runs_every_knowledge_stage():
    run = execute_knowledge_adapter_chain(request=request(), adapters=adapters())
    assert tuple(item.stage for item in run.stage_results) == KNOWLEDGE_BUILD_STAGE_ORDER
    assert all(item.status == "SUCCEEDED" for item in run.stage_results)


def test_chain_passes_only_prior_stage_outputs_forward():
    run = execute_knowledge_adapter_chain(request=request(), adapters=adapters())
    assert run.stage_results[0].input_ids == ()
    assert run.stage_results[1].input_ids == (run.stage_results[0].outputs[0].output_id,)


def test_chain_returns_last_stage_output():
    run = execute_knowledge_adapter_chain(request=request(), adapters=adapters())
    assert run.output_ids == (run.stage_results[-1].outputs[0].output_id,)


def test_chain_is_deterministic():
    assert execute_knowledge_adapter_chain(request=request(), adapters=adapters()) == execute_knowledge_adapter_chain(request=request(), adapters=adapters())


def test_chain_supports_refresh_mode():
    run = execute_knowledge_adapter_chain(request=request("KNOWLEDGE_REFRESH"), adapters=adapters())
    assert not run.blocked


def test_chain_supports_full_cycle_certification_prefix():
    run = execute_knowledge_adapter_chain(request=request("FULL_CYCLE_CERTIFICATION"), adapters=adapters())
    assert len(run.stage_results) == len(KNOWLEDGE_BUILD_STAGE_ORDER)


def test_failure_blocks_all_downstream_stages():
    values = list(adapters())
    values[2] = build_knowledge_stage_adapter(stage="SOURCE_REGISTRATION", capability=lambda **_: (_ for _ in ()).throw(RuntimeError("bad registry")))
    run = execute_knowledge_adapter_chain(request=request(), adapters=values)
    assert run.stage_results[2].status == "FAILED"
    assert all(item.status == "BLOCKED" for item in run.stage_results[3:])
    assert run.blocked


def test_blocked_run_exposes_no_final_output_ids():
    values = list(adapters())
    values[0] = build_knowledge_stage_adapter(stage="DISCOVERY", capability=lambda **_: (_ for _ in ()).throw(RuntimeError("bad")))
    run = execute_knowledge_adapter_chain(request=request(), adapters=values)
    assert run.output_ids == ()


def test_evidence_ids_are_preserved():
    def cap(**_):
        return build_raw_knowledge_stage_output(output_id="o", output_type="t", payload={"a": 1}, evidence_ids=("e1", "e2"))
    result = execute_knowledge_stage(request=request(), adapter=build_knowledge_stage_adapter(stage="DISCOVERY", capability=cap), sequence=1)
    assert result.outputs[0].evidence_ids == ("e1", "e2")


def test_payload_mapping_is_copied():
    payload = {"a": 1}
    value = build_raw_knowledge_stage_output(output_id="o", output_type="t", payload=payload)
    payload["a"] = 2
    assert value.payload["a"] == 1


def test_adapter_run_is_immutable():
    run = execute_knowledge_adapter_chain(request=request(), adapters=adapters())
    with pytest.raises(FrozenInstanceError):
        run.blocked = True  # type: ignore[misc]
