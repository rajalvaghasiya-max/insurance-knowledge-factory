from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from scripts import run_official_policy_currentness_evidence
from scripts import run_official_source_observation


SHA = "a" * 64


def test_official_source_observation_cli_builds_evidence_only_spec(monkeypatch, tmp_path: Path, capsys):
    captured: dict[str, object] = {}

    class FakeSourceObservationRecord:
        def build(self, *, spec, repository_root):
            captured["spec"] = spec
            captured["repository_root"] = repository_root
            return SimpleNamespace(
                record={
                    "observation_id": "obs_1",
                    "official_observation": {"observed_at": spec["observation"]["observed_at"]},
                    "registered_document": {"document_version_id": "docver_1"},
                    "byte_comparison": {"status": "byte_identical_observed"},
                }
            )

        def write_output(self, result, *, repository_root, output_path):
            captured["output_path"] = output_path
            return repository_root / output_path

    monkeypatch.setattr(run_official_source_observation, "SourceObservationRecord", FakeSourceObservationRecord)
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_official_source_observation",
            "--repository-root", str(tmp_path),
            "--registration-path", "knowledge/registration.json",
            "--observation-id", "obs_1",
            "--source-url", "https://example.invalid/policy.pdf",
            "--source-page-url", "https://example.invalid/product",
            "--source-page-artifact-path", "archive/source_pages/product.html",
            "--observed-pdf-path", "archive/raw/policy.pdf",
            "--output-path", "knowledge/governance/observation.json",
        ],
    )

    assert run_official_source_observation.main() == 0

    spec = captured["spec"]
    assert spec["record_type"] == "source_observation_record_v1"
    assert spec["registered_document"] == {"registration_path": "knowledge/registration.json"}
    assert spec["observation"]["retrieval_status"] == "succeeded"
    assert spec["observation"]["observed_pdf_path"] == "archive/raw/policy.pdf"
    assert spec["observation"]["source_page_artifact_path"] == "archive/source_pages/product.html"
    datetime.fromisoformat(spec["observation"]["observed_at"])
    assert "temporal_status" not in spec
    assert "publication" not in spec
    assert "entitlement" not in spec
    output = capsys.readouterr().out
    assert "Byte comparison    : byte_identical_observed" in output
    assert "temporal review remains required" in output


def test_official_policy_currentness_cli_builds_reviewed_evidence_without_temporal_decision(
    monkeypatch, tmp_path: Path, capsys
):
    captured: dict[str, object] = {}

    class FakeDocumentCurrentnessEvidenceRecord:
        def build(self, *, spec, repository_root):
            captured["spec"] = spec
            captured["repository_root"] = repository_root
            return SimpleNamespace(
                record={
                    "registered_document": {"document_version_id": "docver_1"},
                    "source_observation": {"observation_id": "obs_1"},
                    "currentness_evidence_conclusion": "sufficient_for_current_observed_review",
                    "positive_currentness_evidence_count": 1,
                }
            )

        def write_output(self, result, *, repository_root, output_path):
            captured["output_path"] = output_path
            return repository_root / output_path

    monkeypatch.setattr(
        run_official_policy_currentness_evidence,
        "DocumentCurrentnessEvidenceRecord",
        FakeDocumentCurrentnessEvidenceRecord,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_official_policy_currentness_evidence",
            "--repository-root", str(tmp_path),
            "--registration-path", "knowledge/registration.json",
            "--observation-record-path", "knowledge/governance/observation.json",
            "--linked-document-url", "https://example.invalid/policy.pdf",
            "--observed-text", "Policy Wording",
            "--review-rationale", "Official product page retained and reviewed.",
            "--output-path", "knowledge/governance/currentness.json",
        ],
    )

    assert run_official_policy_currentness_evidence.main() == 0

    spec = captured["spec"]
    assert spec["record_type"] == "document_currentness_evidence_record_v1"
    assert spec["reviewed_by_human"] is True
    assert spec["registered_document"] == {"registration_path": "knowledge/registration.json"}
    assert spec["source_observation"] == {"observation_record_path": "knowledge/governance/observation.json"}
    assert spec["evidence_items"][0]["evidence_status"] == "supports_currentness_review"
    assert spec["evidence_items"][0]["verification"] == "retained_official_html_manual_review"
    datetime.fromisoformat(spec["reviewed_at"])
    assert "temporal_status" not in spec
    assert "publication" not in spec
    assert "entitlement" not in spec
    output = capsys.readouterr().out
    assert "Evidence conclusion  : sufficient_for_current_observed_review" in output
    assert "temporal decision remains separate" in output
