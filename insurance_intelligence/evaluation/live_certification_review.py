"""Governed human-review decisions for MO-022G live certification evidence.

A reviewer may accept evidence for later certification consideration, require
rework, or reject it. This record never grants model or rule-family
certification; certification remains a separate governed decision.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping


class LiveCertificationReviewError(ValueError):
    """Raised when a reviewer decision violates governance invariants."""


class LiveCertificationReviewerDecision(str, Enum):
    APPROVED_FOR_CERTIFICATION_CONSIDERATION = "APPROVED_FOR_CERTIFICATION_CONSIDERATION"
    REWORK_REQUIRED = "REWORK_REQUIRED"
    REJECTED = "REJECTED"


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LiveCertificationReviewError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_array(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise LiveCertificationReviewError(f"{field_name} must be a text array")
    return tuple(sorted(item.strip() for item in value))


def _stable_id(prefix: str, value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"{prefix}-{sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class GovernedLiveCertificationReview:
    review_id: str
    schema_version: str
    evidence_id: str
    source_artifact_sha256: str
    contract_id: str
    reviewer_id: str
    reviewed_at: str
    decision: LiveCertificationReviewerDecision
    rationale: str
    reviewed_component_ids: tuple[str, ...]
    acknowledged_reason_codes: tuple[str, ...]
    certification_effect: str
    certification_granted: bool

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        return payload


def build_governed_live_review(
    evidence: Mapping[str, object],
    *,
    reviewer_id: str,
    reviewed_at: str,
    decision: LiveCertificationReviewerDecision,
    rationale: str,
) -> GovernedLiveCertificationReview:
    if not isinstance(evidence, Mapping):
        raise LiveCertificationReviewError("evidence must be an object")
    if not isinstance(decision, LiveCertificationReviewerDecision):
        raise LiveCertificationReviewError("decision must be a reviewer decision")
    if evidence.get("certification_effect") != "NONE":
        raise LiveCertificationReviewError("evidence must have no certification effect")
    if evidence.get("certification_granted") is not False:
        raise LiveCertificationReviewError("evidence must not grant certification")
    if evidence.get("reviewer_decision") != "PENDING":
        raise LiveCertificationReviewError("evidence must be pending review")

    components = evidence.get("components")
    if not isinstance(components, list) or not components:
        raise LiveCertificationReviewError("components must not be empty")
    component_ids: list[str] = []
    statuses: list[str] = []
    for component in components:
        if not isinstance(component, Mapping):
            raise LiveCertificationReviewError("component must be an object")
        component_ids.append(_required_text(component.get("component_id"), "component_id"))
        statuses.append(_required_text(component.get("status"), "component.status"))
    if len(component_ids) != len(set(component_ids)):
        raise LiveCertificationReviewError("component ids must be unique")

    hard_failures = _text_array(evidence.get("hard_failure_codes"), "hard_failure_codes")
    unresolved = _text_array(
        evidence.get("unresolved_component_ids"), "unresolved_component_ids"
    )
    reason_codes = _text_array(
        evidence.get("routing_reason_codes"), "routing_reason_codes"
    )

    if decision is LiveCertificationReviewerDecision.APPROVED_FOR_CERTIFICATION_CONSIDERATION:
        if hard_failures:
            raise LiveCertificationReviewError("approval is forbidden when hard failures exist")
        if unresolved:
            raise LiveCertificationReviewError("approval is forbidden when components are unresolved")
        if any(status != "MATCHED" for status in statuses):
            raise LiveCertificationReviewError("approval requires every component to be MATCHED")

    signature = {
        "evidence_id": evidence.get("evidence_id"),
        "source_artifact_sha256": evidence.get("source_artifact_sha256"),
        "reviewer_id": reviewer_id,
        "reviewed_at": reviewed_at,
        "decision": decision.value,
        "rationale": rationale,
        "component_ids": sorted(component_ids),
        "reason_codes": reason_codes,
    }
    return GovernedLiveCertificationReview(
        review_id=_stable_id("live-certification-review", signature),
        schema_version="1.0",
        evidence_id=_required_text(evidence.get("evidence_id"), "evidence_id"),
        source_artifact_sha256=_required_text(
            evidence.get("source_artifact_sha256"), "source_artifact_sha256"
        ),
        contract_id=_required_text(evidence.get("contract_id"), "contract_id"),
        reviewer_id=_required_text(reviewer_id, "reviewer_id"),
        reviewed_at=_required_text(reviewed_at, "reviewed_at"),
        decision=decision,
        rationale=_required_text(rationale, "rationale"),
        reviewed_component_ids=tuple(sorted(component_ids)),
        acknowledged_reason_codes=reason_codes,
        certification_effect="NONE",
        certification_granted=False,
    )


__all__ = [
    "GovernedLiveCertificationReview",
    "LiveCertificationReviewError",
    "LiveCertificationReviewerDecision",
    "build_governed_live_review",
]
