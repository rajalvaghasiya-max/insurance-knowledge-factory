from pathlib import Path

from .gmvs_models import GMVSValidationResult


REQUIRED_GOVERNANCE_FILES = [
    "knowledge_factory/governance/evolution/factory_evolution_register.json",
    "knowledge_factory/governance/evolution/factory_evolution_register.md",
    "knowledge_factory/governance/principles/engineering_principles.md",
    "knowledge_factory/governance/lessons/factory_lessons_learned.md",
    "knowledge_factory/governance/milestones/factory_milestones.md",
]


def validate_governance(repo_root: Path) -> GMVSValidationResult:
    missing = []

    for relative_path in REQUIRED_GOVERNANCE_FILES:
        if not (repo_root / relative_path).exists():
            missing.append(relative_path)

    status = "PASS" if not missing else "WARN"
    score = 100 if not missing else max(0, 100 - len(missing) * 15)

    notes = (
        ["Factory governance files are present."]
        if not missing
        else [f"Missing governance file: {path}" for path in missing]
    )

    return GMVSValidationResult(
        name="governance",
        status=status,
        score=score,
        notes=notes,
    )