import json
from pathlib import Path

from .gmvs_models import GMVSValidationResult


def validate_manufacturing(repo_root: Path, concept_id: str) -> GMVSValidationResult:
    package_dir = repo_root / "knowledge" / "factory" / "golden_concept_packages" / concept_id

    packages = list(package_dir.glob("*_golden_concept_package.json"))

    if not packages:
        return GMVSValidationResult(
            name="manufacturing",
            status="FAIL",
            score=0,
            notes=[f"No Golden Concept Package found for {concept_id}."],
        )

    latest = max(packages, key=lambda path: path.stat().st_mtime)

    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except Exception as exc:
        return GMVSValidationResult(
            name="manufacturing",
            status="FAIL",
            score=0,
            notes=[f"Could not read package: {exc}"],
        )

    certification = data.get("package_certification", {})
    status = certification.get("status", "UNKNOWN")
    maturity = data.get("maturity_level", "UNKNOWN")

    if status == "PASS" and maturity == "GOLD":
        return GMVSValidationResult(
            name="manufacturing",
            status="PASS",
            score=100,
            notes=[f"{concept_id} manufactured successfully with GOLD maturity."],
        )

    return GMVSValidationResult(
        name="manufacturing",
        status="WARN",
        score=75,
        notes=[
            f"Package found but not fully complete. Certification={status}, Maturity={maturity}"
        ],
    )