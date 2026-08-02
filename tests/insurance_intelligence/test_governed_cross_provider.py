from __future__ import annotations

from dataclasses import dataclass

import pytest

from insurance_intelligence.contracts.rule_family_registry import (
    RuleFamilyBinding,
    build_conditional_copayment_family,
)
from insurance_intelligence.llm.governed_cross_provider import (
    GovernedCrossProviderEvaluator,
    RuleFamilyPreflightError,
)
from scripts.run_mo_022g_star_copay_live import build_live_policy, build_star_copay_contract
from scripts.run_mo_022g_star_copay_openai_gemini import build_star_copay_family_binding


@dataclass
class _ProviderSpy:
    result: object = "delegated-result"
    calls: int = 0

    def evaluate(self, contract, **kwargs):
        self.calls += 1
        return self.result


def test_valid_family_contract_delegates_once():
    provider = _ProviderSpy()
    evaluator = GovernedCrossProviderEvaluator(
        provider=provider,
        family=build_conditional_copayment_family(),
        binding=build_star_copay_family_binding(),
    )

    result = evaluator.evaluate(
        build_star_copay_contract(),
        audience="customer",
        reading_level="plain_language",
        policy=build_live_policy(),
        certification=None,
        data_classification="PUBLIC",
    )

    assert result == "delegated-result"
    assert provider.calls == 1


def test_invalid_family_binding_fails_before_provider_call():
    provider = _ProviderSpy()
    contract = build_star_copay_contract()
    invalid_binding = RuleFamilyBinding(
        family_id="CONDITIONAL_COPAYMENT",
        family_version="1.0",
        contract_id=contract.contract_id,
        component_roles=(
            ("effect", "copay-effect"),
            ("exception", "continuous-renewal-exception"),
            ("scope", "applicability-scope"),
        ),
    )
    evaluator = GovernedCrossProviderEvaluator(
        provider=provider,
        family=build_conditional_copayment_family(),
        binding=invalid_binding,
    )

    with pytest.raises(RuleFamilyPreflightError) as captured:
        evaluator.evaluate(
            contract,
            audience="customer",
            reading_level="plain_language",
            policy=build_live_policy(),
            certification=None,
            data_classification="PUBLIC",
        )

    assert "MISSING_REQUIRED_COMPONENT_ROLE" in captured.value.result.error_codes
    assert "UNBOUND_CONTRACT_COMPONENT" in captured.value.result.error_codes
    assert provider.calls == 0
