from __future__ import annotations

import json
from pathlib import Path

import pytest

from insurance_intelligence.orchestration.star_comprehensive_knowledge_build import (
    StarKnowledgeBuildError,
    build_star_comprehensive_copay_snapshot,
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


def _root(tmp_path: Path) -> Path:
    _write(
        tmp_path,
        PATHS["SOURCE_REGISTRATION"],
        {
            "registration_status": "generic_sources_registered_evidence_review_required",
            "product_context": {
                "insurer_id": "star_health",
                "product_id": "star_comprehensive",
                "source_scope": "reusable_generic",
            },
            "sources": [{"source_id": "ev_1"}],
        },
    )
    _write(
        tmp_path,
        PATHS["DOCUMENT_IDENTITY"],
        {"status": "resolved", "document_id": "doc_1"},
    )
    _write(
        tmp_path,
        PATHS["DOCUMENT_CLASSIFICATION"],
        {
            "classification_status": (
                "reviewed_document_classifications_recorded_not_published"
            )
        },
    )
    _write(
        tmp_path,
        PATHS["LEGAL_BINDING"],
        {
            "binding_status": (
                "reviewed_generic_legal_conditions_bound_not_published"
            ),
            "reviewed_by_human": True,
            "assertions": [
                {
                    "assertion_id": "a1",
                    "assertion_type": "conditional_copayment_rule",
                    "candidate_id": "c1",
                }
            ],
        },
    )
    _write(
        tmp_path,
        PATHS["CANONICAL_PROJECTION"],
        {"status": "evidence_assembled", "canonical_record_id": "cr1"},
    )
    _write(
        tmp_path,
        PATHS["PUBLICATION_DECISION"],
        {"decision_status": "approved", "decision_id": "d1"},
    )
    _write(
        tmp_path,
        PATHS["AUTHORITATIVE_PUBLICATION"],
        {
            "publication_status": "authoritative_published",
            "publication_id": "p1",
        },
    )
    return tmp_path


def _run(tmp_path: Path):
    return build_star_comprehensive_copay_snapshot(
        repository_root=_root(tmp_path),
        build_request_id="build-1",
        artifact_paths=PATHS,
    )


def test_certifies_complete_chain(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.status == "CERTIFIED"
    assert len(result.receipts) == 7


def test_emits_snapshot_and_build_ids(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.knowledge_snapshot_id.startswith("knowledge-snapshot-")
    assert result.build_id.startswith("knowledge-build-")


def test_is_deterministic(tmp_path: Path) -> None:
    root = _root(tmp_path)
    first = build_star_comprehensive_copay_snapshot(
        repository_root=root,
        build_request_id="b",
        artifact_paths=PATHS,
    )
    second = build_star_comprehensive_copay_snapshot(
        repository_root=root,
        build_request_id="b",
        artifact_paths=PATHS,
    )
    assert first == second


def test_snapshot_changes_when_artifact_changes(tmp_path: Path) -> None:
    root = _root(tmp_path)
    first = build_star_comprehensive_copay_snapshot(
        repository_root=root,
        build_request_id="b",
        artifact_paths=PATHS,
    )
    _write(
        root,
        PATHS["CANONICAL_PROJECTION"],
        {"status": "evidence_assembled", "canonical_record_id": "cr2"},
    )
    second = build_star_comprehensive_copay_snapshot(
        repository_root=root,
        build_request_id="b",
        artifact_paths=PATHS,
    )
    assert first.knowledge_snapshot_id != second.knowledge_snapshot_id


def test_collects_governed_ids(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert "a1" in result.assertion_ids
    assert "p1" in result.publication_ids
    assert "ev_1" in result.evidence_ids


def test_receipts_have_sha256(tmp_path: Path) -> None:
    assert all(len(receipt.sha256) == 64 for receipt in _run(tmp_path).receipts)


@pytest.mark.parametrize("stage", list(PATHS))
def test_missing_artifact_fails_closed(tmp_path: Path, stage: str) -> None:
    root = _root(tmp_path)
    (root / PATHS[stage]).unlink()
    with pytest.raises(StarKnowledgeBuildError, match="missing"):
        build_star_comprehensive_copay_snapshot(
            repository_root=root,
            build_request_id="b",
            artifact_paths=PATHS,
        )


def test_wrong_product_fails(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write(
        root,
        PATHS["SOURCE_REGISTRATION"],
        {
            "product_context": {
                "insurer_id": "other",
                "product_id": "x",
                "source_scope": "reusable_generic",
            }
        },
    )
    with pytest.raises(StarKnowledgeBuildError, match="identity"):
        build_star_comprehensive_copay_snapshot(
            repository_root=root,
            build_request_id="b",
            artifact_paths=PATHS,
        )


def test_private_scope_fails(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write(
        root,
        PATHS["SOURCE_REGISTRATION"],
        {
            "product_context": {
                "insurer_id": "star_health",
                "product_id": "star_comprehensive",
                "source_scope": "policy_instance",
            }
        },
    )
    with pytest.raises(StarKnowledgeBuildError, match="reusable"):
        build_star_comprehensive_copay_snapshot(
            repository_root=root,
            build_request_id="b",
            artifact_paths=PATHS,
        )


def test_unreviewed_binding_fails(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write(
        root,
        PATHS["LEGAL_BINDING"],
        {"reviewed_by_human": False, "assertions": []},
    )
    with pytest.raises(StarKnowledgeBuildError, match="human reviewed"):
        build_star_comprehensive_copay_snapshot(
            repository_root=root,
            build_request_id="b",
            artifact_paths=PATHS,
        )


def test_missing_copay_assertion_fails(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write(
        root,
        PATHS["LEGAL_BINDING"],
        {
            "reviewed_by_human": True,
            "assertions": [{"assertion_type": "waiting_period"}],
        },
    )
    with pytest.raises(StarKnowledgeBuildError, match="co-payment"):
        build_star_comprehensive_copay_snapshot(
            repository_root=root,
            build_request_id="b",
            artifact_paths=PATHS,
        )


def test_unpublished_authoritative_record_fails(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write(root, PATHS["AUTHORITATIVE_PUBLICATION"], {"status": "draft"})
    with pytest.raises(StarKnowledgeBuildError, match="publication-ready"):
        build_star_comprehensive_copay_snapshot(
            repository_root=root,
            build_request_id="b",
            artifact_paths=PATHS,
        )


@pytest.mark.parametrize("bad", ["", "   ", None, 7])
def test_invalid_build_request_id_fails(tmp_path: Path, bad: object) -> None:
    with pytest.raises(StarKnowledgeBuildError):
        build_star_comprehensive_copay_snapshot(
            repository_root=_root(tmp_path),
            build_request_id=bad,  # type: ignore[arg-type]
            artifact_paths=PATHS,
        )


def test_unknown_stage_override_fails(tmp_path: Path) -> None:
    with pytest.raises(StarKnowledgeBuildError, match="unknown"):
        build_star_comprehensive_copay_snapshot(
            repository_root=_root(tmp_path),
            build_request_id="b",
            artifact_paths={"NOPE": "x"},
        )


def test_nonexistent_root_fails(tmp_path: Path) -> None:
    with pytest.raises(StarKnowledgeBuildError, match="existing"):
        build_star_comprehensive_copay_snapshot(
            repository_root=tmp_path / "no",
            build_request_id="b",
            artifact_paths=PATHS,
        )


def test_limitations_are_explicit(tmp_path: Path) -> None:
    assert _run(tmp_path).limitations


def test_product_and_topic_are_preserved(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.product_reference == "star_health:star_comprehensive"
    assert result.topic == "conditional_copayment"

def test_collects_nested_publication_decision_id(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write(
        root,
        PATHS["AUTHORITATIVE_PUBLICATION"],
        {
            "publication_status": "authoritative",
            "assertions": [
                {
                    "assertion_id": "a1",
                    "publication_decision_id": "pg_123",
                }
            ],
        },
    )

    result = build_star_comprehensive_copay_snapshot(
        repository_root=root,
        build_request_id="build-publication-id",
        artifact_paths=PATHS,
    )

    assert "pg_123" in result.publication_ids

