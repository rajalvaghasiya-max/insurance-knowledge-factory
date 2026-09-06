from __future__ import annotations

from pathlib import Path

from insurance_intelligence.contracts.evidence import build_input as build_evidence_input
from insurance_intelligence.contracts.full_cycle import (
    INTELLIGENCE_RESPONSE_STAGE_ORDER,
    build_orchestration_request,
    build_product_scope,
)
from insurance_intelligence.contracts.reasoning_plan import (
    build_evidence_requirement,
    build_plan,
)
from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.evidence.coverage_registry_source import (
    build_coverage_registry_published_source_lookup,
)
from insurance_intelligence.evidence.published_resolver import PublishedEvidenceResolver
from insurance_intelligence.orchestration.intelligence_adapters import (
    build_intelligence_stage_adapter,
    deterministic_fake_intelligence_capability,
)
from insurance_intelligence.orchestration.service import run_intelligence_response
from insurance_intelligence.orchestration.user_answer_evidence_adapter import (
    EVIDENCE_STAGE,
    build_user_answer_evidence_stage_adapter,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "knowledge/factory/registry_backed"
LOOKUP = build_coverage_registry_published_source_lookup(
    registry=HEALTH_COVERAGE_REGISTRY,
    repository_root=ROOT,
)


def _request(*, execution_id: str, question: str):
    return build_orchestration_request(
        execution_id=execution_id,
        mode="INTELLIGENCE_RESPONSE",
        product_scope=build_product_scope(
            domain="health",
            insurer_id="star_health",
            product_id="star_comprehensive",
        ),
        question=question,
        audience="customer",
        knowledge_snapshot_id="snapshot:published-health",
        allow_llm_rendering=False,
    )


def _evidence_factory(reason: str, *, evidence_use: str = "USER_ANSWER"):
    def factory(request):
        requirement = build_evidence_requirement(
            requirement_id="req_fact",
            evidence_category="NORMALIZED_PRODUCT_FACT",
            subject_reference="star_health:star_comprehensive",
            required=True,
            authority_requirement="AUTHORITATIVE",
            version_requirement="CURRENT_APPLICABLE",
            reason=reason,
            requested_by_step="step_1",
        )
        plan = build_plan(
            request_id=request.execution_id,
            plan_id=f"plan:{request.execution_id}",
            plan_type="DIRECT_FACT_PLAN",
            execution_mode="DIRECT_GROUNDED",
            goal="resolve published product fact",
            expected_outcome="DIRECT_FACT_RESPONSE",
            plan_status="READY",
            confidence=1.0,
            required_evidence=(requirement,),
        )
        return build_evidence_input(
            request_id=request.execution_id,
            reasoning_plan=plan,
            resolution_context={"evidence_use": evidence_use},
            repository_roots=(str(REGISTRY),),
            strict_mode="STRICT",
        )

    return factory


def _adapters(reason: str, *, evidence_use: str = "USER_ANSWER"):
    resolver = PublishedEvidenceResolver(LOOKUP)
    values = []
    for stage in INTELLIGENCE_RESPONSE_STAGE_ORDER:
        if stage == EVIDENCE_STAGE:
            values.append(
                build_user_answer_evidence_stage_adapter(
                    resolver=resolver,
                    evidence_input_factory=_evidence_factory(
                        reason,
                        evidence_use=evidence_use,
                    ),
                )
            )
        else:
            values.append(
                build_intelligence_stage_adapter(
                    stage=stage,
                    capability=deterministic_fake_intelligence_capability(
                        output_type=f"{stage.lower()}_output"
                    ),
                )
            )
    return tuple(values)


def test_response_orchestration_routes_room_rent_through_publication_backed_user_answer_evidence():
    request = _request(
        execution_id="exec-room-rent-user-answer",
        question="Explain the room rent or room category limit for Star Comprehensive",
    )
    execution = run_intelligence_response(
        request=request,
        adapters=_adapters(
            "Explain the room rent or room category limit for Star Comprehensive"
        ),
    )

    assert execution.result.status == "SUCCEEDED"
    evidence_result = execution.result.stage_results[
        INTELLIGENCE_RESPONSE_STAGE_ORDER.index(EVIDENCE_STAGE)
    ]
    assert evidence_result.status == "SUCCEEDED"
    assert len(evidence_result.outputs) == 1
    assert len(evidence_result.outputs[0].evidence_ids) == 5
    assert execution.result.released_response_id == execution.result.deterministic_response_id


def test_response_orchestration_routes_ped_waiting_period_through_authoritatively_published_user_answer_evidence():
    request = _request(
        execution_id="exec-ped-user-answer",
        question="What is the PED waiting period in Star Comprehensive?",
    )
    execution = run_intelligence_response(
        request=request,
        adapters=_adapters("What is the PED waiting period in Star Comprehensive?"),
    )

    assert execution.result.status == "SUCCEEDED"
    evidence_index = INTELLIGENCE_RESPONSE_STAGE_ORDER.index(EVIDENCE_STAGE)
    evidence_result = execution.result.stage_results[evidence_index]
    assert evidence_result.status == "SUCCEEDED"
    assert len(evidence_result.outputs) == 1
    assert evidence_result.outputs[0].evidence_ids
    assert execution.result.released_response_id == execution.result.deterministic_response_id


def test_production_evidence_stage_rejects_internal_certification_use():
    request = _request(
        execution_id="exec-internal-use-rejected",
        question="Explain room rent",
    )
    execution = run_intelligence_response(
        request=request,
        adapters=_adapters("Explain room rent", evidence_use="INTERNAL_CERTIFICATION"),
    )

    evidence_result = execution.result.stage_results[
        INTELLIGENCE_RESPONSE_STAGE_ORDER.index(EVIDENCE_STAGE)
    ]
    assert evidence_result.status == "FAILED"
    assert "must explicitly use USER_ANSWER" in evidence_result.failure.message
