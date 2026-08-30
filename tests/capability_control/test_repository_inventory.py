from pathlib import Path

from capability_control.catalog import CapabilityCatalog, CapabilityRecord
from capability_control.inventory import (
    build_repository_inventory,
    capability_structural_fingerprints,
    structural_search_text,
)
from capability_control.preflight import preflight_capability


def _capability(*, ownership_paths=("pkg",), capability_id="PLATFORM.TEST"):
    return CapabilityRecord(
        capability_id=capability_id,
        name="Test capability",
        responsibility="Govern test behavior",
        plane="PLATFORM",
        lifecycle_status="ACTIVE",
        authority_role="test authority",
        safety_invariants=("must remain deterministic",),
        reuse_policy="REUSE",
        ownership_paths=ownership_paths,
        introduced_by=None,
        supersedes=(),
        superseded_by=None,
        notes=None,
    )


def _catalog(capability):
    return CapabilityCatalog(
        catalog_version="1.0",
        enforcement_mode="RECONCILIATION",
        governed_roots=("pkg",),
        capabilities=(capability,),
    )


def _write(root: Path, rel: str, text: str):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_relative_import_isolated_form_resolves_submodule(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "from . import foo\n")
    _write(tmp_path, "pkg/foo.py", "VALUE = 1\n")
    inv = build_repository_inventory(tmp_path)
    assert inv.by_module_id["pkg"].internal_imports == ("pkg.foo",)


def test_entrypoint_imports_seed_static_reachability(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/a.py", "VALUE = 1\n")
    _write(tmp_path, "scripts/run_a.py", "import pkg.a\n")
    inv = build_repository_inventory(tmp_path)
    assert inv.by_module_id["pkg.a"].entrypoint_reachable is True


def test_first_party_script_package_marks_is_entrypoint(tmp_path):
    _write(tmp_path, "scripts/__init__.py", "")
    _write(tmp_path, "scripts/run.py", "VALUE = 1\n")
    inv = build_repository_inventory(tmp_path)
    assert inv.by_module_id["scripts.run"].is_entrypoint is True
    assert inv.by_module_id["scripts.run"].entrypoint_reachable is False


def test_inventory_is_deterministic_for_identical_tree(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/a.py", '\"\"\"Alpha module.\"\"\"\nclass Alpha: pass\ndef run(): return 1\n')
    first = build_repository_inventory(tmp_path)
    second = build_repository_inventory(tmp_path)
    assert first.content_digest == second.content_digest
    assert first.records == second.records


def test_source_change_changes_inventory_digest(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    path = _write(tmp_path, "pkg/a.py", "VALUE = 1\n")
    before = build_repository_inventory(tmp_path)
    path.write_text("VALUE = 2\n", encoding="utf-8")
    after = build_repository_inventory(tmp_path)
    assert before.content_digest != after.content_digest
    assert before.by_module_id["pkg.a"].sha256 != after.by_module_id["pkg.a"].sha256


def test_dynamic_import_is_flagged(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/a.py", "import importlib\nimportlib.import_module('pkg.b')\n")
    _write(tmp_path, "pkg/b.py", "VALUE = 1\n")
    inv = build_repository_inventory(tmp_path)
    assert inv.by_module_id["pkg.a"].uses_dynamic_import is True


def test_reverse_imports_are_derived(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/a.py", "import pkg.b\n")
    _write(tmp_path, "pkg/b.py", "VALUE = 1\n")
    inv = build_repository_inventory(tmp_path)
    assert inv.by_module_id["pkg.b"].imported_by == ("pkg.a",)


def test_capability_structural_fingerprint_tracks_owned_implementation(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    path = _write(tmp_path, "pkg/a.py", "def first(): return 1\n")
    capability = _capability(ownership_paths=("pkg/a.py",))
    catalog = _catalog(capability)
    before = capability_structural_fingerprints(
        catalog=catalog, inventory=build_repository_inventory(tmp_path)
    )[0]
    path.write_text("def second(): return 2\n", encoding="utf-8")
    after = capability_structural_fingerprints(
        catalog=catalog, inventory=build_repository_inventory(tmp_path)
    )[0]
    assert before.structural_fingerprint != after.structural_fingerprint
    assert before.owned_module_paths == ("pkg/a.py",)


def test_existing_preflight_can_reuse_structural_inventory_terms(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/provider_compare.py", "class ProviderDisagreementAnalyzer: pass\n")
    capability = _capability(
        ownership_paths=("pkg/provider_compare.py",),
        capability_id="LLM.EVALUATION.TEST",
    )
    catalog = _catalog(capability)
    inventory = build_repository_inventory(tmp_path)
    result = preflight_capability(
        catalog=catalog,
        query="provider disagreement analyzer",
        structural_text_for=lambda record: structural_search_text(
            capability=record, inventory=inventory
        ),
    )
    assert result.new_authorized is False
    assert result.candidates[0].capability_id == "LLM.EVALUATION.TEST"
    assert "disagreement" in result.candidates[0].matched_terms


def test_structural_terms_do_not_change_no_new_authorization_invariant(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/a.py", "class Something: pass\n")
    capability = _capability(ownership_paths=("pkg/a.py",))
    catalog = _catalog(capability)
    inventory = build_repository_inventory(tmp_path)
    result = preflight_capability(
        catalog=catalog,
        query="totally unrelated capability",
        structural_text_for=lambda record: structural_search_text(
            capability=record, inventory=inventory
        ),
    )
    assert result.new_authorized is False
