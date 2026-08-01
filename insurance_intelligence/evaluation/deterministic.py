"""Deterministic baseline evaluation for controlled LLM outputs (MO-022F.3)."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from insurance_intelligence.contracts.llm_evaluation import (
    DeterministicEvaluationResult,
    EvaluationCase,
    EvaluationExecutionStatus,
    EvaluationExpectedOutcome,
    EvaluationVerdict,
    ForbiddenBehaviour,
    ModelExecutionTrace,
    SemanticComponent,
)


class DeterministicEvaluatorError(ValueError):
    """Raised when deterministic evaluation inputs are inconsistent."""


@dataclass(frozen=True)
class DeterministicCheck:
    check_id: str
    passed: bool
    failure_code: str | None = None


_WORD_RE = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")
_PERCENT_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*%")
_EVIDENCE_ID_RE = re.compile(r"\bev-[a-z0-9][a-z0-9-]*\b", re.IGNORECASE)
_SECTION_RE = re.compile(r"\bii\.(?:[1-9]|1[0-9]|2[0-9])\b", re.IGNORECASE)
_SECTION_RANGE_RE = re.compile(
    r"\bii\.(?P<start>[1-9]|1[0-9]|2[0-9])\s+(?:through|to|-)\s+ii\.(?P<end>[1-9]|1[0-9]|2[0-9])\b",
    re.IGNORECASE,
)


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9.%']+", " ", text)
    return " ".join(text.split())


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(_WORD_RE.findall(_normalise(text)))


def _contains_phrase(output: str, expected: str) -> bool:
    normalised_output = _normalise(output)
    normalised_expected = _normalise(expected)
    if normalised_expected in normalised_output:
        return True

    expected_tokens = _tokens(expected)
    output_tokens = set(_tokens(output))
    if not expected_tokens:
        return False

    # Governed phrases may be safely paraphrased, but all material lexical anchors
    # must remain. Stop words are ignored; no semantic model is used.
    anchors = tuple(
        token
        for token in expected_tokens
        if token not in {"a", "an", "and", "as", "at", "be", "before", "for", "in", "is", "of", "or", "the", "to", "where", "with"}
    )
    return bool(anchors) and set(anchors) <= output_tokens


def _has_trigger_paraphrase(output: str, expected: str) -> bool:
    expected_normalised = _normalise(expected)
    if "61" not in expected_normalised or "entry" not in expected_normalised:
        return False

    normalised = _normalise(output)
    has_threshold = "61" in normalised and any(
        phrase in normalised
        for phrase in ("61 years or above", "61 or above", "61 years or older", "61 or older", "age 61")
    )
    has_entry = any(
        term in normalised
        for term in ("age at entry", "when they entered", "when you entered", "when they joined", "when you joined", "entered the policy", "entered the plan", "joined the policy", "joined the plan")
    )
    has_condition = any(
        term in normalised
        for term in ("if ", "when ", "where ", "trigger", "condition applies", "rule applies")
    )
    return has_threshold and has_entry and has_condition


def _has_effect_paraphrase(output: str, expected: str) -> bool:
    expected_normalised = _normalise(expected)
    if "claim" not in expected_normalised or not any(
        term in expected_normalised for term in ("each", "every", "all")
    ):
        return False

    normalised = _normalise(output)
    return any(
        phrase in normalised
        for phrase in ("each and every claim", "each claim", "every claim", "all claims")
    )


def _has_exception_paraphrase(output: str, expected: str) -> bool:
    expected_normalised = _normalise(expected)
    if "before 61" not in expected_normalised or "renew" not in expected_normalised:
        return False

    normalised = _normalise(output)
    has_negation = any(
        phrase in normalised
        for phrase in ("does not apply", "doesn't apply", "not apply", "is exempt", "are exempt")
    )
    has_pre_61_entry = "before 61" in normalised and any(
        term in normalised
        for term in ("entered", "joined", "entry")
    )
    has_continuity = any(
        phrase in normalised
        for phrase in ("renewed continuously", "continuous renewal", "continuously renewed")
    ) and any(
        phrase in normalised
        for phrase in ("without a break", "with no break", "without break", "no break")
    )
    return has_negation and has_pre_61_entry and has_continuity


def _section_set(text: str) -> set[str]:
    return {value.lower() for value in _SECTION_RE.findall(_normalise(text))}


def _has_invalid_scope_range(output: str, governed_sections: set[str]) -> bool:
    if not governed_sections:
        return False

    governed_numbers = {int(value.split(".", 1)[1]) for value in governed_sections}
    for match in _SECTION_RANGE_RE.finditer(_normalise(output)):
        start = int(match.group("start"))
        end = int(match.group("end"))
        expanded = set(range(min(start, end), max(start, end) + 1))
        if expanded != governed_numbers:
            return True
    return False


def _scope_present(case: EvaluationCase, output: str, expected: str) -> bool:
    normalised = _normalise(output)
    observed_sections = _section_set(output)

    # A reference output can carry the authoritative non-contiguous section set.
    # When available, require exact preservation and reject shorthand ranges that
    # silently introduce omitted sections.
    governed_sections = _section_set(case.reference_output or "")
    if governed_sections:
        return (
            "section" in normalised
            and observed_sections == governed_sections
            and not _has_invalid_scope_range(output, governed_sections)
        )

    expected_sections = _section_set(expected)
    if expected_sections:
        return "section" in normalised and expected_sections <= observed_sections

    return "section" in normalised and bool(observed_sections)


def _requirement_present(
    case: EvaluationCase,
    output: str,
    component: SemanticComponent,
    expected: str,
) -> bool:
    normalised = _normalise(output)
    if component is SemanticComponent.APPLICABILITY_SCOPE:
        return _scope_present(case, output, expected)
    if component is SemanticComponent.TRIGGER:
        return _contains_phrase(output, expected) or _has_trigger_paraphrase(output, expected)
    if component is SemanticComponent.EFFECT:
        return _contains_phrase(output, expected) or _has_effect_paraphrase(output, expected)
    if component is SemanticComponent.EXCEPTION:
        return _contains_phrase(output, expected) or _has_exception_paraphrase(output, expected)
    if component is SemanticComponent.EVIDENCE_REFERENCE:
        return _normalise(expected) in normalised
    if component is SemanticComponent.AUDIENCE:
        if _normalise(expected) == "customer":
            return not any(term in normalised for term in ("underwriter", "actuarial", "loss ratio"))
    return _contains_phrase(output, expected)


def _required_percentages(case: EvaluationCase) -> set[str]:
    values: set[str] = set()
    for requirement in case.semantic_requirements:
        values.update(_PERCENT_RE.findall(requirement.expected_text))
    return values


def _detect_forbidden(
    behaviour: ForbiddenBehaviour,
    case: EvaluationCase,
    output: str,
    missing_components: set[SemanticComponent],
) -> bool:
    normalised = _normalise(output)

    if behaviour is ForbiddenBehaviour.MISSING_CONDITION:
        return SemanticComponent.TRIGGER in missing_components or "when where" in normalised
    if behaviour is ForbiddenBehaviour.MISSING_EXCEPTION:
        return SemanticComponent.EXCEPTION in missing_components
    if behaviour is ForbiddenBehaviour.MISSING_SCOPE:
        return SemanticComponent.APPLICABILITY_SCOPE in missing_components
    if behaviour is ForbiddenBehaviour.NUMERICAL_ALTERATION:
        required = _required_percentages(case)
        observed = set(_PERCENT_RE.findall(output))
        return bool(observed - required) or (bool(required) and not required <= observed)
    if behaviour is ForbiddenBehaviour.CERTAINTY_INFLATION:
        return any(
            phrase in normalised
            for phrase in ("definitely applies", "certainly applies", "guaranteed", "without doubt", "always applies")
        )
    if behaviour is ForbiddenBehaviour.UNSUPPORTED_RECOMMENDATION:
        return any(
            phrase in normalised
            for phrase in ("i recommend", "we recommend", "you should buy", "you should choose", "best plan", "must buy")
        )
    if behaviour is ForbiddenBehaviour.CLAIM_PAYMENT_PREDICTION:
        return any(
            phrase in normalised
            for phrase in ("claim will be paid", "claim is guaranteed", "insurer will pay", "claim will definitely")
        )
    if behaviour is ForbiddenBehaviour.CITATION_MISMATCH:
        cited = {value.lower() for value in _EVIDENCE_ID_RE.findall(output)}
        governed = {value.lower() for value in case.governed_evidence_ids}
        evidence_required = any(
            req.component is SemanticComponent.EVIDENCE_REFERENCE
            for req in case.semantic_requirements
        )
        return bool(cited - governed) or (evidence_required and not cited)
    if behaviour is ForbiddenBehaviour.FACT_IMPLICATION_CONFUSION:
        return any(
            phrase in normalised
            for phrase in ("therefore the claim", "this means the claim will", "so the insurer will pay")
        )
    if behaviour is ForbiddenBehaviour.FAILURE_TO_ABSTAIN:
        abstention = any(
            phrase in normalised
            for phrase in ("cannot determine", "cannot confirm", "cannot be confirmed", "insufficient evidence", "remains unresolved", "needs review")
        )
        return not abstention
    if behaviour is ForbiddenBehaviour.UNSUPPORTED_FACT:
        return any(
            phrase in normalised
            for phrase in ("covers all treatments", "covers everything", "has no exclusions", "worldwide coverage", "all claims are covered")
        )
    return False


class DeterministicLLMEvaluator:
    """Run reproducible lexical and policy checks against one controlled case."""

    def evaluate(
        self,
        case: EvaluationCase,
        trace: ModelExecutionTrace,
        *,
        result_id: str | None = None,
    ) -> DeterministicEvaluationResult:
        if trace.case_id != case.case_id:
            raise DeterministicEvaluatorError("trace case_id must match evaluation case")

        resolved_result_id = result_id or f"deterministic-{trace.trace_id}"
        if trace.status is not EvaluationExecutionStatus.COMPLETED:
            return DeterministicEvaluationResult(
                result_id=resolved_result_id,
                case_id=case.case_id,
                trace_id=trace.trace_id,
                verdict=EvaluationVerdict.NOT_EVALUATED,
                passed_check_ids=(),
                failed_check_ids=(),
                failure_codes=(),
                limitations=(f"execution_status:{trace.status.value}",),
            )

        output = trace.output_text or ""
        checks: list[DeterministicCheck] = []
        missing_components: set[SemanticComponent] = set()

        for requirement in case.semantic_requirements:
            present = _requirement_present(
                case,
                output,
                requirement.component,
                requirement.expected_text,
            )
            passed = present or not requirement.required
            if requirement.required and not present:
                missing_components.add(requirement.component)
            checks.append(
                DeterministicCheck(
                    check_id=f"requirement:{requirement.requirement_id}",
                    passed=passed,
                    failure_code=(
                        f"MISSING_{requirement.component.value}" if not passed else None
                    ),
                )
            )

        for behaviour in case.forbidden_behaviours:
            detected = _detect_forbidden(behaviour, case, output, missing_components)
            checks.append(
                DeterministicCheck(
                    check_id=f"forbidden:{behaviour.value}",
                    passed=not detected,
                    failure_code=behaviour.value if detected else None,
                )
            )

        checks.sort(key=lambda item: item.check_id)
        passed_ids = tuple(item.check_id for item in checks if item.passed)
        failed_ids = tuple(item.check_id for item in checks if not item.passed)
        failure_codes = tuple(
            sorted({item.failure_code for item in checks if item.failure_code is not None})
        )

        if failed_ids:
            verdict = EvaluationVerdict.FAILED
        elif case.expected_outcome is EvaluationExpectedOutcome.REVIEW_REQUIRED:
            verdict = EvaluationVerdict.REQUIRES_REVIEW
        else:
            verdict = EvaluationVerdict.PASSED

        return DeterministicEvaluationResult(
            result_id=resolved_result_id,
            case_id=case.case_id,
            trace_id=trace.trace_id,
            verdict=verdict,
            passed_check_ids=passed_ids,
            failed_check_ids=failed_ids,
            failure_codes=failure_codes,
        )
