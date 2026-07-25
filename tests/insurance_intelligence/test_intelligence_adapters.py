from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.full_cycle import (
    INTELLIGENCE_RESPONSE_STAGE_ORDER,
    KNOWLEDGE_BUILD_STAGE_ORDER,
    build_orchestration_request,
    build_product_scope,
)
from insurance_intelligence.orchestration.intelligence_adapters import (
    IntelligenceAdapterError,
    build_intelligence_stage_adapter,
    build_raw_intelligence_stage_output,
    deterministic_fake_intelligence_capability,
    execute_intelligence_adapter_chain,
    execute_intelligence_stage,
)


def request(mode: str = "INTELLIGENCE_RESPONSE", *, allow_llm: bool = True):
    return build_orchestration_request(
        execution_id="exec-023c",
        mode=mode,
        product_scope=build_product_scope(domain="health", insurer_id="star", product_id="comprehensive"),
        question="Explain co-payment",
        audience="customer",
        customer_context={"entry_age": 62},
        knowledge_snapshot_id="snapshot-certified-1" if mode == "INTELLIGENCE_RESPONSE" else None,
        allow_llm_rendering=allow_llm,
    )


def adapters():
    return tuple(
        build_intelligence_stage_adapter(
            stage=stage,
            capability=deterministic_fake_intelligence_capability(
                output_type=f"{stage.lower()}_receipt",
                evidence_ids=("evidence-1",) if stage in {"APPLICABILITY", "DECISION_GATE", "EXPLANATION"} else (),
            ),
        )
        for stage in INTELLIGENCE_RESPONSE_STAGE_ORDER
    )


def test_raw_output_requires_payload():
    with pytest.raises(IntelligenceAdapterError):
        build_raw_intelligence_stage_output(
            execution_id="e", stage="REQUEST_INTAKE", knowledge_snapshot_id="s", output_id="o", output_type="t", payload={}
        )


def test_raw_output_is_immutable():
    value = build_raw_intelligence_stage_output(
        execution_id="e", stage="REQUEST_INTAKE", knowledge_snapshot_id="s", output_id="o", output_type="t", payload={"a": 1}
    )
    with pytest.raises(FrozenInstanceError):
        value.output_id = "x"  # type: ignore[misc]


def test_raw_output_rejects_non_json_payload():
    with pytest.raises(IntelligenceAdapterError):
        build_raw_intelligence_stage_output(
            execution_id="e", stage="REQUEST_INTAKE", knowledge_snapshot_id="s", output_id="o", output_type="t", payload={"bad": object()}
        )


def test_adapter_requires_governed_stage():
    with pytest.raises(IntelligenceAdapterError):
        build_intelligence_stage_adapter(stage="DISCOVERY", capability=lambda **_: None)


def test_adapter_requires_callable():
    with pytest.raises(IntelligenceAdapterError):
        build_intelligence_stage_adapter(stage="REQUEST_INTAKE", capability=None)  # type: ignore[arg-type]


def test_fake_capability_is_deterministic():
    cap = deterministic_fake_intelligence_capability(output_type="receipt")
    kwargs = dict(request=request(), stage="REQUEST_INTAKE", input_ids=("snapshot-certified-1",), knowledge_snapshot_id="snapshot-certified-1")
    assert cap(**kwargs) == cap(**kwargs)


def test_stage_success_normalises_digest():
    result = execute_intelligence_stage(request=request(), adapter=adapters()[0], sequence=1)
    assert result.status == "SUCCEEDED"
    assert len(result.outputs[0].content_digest) == 64


def test_stage_preserves_input_ids():
    result = execute_intelligence_stage(request=request(), adapter=adapters()[1], sequence=2, input_ids=("prior",))
    assert result.input_ids == ("prior",)


def test_stage_with_limitations_is_visible():
    adapter = build_intelligence_stage_adapter(
        stage="REQUEST_INTAKE",
        capability=deterministic_fake_intelligence_capability(output_type="receipt", limitations=("context incomplete",)),
    )
    result = execute_intelligence_stage(request=request(), adapter=adapter, sequence=1)
    assert result.status == "SUCCEEDED_WITH_LIMITATIONS"
    assert result.limitations == ("context incomplete",)


def test_stage_rejects_wrong_sequence():
    with pytest.raises(IntelligenceAdapterError):
        execute_intelligence_stage(request=request(), adapter=adapters()[0], sequence=2)


def test_stage_rejects_knowledge_mode():
    knowledge_request = build_orchestration_request(
        execution_id="knowledge", mode="KNOWLEDGE_BUILD",
        product_scope=build_product_scope(domain="health", insurer_id="star", product_id="comprehensive")
    )
    with pytest.raises(IntelligenceAdapterError):
        execute_intelligence_stage(request=knowledge_request, adapter=adapters()[0], sequence=1)


def test_full_cycle_requires_new_snapshot():
    with pytest.raises(IntelligenceAdapterError):
        execute_intelligence_adapter_chain(request=request("FULL_CYCLE_CERTIFICATION"), adapters=adapters())


