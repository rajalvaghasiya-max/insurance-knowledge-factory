from __future__ import annotations

from dataclasses import replace

from insurance_intelligence.contracts.rule_family_registry import (
    RuleFamilyBinding,
    build_conditional_copayment_family,
    validate_contract_against_family,
)
from insurance_intelligence.contracts.semantic_fidelity import (
    CanonicalSemanticComponent,
    ExplanationSemanticContract,
    SemanticAttribute,
)
from scripts.run_mo_022g_star_copay_live import build_star_copay_contract


def _binding(contract: ExplanationSemanticContract) -> RuleFamilyBinding:
    return RuleFamilyBinding(
        family_id="CONDITIONAL_COPAYMENT",
        family_version="1.0",
        contract_id=contract.contract_id,
        component_roles=(
            ("trigger", contract.components[0].component_id),
            ("effect", contract.components[1].component_id),
            ("exception", contract.components[2].component_id),
            ("scope", contract.components[3].component_id),
        ),
    )


def _replace_attribute(
    component: CanonicalSemanticComponent,
    name: str,
    value: object,
) -> CanonicalSemanticComponent:
    attributes = tuple(
        SemanticAttribute(name=item.name, value=value if item.name == name else item.value)
        for item in component.attributes
    )
    return replace(component, attributes=attributes)


def test_star_contract_matches_reusable_conditional_copayment_family():
    contract = build_star_copay_contract()
    result = validate_contract_against_family(
        contract,
        build_conditional_copayment_family(),
        _binding(contract),
    )
    assert result.valid is True
    assert result.error_codes == ()


def test_second_product_values_reuse_same_family_without_new_validator_code():
    star = build_star_copay_contract()
    second_product = replace(
        star,
        contract_id="contract-second-product-conditional-copay-v1",
        components=(
            _replace_attribute(star.components[0], "value", 65),
            _replace_attribute(star.components[1], "percentage", 20),
            _replace_attribute(star.components[2], "age_value", 65),
            replace(
                star.components[3],
                attributes=(
                    SemanticAttribute("mode", "exact_set"),
                    SemanticAttribute("sections", ("A.1", "A.3", "B.2")),
                ),
            ),
        ),
    )
    result = validate_contract_against_family(
        second_product,
        build_conditional_copayment_family(),
        _binding(second_product),
    )
    assert result.valid is True
    assert result.error_codes == ()


def test_family_validation_rejects_missing_logic_and_invalid_vocabulary():
    contract = build_star_copay_contract()
    exception = contract.components[2]
    invalid_exception = replace(
        exception,
        attributes=tuple(
            item
            for item in exception.attributes
            if item.name != "logical_operator"
        ),
    )
    invalid_trigger = _replace_attribute(contract.components[0], "operator", "approximately")
    invalid_contract = replace(
        contract,
        components=(
            invalid_trigger,
            contract.components[1],
            invalid_exception,
            contract.components[3],
        ),
    )
    result = validate_contract_against_family(
        invalid_contract,
        build_conditional_copayment_family(),
        _binding(invalid_contract),
    )
    assert result.valid is False
    assert result.error_codes == (
        "COMPONENT_ATTRIBUTE_VOCABULARY_MISMATCH",
        "MISSING_REQUIRED_COMPONENT_ATTRIBUTE",
    )


def test_optional_exception_may_be_absent_without_changing_family():
    contract = build_star_copay_contract()
    without_exception = replace(
        contract,
        contract_id="contract-no-exception-conditional-copay-v1",
        components=(contract.components[0], contract.components[1], contract.components[3]),
    )
    binding = RuleFamilyBinding(
        family_id="CONDITIONAL_COPAYMENT",
        family_version="1.0",
        contract_id=without_exception.contract_id,
        component_roles=(
            ("trigger", without_exception.components[0].component_id),
            ("effect", without_exception.components[1].component_id),
            ("scope", without_exception.components[2].component_id),
        ),
    )
    result = validate_contract_against_family(
        without_exception,
        build_conditional_copayment_family(),
        binding,
    )
    assert result.valid is True
    assert result.error_codes == ()
