from __future__ import annotations

import pytest

from insurance_intelligence.contracts.authority_intent_reconciliation import (
    build_output as build_reconciliation_output,
)
from insurance_intelligence.contracts.context import (
    build_output as build_context_output,
    build_resolved_context_item,
)
from insurance_intelligence.contracts.full_cycle import build_product_scope
from insurance_intelligence.entity_resolution.product_resolver import (
    GovernedProductEntity,
    GovernedProductEntityRegistry,
)
from insurance_intelligence.orchestration.product_instance_binding import (
    ProductIdentityRecordEvidence,
    ProductInstanceBindingError,
    bind_product_scope_to_context,
)


def _reconciliation(intent: str, request_id: str = "req-1"):
    return build_reconciliation_output(
        request_id=request_id,
        authority_class="ASSERTIVE",
        primary_intent=intent,
        secondary_intents=(),
        reconciliation_status="CONSISTENT_ASSERTIVE",
        minimum_guard="STANDARD_ASSERTION_GROUNDING",
        advisory_safety_obligation=False,
        authority_clarification_required=False,
        reconciliation_clarification_required=False,
        intent_exit_required=False,
        ordinary_assertion_path_permitted=True,
        recommendation_authorized=False,
        basis="test ordinary assertion path",
    )


def _context(*items, request_id: str = "req-1"):
    return build_context_output(
        request_id=request_id,
        answerability="ANSWERABLE",
        context_completeness=1.0,
        resolved_context=items,
        classification_basis=("user_provided",),
    )


def _item(key: str, value: str, category: str):
    return build_resolved_context_item(
        key=key,
        value=value,
        category=category,
        provenance="USER_PROVIDED",
        source_reference=f"test:{key}",
        confidence=1.0,
        materiality="high",
    )


def _registry():
    return GovernedProductEntityRegistry(
        (
            GovernedProductEntity(
                canonical_entity_id="acme_health:shield_plus",
                insurer_id="acme_health",
                product_id="shield_plus",
                canonical_product_name="Acme Shield Plus",
                uin="ACMEHLIP12345678",
                aliases=("Shield Plus",),
            ),
            GovernedProductEntity(
                canonical_entity_id="acme_health:shield_basic",
                insurer_id="acme_health",
                product_id="shield_basic",
                canonical_product_name="Acme Shield Basic",
                uin="ACMEHLIP87654321",
                aliases=("Shield Basic",),
            ),
        )
    )


def _scope():
    return build_product_scope(
        domain="health",
        insurer_id="acme_health",
        product_id="shield_plus",
    )


def _identity_lookup(entity_id: str):
    if entity_id != "acme_health:shield_plus":
        return None
    return ProductIdentityRecordEvidence(
        canonical_entity_id=entity_id,
        identity_record_ref="governance/acme_shield_plus_identity.json",
        identity_record_hash="a" * 64,
    )


def test_product_explanation_context_is_attested_only_after_governed_exact_scope_match():
    result = bind_product_scope_to_context(
        product_scope=_scope(),
        reconciliation=_reconciliation("PRODUCT_EXPLANATION"),
        context=_context(_item("product_reference", "Shield Plus", "PRODUCT")),
        registry=_registry(),
        identity_record_lookup=_identity_lookup,
    )

    assert result.resolution.status == "RESOLVED"
    assert result.resolution.selected_entity is not None
    assert result.resolution.selected_entity.canonical_entity_id == "acme_health:shield_plus"
    assert len(result.attestations) == 1
    attestation = result.attestations[0]
    assert attestation.context_key == "product_reference"
    assert attestation.instance_kind == "PRODUCT"
    assert attestation.canonical_identity == "acme_health:shield_plus"
    assert result.resolved_candidate_references == {
        "product_reference": "acme_health:shield_plus"
    }


def test_other_governed_product_text_is_not_elevated_to_scoped_identity():
    result = bind_product_scope_to_context(
        product_scope=_scope(),
        reconciliation=_reconciliation("PRODUCT_EXPLANATION"),
        context=_context(_item("product_reference", "Shield Basic", "PRODUCT")),
        registry=_registry(),
        identity_record_lookup=_identity_lookup,
    )

    assert result.resolution.status == "RESOLVED"
    assert result.attestations == ()
    assert result.resolved_candidate_references == {}


def test_policy_or_product_reference_can_bind_product_without_treating_policy_only_keys_as_products():
    dual_use = bind_product_scope_to_context(
        product_scope=_scope(),
        reconciliation=_reconciliation("COVERAGE_CHECK"),
        context=_context(
            _item("coverage_subject", "hospitalization", "SCENARIO"),
            _item("policy_or_product_reference", "Shield Plus", "POLICY"),
        ),
        registry=_registry(),
        identity_record_lookup=_identity_lookup,
    )
    assert tuple(item.context_key for item in dual_use.attestations) == (
        "policy_or_product_reference",
    )

    policy_only = bind_product_scope_to_context(
        product_scope=_scope(),
        reconciliation=_reconciliation("POLICY_COMPARISON"),
        context=_context(
            _item("comparison_subject_1", "Shield Plus", "POLICY"),
            _item("comparison_subject_2", "Shield Basic", "POLICY"),
        ),
        registry=_registry(),
        identity_record_lookup=_identity_lookup,
    )
    assert policy_only.attestations == ()
    assert policy_only.resolved_candidate_references == {}


def test_identity_record_evidence_must_match_the_resolved_scoped_entity():
    def mismatched_lookup(_: str):
        return ProductIdentityRecordEvidence(
            canonical_entity_id="acme_health:shield_basic",
            identity_record_ref="governance/wrong_identity.json",
            identity_record_hash="b" * 64,
        )

    with pytest.raises(ProductInstanceBindingError, match="canonical_entity_id"):
        bind_product_scope_to_context(
            product_scope=_scope(),
            reconciliation=_reconciliation("PRODUCT_EXPLANATION"),
            context=_context(_item("product_reference", "Shield Plus", "PRODUCT")),
            registry=_registry(),
            identity_record_lookup=mismatched_lookup,
        )
