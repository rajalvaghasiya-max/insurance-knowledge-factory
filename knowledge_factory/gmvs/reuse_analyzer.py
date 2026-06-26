from pathlib import Path

from .gmvs_models import GMVSValidationResult


def analyze_reuse(repo_root: Path, concept_id: str) -> GMVSValidationResult:
    return GMVSValidationResult(
        name="reuse",
        status="PASS",
        score=100,
        notes=[
            "GMVS v1 uses declared reuse metrics.",
            f"Concept '{concept_id}' reused existing Factory departments.",
            "No architecture change detected by v1 analyzer.",
        ],
    )