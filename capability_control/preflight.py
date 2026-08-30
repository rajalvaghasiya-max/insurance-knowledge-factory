"""Deterministic semantic-retrieval preflight over the capability catalog.

This is a retrieval aid, not architecture authority. A low or absent score may
never authorize NEW; it only means the deterministic lexical search did not
surface a strong existing candidate.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable

from .catalog import CapabilityCatalog, CapabilityRecord

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "in", "into", "is", "it", "of", "on", "or", "the", "to", "with",
        "that", "this", "may", "must", "only", "before", "after", "existing",
    }
)


@dataclass(frozen=True)
class CapabilityCandidate:
    capability_id: str
    name: str
    lifecycle_status: str
    reuse_policy: str
    score: float
    matched_terms: tuple[str, ...]


@dataclass(frozen=True)
class CapabilityPreflightResult:
    query: str
    candidates: tuple[CapabilityCandidate, ...]
    classification: str
    new_authorized: bool


def _tokens(text: str) -> frozenset[str]:
    return frozenset(
        token for token in _TOKEN_RE.findall(text.lower())
        if len(token) > 1 and token not in _STOPWORDS
    )


def _record_text(record: CapabilityRecord, structural_text: str = "") -> str:
    return " ".join(
        (
            record.capability_id.replace(".", " ").replace("_", " "),
            record.name,
            record.responsibility,
            record.authority_role,
            " ".join(record.safety_invariants),
            record.notes or "",
            structural_text,
        )
    )


def _score(
    query_tokens: frozenset[str],
    record: CapabilityRecord,
    structural_text: str = "",
) -> CapabilityCandidate | None:
    if not query_tokens:
        return None
    record_tokens = _tokens(_record_text(record, structural_text))
    overlap = tuple(sorted(query_tokens & record_tokens))
    if not overlap:
        return None
    coverage = len(overlap) / len(query_tokens)
    precision = len(overlap) / len(record_tokens) if record_tokens else 0.0
    # Coverage dominates because preflight is a recall-oriented retrieval aid.
    score = round((0.85 * coverage) + (0.15 * precision), 4)
    return CapabilityCandidate(
        capability_id=record.capability_id,
        name=record.name,
        lifecycle_status=record.lifecycle_status,
        reuse_policy=record.reuse_policy,
        score=score,
        matched_terms=overlap,
    )


def preflight_capability(
    *,
    catalog: CapabilityCatalog,
    query: str,
    limit: int = 8,
    structural_text_for: Callable[[CapabilityRecord], str] | None = None,
) -> CapabilityPreflightResult:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")

    query_tokens = _tokens(query)
    candidates: list[CapabilityCandidate] = []
    for record in catalog.capabilities:
        structural_text = structural_text_for(record) if structural_text_for else ""
        candidate = _score(query_tokens, record, structural_text)
        if candidate is not None:
            candidates.append(candidate)
    candidates.sort(key=lambda item: (-item.score, item.capability_id))
    selected = tuple(candidates[:limit])

    # A lexical match is evidence to inspect existing capability. No lexical
    # result, however, is never evidence that NEW is safe or authorized.
    classification = (
        "EXISTING_CAPABILITY_CANDIDATES_FOUND"
        if selected
        else "NO_LEXICAL_CANDIDATE_FOUND_REQUIRES_MANUAL_REPOSITORY_REVIEW"
    )
    return CapabilityPreflightResult(
        query=query.strip(),
        candidates=selected,
        classification=classification,
        new_authorized=False,
    )
