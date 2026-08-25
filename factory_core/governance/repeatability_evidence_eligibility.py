"""Fail-closed evidence eligibility for current-product repeatability scoring.

Semantic certification answers whether a claim faithfully represents one immutable
source version. This gate answers a different question: whether that source version
is eligible to count as evidence for a *current-product* repeatability experiment.

The gate consumes only the governed document-identity/currentness overlay output. It
does not alter semantic certification and deliberately permits historical documents
to remain semantically certifiable outside current-product scoring.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class RepeatabilityEvidenceEligibilityError(ValueError):
    """Raised when the eligibility input is malformed or ambiguous."""


@dataclass(frozen=True)
class RepeatabilityEvidenceEligibilityResult:
    eligible: bool
    status: str
    reason: str
    document_version_id: str | None
    content_sha256: str | None
    temporal_status: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "status": self.status,
            "reason": self.reason,
            "document_version_id": self.document_version_id,
            "content_sha256": self.content_sha256,
            "temporal_status": self.temporal_status,
        }


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise RepeatabilityEvidenceEligibilityError(f"{label} must be a JSON object")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RepeatabilityEvidenceEligibilityError(f"{label} must be a non-empty string")
    return value.strip()


class CurrentProductRepeatabilityEvidenceEligibility:
    """Evaluate one exact governed document version for current-product scoring."""

    OVERLAY_TYPE = "document_identity_resolution_overlay_v1"
    OVERLAY_STATUS = "reviewed_document_identity_resolution_recorded_not_published"
    ELIGIBLE_STATUS = "ELIGIBLE_FOR_CURRENT_PRODUCT_REPEATABILITY_SCORING"
    BLOCKED_STATUS = "BLOCKED_FROM_CURRENT_PRODUCT_REPEATABILITY_SCORING"

    @classmethod
    def evaluate(
        cls,
        overlay: Mapping[str, Any],
        *,
        entity_id: str,
        document_version_id: str,
        content_sha256: str,
        document_type: str,
    ) -> RepeatabilityEvidenceEligibilityResult:
        manifest = _mapping(overlay, "overlay")
        expected_entity = _nonempty(entity_id, "entity_id")
        expected_version = _nonempty(document_version_id, "document_version_id")
        expected_sha = _nonempty(content_sha256, "content_sha256")
        expected_type = _nonempty(document_type, "document_type")

        if manifest.get("overlay_type") != cls.OVERLAY_TYPE:
            raise RepeatabilityEvidenceEligibilityError(
                "overlay must be document_identity_resolution_overlay_v1"
            )
        if manifest.get("overlay_status") != cls.OVERLAY_STATUS:
            return cls._blocked("identity_overlay_not_reviewed", expected_version, expected_sha, None)

        product = _mapping(manifest.get("product_identity_reference"), "product_identity_reference")
        if product.get("entity_id") != expected_entity:
            return cls._blocked("product_identity_mismatch", expected_version, expected_sha, None)

        documents = manifest.get("documents")
        if not isinstance(documents, list):
            raise RepeatabilityEvidenceEligibilityError("overlay.documents must be a JSON array")

        matches: list[Mapping[str, Any]] = []
        for raw in documents:
            row = _mapping(raw, "overlay.documents[]")
            link = _mapping(row.get("document_version_link"), "document_version_link")
            if (
                link.get("document_version_id") == expected_version
                and link.get("content_sha256") == expected_sha
                and link.get("document_type") == expected_type
            ):
                matches.append(row)

        if len(matches) != 1:
            reason = "document_version_not_found" if not matches else "ambiguous_document_version_binding"
            return cls._blocked(reason, expected_version, expected_sha, None)

        resolution = _mapping(matches[0].get("identity_resolution"), "identity_resolution")
        temporal = resolution.get("temporal_status")
        if resolution.get("resolution_status") != "resolved":
            return cls._blocked("document_identity_not_resolved", expected_version, expected_sha, temporal)
        if resolution.get("evidence_review_eligibility") != "eligible_for_evidence_review":
            return cls._blocked("document_not_evidence_review_eligible", expected_version, expected_sha, temporal)
        if temporal != "current_observed_reviewed":
            return cls._blocked(
                f"currentness_not_eligible:{temporal or 'missing'}",
                expected_version,
                expected_sha,
                temporal,
            )
        if resolution.get("current_entitlement_publication_eligibility") != "eligible":
            return cls._blocked("current_entitlement_not_eligible", expected_version, expected_sha, temporal)

        return RepeatabilityEvidenceEligibilityResult(
            eligible=True,
            status=cls.ELIGIBLE_STATUS,
            reason="governed_current_product_evidence_eligible",
            document_version_id=expected_version,
            content_sha256=expected_sha,
            temporal_status=temporal,
        )

    @classmethod
    def _blocked(
        cls,
        reason: str,
        document_version_id: str | None,
        content_sha256: str | None,
        temporal_status: str | None,
    ) -> RepeatabilityEvidenceEligibilityResult:
        return RepeatabilityEvidenceEligibilityResult(
            eligible=False,
            status=cls.BLOCKED_STATUS,
            reason=reason,
            document_version_id=document_version_id,
            content_sha256=content_sha256,
            temporal_status=temporal_status,
        )
