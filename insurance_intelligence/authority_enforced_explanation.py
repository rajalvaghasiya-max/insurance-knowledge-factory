"""Authority-enforced entry point for the existing Explanation Generator."""
from __future__ import annotations

from collections.abc import Callable, Mapping

from insurance_intelligence.contracts.authority_enforcement import AuthorityEnforcementResult
from insurance_intelligence.contracts.reasoning import Finding
from insurance_intelligence.contracts.explanation import build_input as build_explanation_input
from insurance_intelligence.explanation.generator import generate_explanation
from insurance_intelligence.explanation.registry import ExplanationStyleRegistry, TerminologyRegistry


class AuthorityExplanationEnforcementError(ValueError):
    """Raised when explanation generation would bypass authority enforcement."""


class AuthorityEnforcedExplanationGenerator:
    """Permit rendering only after the ordinary assertive path has cleared.

    The legacy Explanation Generator remains unchanged for historical pilot
    compatibility. New Insurance Intelligence orchestration should enter through
    this wrapper so a raw DecisionGateOutput cannot bypass the authority guard.
    """

    def __init__(self, generator: Callable[..., object] = generate_explanation) -> None:
        self._generator = generator

    def generate(
        self,
        *,
        authority_result: AuthorityEnforcementResult,
        findings_by_id: Mapping[str, Finding],
        style_registry: ExplanationStyleRegistry,
        terminology_registry: TerminologyRegistry | None = None,
        audience: str = "CUSTOMER",
        reading_level: str = "SIMPLE",
        explanation_mode: str = "PLAIN_LANGUAGE",
        communication_context: Mapping[str, object] | None = None,
    ):
        if not isinstance(authority_result, AuthorityEnforcementResult):
            raise AuthorityExplanationEnforcementError(
                "authority_result must be a validated AuthorityEnforcementResult"
            )
        if authority_result.enforcement_outcome != "DELEGATED_TO_DECISION_GATE":
            raise AuthorityExplanationEnforcementError(
                "explanation is not authorized unless authority enforcement delegated to Decision Gate"
            )
        if not authority_result.decision_gate_called or authority_result.decision_output is None:
            raise AuthorityExplanationEnforcementError(
                "delegated authority result must preserve the Decision Gate output"
            )
        if authority_result.advisory_safety_obligation:
            raise AuthorityExplanationEnforcementError(
                "advisory safety obligation cannot enter the ordinary explanation path"
            )
        if not authority_result.ordinary_assertion_path_permitted:
            raise AuthorityExplanationEnforcementError(
                "ordinary assertion path must be explicitly permitted before explanation"
            )
        if authority_result.recommendation_authorized:
            raise AuthorityExplanationEnforcementError(
                "recommendation authorization is not supported by this milestone"
            )

        explanation_input = build_explanation_input(
            request_id=authority_result.request_id,
            decision_output=authority_result.decision_output,
            audience=audience,
            reading_level=reading_level,
            explanation_mode=explanation_mode,
            communication_context=communication_context,
        )
        return self._generator(
            explanation_input=explanation_input,
            findings_by_id=findings_by_id,
            style_registry=style_registry,
            terminology_registry=terminology_registry,
        )
