from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from insurance_intelligence.orchestration.full_cycle_certification import (
    FullCycleCertificationError,
    run_full_knowledge_to_explanation_certification,
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


def _run(tmp_path: Path, **overrides):
    _build_artifacts(tmp_path)
    response_root = _response_registry(tmp_path / "response_registry")
    values = dict(
        repository_root=tmp_path,
        build_request_id="build-1",
        response_request_id="response-1",
        question="Will this co-payment apply to my treatment?",
        customer_context={"trigger_status": "CONFIRMED"},
        artifact_paths=PATHS,
        response_repository_root=response_root,
    )
    values.update(overrides)
    return run_full_knowledge_to_explanation_certification(**values)


def test_full_cycle_is_certified(tmp_path: Path) -> None:
    assert _run(tmp_path).status == "CERTIFIED"


def test_build_snapshot_is_passed_to_response_unchanged(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.knowledge_snapshot_id == result.build.knowledge_snapshot_id
    assert result.response.knowledge_snapshot_id == result.build.knowledge_snapshot_id


def test_product_and_topic_remain_aligned(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.product_reference == result.build.product_reference == result.response.product_reference
    assert result.topic == result.build.topic == result.response.topic


def test_build_receipts_are_preserved(tmp_path: Path) -> None:
    assert len(_run(tmp_path).build.receipts) == 7


def test_publication_ids_are_preserved(tmp_path: Path) -> None:
    assert {"pd_1", "pg_1"}.issubset(set(_run(tmp_path).build.publication_ids))


def test_real_response_is_released(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.released_response_id == result.response.response.response_id
    assert result.response.response.direct_answer.startswith("Yes.")


def test_not_triggered_cycle_returns_direct_no(tmp_path: Path) -> None:
    result = _run(tmp_path, customer_context={"trigger_status": "NOT_TRIGGERED"})
    assert result.response.response.direct_answer.startswith("No.")


def test_general_cycle_returns_supported_conditional_answer(tmp_path: Path) -> None:
    result = _run(tmp_path, customer_context={})
    assert result.response.response.response_status in {"ANSWER", "ANSWER_WITH_LIMITATIONS"}
    assert "conditional 10% co-payment" in result.response.response.direct_answer


def test_cycle_uses_no_llm(tmp_path: Path) -> None:
    assert _run(tmp_path).response.used_llm is False


def test_question_is_trimmed(tmp_path: Path) -> None:
    assert _run(tmp_path, question="  Explain co-payment  ").question == "Explain co-payment"


def test_limitations_include_build_and_response(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.build.limitations[0] in result.limitations
    assert set(result.response.limitations).issubset(set(result.limitations))


def test_limitations_are_deduplicated(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert len(result.limitations) == len(set(result.limitations))


def test_certification_id_is_deterministic(tmp_path: Path) -> None:
    first = _run(tmp_path)
    second = _run(tmp_path)
    assert first.certification_id == second.certification_id


def test_changed_build_artifact_changes_certification_identity(tmp_path: Path) -> None:
    first = _run(tmp_path)
    _write(tmp_path, PATHS["CANONICAL_PROJECTION"], {"status": "evidence_assembled", "canonical_record_id": "cr2"})
    response_root = _response_registry(tmp_path / "response_registry")
    second = run_full_knowledge_to_explanation_certification(
        repository_root=tmp_path,
        build_request_id="build-1",
        response_request_id="response-1",
        question="Will this co-payment apply to my treatment?",
        customer_context={"trigger_status": "CONFIRMED"},
        artifact_paths=PATHS,
        response_repository_root=response_root,
    )
    assert first.certification_id != second.certification_id


def test_result_is_immutable(tmp_path: Path) -> None:
    result = _run(tmp_path)
    with pytest.raises(FrozenInstanceError):
        result.status = "FAILED"  # type: ignore[misc]


def test_customer_context_is_not_mutated(tmp_path: Path) -> None:
    context = {"trigger_status": "CONFIRMED"}
    _run(tmp_path, customer_context=context)
    assert context == {"trigger_status": "CONFIRMED"}


def test_missing_build_artifact_fails_before_response(tmp_path: Path) -> None:
    _build_artifacts(tmp_path)
    (tmp_path / PATHS["LEGAL_BINDING"]).unlink()
    response_root = _response_registry(tmp_path / "response_registry")
    with pytest.raises(FullCycleCertificationError, match="knowledge certification failed"):
        run_full_knowledge_to_explanation_certification(
            repository_root=tmp_path,
            build_request_id="build-1",
            response_request_id="response-1",
            question="Explain",
            artifact_paths=PATHS,
            response_repository_root=response_root,
        )


def test_missing_response_registry_fails_after_build(tmp_path: Path) -> None:
    _build_artifacts(tmp_path)
    with pytest.raises(FullCycleCertificationError, match="response certification failed"):
        run_full_knowledge_to_explanation_certification(
            repository_root=tmp_path,
            build_request_id="build-1",
            response_request_id="response-1",
            question="Explain",
            artifact_paths=PATHS,
            response_repository_root=tmp_path / "missing",
        )


@pytest.mark.parametrize("field,value", [
    ("response_request_id", ""),
    ("question", ""),
])
def test_required_response_text_is_validated(tmp_path: Path, field: str, value: str) -> None:
    _build_artifacts(tmp_path)
    response_root = _response_registry(tmp_path / "response_registry")
    values = dict(
        repository_root=tmp_path,
        build_request_id="build-1",
        response_request_id="response-1",
        question="Explain",
        artifact_paths=PATHS,
        response_repository_root=response_root,
    )
    values[field] = value
    with pytest.raises(FullCycleCertificationError):
        run_full_knowledge_to_explanation_certification(**values)


def test_invalid_build_request_is_normalised(tmp_path: Path) -> None:
    _build_artifacts(tmp_path)
    response_root = _response_registry(tmp_path / "response_registry")
    with pytest.raises(FullCycleCertificationError, match="knowledge certification failed"):
        run_full_knowledge_to_explanation_certification(
            repository_root=tmp_path,
            build_request_id="",
            response_request_id="response-1",
            question="Explain",
            artifact_paths=PATHS,
            response_repository_root=response_root,
        )


def test_nonexistent_repository_root_fails(tmp_path: Path) -> None:
    with pytest.raises(FullCycleCertificationError, match="repository_root"):
        run_full_knowledge_to_explanation_certification(
            repository_root=tmp_path / "missing",
            build_request_id="build-1",
            response_request_id="response-1",
            question="Explain",
        )


def test_evidence_reference_survives_full_cycle(tmp_path: Path) -> None:
    refs = _run(tmp_path).response.response.evidence_references
    assert refs and refs[0].locator == "page 39"


def test_no_generated_example_is_introduced(tmp_path: Path) -> None:
    text = " ".join(section.text for section in _run(tmp_path).response.response.sections)
    assert "₹" not in text and "1,00,000" not in text


def test_build_and_response_request_ids_are_preserved(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.build_request_id == "build-1"
    assert result.response_request_id == "response-1"
