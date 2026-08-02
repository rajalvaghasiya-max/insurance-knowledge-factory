"""Controlled certification decisions for governed semantic fidelity evidence.

Repeat-run stability evidence is necessary but never sufficient for certification.
A decision also requires evidence binding, an explicit human review outcome, and
all configured policy thresholds to pass.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

from insurance_intelligence.evaluation.cross_provider_repeat_run import (
    CrossProviderRepeatRunEvidence,
)


class CertificationDecisionError(ValueError):
    """Raised when a certification decision request violates invariants."""


class HumanReviewDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ControlledCertificationStatus(str, Enum):
    CERTIFIED = "CERTIFIED"
    REVIEW_ONLY = "REVIEW_ONLY"
    REJECTED = "REJECTED"


class CertificationConfidenceMode(str, Enum):
    """Controls how provider-reported confidence affects certification."""

    THRESHOLD_REQUIRED = "THRESHOLD_REQUIRED"
    DETERMINISTIC_PROOF_PRIMARY = "DETERMINISTIC_PROOF_PRIMARY"


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CertificationDecisionError(f"{field} must be non-empty text")
    return value.strip()


def _text_tuple(values: tuple[str, ...], field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise CertificationDecisionError(f"{field} must be a tuple")
    normalized = tuple(_text(value, field) for value in values)
    if not allow_empty and not normalized:
        raise CertificationDecisionError(f"{field} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise CertificationDecisionError(f"{field} must not contain duplicates")
    return normalized


def _score(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CertificationDecisionError(f"{field} must be numeric")
    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise CertificationDecisionError(f"{field} must be between 0 and 1")
    return result


def _stable_id(prefix: str, payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"{prefix}-{sha256(encoded.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class CertificationDecisionPolicy:
    policy_id: str
    minimum_confidence: float
    required_stability_status: str = "CROSS_PROVIDER_SEMANTICALLY_STABLE"
    require_human_approval: bool = True
    confidence_mode: CertificationConfidenceMode = CertificationConfidenceMode.THRESHOLD_REQUIRED

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _text(self.policy_id, "policy_id"))
        object.__setattr__(self, "minimum_confidence", _score(self.minimum_confidence, "minimum_confidence"))
        object.__setattr__(
            self,
            "required_stability_status",
            _text(self.required_stability_status, "required_stability_status"),
        )
        if not isinstance(self.require_human_approval, bool):
            raise CertificationDecisionError("require_human_approval must be boolean")
        if not isinstance(self.confidence_mode, CertificationConfidenceMode):
            raise CertificationDecisionError("confidence_mode must be a CertificationConfidenceMode")


@dataclass(frozen=True)
class HumanCertificationReview:
    reviewer_id: str
    decision: HumanReviewDecision
    reviewed_evidence_ids: tuple[str, ...]
    rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "reviewer_id", _text(self.reviewer_id, "reviewer_id"))
        if not isinstance(self.decision, HumanReviewDecision):
            raise CertificationDecisionError("decision must be a HumanReviewDecision")
        object.__setattr__(
            self,
            "reviewed_evidence_ids",
            _text_tuple(self.reviewed_evidence_ids, "reviewed_evidence_ids"),
        )
        object.__setattr__(self, "rationale", _text(self.rationale, "rationale"))


@dataclass(frozen=True)
class ControlledCertificationDecision:
    decision_id: str
    status: ControlledCertificationStatus
    reason_codes: tuple[str, ...]
    contract_id: str
    rule_family_id: str
    rule_family_version: str
    batch_id: str
    policy_id: str
    confidence_mode: CertificationConfidenceMode
    minimum_observed_confidence: float
    minimum_required_confidence: float
    reviewer_id: str | None
    approved_evidence_ids: tuple[str, ...]
    certification_effect: str
    certification_granted: bool


def decide_controlled_certification(
    evidence: CrossProviderRepeatRunEvidence,
    *,
    policy: CertificationDecisionPolicy,
    approved_evidence_ids: tuple[str, ...],
    human_review: HumanCertificationReview | None,
) -> ControlledCertificationDecision:
    if not isinstance(evidence, CrossProviderRepeatRunEvidence):
        raise CertificationDecisionError("evidence must be CrossProviderRepeatRunEvidence")
    if not isinstance(policy, CertificationDecisionPolicy):
        raise CertificationDecisionError("policy must be CertificationDecisionPolicy")
    approved_ids = _text_tuple(approved_evidence_ids, "approved_evidence_ids")

    reasons: set[str] = set()
    if evidence.status != policy.required_stability_status:
        reasons.add("STABILITY_EVIDENCE_INSUFFICIENT")
    if not evidence.exact_agreement_every_run:
        reasons.add("EXACT_AGREEMENT_NOT_PROVEN")
    if not evidence.all_components_matched:
        reasons.add("CANONICAL_MATCH_NOT_PROVEN")
    if not evidence.hard_failure_free:
        reasons.add("HARD_FAILURE_PRESENT")
    if not evidence.unresolved_free:
        reasons.add("UNRESOLVED_COMPONENT_PRESENT")
    if not evidence.preflight_passed_every_run:
        reasons.add("RULE_FAMILY_PREFLIGHT_NOT_PROVEN")

    deterministic_proof_complete = not reasons
    if (
        policy.confidence_mode is CertificationConfidenceMode.THRESHOLD_REQUIRED
        and evidence.minimum_observed_confidence < policy.minimum_confidence
    ):
        reasons.add("MINIMUM_CONFIDENCE_NOT_MET")
    elif (
        policy.confidence_mode is CertificationConfidenceMode.DETERMINISTIC_PROOF_PRIMARY
        and not deterministic_proof_complete
        and evidence.minimum_observed_confidence < policy.minimum_confidence
    ):
        reasons.add("MINIMUM_CONFIDENCE_NOT_MET")

    reviewer_id: str | None = None
    if human_review is None:
        if policy.require_human_approval:
            reasons.add("HUMAN_APPROVAL_REQUIRED")
    else:
        reviewer_id = human_review.reviewer_id
        if set(human_review.reviewed_evidence_ids) != set(approved_ids):
            reasons.add("HUMAN_REVIEW_EVIDENCE_MISMATCH")
        if human_review.decision is HumanReviewDecision.REJECT:
            reasons.add("HUMAN_REVIEW_REJECTED")

    if "HUMAN_REVIEW_REJECTED" in reasons:
        status = ControlledCertificationStatus.REJECTED
    elif reasons:
        status = ControlledCertificationStatus.REVIEW_ONLY
    else:
        status = ControlledCertificationStatus.CERTIFIED

    granted = status is ControlledCertificationStatus.CERTIFIED
    payload = {
        "batch_id": evidence.batch_id,
        "policy_id": policy.policy_id,
        "confidence_mode": policy.confidence_mode.value,
        "reviewer_id": reviewer_id,
        "approved_evidence_ids": approved_ids,
        "status": status.value,
        "reason_codes": sorted(reasons),
    }
    return ControlledCertificationDecision(
        decision_id=_stable_id("certification-decision", payload),
        status=status,
        reason_codes=tuple(sorted(reasons)),
        contract_id=evidence.contract_id,
        rule_family_id=evidence.rule_family_id,
        rule_family_version=evidence.rule_family_version,
        batch_id=evidence.batch_id,
        policy_id=policy.policy_id,
        confidence_mode=policy.confidence_mode,
        minimum_observed_confidence=evidence.minimum_observed_confidence,
        minimum_required_confidence=policy.minimum_confidence,
        reviewer_id=reviewer_id,
        approved_evidence_ids=approved_ids,
        certification_effect="GRANT" if granted else "NONE",
        certification_granted=granted,
    )


__all__ = [
    "CertificationConfidenceMode",
    "CertificationDecisionError",
    "CertificationDecisionPolicy",
    "ControlledCertificationDecision",
    "ControlledCertificationStatus",
    "HumanCertificationReview",
    "HumanReviewDecision",
    "decide_controlled_certification",
]
