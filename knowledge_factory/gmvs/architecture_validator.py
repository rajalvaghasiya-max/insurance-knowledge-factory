from pathlib import Path

from .gmvs_models import GMVSValidationResult


REQUIRED_PATHS = [
    "knowledge_factory/golden_concept_package",
    "knowledge_factory/governance",
    "knowledge_factory/gmvs",
    "knowledge_factory/shared/asset_normalizer.py",
]


def validate_architecture(repo_root: Path) -> GMVSValidationResult:
    missing = []

    for relative_path in REQUIRED_PATHS:
        if not (repo_root / relative_path).exists():
            missing.append(relative_path)

    status = "PASS" if not missing else "FAIL"
    score = 100 if not missing else max(0, 100 - len(missing) * 20)

    notes = (
        ["Required Factory architecture paths are present."]
        if not missing
        else [f"Missing: {path}" for path in missing]
    )

    return GMVSValidationResult(
        name="architecture",
        status=status,
        score=score,
        notes=notes,
    )