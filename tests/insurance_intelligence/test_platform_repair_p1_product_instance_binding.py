from insurance_intelligence.orchestration.product_instance_binding import (
    _product_compatible_context_keys,
)


def test_policy_fact_reference_is_product_compatible_for_governed_scope_binding():
    keys = _product_compatible_context_keys("POLICY_FACT_LOOKUP")
    assert "policy_or_document_reference" in keys


def test_existing_policy_or_product_reference_remains_product_compatible():
    keys = _product_compatible_context_keys("COVERAGE_CHECK")
    assert "policy_or_product_reference" in keys
