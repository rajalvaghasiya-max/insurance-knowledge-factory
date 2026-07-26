
from __future__ import annotations

import argparse
import json
from pathlib import Path

from factory_core.architecture.canonical_model_inventory import (
    InventoryOptions,
    build_canonical_model_inventory,
)

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory current JSON artifacts for Canonical Fact & Evidence Model v1 design."
    )
    parser.add_argument("--root", default=".", help="Repository root to inventory.")
    parser.add_argument(
        "--output",
        default="docs/architecture/canonical_model_inventory_report.json",
        help="Output path, relative to --root unless absolute.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)

    report = build_canonical_model_inventory(InventoryOptions(root=root))
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("=" * 70)
    print("CANONICAL FACT & EVIDENCE INVENTORY")
    print("=" * 70)
    print(f"Repository root  : {root}")
    print(f"Artifacts found  : {report['summary']['artifact_count']}")
    print(f"Unreadable files : {report['summary']['failure_count']}")
    print(f"Artifact types   : {report['summary']['artifact_types']}")
    print(f"Report           : {output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
