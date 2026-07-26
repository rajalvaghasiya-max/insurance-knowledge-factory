"""Deterministic baseline-versus-LLM evaluation for controlled rendering (MO-022F)."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Mapping, Sequence

from insurance_intelligence.llm.service import HybridRenderingResult


class LLMBaselineError(ValueError):
    """Raised when a hybrid-rendering baseline input is invalid."""


LEGALISTIC_TERMS = frozenset({
    "shall", "herein", "thereof", "wherein", "aforementioned", "pursuant",
    "borne", "bear", "admissible", "applicable", "notwithstanding", "subject",
})


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LLMBaselineError(f"{label} must be a non-empty string")
    return value


def _words(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[A-Za-z0-9₹%]+(?:['’-][A-Za-z0-9]+)?", text))


def _sentence_count(text: str) -> int:
    return max(1, len([part for part in re.split(r"[.!?]+", text) if part.strip()]))


def _complex_term_count(text: str) -> int:
    return sum(1 for word in _words(text.lower()) if word in LEGALISTIC_TERMS)


@dataclass(frozen=True)
class ReadabilitySignals:
    word_count: int
    sentence_count: int
    average_words_per_sentence: float
    legalistic_term_count: int


@dataclass(frozen=True)
class SectionBaselineComparison:
    comparison_id: str
    source_section_id: str
    deterministic_text: str
    released_text: str
    deterministic_signals: ReadabilitySignals
    released_signals: ReadabilitySignals
    wording_changed: bool
    readability_improved: bool


@dataclass(frozen=True)
class HybridBaselineCase:
    case_id: str
    scenario_id: str
    result: HybridRenderingResult


@dataclass(frozen=True)
class HybridScenarioOutcome:
    outcome_id: str
    case_id: str
    scenario_id: str
    request_id: str
    rendering_id: str
    outcome_status: str
    rendering_status: str
    fidelity_status: str
    fallback_reason: str | None
    provider_status: str
    section_comparisons: tuple[SectionBaselineComparison, ...]
    released_section_count: int
    deterministic_section_count: int
    readability_improved_section_count: int


@dataclass(frozen=True)
class HybridBaselineReport:
    report_id: str
    report_status: str
    scenario_outcomes: tuple[HybridScenarioOutcome, ...]
    scenario_outcome_map: Mapping[str, HybridScenarioOutcome]
    total_scenarios: int
    released_scenarios: int
    fallback_scenarios: int
    provider_failed_scenarios: int
    fidelity_verified_scenarios: int
    readability_improved_scenarios: int
    total_deterministic_sections: int
    total_released_sections: int
    release_rate: float
    fallback_rate: float
    fidelity_pass_rate: float


def build_case(*, case_id: str, scenario_id: str, result: HybridRenderingResult) -> HybridBaselineCase:
    if not isinstance(result, HybridRenderingResult):
        raise LLMBaselineError("result must be HybridRenderingResult")
    return HybridBaselineCase(
        case_id=_nonempty(case_id, "case_id"),
        scenario_id=_nonempty(scenario_id, "scenario_id"),
        result=result,
    )


def readability_signals(text: str) -> ReadabilitySignals:
    validated = _nonempty(text, "text")
    words = _words(validated)
    sentences = _sentence_count(validated)
    return ReadabilitySignals(
        word_count=len(words),
        sentence_count=sentences,
        average_words_per_sentence=round(len(words) / sentences, 4),
        legalistic_term_count=_complex_term_count(validated),
    )


def _is_improved(source: ReadabilitySignals, released: ReadabilitySignals, changed: bool) -> bool:
    if not changed:
        return False
    legal_better = released.legalistic_term_count < source.legalistic_term_count
    sentence_better = released.average_words_per_sentence < source.average_words_per_sentence
    no_material_regression = (
        released.legalistic_term_count <= source.legalistic_term_count
        and released.average_words_per_sentence <= source.average_words_per_sentence + 3.0
    )
    return no_material_regression and (legal_better or sentence_better)


def evaluate_case(case: HybridBaselineCase) -> HybridScenarioOutcome:
    if not isinstance(case, HybridBaselineCase):
        raise TypeError("case must be HybridBaselineCase")
    result = case.result
    deterministic = result.deterministic_explanation.sections
    source_by_id = {section.section_id: section for section in deterministic}
    if len(source_by_id) != len(deterministic):
        raise LLMBaselineError("deterministic section IDs must be unique")

    comparisons: list[SectionBaselineComparison] = []
    if result.used_fallback:
        released_pairs = tuple((section.section_id, section.text) for section in deterministic)
    else:
        released_pairs = tuple((section.source_section_id, section.text) for section in result.output.rendered_sections)
        if {section_id for section_id, _ in released_pairs} != set(source_by_id):
            raise LLMBaselineError("released section coverage must match deterministic section coverage")

    for source_id, released_text in sorted(released_pairs):
        source = source_by_id.get(source_id)
        if source is None:
            raise LLMBaselineError(f"unknown released source section {source_id!r}")
        source_signals = readability_signals(source.text)
        released_signals = readability_signals(released_text)
        changed = source.text != released_text
        comparisons.append(SectionBaselineComparison(
            comparison_id=_stable_id("llm-section-comparison", case.scenario_id, source_id, source.text, released_text),
            source_section_id=source_id,
            deterministic_text=source.text,
            released_text=released_text,
            deterministic_signals=source_signals,
            released_signals=released_signals,
            wording_changed=changed,
            readability_improved=_is_improved(source_signals, released_signals, changed),
        ))

    provider_status = result.output.provider_response.status if result.output.provider_response else "NOT_CALLED"
    if result.used_fallback:
        outcome_status = "PROVIDER_FAILED" if result.output.rendering_status == "PROVIDER_FAILED" else "FALLBACK"
    else:
        outcome_status = "RELEASED"
    fallback_reason = result.output.fallback.reason if result.output.fallback else None
    improved_count = sum(item.readability_improved for item in comparisons)
    return HybridScenarioOutcome(
        outcome_id=_stable_id("llm-scenario-outcome", case.scenario_id, result.service_result_id, outcome_status),
        case_id=case.case_id,
        scenario_id=case.scenario_id,
        request_id=result.output.request_id,
        rendering_id=result.output.rendering_id,
        outcome_status=outcome_status,
        rendering_status=result.output.rendering_status,
        fidelity_status=result.output.fidelity_status,
        fallback_reason=fallback_reason,
        provider_status=provider_status,
        section_comparisons=tuple(comparisons),
        released_section_count=len(comparisons),
        deterministic_section_count=len(deterministic),
        readability_improved_section_count=improved_count,
    )


def evaluate_hybrid_baseline(cases: Sequence[HybridBaselineCase]) -> HybridBaselineReport:
    case_tuple = tuple(cases)
    if not case_tuple:
        raise LLMBaselineError("at least one baseline case is required")
    if any(not isinstance(case, HybridBaselineCase) for case in case_tuple):
        raise TypeError("all cases must be HybridBaselineCase")
    scenario_ids = [case.scenario_id for case in case_tuple]
    case_ids = [case.case_id for case in case_tuple]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise LLMBaselineError("scenario IDs must be unique")
    if len(case_ids) != len(set(case_ids)):
        raise LLMBaselineError("case IDs must be unique")

    outcomes = tuple(evaluate_case(case) for case in sorted(case_tuple, key=lambda item: item.scenario_id))
    released = sum(item.outcome_status == "RELEASED" for item in outcomes)
    fallback = sum(item.outcome_status in {"FALLBACK", "PROVIDER_FAILED"} for item in outcomes)
    provider_failed = sum(item.outcome_status == "PROVIDER_FAILED" for item in outcomes)
    fidelity_verified = sum(item.fidelity_status == "VERIFIED" for item in outcomes)
    readability_improved = sum(item.readability_improved_section_count > 0 for item in outcomes)
    total = len(outcomes)
    total_deterministic_sections = sum(item.deterministic_section_count for item in outcomes)
    total_released_sections = sum(item.released_section_count for item in outcomes)
    if released == total:
        status = "PASS"
    elif fallback == total:
        status = "FALLBACK_ONLY"
    else:
        status = "MIXED"
    signature = tuple((item.scenario_id, item.outcome_id) for item in outcomes)
    return HybridBaselineReport(
        report_id=_stable_id("llm-baseline-report", signature),
        report_status=status,
        scenario_outcomes=outcomes,
        scenario_outcome_map={item.scenario_id: item for item in outcomes},
        total_scenarios=total,
        released_scenarios=released,
        fallback_scenarios=fallback,
        provider_failed_scenarios=provider_failed,
        fidelity_verified_scenarios=fidelity_verified,
        readability_improved_scenarios=readability_improved,
        total_deterministic_sections=total_deterministic_sections,
        total_released_sections=total_released_sections,
        release_rate=round(released / total, 4),
        fallback_rate=round(fallback / total, 4),
        fidelity_pass_rate=round(fidelity_verified / total, 4),
    )
