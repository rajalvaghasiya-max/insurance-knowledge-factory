from pathlib import Path

from scripts.audit_repository_cleanup_candidates import audit


def test_reference_free_backup_is_high_confidence_candidate(tmp_path: Path) -> None:
    backup = tmp_path / "module_backup.py"
    backup.write_text("print('old')\n", encoding="utf-8")
    (tmp_path / "module.py").write_text("print('current')\n", encoding="utf-8")

    findings = audit(tmp_path)

    assert len(findings) == 1
    assert findings[0].path == "module_backup.py"
    assert findings[0].category == "BACKUP_COPY"
    assert findings[0].reference_count == 0
    assert findings[0].deletion_confidence == "HIGH"


def test_referenced_backup_requires_review(tmp_path: Path) -> None:
    backup = tmp_path / "module_backup.py"
    backup.write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("See module_backup.py before cleanup.\n", encoding="utf-8")

    findings = audit(tmp_path)

    assert len(findings) == 1
    assert findings[0].reference_count == 1
    assert findings[0].referenced_by == ("notes.md",)
    assert findings[0].deletion_confidence == "REVIEW_REQUIRED"


def test_normal_versioned_files_are_not_cleanup_candidates(tmp_path: Path) -> None:
    (tmp_path / "contract_v1.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "artifact.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "review.md").write_text("review\n", encoding="utf-8")

    assert audit(tmp_path) == ()


def test_template_names_are_not_misclassified_as_temporary_files(tmp_path: Path) -> None:
    (tmp_path / "template.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "templates.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "learning_path_templates.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "run_reviewer_decision_record_template.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "test_explanation_templates.py").write_text("VALUE = 1\n", encoding="utf-8")

    assert audit(tmp_path) == ()


def test_real_temp_suffix_is_flagged(tmp_path: Path) -> None:
    temporary = tmp_path / "module_temp.py"
    temporary.write_text("VALUE = 1\n", encoding="utf-8")

    findings = audit(tmp_path)

    assert len(findings) == 1
    assert findings[0].category == "TEMPORARY_FILE"
    assert findings[0].deletion_confidence == "HIGH"


def test_duplicate_extension_is_flagged_without_inferring_deletion_when_referenced(
    tmp_path: Path,
) -> None:
    duplicate = tmp_path / "extractor.py.py"
    duplicate.write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "manifest.txt").write_text("extractor.py.py\n", encoding="utf-8")

    findings = audit(tmp_path)

    assert len(findings) == 1
    assert findings[0].category == "DUPLICATE_EXTENSION"
    assert findings[0].deletion_confidence == "REVIEW_REQUIRED"