def test_response_snapshot_mismatch_is_rejected():
    with pytest.raises(IntelligenceAdapterError):
        execute_intelligence_adapter_chain(request=request(), adapters=adapters(), knowledge_snapshot_id="other")


def test_capability_exception_becomes_failed_result():
    def boom(**_):
        raise RuntimeError("offline failure")
    adapter = build_intelligence_stage_adapter(stage="REQUEST_INTAKE", capability=boom)
    result = execute_intelligence_stage(request=request(), adapter=adapter, sequence=1)
    assert result.status == "FAILED"
    assert result.failure.failure_kind == "STAGE_ERROR"


def test_invalid_capability_output_fails_closed():
    adapter = build_intelligence_stage_adapter(stage="REQUEST_INTAKE", capability=lambda **_: {"bad": True})
    result = execute_intelligence_stage(request=request(), adapter=adapter, sequence=1)
    assert result.status == "FAILED"


def test_identity_mismatch_fails_closed():
    def cap(**kwargs):
        return build_raw_intelligence_stage_output(
            execution_id="wrong", stage=kwargs["stage"], knowledge_snapshot_id=kwargs["knowledge_snapshot_id"],
            output_id="o", output_type="t", payload={"a": 1}
        )
    result = execute_intelligence_stage(
        request=request(), adapter=build_intelligence_stage_adapter(stage="REQUEST_INTAKE", capability=cap), sequence=1
    )
    assert result.status == "FAILED"


def test_chain_requires_exact_order():
    with pytest.raises(IntelligenceAdapterError):
        execute_intelligence_adapter_chain(request=request(), adapters=tuple(reversed(adapters())))


def test_chain_rejects_duplicate_stage():
    values = list(adapters())
    values[-1] = values[0]
    with pytest.raises(IntelligenceAdapterError):
        execute_intelligence_adapter_chain(request=request(), adapters=values)


def test_chain_runs_every_runtime_stage():
    run = execute_intelligence_adapter_chain(request=request(), adapters=adapters())
    assert tuple(item.stage for item in run.stage_results) == INTELLIGENCE_RESPONSE_STAGE_ORDER
    assert all(item.status == "SUCCEEDED" for item in run.stage_results)


def test_chain_starts_from_certified_snapshot():
    run = execute_intelligence_adapter_chain(request=request(), adapters=adapters())
    assert run.stage_results[0].input_ids == ("snapshot-certified-1",)


def test_chain_passes_only_prior_output_forward():
    run = execute_intelligence_adapter_chain(request=request(), adapters=adapters())
    assert run.stage_results[1].input_ids == (run.stage_results[0].outputs[0].output_id,)


def test_chain_preserves_response_linkage():
    run = execute_intelligence_adapter_chain(request=request(), adapters=adapters())
    assert run.deterministic_response_id == run.stage_results[8].outputs[0].output_id
    assert run.released_response_id == run.stage_results[9].outputs[0].output_id
    assert run.evaluation_report_id == run.stage_results[10].outputs[0].output_id


def test_llm_disabled_uses_deterministic_response():
    run = execute_intelligence_adapter_chain(request=request(allow_llm=False), adapters=adapters())
    assert run.stage_results[9].status == "NOT_REQUIRED"
    assert run.released_response_id == run.deterministic_response_id


def test_full_cycle_uses_governed_sequence_offset():
    run = execute_intelligence_adapter_chain(
        request=request("FULL_CYCLE_CERTIFICATION"), adapters=adapters(), knowledge_snapshot_id="new-snapshot"
    )
    assert run.stage_results[0].sequence == len(KNOWLEDGE_BUILD_STAGE_ORDER) + 1
    assert run.knowledge_snapshot_id == "new-snapshot"


def test_failure_blocks_all_downstream_stages():
    values = list(adapters())
    values[3] = build_intelligence_stage_adapter(
        stage="CONTEXT_BUILDING", capability=lambda **_: (_ for _ in ()).throw(RuntimeError("bad context"))
    )
    run = execute_intelligence_adapter_chain(request=request(), adapters=values)
    assert run.stage_results[3].status == "FAILED"
    assert all(item.status == "BLOCKED" for item in run.stage_results[4:])
    assert run.blocked


def test_blocked_run_exposes_no_response_ids():
    values = list(adapters())
    values[0] = build_intelligence_stage_adapter(
        stage="REQUEST_INTAKE", capability=lambda **_: (_ for _ in ()).throw(RuntimeError("bad"))
    )
    run = execute_intelligence_adapter_chain(request=request(), adapters=values)
    assert run.output_ids == ()
    assert run.deterministic_response_id is None
    assert run.released_response_id is None
    assert run.evaluation_report_id is None


def test_evidence_ids_are_preserved():
    run = execute_intelligence_adapter_chain(request=request(), adapters=adapters())
    applicability = run.stage_results[5]
    assert applicability.outputs[0].evidence_ids == ("evidence-1",)


def test_adapter_run_is_immutable():
    run = execute_intelligence_adapter_chain(request=request(), adapters=adapters())
    with pytest.raises(FrozenInstanceError):
        run.blocked = True  # type: ignore[misc]
