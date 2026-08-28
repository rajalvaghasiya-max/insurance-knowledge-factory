from insurance_intelligence.contracts.full_cycle import (
    FULL_CYCLE_STAGE_ORDER,
    INTELLIGENCE_RESPONSE_STAGE_ORDER,
    KNOWLEDGE_BUILD_STAGE_ORDER,
    build_orchestration_request,
    build_product_scope,
)


EXPECTED_SAFE_RESPONSE_ORDER = (
    "REQUEST_INTAKE",
    "CERTIFIED_KNOWLEDGE_RETRIEVAL",
    "AUTHORITY_CLASSIFICATION",
    "INTENT_ANALYSIS",
    "AUTHORITY_INTENT_RECONCILIATION",
    "CONTEXT_BUILDING",
    "INSTANCE_SUFFICIENCY",
    "REASONING_PLANNING",
    "EVIDENCE_RESOLUTION_ENFORCED",
    "REASONING",
    "DECISION_GATE_AUTHORITY_ENFORCED",
    "EXPLANATION_AUTHORITY_ENFORCED",
    "RESPONSE_ASSEMBLY",
    "LLM_RENDERING",
    "FINAL_EVALUATION",
)


def _scope():
    return build_product_scope(
        domain="health",
        insurer_id="star_health",
        product_id="star_comprehensive",
    )


def test_response_order_exactly_matches_guarded_safety_path():
    assert INTELLIGENCE_RESPONSE_STAGE_ORDER == EXPECTED_SAFE_RESPONSE_ORDER


def test_full_cycle_appends_guarded_response_order_after_knowledge_build():
    assert FULL_CYCLE_STAGE_ORDER == KNOWLEDGE_BUILD_STAGE_ORDER + EXPECTED_SAFE_RESPONSE_ORDER


def test_unguarded_legacy_top_level_stages_are_not_exposed():
    forbidden = {
        "APPLICABILITY",
        "DECISION_GATE",
        "EXPLANATION",
    }
    assert forbidden.isdisjoint(INTELLIGENCE_RESPONSE_STAGE_ORDER)


def test_authority_is_classified_before_intent_reconciliation():
    order = INTELLIGENCE_RESPONSE_STAGE_ORDER
    assert order.index("AUTHORITY_CLASSIFICATION") < order.index("AUTHORITY_INTENT_RECONCILIATION")
    assert order.index("INTENT_ANALYSIS") < order.index("AUTHORITY_INTENT_RECONCILIATION")


def test_instance_sufficiency_precedes_planning_and_evidence():
    order = INTELLIGENCE_RESPONSE_STAGE_ORDER
    assert order.index("INSTANCE_SUFFICIENCY") < order.index("REASONING_PLANNING")
    assert order.index("INSTANCE_SUFFICIENCY") < order.index("EVIDENCE_RESOLUTION_ENFORCED")


def test_guarded_evidence_precedes_reasoning_and_guarded_decision():
    order = INTELLIGENCE_RESPONSE_STAGE_ORDER
    assert order.index("EVIDENCE_RESOLUTION_ENFORCED") < order.index("REASONING")
    assert order.index("REASONING") < order.index("DECISION_GATE_AUTHORITY_ENFORCED")


def test_guarded_decision_precedes_guarded_explanation_and_response():
    order = INTELLIGENCE_RESPONSE_STAGE_ORDER
    assert order.index("DECISION_GATE_AUTHORITY_ENFORCED") < order.index("EXPLANATION_AUTHORITY_ENFORCED")
    assert order.index("EXPLANATION_AUTHORITY_ENFORCED") < order.index("RESPONSE_ASSEMBLY")


def test_intelligence_request_uses_guarded_order_by_default():
    request = build_orchestration_request(
        execution_id="safe-order-1",
        mode="INTELLIGENCE_RESPONSE",
        product_scope=_scope(),
        question="What does this co-payment mean?",
        audience="CUSTOMER",
        knowledge_snapshot_id="snapshot-1",
    )
    assert request.requested_stage_order == EXPECTED_SAFE_RESPONSE_ORDER
