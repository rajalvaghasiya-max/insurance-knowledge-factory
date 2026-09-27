from __future__ import annotations

from insurance_intelligence.orchestration.intelligence_adapters import (
    execute_intelligence_stage,
)
from insurance_intelligence.orchestration.real_response_assembly import (
    build_real_response_assembly_adapters,
)
from insurance_intelligence.response.human_answer import project_human_answer

from tests.insurance_intelligence.test_d0_resolved_waiting_period_human_answer_rerun import (
    _dependencies,
    _request,
    _responses,
    _styles,
)


def test_case_b_leads_with_supplied_dates_and_omits_not_applicable_clauses() -> None:
    request = _request()
    dependencies = _dependencies(request)
    adapters = build_real_response_assembly_adapters(
        dependencies=dependencies,
        style_registry=_styles(),
        response_registry=_responses(),
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
    assert len(reasoning.findings) == 1
    finding = reasoning.findings[0]
    assert finding.customer_qualifications
    assert all(
        item.applicability_status == "NOT_APPLICABLE"
        for item in finding.customer_qualifications
    )

    response = dependencies.store.get(f"{request.execution_id}:real:response_assembly")
    projection = project_human_answer(response)
    customer_text = " ".join(
        (
            projection.human_view.answer,
            *projection.human_view.meaning,
            *projection.human_view.unknowns,
            projection.human_view.next_step or "",
        )
    ).casefold()

    assert "still active" in projection.human_view.answer.casefold()
    assert "2026-01-01" in projection.human_view.answer
    assert "2026-01-15" in projection.human_view.answer
    for qualification in finding.customer_qualifications:
        assert qualification.text.casefold() not in customer_text
        assert qualification.text.casefold() in (finding.exception or "").casefold()

    assert finding.applicability_scope
    assert finding.applicability_scope.casefold() not in customer_text
