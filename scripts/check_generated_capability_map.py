"""Validate or emit the deterministic generated PolicyScna capability map."""
from __future__ import annotations

import argparse
from pathlib import Path

from capability_control.system_map import CapabilitySystemMapError, generate_capability_map

CATALOG_PATH = Path("governance/capabilities/catalog.json")
FINGERPRINT_PATH = Path("governance/capabilities/generated/structural_fingerprints.json")
GENERATED_MAP_PATH = Path("docs/architecture/generated/POLICYSCNA_CAPABILITY_MAP.md")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit", action="store_true", help="Print the expected generated map")
    args = parser.parse_args()
    try:
        expected = generate_capability_map(CATALOG_PATH, FINGERPRINT_PATH)
    except CapabilitySystemMapError as exc:
        print(f"CAPABILITY_MAP_FAIL {exc}")
        return 1

    if args.emit:
        print(expected, end="")
        return 0

    try:
        actual = GENERATED_MAP_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"CAPABILITY_MAP_FAIL cannot read generated map: {exc}")
        return 1
    if actual != expected:
        print("CAPABILITY_MAP_STALE regenerate the deterministic capability map")
        return 1
    print("CAPABILITY_MAP_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
