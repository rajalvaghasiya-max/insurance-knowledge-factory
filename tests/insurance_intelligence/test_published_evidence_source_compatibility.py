from pathlib import Path

from insurance_intelligence.contracts.evidence import build_input
from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement, build_plan
from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.evidence.coverage_registry_source import (
    build_coverage_registry_published_source_lookup,
)
from insurance_intelligence.evidence.published_resolver import PublishedEvidenceResolver


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "knowledge/factory/registry_backed"
SOURCE_LOOKUP = build_coverage_registry_published_source_lookup(
    registry=HEALTH_COVERAGE_REGISTRY,
    repository_root=ROOT,
)


def _room_rent_source():
    requirement = build_evidence_requirement(
        requirement_id="source-selection",
        evidence_category="NORMALIZED_PRODUCT_FACT",
        subject_reference="star_health:star_comprehensive",
        required=True,
        authority_requirement="AUTHORITATIVE",
        version_requirement="CURRENT_APPLICABLE",
        reason="Explain the room rent or room category limit for Star Comprehensive",
        requested_by_step="step-1",
    )
    source = SOURCE_LOOKUP("star_health:star_comprehensive", requirement)
    assert source is not None
    assert {item.source_type for item in source.certified_evidence.evidence_packages} == {
        "POLICY_WORDING"
    }
    return source


def _resolve(*, evidence_category: str):
    requirement = build_evidence_requirement(
        requirement_id=f"requirement:{evidence_category.lower()}",
        evidence_category=evidence_category,
        subject_reference="star_health:star_comprehensive",
        required=True,
        authority_requirement="AUTHORITATIVE",
        version_requirement="CURRENT_APPLICABLE",
        reason="Resolve the governed room-rent publication",
        requested_by_step="step-1",
    )
    plan = build_plan(
        request_id=f"request:{evidence_category.lower()}",
        plan_id=f"plan:{evidence_category.lower()}",
        plan_type="DIRECT_FACT_PLAN",
        execution_mode="DIRECT_GROUNDED",
        goal="Resolve the governed room-rent publication",
        expected_outcome="DIRECT_FACT_RESPONSE",
        plan_status="READY",
        confidence=1.0,
        required_evidence=(requirement,),
    )
    source = _room_rent_source()
    return PublishedEvidenceResolver(lambda entity, req: source).resolve(
        build_input(
            request_id=plan.request_id,
            reasoning_plan=plan,
            resolution_context={"evidence_use": "USER_ANSWER"},
            repository_roots=(str(REGISTRY_ROOT),),
            strict_mode="STRICT",
        )
    )


def test_policy_wording_requirement_accepts_policy_wording_publication() -> None:
    output = _resolve(evidence_category="POLICY_WORDING")

    assert output.evidence_packages
    assert output.requirement_results[0].status == "SATISFIED"
    assert {item.source_type for item in output.evidence_packages} == {"POLICY_WORDING"}


def test_policy_schedule_requirement_rejects_policy_wording_publication() -> None:
    output = _resolve(evidence_category="POLICY_SCHEDULE")

    assert not output.evidence_packages
    result = output.requirement_results[0]
    assert result.status == "MISSING"
    assert "source type does not satisfy planner evidence category POLICY_SCHEDULE" in (
        result.missing_reason or ""
    )
