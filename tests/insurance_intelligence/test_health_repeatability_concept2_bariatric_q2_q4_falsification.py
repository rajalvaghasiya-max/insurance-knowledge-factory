from __future__ import annotations

from insurance_intelligence.contracts.full_cycle import build_orchestration_request, build_product_scope
from insurance_intelligence.orchestration.intelligence_adapters import execute_intelligence_stage
from insurance_intelligence.orchestration.real_response_assembly import build_real_response_assembly_adapters
from insurance_intelligence.response.human_answer import project_human_answer

from tests.insurance_intelligence import test_health_repeatability_concept2_bariatric as base


def _run(question: str, *, execution_id: str):
    request = build_orchestration_request(
        execution_id=execution_id,
        mode="INTELLIGENCE_RESPONSE",
        product_scope=build_product_scope(
            domain="health",
            insurer_id="star_health",
            product_id="star_comprehensive",
        ),
        question=question,
        audience="CUSTOMER",
        knowledge_snapshot_id="health-repeatability-concept2-bariatric-v1",
        allow_llm_rendering=False,
    )
    dependencies = base._dependencies(request)
    adapters = build_real_response_assembly_adapters(
        dependencies=dependencies,
        style_registry=base._styles(),
        response_registry=base._responses(),
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

    response = dependencies.store.get(f"{request.execution_id}:real:response_assembly")
    return project_human_answer(response)


def _customer_text(projection):
    view = projection.human_view
    return " ".join((view.answer, *view.meaning, *view.unknowns, view.next_step or "")).casefold()


def test_q2_explains_bariatric_eligibility_conditions_in_customer_language():
    projection = _run(
        "What conditions must I meet for bariatric surgery under Star Comprehensive?",
        execution_id="health-repeatability-concept2-q2",
    )
    text = _customer_text(projection)

    assert "above 18" in text
    assert "two" in text and "surgeon" in text
    assert "cashless" in text and "approval" in text
    assert "bmi" in text
    assert "weight-loss" in text or "weight loss" in text
    assert "eligibility_criteria" not in text
    assert "guaranteed" not in text


def test_q3_bmi_and_diabetes_do_not_become_blanket_coverage_decision():
    projection = _run(
        "My BMI is 37 and I have diabetes. Is bariatric surgery covered?",
        execution_id="health-repeatability-concept2-q3",
    )
    view = projection.human_view
    text = _customer_text(projection)

    assert "bmi" in text
    assert "37" in text or "35" in text
    assert "surgeon" in text
    assert "cashless" in text and "approval" in text
    assert "weight-loss" in text or "weight loss" in text
    assert "will be covered" not in view.answer.casefold()
    assert "claim will be approved" not in text
    assert "guaranteed" not in text


def test_q4_cosmetic_reason_surfaces_non_applicability_without_payment_claim():
    projection = _run(
        "Is bariatric surgery for cosmetic reasons covered?",
        execution_id="health-repeatability-concept2-q4",
    )
    text = _customer_text(projection)

    assert "cosmetic" in text
    assert "does not apply" in text or "not covered" in text or "non-applic" in text
    assert "claim will be approved" not in text
    assert "claim will be paid" not in text
    assert "guaranteed" not in text
