from pathlib import Path

from .gmvs_models import GMVSValidationResult


def validate_readiness(repo_root: Path, concept_id: str) -> GMVSValidationResult:
    concept_dir = repo_root / "knowledge" / "factory" / "golden_concepts" / concept_id

    if concept_dir.exists():
        return GMVSValidationResult(
            name="readiness",
            status="PASS",
            score=100,
            notes=[f"Concept directory found: {concept_id}"],
        )

    return GMVSValidationResult(
        name="readiness",
        status="WARN",
        score=70,
        notes=[f"Concept directory not found yet: {concept_id}"],
    )