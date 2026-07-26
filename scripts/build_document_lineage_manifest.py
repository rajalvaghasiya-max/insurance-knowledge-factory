"""CLI for P2.5-D Document Registry Bridge."""
from __future__ import annotations

import argparse
from pathlib import Path

from factory_core.canonical.document_registry_bridge import DocumentRegistryBridge


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a read-only P2.5-C lineage manifest.")
    parser.add_argument("--spec-path", required=True, help="Reviewed P2.5-D bridge specification JSON")
    parser.add_argument("--repository-root", default=".", help="Repository root used for relative source paths")
    parser.add_argument("--output-path", required=True, help="Separate manifest output JSON")
    args = parser.parse_args()

    bridge = DocumentRegistryBridge()
    result = bridge.build_from_spec_file(spec_path=args.spec_path, repository_root=args.repository_root)
    output = bridge.write_manifest(result, args.output_path)
    print("=" * 70)
    print("DOCUMENT REGISTRY BRIDGE")
    print("=" * 70)
    print(f"Bridge status   : {result.report['bridge_status']}")
    print(f"Documents       : {result.report['document_count']}")
    print(f"Evidence spans  : {result.report['evidence_span_count']}")
    print(f"Output          : {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
