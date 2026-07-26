from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from insurance_intelligence.contracts.llm_evaluation import (
    EvaluationCaseCategory,
    LLMResponsibility,
)
from insurance_intelligence.evaluation.dataset import (
    EvaluationDatasetError,
    load_evaluation_dataset,
)

FIXTURES = Path("tests/fixtures/insurance_intelligence/llm_evaluation")


def _copy(tmp_path: Path) -> Path:
    target = tmp_path / "dataset"
    shutil.copytree(FIXTURES, target)
    return target


def test_loads_versioned_dataset_with_expected_counts() -> None:
    dataset = load_evaluation_dataset(FIXTURES)
    assert dataset.dataset_id == "policyscna-mo-022f-controlled-evaluation"
    assert dataset.dataset_version == "1.0.0"
    assert dataset.schema_version == "1.0"
    assert len(dataset.cases) == 24
    assert dataset.summary()["by_category"] == {
        "ADVERSARIAL": 7,
        "HISTORICAL_REGRESSION": 4,
        "KNOWN_BAD": 7,
        "KNOWN_GOOD": 6,
    }


def test_cases_are_deterministically_ordered() -> None:
    dataset = load_evaluation_dataset(FIXTURES)
    ids = [case.case_id for case in dataset.cases]
    assert ids == sorted(ids)


def test_filter_by_category_responsibility_and_tag() -> None:
    dataset = load_evaluation_dataset(FIXTURES)
    assert len(dataset.filter(category=EvaluationCaseCategory.KNOWN_GOOD)) == 6
    assert len(dataset.filter(responsibility=LLMResponsibility.AUDIENCE_ADAPTATION)) == 2
    assert [case.case_id for case in dataset.filter(tags=("byte-preserved",))] == [
        "hist-004"
    ]


def test_real_star_statement_is_byte_preserved() -> None:
    dataset = load_evaluation_dataset(FIXTURES)
    case = next(case for case in dataset.cases if case.case_id == "hist-004")
    expected = "Star Comprehensive applies a 10% co-payment to each and every claim for fresh as well as renewal policies where the insured person's age at entry is 61 years or above. The co-payment does not apply where the insured person entered the policy before attaining 61 years of age and renewed continuously without a break. The policy wording limits this co-payment to Sections II.1, II.2, II.3, II.4, II.5, II.6, II.7, II.8, II.9, II.10, II.11, II.15 and II.25."
    assert case.reference_output == expected


def test_historical_cases_have_defect_references() -> None:
    dataset = load_evaluation_dataset(FIXTURES)
    historical = dataset.filter(category=EvaluationCaseCategory.HISTORICAL_REGRESSION)
    assert all(case.historical_defect_id for case in historical)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda m: m.update(schema_version="2.0"), "unsupported dataset schema_version"),
        (lambda m: m.update(case_count=999), "case_count does not match"),
        (lambda m: m.update(files=m["files"] + [m["files"][0]]), "must not contain duplicates"),
    ],
)
def test_rejects_invalid_manifest(tmp_path: Path, mutation, message: str) -> None:
    root = _copy(tmp_path)
    path = root / "manifest.json"
    payload = json.loads(path.read_text())
    mutation(payload)
    path.write_text(json.dumps(payload))
    with pytest.raises(EvaluationDatasetError, match=message):
        load_evaluation_dataset(root)


def test_rejects_duplicate_case_ids_across_files(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    known_bad = json.loads((root / "known_bad.json").read_text())
    known_good = json.loads((root / "known_good.json").read_text())
    duplicate = dict(known_good["cases"][0])
    duplicate["category"] = "KNOWN_BAD"
    known_bad["cases"].append(duplicate)
    (root / "known_bad.json").write_text(json.dumps(known_bad))
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["case_count"] += 1
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(EvaluationDatasetError, match="case IDs must be unique"):
        load_evaluation_dataset(root)


def test_rejects_category_file_mismatch(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    payload = json.loads((root / "known_good.json").read_text())
    payload["cases"][0]["category"] = "KNOWN_BAD"
    (root / "known_good.json").write_text(json.dumps(payload))
    with pytest.raises(EvaluationDatasetError, match="does not match"):
        load_evaluation_dataset(root)


def test_rejects_missing_evidence_reference(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    payload = json.loads((root / "known_good.json").read_text())
    payload["cases"][0]["governed_evidence_ids"] = []
    (root / "known_good.json").write_text(json.dumps(payload))
    with pytest.raises(EvaluationDatasetError, match="governed_evidence_ids must not be empty"):
        load_evaluation_dataset(root)


def test_rejects_invalid_enum_value(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    payload = json.loads((root / "known_good.json").read_text())
    payload["cases"][0]["responsibility"] = "MAGIC"
    (root / "known_good.json").write_text(json.dumps(payload))
    with pytest.raises(EvaluationDatasetError, match="invalid responsibility"):
        load_evaluation_dataset(root)
