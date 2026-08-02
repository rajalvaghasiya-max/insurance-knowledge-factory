"""Governed cross-provider execution with mandatory rule-family preflight."""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.contracts.rule_family_registry import (
    RuleFamilyBinding,
    RuleFamilyDefinition,
    RuleFamilyValidationResult,
    validate_contract_against_family,
)
from insurance_intelligence.contracts.semantic_fidelity import (
    ExplanationSemanticContract,
    FidelityRoutingPolicy,
    RuleFamilyCertification,
)
from insurance_intelligence.llm.openai_gemini_cross_provider import (
    OpenAIGeminiCrossProvider,
    OpenAIGeminiCrossProviderResult,
)


class RuleFamilyPreflightError(RuntimeError):
    """Raised before provider execution when a contract is not family-conformant."""

    def __init__(self, result: RuleFamilyValidationResult):
        self.result = result
        codes = ", ".join(result.error_codes) or "UNKNOWN_RULE_FAMILY_PREFLIGHT_FAILURE"
        super().__init__(f"Rule-family preflight failed: {codes}")


@dataclass(frozen=True)
class GovernedCrossProviderEvaluator:
    provider: OpenAIGeminiCrossProvider
    family: RuleFamilyDefinition
    binding: RuleFamilyBinding

    def evaluate(
        self,
        contract: ExplanationSemanticContract,
        *,
        audience: str,
        reading_level: str,
        policy: FidelityRoutingPolicy,
        certification: RuleFamilyCertification | None,
        data_classification: str,
    ) -> OpenAIGeminiCrossProviderResult:
        preflight = validate_contract_against_family(contract, self.family, self.binding)
        if not preflight.valid:
            raise RuleFamilyPreflightError(preflight)
        return self.provider.evaluate(
            contract,
            audience=audience,
            reading_level=reading_level,
            policy=policy,
            certification=certification,
            data_classification=data_classification,
        )


__all__ = [
    "GovernedCrossProviderEvaluator",
    "RuleFamilyPreflightError",
]
