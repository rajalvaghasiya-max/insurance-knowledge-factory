from __future__ import annotations

import pytest

from insurance_intelligence.contracts.full_cycle import (
    INTELLIGENCE_RESPONSE_STAGE_ORDER,
    KNOWLEDGE_BUILD_STAGE_ORDER,
    build_orchestration_request,
    build_product_scope,
)
from insurance_intelligence.orchestration.intelligence_adapters import (
    build_intelligence_stage_adapter,
    deterministic_fake_intelligence_capability,
)
from insurance_intelligence.orchestration.knowledge_adapters import (
    build_knowledge_stage_adapter,
    deterministic_fake_capability,
)
from insurance_intelligence.orchestration.service import (
    OrchestrationServiceError,
    run_full_cycle_certification,
    run_intelligence_response,
    run_knowledge_build,
)


def scope():
    return build_product_scope(domain="health", insurer_id="star_health", product_id="star_comprehensive")


def request(mode, **kwargs):
    base = dict(execution_id=f"exec-{mode.lower()}", mode=mode, product_scope=scope())
    base.update(kwargs)
    return build_orchestration_request(**base)


def k_adapters(fail_stage=None, limitation_stage=None):
    values = []
    for stage in KNOWLEDGE_BUILD_STAGE_ORDER:
        if stage == fail_stage:
            def bad(**_):
                raise RuntimeError("boom")
            cap = bad
        else:
            cap = deterministic_fake_capability(
                output_type=f"{stage.lower()}_output",
                limitations=("limited",) if stage == limitation_stage else (),
            )
        values.append(build_knowledge_stage_adapter(stage=stage, capability=cap))
    return tuple(values)


def i_adapters(fail_stage=None, limitation_stage=None):
    values = []
    for stage in INTELLIGENCE_RESPONSE_STAGE_ORDER:
        if stage == fail_stage:
            def bad(**_):
                raise RuntimeError("boom")
            cap = bad
        else:
            cap = deterministic_fake_intelligence_capability(
                output_type=f"{stage.lower()}_output",
                limitations=("limited",) if stage == limitation_stage else (),
            )
        values.append(build_intelligence_stage_adapter(stage=stage, capability=cap))
    return tuple(values)


def test_knowledge_build_succeeds():
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=k_adapters())
    assert execution.result.status == "SUCCEEDED"
    assert execution.result.knowledge_snapshot_id
    assert execution.state.terminal is True


def test_knowledge_refresh_succeeds():
    execution = run_knowledge_build(request=request("KNOWLEDGE_REFRESH", force_refresh=True), adapters=k_adapters())
    assert execution.result.mode == "KNOWLEDGE_REFRESH"


def test_knowledge_service_rejects_response_mode():
    req = request("INTELLIGENCE_RESPONSE", question="q", audience="customer", knowledge_snapshot_id="snap")
    with pytest.raises(OrchestrationServiceError):
        run_knowledge_build(request=req, adapters=k_adapters())


def test_response_succeeds():
    req = request("INTELLIGENCE_RESPONSE", question="q", audience="customer", knowledge_snapshot_id="snap")
    execution = run_intelligence_response(request=req, adapters=i_adapters())
    assert execution.result.status == "SUCCEEDED"
    assert execution.result.deterministic_response_id
    assert execution.result.released_response_id
    assert execution.result.evaluation_report_id


def test_response_without_llm_uses_deterministic_fallback():
    req = request("INTELLIGENCE_RESPONSE", question="q", audience="customer", knowledge_snapshot_id="snap", allow_llm_rendering=False)
    execution = run_intelligence_response(request=req, adapters=i_adapters())
    assert execution.result.stage_results[-2].status == "NOT_REQUIRED"
    assert execution.result.released_response_id == execution.result.deterministic_response_id


def test_response_service_rejects_build_mode():
    with pytest.raises(OrchestrationServiceError):
        run_intelligence_response(request=request("KNOWLEDGE_BUILD"), adapters=i_adapters())


def test_full_cycle_succeeds():
    req = request("FULL_CYCLE_CERTIFICATION", question="q", audience="customer")
    execution = run_full_cycle_certification(request=req, knowledge_adapters=k_adapters(), intelligence_adapters=i_adapters())
    assert execution.result.status == "SUCCEEDED"
    assert len(execution.result.stage_results) == len(KNOWLEDGE_BUILD_STAGE_ORDER) + len(INTELLIGENCE_RESPONSE_STAGE_ORDER)
    assert execution.result.knowledge_snapshot_id


def test_full_cycle_rejects_wrong_mode():
    with pytest.raises(OrchestrationServiceError):
        run_full_cycle_certification(request=request("KNOWLEDGE_BUILD"), knowledge_adapters=k_adapters(), intelligence_adapters=i_adapters())


def test_knowledge_failure_blocks_suffix():
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=k_adapters(fail_stage="PARSING"))
    assert execution.result.status == "FAILED"
    assert execution.result.stage_results[3].status == "FAILED"
    assert all(r.status == "BLOCKED" for r in execution.result.stage_results[4:])
    assert execution.result.knowledge_snapshot_id is None


