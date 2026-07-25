"""Deterministic fidelity gate for candidate LLM renderings (MO-022D)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import re
from typing import Iterable

from insurance_intelligence.contracts.llm_rendering import (
    CandidateRenderedSection,
    RenderingFidelityCheck,
    build_fidelity_check,
)
from insurance_intelligence.llm.output_parser import ParsedProviderOutput
from insurance_intelligence.llm.prompt_builder import EvidenceLockedPromptPacket, PromptSourceSection


@dataclass(frozen=True)
class FidelityValidationResult:
    validation_id: str
    status: str
    checks: tuple[RenderingFidelityCheck, ...]
    accepted_sections: tuple[CandidateRenderedSection, ...]
    failure_reasons: tuple[str, ...]


_NUMBER_RE = re.compile(r"(?<![\w.])(?:₹\s*)?\d+(?:,\d{2,3})*(?:\.\d+)?\s*%?")
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z'-]*")
_CONDITION_MARKERS = frozenset({"if", "when", "only", "unless", "provided", "subject"})
_RECOMMENDATION_MARKERS = (
    "you should", "we recommend", "best plan", "better plan", "must buy", "should buy",
    "choose this", "switch to", "increase your", "take a top up", "take a top-up",
)
_GUARANTEE_MARKERS = ("guaranteed", "always covered", "claim will be paid", "will definitely")
_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "are", "was", "were",
    "be", "been", "being", "this", "that", "it", "you", "your", "will", "with", "as", "by", "at",
    "from", "may", "can", "need", "have", "has", "had", "when", "if", "only", "unless", "provided",
    "subject", "insured", "customer", "policy", "amount", "pay", "pays", "payment",
})


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _normalise_number(token: str) -> str:
    value = token.replace("₹", "").replace(",", "").replace(" ", "")
    suffix = "%" if value.endswith("%") else ""
    value = value.removesuffix("%")
    try:
        number = Decimal(value).normalize()
        rendered = format(number, "f").rstrip("0").rstrip(".") if "." in format(number, "f") else format(number, "f")
    except InvalidOperation:
        rendered = value
    return rendered + suffix


def _numbers(text: str) -> tuple[str, ...]:
    return tuple(_normalise_number(match.group(0)) for match in _NUMBER_RE.finditer(text))


def _words(text: str) -> set[str]:
    return {word.lower() for word in _WORD_RE.findall(text)}


def _content_words(text: str) -> set[str]:
    return {word for word in _words(text) if word not in _STOPWORDS and len(word) > 2}


def _check(check_type: str, passed: bool, source: PromptSourceSection, candidate: CandidateRenderedSection, description: str) -> RenderingFidelityCheck:
    return build_fidelity_check(
        check_id=_stable_id("fidelity-check", check_type, source.section_id, candidate.section_id, passed),
        check_type=check_type,
        status="PASSED" if passed else "FAILED",
        description=description,
        source_section_ids=(source.section_id,),
        candidate_section_ids=(candidate.section_id,),
    )


def validate_fidelity(
    prompt_packet: EvidenceLockedPromptPacket,
    parsed_output: ParsedProviderOutput,
) -> FidelityValidationResult:
    """Validate meaning-preserving rendering using conservative deterministic checks."""
    if not isinstance(prompt_packet, EvidenceLockedPromptPacket):
        raise TypeError("prompt_packet must be EvidenceLockedPromptPacket")
    if not isinstance(parsed_output, ParsedProviderOutput):
        raise TypeError("parsed_output must be ParsedProviderOutput")
    if parsed_output.provider_request_id == "":
        raise ValueError("parsed output provider request identity is missing")

    source_by_id = {section.section_id: section for section in prompt_packet.source_sections}
    candidate_by_source = {section.source_section_id: section for section in parsed_output.candidate_sections}
    checks: list[RenderingFidelityCheck] = []
    failures: list[str] = []

    for source_id in tuple(source_by_id):
        source = source_by_id[source_id]
        candidate = candidate_by_source.get(source_id)
        if candidate is None:
            # Parser should prevent this, but fail closed if called independently.
            failures.append("INVALID_STRUCTURE")
            continue

        scope_ok = (
            candidate.section_type == source.section_type
            and candidate.approved_finding_ids == source.approved_finding_ids
            and candidate.clarification_ids == source.clarification_ids
        )
        checks.append(_check("FINDING_SCOPE_PRESERVED", scope_ok, source, candidate, "Finding/clarification and section scope preserved."))
        if not scope_ok: failures.append("DECISION_SCOPE_MISMATCH")

        evidence_ok = candidate.evidence_ids == source.evidence_ids
        checks.append(_check("EVIDENCE_PRESERVED", evidence_ok, source, candidate, "Evidence identities preserved."))
        if not evidence_ok: failures.append("EVIDENCE_MISMATCH")

        numeric_ok = _numbers(candidate.text) == _numbers(source.text)
        checks.append(_check("NUMERIC_FIDELITY", numeric_ok, source, candidate, "Numbers and percentages preserved exactly."))
        if not numeric_ok: failures.append("NUMERIC_CHANGE")

        source_markers = _words(source.text) & _CONDITION_MARKERS
        candidate_markers = _words(candidate.text) & _CONDITION_MARKERS
        condition_ok = not source_markers or source_markers <= candidate_markers
        checks.append(_check("CONDITION_PRESERVED", condition_ok, source, candidate, "Material condition markers preserved."))
        if not condition_ok: failures.append("MISSING_CONDITION")

        limitation_ok = candidate.limitation_ids == source.limitation_ids
        checks.append(_check("LIMITATION_PRESERVED", limitation_ok, source, candidate, "Limitation identities preserved."))
        if not limitation_ok: failures.append("MISSING_LIMITATION")

        clarification_ok = candidate.clarification_ids == source.clarification_ids
        checks.append(_check("CLARIFICATION_SCOPE_PRESERVED", clarification_ok, source, candidate, "Clarification boundary preserved."))
        if not clarification_ok: failures.append("DECISION_SCOPE_MISMATCH")

        source_content = _content_words(source.text)
        candidate_content = _content_words(candidate.text)
        novel = candidate_content - source_content
        # Conservative fail-closed threshold: wording may vary, but a candidate cannot introduce
        # a cluster of new content terms not present in the approved source.
        new_facts_ok = len(novel) <= max(2, len(source_content) // 2)
        checks.append(_check("NO_NEW_FACTS", new_facts_ok, source, candidate, "No material cluster of new content terms introduced."))
        if not new_facts_ok: failures.append("UNSUPPORTED_CONTENT")

        lowered = candidate.text.lower()
        recommendation_ok = not any(marker in lowered for marker in _RECOMMENDATION_MARKERS)
        checks.append(_check("NO_RECOMMENDATION", recommendation_ok, source, candidate, "No recommendation or purchase direction introduced."))
        if not recommendation_ok: failures.append("UNSUPPORTED_CONTENT")

        reasoning_ok = not any(marker in lowered for marker in _GUARANTEE_MARKERS)
        checks.append(_check("NO_NEW_REASONING", reasoning_ok, source, candidate, "No guarantee or unsupported conclusion introduced."))
        if not reasoning_ok: failures.append("UNSUPPORTED_CONTENT")

    unique_failures = tuple(dict.fromkeys(failures))
    status = "FAILED" if unique_failures else "VERIFIED"
    accepted = () if unique_failures else parsed_output.candidate_sections
    return FidelityValidationResult(
        validation_id=_stable_id("fidelity-validation", prompt_packet.prompt_packet_id, parsed_output.parse_id, status, unique_failures),
        status=status,
        checks=tuple(checks),
        accepted_sections=accepted,
        failure_reasons=unique_failures,
    )
