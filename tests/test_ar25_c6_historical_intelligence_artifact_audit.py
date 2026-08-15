from pathlib import Path
import subprocess
import sys

from scripts.audit_historical_intelligence_artifacts import audit


def _write(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n", encoding="utf-8")


def test_known_bypass_static_artifacts_are_retained_as_firewall_fixtures(tmp_path: Path) -> None:
    known = (
        "knowledge/health/comparisons/"
        "star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison.json"
    )
    _write(tmp_path, known)

    findings = audit(tmp_path)

    assert len(findings) == 1
    assert findings[0].path == known
    assert findings[0].disposition == "RETAIN_FIREWALL_FIXTURE"


def test_uninventoried_historical_output_requires_review_not_automatic_deletion(tmp_path: Path) -> None:
    path = "knowledge/health/recommendations/ad_hoc_old_recommendation.json"
    _write(tmp_path, path)

    findings = audit(tmp_path)

    assert len(findings) == 1
    assert findings[0].path == path
    assert findings[0].disposition == "REVIEW_REQUIRED"


def test_unrelated_knowledge_files_are_outside_c6_scope(tmp_path: Path) -> None:
    _write(tmp_path, "knowledge/health/star_health/product/source.json")
    assert audit(tmp_path) == ()


def test_audit_script_runs_directly_from_repository_root() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_historical_intelligence_artifacts.py"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "AR-2.5 C6 HISTORICAL INTELLIGENCE ARTIFACT AUDIT" in result.stdout
