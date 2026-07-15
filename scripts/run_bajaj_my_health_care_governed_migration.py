"""P1.5c — thin Bajaj My Health Care compatibility wrapper.

All orchestration, source-hash validation, specification loading, and
stage sequencing now live in the generic, specification-driven runner
at scripts/run_governed_product_migration.py. This wrapper contains no
migration logic of its own: it only points that generic runner at the
existing approved Bajaj migration manifest and preserves the original
CLI output format for backward compatibility.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from scripts.run_governed_product_migration import load_manifest, run_migration

# Anchored to this module's own location, not the process current working
# directory. Using a bare repository-relative string with load_manifest()
# depends on CWD == repository root at import time, which does not hold in
# every invocation context (e.g. imported from an external working
# directory). This module lives at <repository_root>/scripts/<this file>,
# so parents[1] is the repository root regardless of CWD.
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = Path("docs/architecture/bajaj_my_health_care_migration_manifest.json")

# Backward-compatible constant. Mechanically derived from the governed
# migration manifest at import time -- not an independently maintained
# duplicate of the hash. Any future change to the approved source
# document's hash must be made in the manifest; this constant will
# always reflect that single governed value.
EXPECTED_POLICY_WORDING_SHA256 = load_manifest(PACKAGE_ROOT / MANIFEST_PATH).expected_source_sha256


def run_bajaj_migration(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    return run_migration(root, root / MANIFEST_PATH)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the narrow Bajaj My Health Care governed migration "
        "(thin wrapper around the generic governed product migration runner)."
    )
    parser.add_argument("--repository-root", required=True)
    args = parser.parse_args()
    result = run_bajaj_migration(args.repository_root)
    print("=" * 70)
    print("BAJAJ MY HEALTH CARE — GOVERNED MIGRATION")
    print("=" * 70)
    print(f"Product              : {result['entity_id']}")
    print(f"Source SHA-256       : {result['source_sha256']}")
    print(f"Source registration  : {result['source_registration_status']}")
    print(f"Classification       : {result['classification_status']}")
    print(f"Identity             : {result['identity_status']}")
    print(f"Resolution           : {result['resolution_status']}")
    print(f"Temporal             : {result['temporal_status']}")
    print(f"Evidence review      : {result['evidence_review_eligibility']}")
    print(f"Current entitlement  : {result['current_entitlement_publication_eligibility']}")
    print(f"Overlay              : {result['overlay_output_path']}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
