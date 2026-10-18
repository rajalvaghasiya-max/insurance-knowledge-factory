"""Check persisted capability implementation fingerprints against current repository structure."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from capability_control.catalog import CapabilityCatalogError, load_catalog
from capability_control.inventory import (
    build_repository_inventory,
    capability_structural_fingerprints,
)

DEFAULT_CATALOG = "governance/capabilities/catalog.json"
DEFAULT_BASELINE = "governance/capabilities/generated/structural_fingerprints.json"
BASELINE_SCHEMA_VERSION = "1.0"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument(
        "--emit-baseline",
        action="store_true",
        help="print the deterministic baseline JSON for bootstrap/review instead of checking",
    )
    return parser


def _baseline_payload(repo_root: Path, catalog_path: Path) -> dict[str, object]:
    catalog = load_catalog(catalog_path)
    inventory = build_repository_inventory(repo_root)
    fingerprints = capability_structural_fingerprints(catalog=catalog, inventory=inventory)
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "inventory_schema_version": inventory.schema_version,
        "capabilities": [
            {
                "capability_id": item.capability_id,
                "owned_module_paths": list(item.owned_module_paths),
                "structural_fingerprint": item.structural_fingerprint,
            }
            for item in fingerprints
        ],
    }


def _canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _load_baseline(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"fingerprint baseline is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"fingerprint baseline is invalid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("fingerprint baseline root must be an object")
    if raw.get("schema_version") != BASELINE_SCHEMA_VERSION:
        raise ValueError(f"fingerprint baseline schema_version must be {BASELINE_SCHEMA_VERSION!r}")
    capabilities = raw.get("capabilities")
    if not isinstance(capabilities, list):
        raise ValueError("fingerprint baseline capabilities must be a list")
    return raw


def _index(payload: dict[str, object]) -> dict[str, tuple[tuple[str, ...], str]]:
    indexed: dict[str, tuple[tuple[str, ...], str]] = {}
    for raw in payload.get("capabilities", []):
        if not isinstance(raw, dict):
            raise ValueError("fingerprint baseline capability entries must be objects")
        capability_id = raw.get("capability_id")
        paths = raw.get("owned_module_paths")
        fingerprint = raw.get("structural_fingerprint")
        if not isinstance(capability_id, str) or not capability_id:
            raise ValueError("fingerprint baseline capability_id must be non-empty")
        if capability_id in indexed:
            raise ValueError(f"duplicate fingerprint baseline capability_id: {capability_id}")
        if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
            raise ValueError(f"owned_module_paths must be a string list for {capability_id}")
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            raise ValueError(f"structural_fingerprint must be sha256 hex for {capability_id}")
        indexed[capability_id] = (tuple(paths), fingerprint)
    return indexed


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    catalog_path = Path(args.catalog)
    if not catalog_path.is_absolute():
        catalog_path = repo_root / catalog_path
    baseline_path = Path(args.baseline)
    if not baseline_path.is_absolute():
        baseline_path = repo_root / baseline_path

    try:
        current = _baseline_payload(repo_root, catalog_path)
    except CapabilityCatalogError as exc:
        print(f"CAPABILITY_FINGERPRINT_INVALID_CATALOG: {exc}", file=sys.stderr)
        return 2

    if args.emit_baseline:
        print(_canonical_json(current), end="")
        return 0

    try:
        committed = _load_baseline(baseline_path)
        old = _index(committed)
        new = _index(current)
    except ValueError as exc:
        print(f"CAPABILITY_FINGERPRINT_BASELINE_INVALID: {exc}", file=sys.stderr)
        return 2

    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(
        capability_id
        for capability_id in set(old) & set(new)
        if old[capability_id] != new[capability_id]
    )

    for capability_id in added:
        print(f"CAPABILITY_FINGERPRINT_ADDED {capability_id}", file=sys.stderr)
    for capability_id in removed:
        print(f"CAPABILITY_FINGERPRINT_REMOVED {capability_id}", file=sys.stderr)
    for capability_id in changed:
        print(f"CAPABILITY_IMPLEMENTATION_CHANGED {capability_id}", file=sys.stderr)

    if added or removed or changed:
        print(
            "CAPABILITY_FINGERPRINT_DRIFT: regenerate the baseline only after reviewing the PR capability-impact declaration.",
            file=sys.stderr,
        )
        return 1

    print(f"CAPABILITY_FINGERPRINT_OK capabilities={len(new)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
