from __future__ import annotations

import pytest

from insurance_intelligence.contracts.authority_intent_reconciliation import build_output as build_reconciliation
from insurance_intelligence.contracts.context import build_output as build_context, build_resolved_context_item
from insurance_intelligence.contracts.instance_sufficiency import (
    InstanceSufficiencyContractError,
    build_attestation,
    build_input,
)
from insurance_intelligence.instance_sufficiency import InstanceSufficiencyGuard


def reconciliation(*, intent="TERM_EXPLANATION", status="CONSISTENT_ASSERTIVE", exit_required=False):
    return build_reconciliation(
        request_id="req-1",
        authority_class="ASSERTIVE",
        primary_intent=intent,
        secondary_intents=(),
        reconciliation_status=status,
        minimum_guard="OUT_OF_SCOPE_EXIT" if status == "OUT_OF_SCOPE" else (
            "INTENT_EXIT_BEFORE_REASONING" if exit_required else "STANDARD_ASSERTION_GROUNDING"
        ),
        advisory_safety_obligation=False,
        authority_clarification_required=False,
        reconciliation_clarification_required=False,
        intent_exit_required=exit_required,
        ordinary_assertion_path_permitted=not exit_required,
        recommendation_authorized=False,
        basis="test fixture",
    )


def context(*, answerability="ANSWERABLE", items=()):
    return build_context(
        request_id="req-1",
        answerability=answerability,
        context_completeness=1.0 if answerability == "ANSWERABLE" else 0.5,
        resolved_context=items,
        clarification_questions=("Please clarify.",) if answerability == "CLARIFICATION_REQUIRED" else (),
        classification_basis=("user_provided",),
    )


def item(key: str, value: str = "Star Comprehensive"):
    return build_resolved_context_item(
        key=key,
        value=value,
        category="PRODUCT" if "product" in key or "comparison" in key else "POLICY",
        provenance="USER_PROVIDED",
        source_reference="turn:user",
        confidence=1.0,
        materiality="high",
    )


def resolved_attestation(key: str, kind: str = "PRODUCT"):
    return build_attestation(
        instance_kind=kind,
        context_key=key,
        resolution_status="RESOLVED",
        canonical_identity="star_health:star_comprehensive",
        identity_record_ref="knowledge/factory/identity/star.json",
        identity_record_hash="a" * 64,
        resolution_basis="governed_identity_record",
    )


def evaluate(rec, ctx, attestations=()):
    return InstanceSufficiencyGuard().evaluate(
        build_input(
            request_id="req-1",
            reconciliation=rec,
            context=ctx,
            attestations=attestations,
        )
    )


def test_instance_insensitive_term_explanation_passes_without_identity():
    result = evaluate(reconciliation(intent="TERM_EXPLANATION"), context())
    assert result.outcome == "PASS"
    assert result.planning_authorized is True
    assert result.required_instance_keys == ()


def test_product_explanation_requires_governed_identity_attestation():
    ctx = context(items=(item("product_reference"),))
    result = evaluate(reconciliation(intent="PRODUCT_EXPLANATION"), ctx)
    assert result.outcome == "CLARIFICATION_REQUIRED"
    assert result.planning_authorized is False
    assert result.unresolved_instance_keys == ("product_reference",)


def test_product_explanation_passes_with_resolved_identity_attestation():
    ctx = context(items=(item("product_reference"),))
    result = evaluate(
        reconciliation(intent="PRODUCT_EXPLANATION"),
        ctx,
        (resolved_attestation("product_reference"),),
    )
    assert result.outcome == "PASS"
    assert result.resolved_instance_keys == ("product_reference",)


def test_product_comparison_requires_both_subjects_to_resolve():
    ctx = context(items=(item("comparison_subject_1", "A"), item("comparison_subject_2", "B")))
    result = evaluate(
        reconciliation(intent="PRODUCT_COMPARISON"),
        ctx,
        (resolved_attestation("comparison_subject_1"),),
    )
    assert result.outcome == "CLARIFICATION_REQUIRED"
    assert result.resolved_instance_keys == ("comparison_subject_1",)
    assert result.unresolved_instance_keys == ("comparison_subject_2",)


def test_candidate_text_without_governed_attestation_never_counts_as_identity():
    ctx = context(items=(
        build_resolved_context_item(
            key="policy_or_product_reference",
            value="Star Comprehensive",
            category="POLICY",
            provenance="SYSTEM_DERIVED",
            source_reference="intent_analysis.candidate_entities",
            confidence=0.95,
            materiality="high",
        ),
    ))
    result = evaluate(reconciliation(intent="COVERAGE_CHECK"), ctx)
    assert result.outcome == "CLARIFICATION_REQUIRED"
    assert result.planning_authorized is False


def test_ambiguous_attestation_fails_closed():
    ctx = context(items=(item("product_reference"),))
    attestation = build_attestation(
        instance_kind="PRODUCT",
        context_key="product_reference",
        resolution_status="AMBIGUOUS",
        resolution_basis="multiple_governed_candidates",
    )
    result = evaluate(reconciliation(intent="PRODUCT_EXPLANATION"), ctx, (attestation,))
    assert result.outcome == "CLARIFICATION_REQUIRED"


def test_clause_implication_without_specific_instance_can_pass():
    result = evaluate(reconciliation(intent="CLAUSE_IMPLICATION"), context())
    assert result.outcome == "PASS"
    assert result.required_instance_keys == ()


def test_clause_implication_with_specific_reference_requires_resolution():
    ctx = context(items=(item("policy_or_product_reference"),))
    result = evaluate(reconciliation(intent="CLAUSE_IMPLICATION"), ctx)
    assert result.outcome == "CLARIFICATION_REQUIRED"
    assert result.unresolved_instance_keys == ("policy_or_product_reference",)


def test_upstream_context_clarification_exits_before_instance_planning():
    result = evaluate(reconciliation(intent="PRODUCT_EXPLANATION"), context(answerability="CLARIFICATION_REQUIRED"))
    assert result.outcome == "CLARIFICATION_REQUIRED"
    assert result.planning_authorized is False


def test_out_of_scope_is_preserved():
    rec = build_reconciliation(
        request_id="req-1",
        authority_class="ASSERTIVE",
        primary_intent="OUT_OF_SCOPE",
        secondary_intents=(),
        reconciliation_status="OUT_OF_SCOPE",
        minimum_guard="OUT_OF_SCOPE_EXIT",
        advisory_safety_obligation=False,
        authority_clarification_required=False,
        reconciliation_clarification_required=False,
        intent_exit_required=True,
        ordinary_assertion_path_permitted=False,
        recommendation_authorized=False,
        basis="test fixture",
    )
    result = evaluate(rec, context(answerability="OUT_OF_SCOPE"))
    assert result.outcome == "OUT_OF_SCOPE"
    assert result.planning_authorized is False


def test_resolved_attestation_requires_identity_record_and_hash():
    with pytest.raises(InstanceSufficiencyContractError):
        build_attestation(
            instance_kind="PRODUCT",
            context_key="product_reference",
            resolution_status="RESOLVED",
            canonical_identity="star_health:star_comprehensive",
            resolution_basis="governed_identity_record",
        )


def test_cross_request_mismatch_is_rejected():
    bad_context = build_context(
        request_id="other",
        answerability="ANSWERABLE",
        context_completeness=1.0,
        classification_basis=("fallback_rule",),
    )
    with pytest.raises(InstanceSufficiencyContractError):
        build_input(
            request_id="req-1",
            reconciliation=reconciliation(),
            context=bad_context,
        )
