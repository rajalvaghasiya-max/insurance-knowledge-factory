from __future__ import annotations

from dataclasses import replace

from insurance_intelligence.contracts.rule_family_registry import RuleFamilyBinding
from insurance_intelligence.contracts.semantic_fidelity import (
    SemanticAttribute,
    SemanticComparisonStatus,
    SemanticComponentComparison,
    SemanticFidelityReport,
)
from insurance_intelligence.evaluation.explanation_coherence import (
    ExplanationCoherenceStatus,
    validate_explanation_coherence,
)
from scripts.run_mo_022g_star_copay_live import build_star_copay_contract


def _binding() -> RuleFamilyBinding:
    return RuleFamilyBinding(
        family_id="CONDITIONAL_COPAYMENT",
        family_version="1.0",
        contract_id="contract-star-comprehensive-conditional-copay-v1",
        component_roles=(
            ("trigger", "entry-age-trigger"),
            ("effect", "copay-effect"),
            ("exception", "continuous-renewal-exception"),
            ("scope", "applicability-scope"),
        ),
    )


def _report(contract, *, mismatched_component_id: str | None = None) -> SemanticFidelityReport:
    comparisons = []
    for component in contract.components:
        status = (
            SemanticComparisonStatus.MISMATCHED
            if component.component_id == mismatched_component_id
            else SemanticComparisonStatus.MATCHED
        )
        comparisons.append(
            SemanticComponentComparison(
                component_id=component.component_id,
                status=status,
                risk_tier=component.risk_tier,
                mismatch_codes=("TEST_MISMATCH",) if status is SemanticComparisonStatus.MISMATCHED else (),
                expected_attributes=component.attributes,
                observed_attributes=component.attributes,
                confidence=0.9,
                extractor_agreement=1.0,
            )
        )
    return SemanticFidelityReport(
        report_id="report-1",
        contract_id=contract.contract_id,
        comparisons=tuple(comparisons),
        hard_failure_codes=(),
        unresolved_component_ids=(),
    )


def _replace_component_attributes(contract, component_id: str, **changes: object):
    components = []
    for component in contract.components:
        if component.component_id != component_id:
            components.append(component)
            continue
        values = {item.name: item.value for item in component.attributes}
        values.update(changes)
        components.append(
            replace(
                component,
                attributes=tuple(
                    SemanticAttribute(name=name, value=value)
                    for name, value in values.items()
                ),
            )
        )
    return replace(contract, components=tuple(components))


def test_star_conditional_copay_is_deterministically_coherent():
    contract = build_star_copay_contract()

    result = validate_explanation_coherence(contract, _binding(), _report(contract))

    assert result.status is ExplanationCoherenceStatus.COHERENT
    assert result.failure_codes == ()
    assert all(check.passed for check in result.checks)


def test_component_fidelity_mismatch_makes_coherence_incomplete():
    contract = build_star_copay_contract()

    result = validate_explanation_coherence(
        contract,
        _binding(),
        _report(contract, mismatched_component_id="copay-effect"),
    )

    assert result.status is ExplanationCoherenceStatus.INCOMPLETE
    assert "COHERENCE_PROOF_INCOMPLETE" in result.failure_codes


def test_overlapping_exception_and_trigger_fail_as_cross_component_contradiction():
    contract = _replace_component_attributes(
        build_star_copay_contract(),
        "continuous-renewal-exception",
        age_operator="<",
        age_value=62,
    )

    result = validate_explanation_coherence(contract, _binding(), _report(contract))

    assert result.status is ExplanationCoherenceStatus.INCOHERENT
    assert "TRIGGER_EXCEPTION_CONTRADICTION" in result.failure_codes


def test_exception_or_logic_fails_closed_as_incoherent():
    contract = _replace_component_attributes(
        build_star_copay_contract(),
        "continuous-renewal-exception",
        logical_operator="OR",
    )

    result = validate_explanation_coherence(contract, _binding(), _report(contract))

    assert result.status is ExplanationCoherenceStatus.INCOHERENT
    assert "EXCEPTION_LOGIC_MISMATCH" in result.failure_codes