def test_response_failure_blocks_suffix():
    req = request("INTELLIGENCE_RESPONSE", question="q", audience="customer", knowledge_snapshot_id="snap")
    execution = run_intelligence_response(
        request=req,
        adapters=i_adapters(fail_stage="DECISION_GATE_AUTHORITY_ENFORCED"),
    )
    assert execution.result.status == "FAILED"
    assert execution.result.deterministic_response_id is None


def test_full_cycle_knowledge_failure_blocks_all_runtime_stages():
    req = request("FULL_CYCLE_CERTIFICATION", question="q", audience="customer")
    execution = run_full_cycle_certification(request=req, knowledge_adapters=k_adapters(fail_stage="PARSING"), intelligence_adapters=i_adapters())
    assert execution.result.status == "FAILED"
    assert all(r.status == "BLOCKED" for r in execution.result.stage_results[10:])


def test_limitations_aggregate():
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=k_adapters(limitation_stage="QUALITY_AUDIT"))
    assert execution.result.status == "SUCCEEDED_WITH_LIMITATIONS"
    assert execution.result.limitations == ("limited",)


def test_trace_is_contiguous_and_complete():
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=k_adapters())
    assert [e.sequence for e in execution.result.trace] == list(range(1, 13))
    assert execution.result.trace[0].event_type == "EXECUTION_STARTED"
    assert execution.result.trace[-1].event_type == "EXECUTION_COMPLETED"


def test_state_contains_checkpoint_for_each_successful_stage():
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=k_adapters())
    assert len(execution.state.checkpoints) == 10
    assert execution.state.last_validated_sequence == 10


def test_failed_state_is_not_terminal_success():
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=k_adapters(fail_stage="PARSING"))
    assert execution.state.terminal is False
    assert execution.state.next_stage == "PARSING"
    assert execution.state.resumable is True


def test_deterministic_ids_across_repeated_runs():
    req = request("INTELLIGENCE_RESPONSE", question="q", audience="customer", knowledge_snapshot_id="snap")
    one = run_intelligence_response(request=req, adapters=i_adapters())
    two = run_intelligence_response(request=req, adapters=i_adapters())
    assert one.result == two.result
    assert one.state.state_id == two.state.state_id


def test_only_previous_output_is_passed_downstream():
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=k_adapters())
    for prior, current in zip(execution.result.stage_results, execution.result.stage_results[1:]):
        assert current.input_ids == (prior.outputs[0].output_id,)


def test_response_first_stage_starts_from_snapshot():
    req = request("INTELLIGENCE_RESPONSE", question="q", audience="customer", knowledge_snapshot_id="snap")
    execution = run_intelligence_response(request=req, adapters=i_adapters())
    assert execution.result.stage_results[0].input_ids == ("snap",)


def test_full_cycle_runtime_starts_from_new_snapshot():
    req = request("FULL_CYCLE_CERTIFICATION", question="q", audience="customer")
    execution = run_full_cycle_certification(request=req, knowledge_adapters=k_adapters(), intelligence_adapters=i_adapters())
    snapshot = execution.result.knowledge_snapshot_id
    assert execution.result.stage_results[len(KNOWLEDGE_BUILD_STAGE_ORDER)].input_ids == (snapshot,)


def test_no_response_ids_on_knowledge_only_run():
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=k_adapters())
    assert execution.result.deterministic_response_id is None
    assert execution.result.released_response_id is None
    assert execution.result.evaluation_report_id is None


def test_failed_result_has_no_snapshot():
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=k_adapters(fail_stage="DISCOVERY"))
    assert execution.result.knowledge_snapshot_id is None


def test_trace_failed_event_references_failure():
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=k_adapters(fail_stage="DISCOVERY"))
    event = execution.result.trace[1]
    assert event.event_type == "STAGE_FAILED"
    assert event.reference_ids[0].startswith("failure:")


def test_not_required_trace_is_stage_skipped():
    req = request("INTELLIGENCE_RESPONSE", question="q", audience="customer", knowledge_snapshot_id="snap", allow_llm_rendering=False)
    execution = run_intelligence_response(request=req, adapters=i_adapters())
    llm_event = next(e for e in execution.result.trace if e.stage == "LLM_RENDERING")
    assert llm_event.event_type == "STAGE_SKIPPED"


def test_duplicate_limitations_are_deduplicated():
    adapters = list(k_adapters(limitation_stage="QUALITY_AUDIT"))
    adapters[6] = build_knowledge_stage_adapter(stage="PRODUCT_IDENTITY", capability=deterministic_fake_capability(output_type="x", limitations=("limited",)))
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=tuple(adapters))
    assert execution.result.limitations == ("limited",)


def test_all_results_match_execution_identity():
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=k_adapters())
    assert {r.execution_id for r in execution.result.stage_results} == {execution.request.execution_id}


def test_result_and_state_share_stage_results():
    execution = run_knowledge_build(request=request("KNOWLEDGE_BUILD"), adapters=k_adapters())
    assert execution.result.stage_results == execution.state.completed_stage_results