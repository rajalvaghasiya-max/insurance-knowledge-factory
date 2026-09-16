from __future__ import annotations

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


def test_published_resolver_preserves_authoritative_publication_limitations() -> None:
    requirement = build_evidence_requirement(
        requirement_id="req_fact",
        evidence_category="NORMALIZED_PRODUCT_FACT",
        subject_reference="star_health:star_comprehensive",
        required=True,
        authority_requirement="AUTHORITATIVE",
        version_requirement="CURRENT_APPLICABLE",
        reason="What is the PED waiting period in Star Comprehensive?",
        requested_by_step="step_1",
    )
    plan = build_plan(
        request_id="req-d0-ped-limitations",
        plan_id="plan-d0-ped-limitations",
        plan_type="DIRECT_FACT_PLAN",
        execution_mode="DIRECT_GROUNDED",
        goal="Address a TERM_EXPLANATION request: What is the PED waiting period in Star Comprehensive?",
        expected_outcome="DIRECT_FACT_RESPONSE",
        plan_status="READY",
        confidence=1.0,
        required_evidence=(requirement,),
    )
    lookup = build_coverage_registry_published_source_lookup(
        registry=HEALTH_COVERAGE_REGISTRY,
        repository_root=ROOT,
    )
    output = PublishedEvidenceResolver(lookup).resolve(
        build_input(
            request_id=plan.request_id,
            reasoning_plan=plan,
            resolution_context={"evidence_use": "USER_ANSWER"},
            repository_roots=(str(REGISTRY_ROOT),),
            strict_mode="STRICT",
        )
    )

    limitation_text = " ".join(output.limitations).lower()
    assert output.evidence_packages
    assert "customer-specific eligibility" in limitation_text
    assert "claim payment" in limitation_text
    assert "36 months to 12 months" in limitation_text
    assert "policy-specific selection evidence" in limitation_text
