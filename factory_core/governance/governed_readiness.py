"""Generic governed product-readiness assessment contract.

This module deliberately keeps legacy extraction coverage separate from governed
readiness. A summary status is derived from independently assessed dimensions;
callers cannot assert READY/PUBLISHED directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


ASSESSMENT_VERSION = "0.1"

SOURCE_GOVERNANCE_STATES = frozenset(
    {"NOT_ASSESSED", "CURRENT_GOVERNED", "CURRENTNESS_UNRESOLVED", "HISTORICAL_ONLY"}
)
SEMANTIC_REVIEW_STATES = frozenset(
    {"NOT_ASSESSED", "COMPLETE", "PARTIAL", "CONFLICTING"}
)
APPLICABILITY_STATES = frozenset(
    {"NOT_ASSESSED", "RESOLVED", "PARTIAL", "UNRESOLVED"}
)
PUBLICATION_ELIGIBILITY_STATES = frozenset(
    {"NOT_ASSESSED", "ELIGIBLE", "INELIGIBLE", "REVIEW_REQUIRED"}
)
PUBLICATION_STATES = frozenset(
    {"NOT_ASSESSED", "NOT_PUBLISHED", "PUBLISHED"}
)
READINESS_STATES = frozenset(
    {"NOT_ASSESSED", "BLOCKED", "REVIEW_REQUIRED", "READY_FOR_PUBLICATION_REVIEW", "PUBLISHED"}
)


class GovernedReadinessContractError(ValueError):
    """Raised when a governed-readiness assessment is invalid or inconsistent."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedReadinessContractError(f"{label} must be a non-empty string")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    text = _text(value, label)
    if text not in allowed:
        raise GovernedReadinessContractError(
            f"{label} must be one of {sorted(allowed)}; got {text!r}"
        )
    return text


