from pathlib import Path
import re


AUTHORITATIVE_PRODUCTION_DIRS = (
    Path("factory_core"),
    Path("insurance_intelligence"),
)

KNOWLEDGE_DOMAINS_IMPORT = re.compile(
    r"^\s*(?:from\s+knowledge_domains(?:\.|\s)|import\s+knowledge_domains(?:\.|\s|$))",
    re.MULTILINE,
)


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in root.rglob("*.py")
            if "__pycache__" not in path.parts
        )
    )


def test_authoritative_production_code_does_not_import_transitional_knowledge_domains() -> None:
    offenders: list[str] = []
    for root in AUTHORITATIVE_PRODUCTION_DIRS:
        for path in _python_files(root):
            text = path.read_text(encoding="utf-8")
            if KNOWLEDGE_DOMAINS_IMPORT.search(text):
                offenders.append(path.as_posix())

    assert offenders == [], (
        "authoritative production code must not import transitional knowledge_domains: "
        + ", ".join(offenders)
    )


def test_health_domain_readme_declares_transitional_status() -> None:
    text = Path("knowledge_domains/health/README.md").read_text(encoding="utf-8")
    assert "TRANSITIONAL_REVIEW_REQUIRED" in text
    assert "not the canonical location" in text.lower()
    assert "do not add new architectural capability here" in text.lower()
    assert "health is the active production domain" not in text.lower()


def test_authoritative_architecture_classification_matches_transitional_status() -> None:
    text = Path(
        "docs/architecture/ACTIVE_AND_HISTORICAL_ARCHITECTURE_CLASSIFICATION.md"
    ).read_text(encoding="utf-8")
    assert "### `knowledge_domains/`" in text
    assert "Status: **TRANSITIONAL_REVIEW_REQUIRED**" in text
    assert "NO NEW ARCHITECTURAL DEVELOPMENT" in text
