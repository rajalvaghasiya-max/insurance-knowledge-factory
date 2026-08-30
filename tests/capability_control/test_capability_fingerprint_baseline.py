from __future__ import annotations

import json
from pathlib import Path

from scripts.check_capability_fingerprints import main


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _catalog(repo: Path) -> Path:
    path = repo / "governance/capabilities/catalog.json"
    _write(
        path,
        json.dumps(
            {
                "catalog_version": "1.0",
                "enforcement_mode": "RECONCILIATION",
                "governed_roots": ["pkg"],
                "capabilities": [
                    {
                        "capability_id": "PLATFORM.TEST",
                        "name": "Test capability",
                        "responsibility": "test fingerprint baseline",
                        "plane": "PLATFORM",
                        "lifecycle_status": "ACTIVE",
                        "authority_role": "test only",
                        "safety_invariants": ["test invariant"],
                        "reuse_policy": "REUSE",
                        "ownership_paths": ["pkg/service.py"],
                        "introduced_by": None,
                        "supersedes": [],
                        "superseded_by": None,
                        "notes": None,
                    }
                ],
            }
        ),
    )
    return path


def test_emit_baseline_is_deterministic(tmp_path, capsys):
    _write(tmp_path / "pkg/__init__.py", "")
    _write(tmp_path / "pkg/service.py", "def run():\n    return 1\n")
    catalog = _catalog(tmp_path)

    assert main(["--repo-root", str(tmp_path), "--catalog", str(catalog), "--emit-baseline"]) == 0
    first = capsys.readouterr().out
    assert main(["--repo-root", str(tmp_path), "--catalog", str(catalog), "--emit-baseline"]) == 0
    second = capsys.readouterr().out
    assert first == second
    payload = json.loads(first)
    assert payload["capabilities"][0]["capability_id"] == "PLATFORM.TEST"


def test_matching_baseline_passes(tmp_path, capsys):
    _write(tmp_path / "pkg/__init__.py", "")
    _write(tmp_path / "pkg/service.py", "def run():\n    return 1\n")
    catalog = _catalog(tmp_path)
    assert main(["--repo-root", str(tmp_path), "--catalog", str(catalog), "--emit-baseline"]) == 0
    emitted = capsys.readouterr().out
    baseline = tmp_path / "baseline.json"
    baseline.write_text(emitted, encoding="utf-8")

    assert main(["--repo-root", str(tmp_path), "--catalog", str(catalog), "--baseline", str(baseline)]) == 0
    assert "CAPABILITY_FINGERPRINT_OK capabilities=1" in capsys.readouterr().out


def test_implementation_change_fails_closed(tmp_path, capsys):
    _write(tmp_path / "pkg/__init__.py", "")
    service = tmp_path / "pkg/service.py"
    _write(service, "def run():\n    return 1\n")
    catalog = _catalog(tmp_path)
    assert main(["--repo-root", str(tmp_path), "--catalog", str(catalog), "--emit-baseline"]) == 0
    baseline = tmp_path / "baseline.json"
    baseline.write_text(capsys.readouterr().out, encoding="utf-8")

    _write(service, "def run():\n    return 2\n")
    assert main(["--repo-root", str(tmp_path), "--catalog", str(catalog), "--baseline", str(baseline)]) == 1
    err = capsys.readouterr().err
    assert "CAPABILITY_IMPLEMENTATION_CHANGED PLATFORM.TEST" in err
    assert "CAPABILITY_FINGERPRINT_DRIFT" in err


def test_missing_baseline_is_invalid_not_silently_bootstrapped(tmp_path, capsys):
    _write(tmp_path / "pkg/__init__.py", "")
    _write(tmp_path / "pkg/service.py", "def run():\n    return 1\n")
    catalog = _catalog(tmp_path)

    assert main([
        "--repo-root", str(tmp_path),
        "--catalog", str(catalog),
        "--baseline", str(tmp_path / "missing.json"),
    ]) == 2
    assert "CAPABILITY_FINGERPRINT_BASELINE_INVALID" in capsys.readouterr().err


def test_capability_addition_requires_baseline_update(tmp_path, capsys):
    _write(tmp_path / "pkg/__init__.py", "")
    _write(tmp_path / "pkg/service.py", "def run():\n    return 1\n")
    catalog = _catalog(tmp_path)
    assert main(["--repo-root", str(tmp_path), "--catalog", str(catalog), "--emit-baseline"]) == 0
    baseline = tmp_path / "baseline.json"
    baseline.write_text(capsys.readouterr().out, encoding="utf-8")

    raw = json.loads(catalog.read_text(encoding="utf-8"))
    _write(tmp_path / "pkg/extra.py", "def extra():\n    return True\n")
    raw["capabilities"].append(
        {
            **raw["capabilities"][0],
            "capability_id": "PLATFORM.EXTRA",
            "name": "Extra capability",
            "ownership_paths": ["pkg/extra.py"],
        }
    )
    catalog.write_text(json.dumps(raw), encoding="utf-8")

    assert main(["--repo-root", str(tmp_path), "--catalog", str(catalog), "--baseline", str(baseline)]) == 1
    assert "CAPABILITY_FINGERPRINT_ADDED PLATFORM.EXTRA" in capsys.readouterr().err
