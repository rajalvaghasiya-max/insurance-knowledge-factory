"""MO-011: narrowly scoped regression test proving the governed Star
source bundle (the artifact involved in the MO-010/MO-011 CRLF
incident) is LF-controlled by .gitattributes and contains no CRLF
bytes in the working tree. Read-only; does not modify, regenerate, or
normalize any file.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

STAR_BUNDLE_RELATIVE = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_source_registration/star_health_star_comprehensive_generic_source_bundle.json"
)

GITATTRIBUTES_PATH = REPO_ROOT / ".gitattributes"
VERIFY_SCRIPT_PATH = REPO_ROOT / "scripts" / "verify_line_endings.py"


def _check_attr(relative_path: str) -> dict[str, str]:
    result = subprocess.run(
        ["git", "check-attr", "text", "eol", "binary", "--", relative_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    attrs: dict[str, str] = {}
    for line in result.stdout.splitlines():
        _, attribute, value = line.split(":", 2)
        attrs[attribute.strip()] = value.strip()
    return attrs


def test_gitattributes_file_exists():
    assert GITATTRIBUTES_PATH.is_file()


def test_verify_line_endings_script_exists():
    assert VERIFY_SCRIPT_PATH.is_file()


def test_star_bundle_is_lf_controlled():
    attrs = _check_attr(STAR_BUNDLE_RELATIVE)
    assert attrs.get("text") == "set"
    assert attrs.get("eol") == "lf"


def test_star_bundle_contains_no_crlf_bytes():
    absolute = REPO_ROOT / STAR_BUNDLE_RELATIVE
    assert absolute.is_file(), f"expected governed artifact not found: {STAR_BUNDLE_RELATIVE}"
    raw = absolute.read_bytes()
    assert b"\r\n" not in raw


def test_json_python_and_markdown_are_lf_controlled_by_default():
    """Spot-check representative extensions covered by the policy."""
    samples = {
        "docs/architecture/MO-011_DETERMINISTIC_LINE_ENDINGS.md": "md",
        "scripts/verify_line_endings.py": "py",
        "docs/architecture/star_health_star_comprehensive_migration_manifest.json": "json",
    }
    for relative, _label in samples.items():
        if not (REPO_ROOT / relative).is_file():
            continue
        attrs = _check_attr(relative)
        assert attrs.get("text") == "set", f"{relative} not classified as text"
        assert attrs.get("eol") == "lf", f"{relative} not LF-controlled"


def test_bat_and_cmd_files_preserve_crlf():
    """These extensions are not present in the repository today; this
    test asserts the attribute rule itself (not a specific tracked
    file), using a hypothetical path -- git check-attr evaluates
    pattern rules independent of whether the file exists."""
    for hypothetical in ("scripts/example.bat", "scripts/example.cmd"):
        attrs = _check_attr(hypothetical)
        assert attrs.get("eol") == "crlf", f"{hypothetical} should remain CRLF per policy"


def test_pdf_and_common_binaries_are_marked_binary():
    for hypothetical in ("archive/example.pdf", "archive/example.docx", "archive/example.zip"):
        attrs = _check_attr(hypothetical)
        assert attrs.get("text") == "unset", f"{hypothetical} should not be treated as text"


def test_verify_line_endings_script_runs_successfully():
    result = subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT_PATH), "--all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK:" in result.stdout


def test_verify_line_endings_script_did_not_modify_anything():
    """The validation script must be strictly read-only."""
    before = subprocess.run(
        ["git", "status", "--short"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout
    subprocess.run([sys.executable, str(VERIFY_SCRIPT_PATH), "--all"], cwd=REPO_ROOT, capture_output=True, text=True)
    after = subprocess.run(
        ["git", "status", "--short"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout
    assert before == after
