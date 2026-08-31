from __future__ import annotations

import hashlib
import json
from pathlib import Path

from insurance_intelligence.orchestration.guarded_full_cycle_certification import (
    run_guarded_full_knowledge_to_explanation_certification,
)
from insurance_intelligence.orchestration.guarded_star_comprehensive_pilot import (
    CURRENTNESS_LIMITATION_TEXT,
)


PATHS = {
    "SOURCE_REGISTRATION": "artifacts/source.json",
    "DOCUMENT_IDENTITY": "artifacts/identity.json",
    "DOCUMENT_CLASSIFICATION": "artifacts/classification.json",
    "LEGAL_BINDING": "artifacts/binding.json",
    "CANONICAL_PROJECTION": "artifacts/projection.json",
    "PUBLICATION_DECISION": "artifacts/decision.json",
    "AUTHORITATIVE_PUBLICATION": "artifacts/authoritative.json",
}


def _write(root: Path, relative: str, value: object) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _build_artifacts(root: Path) -> None:
    _write(root, PATHS["SOURCE_REGISTRATION"], {
        "registration_status": "generic_sources_registered_evidence_review_required",
        "product_context": {"insurer_id": "star_health", "product_id": "star_comprehensive", "source_scope": "reusable_generic"},
        "sources": [{"source_id": "ev_1"}],
    })
    _write(root, PATHS["DOCUMENT_IDENTITY"], {"status": "resolved", "document_id": "doc_1"})
    _write(root, PATHS["DOCUMENT_CLASSIFICATION"], {"classification_status": "reviewed_document_classifications_recorded_not_published"})
    _write(root, PATHS["LEGAL_BINDING"], {
        "binding_status": "reviewed_generic_legal_conditions_bound_not_published",
        "reviewed_by_human": True,
        "assertions": [{"assertion_id": "a1", "assertion_type": "conditional_copayment_rule", "candidate_id": "candidate-1"}],
    })
    _write(root, PATHS["CANONICAL_PROJECTION"], {"status": "evidence_assembled", "canonical_record_id": "cr1"})
    _write(root, PATHS["PUBLICATION_DECISION"], {"decision_status": "approved", "decision_id": "pd_1"})
    _write(root, PATHS["AUTHORITATIVE_PUBLICATION"], {
        "publication_status": "authoritative",
        "assertions": [{"assertion_id": "a1", "publication_decision_id": "pg_1"}],
    })


def _response_registry(root: Path) -> Path:
    base = root / "star_health_star_comprehensive"
    binding_dir = base / "generic_legal_condition_binding"
    projection_dir = base / "generic_legal_condition_canonical_projection"
    registration_dir = base / "generic_source_registration"
    source_dir = base / "source"
    for item in (binding_dir, projection_dir, registration_dir, source_dir):
        item.mkdir(parents=True, exist_ok=True)
    source = source_dir / "policy_wording.txt"
    source.write_text("10% co-payment applies under the documented entry-age condition.", encoding="utf-8")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    candidate_hash = hashlib.sha256(b"10% co-payment").hexdigest()
    binding = binding_dir / "star_health_star_comprehensive_conditional_copayment.json"
    binding.write_text(json.dumps({
        "product_context": {"product_display_name": "Star Comprehensive"},
        "assertions": [{
            "reviewed_statement": "A 10% co-payment applies under the documented entry-age condition.",
            "evidence": [{
                "candidate_id": "candidate-1",
                "document_id": "star-policy-wording",
                "document_version_id": "star-policy-wording-v1",
                "source_page": 39,
                "candidate_text_sha256": candidate_hash,
            }],
        }],
    }, sort_keys=True), encoding="utf-8")
    binding_hash = hashlib.sha256(binding.read_bytes()).hexdigest()
    projection = projection_dir / "star_health_star_comprehensive_conditional_copayment.canonical.json"
    projection.write_text(json.dumps({
        "projection_report": {"binding_manifest_sha256": binding_hash},
        "canonical_bundle": {
            "source_documents": [{"document_type": "POLICY_WORDING"}],
            "document_versions": [{
                "storage_locator": str(source),
                "content_sha256": source_hash,
                "effective_from": "2025-01-01",
                "effective_to": None,
            }],
        },
    }, sort_keys=True), encoding="utf-8")
    (registration_dir / "policy_wording_registration.json").write_text(json.dumps({
        "evidence_review": {"candidates": [{"candidate_id": "candidate-1", "excerpt": "10% co-payment applies."}]}
    }, sort_keys=True), encoding="utf-8")
    return root


def _run(tmp_path: Path):
    _build_artifacts(tmp_path)
    response_root = _response_registry(tmp_path / "response_registry")
    return run_guarded_full_knowledge_to_explanation_certification(
        repository_root=tmp_path,
        build_request_id="guarded-build-1",
        response_request_id="guarded-response-1",
        question="Will this co-payment apply to my treatment?",
        customer_context={"trigger_status": "CONFIRMED"},
        artifact_paths=PATHS,
        response_repository_root=response_root,
    )


def test_guarded_full_cycle_reearns_certification(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.status == "CERTIFIED_GUARDED"
    assert result.response.guard_status == "GUARDED"
    assert result.response.instance_sufficiency.outcome == "PASS"
    assert result.response.evidence_enforcement.outcome == "EVIDENCE_RESOLUTION_AUTHORIZED"
    assert result.response.authority_enforcement.enforcement_outcome == "DELEGATED_TO_DECISION_GATE"
    assert result.response.render_conformance.outcome == "PASS"


def test_guarded_certification_preserves_snapshot_and_release_identity(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.knowledge_snapshot_id == result.build.knowledge_snapshot_id
    assert result.response.knowledge_snapshot_id == result.build.knowledge_snapshot_id
    assert result.released_response_id == result.response.response.response_id


def test_guarded_certification_carries_currentness_limitation(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.response.temporal_status == "compatibility_unverified"
    assert CURRENTNESS_LIMITATION_TEXT in result.limitations