def _unique_text(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise GovernedReadinessContractError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class GovernedReadinessAssessment:
    assessment_version: str
    entity_id: str
    source_governance: str
    semantic_review: str
    applicability: str
    publication_eligibility: str
    publication_state: str
    unresolved_residue: tuple[str, ...]
    evidence_references: tuple[str, ...]
    note: str | None
    status: str


def derive_readiness_status(
    *,
    source_governance: str,
    semantic_review: str,
    applicability: str,
    publication_eligibility: str,
    publication_state: str,
    unresolved_residue: Sequence[str] = (),
) -> str:
    dimensions = (
        source_governance,
        semantic_review,
        applicability,
        publication_eligibility,
        publication_state,
    )
    if all(value == "NOT_ASSESSED" for value in dimensions):
        return "NOT_ASSESSED"

    if source_governance in {"CURRENTNESS_UNRESOLVED", "HISTORICAL_ONLY"}:
        return "BLOCKED"
    if semantic_review == "CONFLICTING":
        return "BLOCKED"
    if applicability == "UNRESOLVED":
        return "BLOCKED"
    if publication_eligibility == "INELIGIBLE":
        return "BLOCKED"

    fully_ready = (
        source_governance == "CURRENT_GOVERNED"
        and semantic_review == "COMPLETE"
        and applicability == "RESOLVED"
        and publication_eligibility == "ELIGIBLE"
        and not tuple(unresolved_residue)
    )

    if publication_state == "PUBLISHED":
        if not fully_ready:
            raise GovernedReadinessContractError(
                "publication_state PUBLISHED requires fully resolved governed readiness with no unresolved residue"
            )
        return "PUBLISHED"

    if fully_ready and publication_state == "NOT_PUBLISHED":
        return "READY_FOR_PUBLICATION_REVIEW"

    return "REVIEW_REQUIRED"


def build_governed_readiness_assessment(
    *,
    entity_id: str,
    source_governance: str,
    semantic_review: str,
    applicability: str,
    publication_eligibility: str,
    publication_state: str,
    unresolved_residue: Sequence[str] = (),
    evidence_references: Sequence[str] = (),
    note: str | None = None,
    assessment_version: str = ASSESSMENT_VERSION,
) -> GovernedReadinessAssessment:
    if assessment_version != ASSESSMENT_VERSION:
        raise GovernedReadinessContractError(
            f"assessment_version must be {ASSESSMENT_VERSION!r}"
        )

    entity = _text(entity_id, "entity_id")
    source = _member(source_governance, SOURCE_GOVERNANCE_STATES, "source_governance")
    semantic = _member(semantic_review, SEMANTIC_REVIEW_STATES, "semantic_review")
    applicability_value = _member(applicability, APPLICABILITY_STATES, "applicability")
    eligibility = _member(
        publication_eligibility,
        PUBLICATION_ELIGIBILITY_STATES,
        "publication_eligibility",
    )
    publication = _member(publication_state, PUBLICATION_STATES, "publication_state")
    residue = _unique_text(unresolved_residue, "unresolved_residue")
    references = _unique_text(evidence_references, "evidence_references")

    if any(
        value != "NOT_ASSESSED"
        for value in (source, semantic, applicability_value, eligibility, publication)
    ) and not references:
        raise GovernedReadinessContractError(
            "assessed governed readiness requires at least one evidence_reference"
        )

    normalized_note = None if note is None else _text(note, "note")
    status = derive_readiness_status(
        source_governance=source,
        semantic_review=semantic,
        applicability=applicability_value,
        publication_eligibility=eligibility,
        publication_state=publication,
        unresolved_residue=residue,
    )

    return GovernedReadinessAssessment(
        assessment_version=assessment_version,
        entity_id=entity,
        source_governance=source,
        semantic_review=semantic,
        applicability=applicability_value,
        publication_eligibility=eligibility,
        publication_state=publication,
        unresolved_residue=residue,
        evidence_references=references,
        note=normalized_note,
        status=status,
    )


def assessment_from_mapping(data: Mapping[str, object], *, expected_entity_id: str) -> GovernedReadinessAssessment:
    if not isinstance(data, Mapping):
        raise GovernedReadinessContractError("assessment must be a mapping")

    allowed = {
        "assessment_version",
        "entity_id",
        "source_governance",
        "semantic_review",
        "applicability",
        "publication_eligibility",
        "publication_state",
        "unresolved_residue",
        "evidence_references",
        "note",
    }
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise GovernedReadinessContractError(
            "unknown governed-readiness field(s): " + ", ".join(unknown)
        )

    required = allowed - {"assessment_version", "note"}
    missing = sorted(required - set(data))
    if missing:
        raise GovernedReadinessContractError(
            "missing governed-readiness field(s): " + ", ".join(missing)
        )

    entity_id = _text(data["entity_id"], "entity_id")
    if entity_id != expected_entity_id:
        raise GovernedReadinessContractError(
            f"entity_id must match requested entity {expected_entity_id!r}"
        )

    unresolved = data["unresolved_residue"]
    references = data["evidence_references"]
    if not isinstance(unresolved, list):
        raise GovernedReadinessContractError("unresolved_residue must be a list")
    if not isinstance(references, list):
        raise GovernedReadinessContractError("evidence_references must be a list")

    return build_governed_readiness_assessment(
        assessment_version=str(data.get("assessment_version", ASSESSMENT_VERSION)),
        entity_id=entity_id,
        source_governance=data["source_governance"],  # type: ignore[arg-type]
        semantic_review=data["semantic_review"],  # type: ignore[arg-type]
        applicability=data["applicability"],  # type: ignore[arg-type]
        publication_eligibility=data["publication_eligibility"],  # type: ignore[arg-type]
        publication_state=data["publication_state"],  # type: ignore[arg-type]
        unresolved_residue=unresolved,
        evidence_references=references,
        note=data.get("note"),  # type: ignore[arg-type]
    )
