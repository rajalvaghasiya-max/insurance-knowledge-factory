"""MO-010: execute the real, unmodified generic legal-condition canonical
projection contract against the tracked Star Comprehensive copay binding
manifest.

Integration update: the binding manifest was regenerated for real
against the current committed generic source bundle (CTO-authorized
integration step), resolving this order's original diagnosis of a
source-lineage hash mismatch between the two artifacts committed
together in c6aae3f (the bundle embeds a wall-clock registered_at
timestamp, so its hash was not stable across regeneration runs, and
the original binding had been computed against an earlier bundle
generation than the one ultimately committed). Lineage is now
consistent, and real, unmodified canonical projection succeeds
end-to-end against the actual committed repository -- proven directly
below, not only via an isolated scaffold.

The isolated (tmp_path, never committed) scaffold tests remain to
prove the contract's failure boundaries in isolation -- including a
synthetic reproduction of the now-corrected lineage-mismatch class of
failure -- without depending on committed repository state.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory_core.canonical.generic_legal_condition_canonical_projection import (
    GenericLegalConditionCanonicalProjection,
    GenericLegalConditionCanonicalProjectionError,
)

PROJECTION_SPEC = "docs/architecture/star_health_star_comprehensive_conditional_copayment_canonical_projection_spec.json"
REAL_BINDING_MANIFEST = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_legal_condition_binding/star_health_star_comprehensive_conditional_copayment.json"
)
REAL_CLASSIFICATION_MANIFEST = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "governance/star_health_star_comprehensive_document_classification.json"
)

APPROVED_ENTITY_INSURER = "star_health"
APPROVED_ENTITY_PRODUCT = "star_comprehensive"
APPROVED_UIN = "SHAHLIP26044V092526"
APPROVED_DOCUMENT_ID = "star_health_star_comprehensive_policy_wording_v1"
APPROVED_SOURCE_SHA256 = "b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f"


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


# --- Real execution against the tracked, committed repository --------------

def test_real_binding_and_classification_manifests_exist():
    assert Path(REAL_BINDING_MANIFEST).is_file()
    assert Path(REAL_CLASSIFICATION_MANIFEST).is_file()


def test_real_execution_succeeds_against_committed_repository():
    """The binding was regenerated for real against the current committed
    bundle (CTO-authorized integration step), restoring lineage
    consistency. Real, unmodified canonical projection now succeeds
    end-to-end against the actual committed repository state -- not a
    tmp_path scaffold."""
    result = GenericLegalConditionCanonicalProjection().project_from_spec_file(
        spec_path=PROJECTION_SPEC, repository_root="."
    )
    from factory_core.canonical.legacy_conditional_rule_adapter import canonical_bundle_to_dict

    bundle_dict = canonical_bundle_to_dict(result.bundle)
    assert bundle_dict["product_identities"][0]["uin"] == APPROVED_UIN
    assert bundle_dict["assertions"][0]["publication_status"] == "unpublished"


def test_real_binding_manifest_bundle_hash_matches_committed_bundle():
    """Confirms the lineage-consistency fix directly with concrete values,
    not merely inferred from a successful contract call."""
    binding = _load(REAL_BINDING_MANIFEST)
    import hashlib

    bundle_path = Path(binding["generic_source_bundle_path"])
    actual_hash = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    assert binding["generic_source_bundle_sha256"] == actual_hash


# --- Isolated success path (tmp_path, self-consistent, never committed) ----

def _self_consistent_bundle() -> dict:
    return {
        "schema_version": "1.0",
        "registration_type": "generic_source_registration_bundle_v1",
        "registration_status": "generic_sources_registered_evidence_review_required",
        "product_context": {
            "insurer_id": APPROVED_ENTITY_INSURER,
            "product_id": APPROVED_ENTITY_PRODUCT,
            "product_display_name": "Star Comprehensive Insurance Policy",
            "source_scope": "reusable_generic",
            "reviewed_generic_source_confirmation": True,
        },
        "sources": [
            {
                "document_id": APPROVED_DOCUMENT_ID,
                "authority_role": "primary_legal",
                "audience_scope": "generic_public",
                "document_version_id": f"docver_{APPROVED_DOCUMENT_ID}_{APPROVED_SOURCE_SHA256[:16]}",
                "registration_output_path": "generic_source_registration/policy_wording_registration.json",
                "registration_status": "source_registered_evidence_review_required",
            }
        ],
    }


def _registration_record() -> dict:
    real_registration = _load(
        "knowledge/factory/registry_backed/star_health_star_comprehensive/"
        "generic_source_registration/policy_wording_registration.json"
    )
    trimmed = dict(real_registration)
    trimmed["evidence_review"] = {
        "candidates": [
            candidate
            for candidate in real_registration["evidence_review"]["candidates"]
            if candidate["candidate_id"] == "candidate_page_39"
        ]
    }
    return trimmed


def _classification_record() -> dict:
    return {
        "classification_status": "reviewed_document_classifications_recorded_not_published",
        "documents": [
            {
                "document_id": APPROVED_DOCUMENT_ID,
                "document_version_id": f"docver_{APPROVED_DOCUMENT_ID}_{APPROVED_SOURCE_SHA256[:16]}",
                "classification": "reusable_generic",
                "reuse_action": "reusable_evidence_candidate",
            }
        ],
    }


def _binding_manifest(bundle_path: Path, bundle_sha256: str) -> dict:
    real_binding = _load(REAL_BINDING_MANIFEST)
    manifest = dict(real_binding)
    manifest["generic_source_bundle_path"] = "generic_source_registration/star_health_star_comprehensive_generic_source_bundle.json"
    manifest["generic_source_bundle_sha256"] = bundle_sha256
    return manifest


def _prepare_self_consistent_root(tmp_path) -> Path:
    import hashlib

    root = tmp_path
    bundle_relative = "generic_source_registration/star_health_star_comprehensive_generic_source_bundle.json"
    _write_json(root / bundle_relative, _self_consistent_bundle())
    bundle_sha256 = hashlib.sha256((root / bundle_relative).read_bytes()).hexdigest()

    _write_json(root / "generic_source_registration/policy_wording_registration.json", _registration_record())
    _write_json(
        root / "governance/star_health_star_comprehensive_document_classification.json",
        _classification_record(),
    )
    _write_json(
        root / "generic_legal_condition_binding/star_health_star_comprehensive_conditional_copayment.json",
        _binding_manifest(root / bundle_relative, bundle_sha256),
    )

    projection_spec = _load(PROJECTION_SPEC)
    projection_spec["binding_manifest_path"] = "generic_legal_condition_binding/star_health_star_comprehensive_conditional_copayment.json"
    projection_spec["classification_manifest_path"] = "governance/star_health_star_comprehensive_document_classification.json"
    spec_path = root / "projection_spec.json"
    _write_json(spec_path, projection_spec)
    return spec_path


def test_valid_governed_binding_succeeds(tmp_path):
    spec_path = _prepare_self_consistent_root(tmp_path)
    result = GenericLegalConditionCanonicalProjection().project_from_spec_file(
        spec_path=spec_path, repository_root=tmp_path
    )
    report = result.report
    assert report["classification_manifest_path"] == "governance/star_health_star_comprehensive_document_classification.json"


def test_copay_condition_exception_and_scope_preserved(tmp_path):
    spec_path = _prepare_self_consistent_root(tmp_path)
    result = GenericLegalConditionCanonicalProjection().project_from_spec_file(
        spec_path=spec_path, repository_root=tmp_path
    )
    from factory_core.canonical.legacy_conditional_rule_adapter import canonical_bundle_to_dict

    bundle_dict = canonical_bundle_to_dict(result.bundle)
    statement = bundle_dict["assertions"][0]["payload"]["reviewed_statement"]
    # Financial effect (10%) and trigger (age at entry >= 61).
    assert "10% co-payment" in statement
    assert "age at entry is 61 years or above" in statement
    # Exception (entry before 61, continuous renewal without a break).
    assert "before attaining 61 years of age and renewed continuously without a break" in statement
    # Scope: all 13 named sections, not a broader or narrower set.
    for section in ("II.1", "II.2", "II.3", "II.4", "II.5", "II.6", "II.7", "II.8", "II.9", "II.10", "II.11", "II.15", "II.25"):
        assert section in statement, f"missing scoped section {section}"
    assert "II.12" not in statement and "II.20" not in statement


def test_canonical_result_remains_unpublished(tmp_path):
    spec_path = _prepare_self_consistent_root(tmp_path)
    result = GenericLegalConditionCanonicalProjection().project_from_spec_file(
        spec_path=spec_path, repository_root=tmp_path
    )
    from factory_core.canonical.legacy_conditional_rule_adapter import canonical_bundle_to_dict

    bundle_dict = canonical_bundle_to_dict(result.bundle)
    assertion = bundle_dict["assertions"][0]
    assert assertion["publication_status"] == "unpublished"
    decision = bundle_dict["publication_decisions"][0]
    assert decision["decision_status"] == "unpublished"


def test_current_entitlement_remains_blocked(tmp_path):
    """Neither the assertion nor the publication decision may claim
    current-entitlement approval or authoritative status."""
    spec_path = _prepare_self_consistent_root(tmp_path)
    result = GenericLegalConditionCanonicalProjection().project_from_spec_file(
        spec_path=spec_path, repository_root=tmp_path
    )
    from factory_core.canonical.legacy_conditional_rule_adapter import canonical_bundle_to_dict

    bundle_dict = canonical_bundle_to_dict(result.bundle)
    bundle_text = json.dumps(bundle_dict).lower()
    assert "entitled" not in bundle_text
    assert "authoritative" not in bundle_text
    assert bundle_dict["assertions"][0]["validation_status"] == "evidence_assembled"


def test_second_execution_is_semantically_deterministic(tmp_path):
    spec_path = _prepare_self_consistent_root(tmp_path)
    result_a = GenericLegalConditionCanonicalProjection().project_from_spec_file(spec_path=spec_path, repository_root=tmp_path)
    result_b = GenericLegalConditionCanonicalProjection().project_from_spec_file(spec_path=spec_path, repository_root=tmp_path)

    from factory_core.canonical.legacy_conditional_rule_adapter import canonical_bundle_to_dict

    def _strip_timestamps(bundle_dict: dict) -> dict:
        stripped = json.loads(json.dumps(bundle_dict))
        for decision in stripped.get("publication_decisions", []):
            decision.pop("decided_at", None)
        return stripped

    dict_a = _strip_timestamps(canonical_bundle_to_dict(result_a.bundle))
    dict_b = _strip_timestamps(canonical_bundle_to_dict(result_b.bundle))
    assert dict_a == dict_b, "non-timestamp canonical payload differs between two runs of the same governed input"


def test_wrong_source_lineage_fails_closed(tmp_path):
    """Isolated proof that a binding manifest whose recorded bundle hash
    disagrees with the actual bundle file is rejected -- the same check
    that caught the real, now-corrected lineage inconsistency this order
    resolved (see test_real_binding_manifest_bundle_hash_matches_committed_bundle)."""
    spec_path = _prepare_self_consistent_root(tmp_path)
    binding_path = tmp_path / "generic_legal_condition_binding/star_health_star_comprehensive_conditional_copayment.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    binding["generic_source_bundle_sha256"] = "0" * 64
    binding_path.write_text(json.dumps(binding), encoding="utf-8")
    with pytest.raises(GenericLegalConditionCanonicalProjectionError, match="generic source bundle hash mismatch"):
        GenericLegalConditionCanonicalProjection().project_from_spec_file(spec_path=spec_path, repository_root=tmp_path)


def test_wrong_entity_binding_fails_closed(tmp_path):
    """A bundle whose product_context declares a different insurer than
    the projection specification must be rejected -- proves the contract
    will not silently project a legal condition onto the wrong product."""
    spec_path = _prepare_self_consistent_root(tmp_path)
    bundle_path = tmp_path / "generic_source_registration/star_health_star_comprehensive_generic_source_bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["product_context"]["insurer_id"] = "aditya_birla_health"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    binding_path = tmp_path / "generic_legal_condition_binding/star_health_star_comprehensive_conditional_copayment.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    import hashlib

    binding["generic_source_bundle_sha256"] = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    binding_path.write_text(json.dumps(binding), encoding="utf-8")

    with pytest.raises(GenericLegalConditionCanonicalProjectionError, match="product context mismatch"):
        GenericLegalConditionCanonicalProjection().project_from_spec_file(spec_path=spec_path, repository_root=tmp_path)


def test_missing_binding_manifest_fails_closed(tmp_path):
    spec_path = _prepare_self_consistent_root(tmp_path)
    (tmp_path / "generic_legal_condition_binding/star_health_star_comprehensive_conditional_copayment.json").unlink()
    with pytest.raises((GenericLegalConditionCanonicalProjectionError, FileNotFoundError), match="binding_manifest was not found"):
        GenericLegalConditionCanonicalProjection().project_from_spec_file(spec_path=spec_path, repository_root=tmp_path)


def test_wrong_binding_status_fails_closed(tmp_path):
    spec_path = _prepare_self_consistent_root(tmp_path)
    binding_path = tmp_path / "generic_legal_condition_binding/star_health_star_comprehensive_conditional_copayment.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    binding["binding_status"] = "reviewed_generic_legal_conditions_bound_and_published"
    binding_path.write_text(json.dumps(binding), encoding="utf-8")
    with pytest.raises(GenericLegalConditionCanonicalProjectionError):
        GenericLegalConditionCanonicalProjection().project_from_spec_file(spec_path=spec_path, repository_root=tmp_path)
