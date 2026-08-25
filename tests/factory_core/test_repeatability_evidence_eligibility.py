from __future__ import annotations

from copy import deepcopy

from factory_core.governance.repeatability_evidence_eligibility import (
    CurrentProductRepeatabilityEvidenceEligibility,
)


ENTITY_ID = "bajaj_allianz_general:my_health_care"
SHA = "05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158"
VERSION_ID = "docver_bajaj_my_health_care_policy_wording_v2_05dc291324340d52"


def _overlay() -> dict:
    return {
        "schema_version": "1.0",
        "overlay_type": "document_identity_resolution_overlay_v1",
        "overlay_status": "reviewed_document_identity_resolution_recorded_not_published",
        "product_identity_reference": {"entity_id": ENTITY_ID},
        "documents": [
            {
                "document_version_link": {
                    "content_sha256": SHA,
                    "document_type": "policy_wording",
                    "document_version_id": VERSION_ID,
                    "document_id": "bajaj_my_health_care_policy_wording_v2",
                },
                "identity_resolution": {
                    "resolution_status": "resolved",
                    "evidence_review_eligibility": "eligible_for_evidence_review",
                    "temporal_status": "current_observed_reviewed",
                    "current_entitlement_publication_eligibility": "eligible",
                },
            }
        ],
    }


def _evaluate(overlay: dict):
    return CurrentProductRepeatabilityEvidenceEligibility.evaluate(
        overlay,
        entity_id=ENTITY_ID,
        document_version_id=VERSION_ID,
        content_sha256=SHA,
        document_type="policy_wording",
    )


def test_current_reviewed_exact_version_is_eligible_for_current_product_scoring() -> None:
    result = _evaluate(_overlay())
    assert result.eligible is True
    assert result.status == "ELIGIBLE_FOR_CURRENT_PRODUCT_REPEATABILITY_SCORING"
    assert result.reason == "governed_current_product_evidence_eligible"
    assert result.temporal_status == "current_observed_reviewed"


def test_historical_or_replaced_document_can_exist_but_cannot_score_as_current() -> None:
    for temporal_status in ("historical", "replaced", "compatibility_unverified", "unknown"):
        overlay = _overlay()
        overlay["documents"][0]["identity_resolution"]["temporal_status"] = temporal_status
        overlay["documents"][0]["identity_resolution"]["current_entitlement_publication_eligibility"] = "blocked"
        result = _evaluate(overlay)
        assert result.eligible is False
        assert result.reason == f"currentness_not_eligible:{temporal_status}"


def test_exact_hash_and_version_are_required_for_scoring() -> None:
    wrong_sha = CurrentProductRepeatabilityEvidenceEligibility.evaluate(
        _overlay(),
        entity_id=ENTITY_ID,
        document_version_id=VERSION_ID,
        content_sha256="f" * 64,
        document_type="policy_wording",
    )
    assert wrong_sha.eligible is False
    assert wrong_sha.reason == "document_version_not_found"

    wrong_version = CurrentProductRepeatabilityEvidenceEligibility.evaluate(
        _overlay(),
        entity_id=ENTITY_ID,
        document_version_id="docver_wrong",
        content_sha256=SHA,
        document_type="policy_wording",
    )
    assert wrong_version.eligible is False
    assert wrong_version.reason == "document_version_not_found"


def test_product_identity_and_document_role_must_match() -> None:
    wrong_product = CurrentProductRepeatabilityEvidenceEligibility.evaluate(
        _overlay(),
        entity_id="other:product",
        document_version_id=VERSION_ID,
        content_sha256=SHA,
        document_type="policy_wording",
    )
    assert wrong_product.eligible is False
    assert wrong_product.reason == "product_identity_mismatch"

    wrong_role = CurrentProductRepeatabilityEvidenceEligibility.evaluate(
        _overlay(),
        entity_id=ENTITY_ID,
        document_version_id=VERSION_ID,
        content_sha256=SHA,
        document_type="brochure",
    )
    assert wrong_role.eligible is False
    assert wrong_role.reason == "document_version_not_found"


def test_resolved_identity_and_review_eligibility_are_independent_requirements() -> None:
    unresolved = _overlay()
    unresolved["documents"][0]["identity_resolution"]["resolution_status"] = "unresolved"
    assert _evaluate(unresolved).reason == "document_identity_not_resolved"

    blocked = _overlay()
    blocked["documents"][0]["identity_resolution"]["evidence_review_eligibility"] = "blocked"
    assert _evaluate(blocked).reason == "document_not_evidence_review_eligible"


def test_current_temporal_status_without_entitlement_eligibility_is_still_blocked() -> None:
    overlay = _overlay()
    overlay["documents"][0]["identity_resolution"]["current_entitlement_publication_eligibility"] = "blocked"
    result = _evaluate(overlay)
    assert result.eligible is False
    assert result.reason == "current_entitlement_not_eligible"


def test_ambiguous_exact_binding_fails_closed() -> None:
    overlay = _overlay()
    overlay["documents"].append(deepcopy(overlay["documents"][0]))
    result = _evaluate(overlay)
    assert result.eligible is False
    assert result.reason == "ambiguous_document_version_binding"
