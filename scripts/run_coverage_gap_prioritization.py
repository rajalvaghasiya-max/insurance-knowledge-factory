from __future__ import annotations

import argparse
import json

from factory_core.canonical.coverage_gap_prioritization import CoverageGapPrioritization


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a read-only reviewed coverage-gap prioritisation backlog."
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    runner = CoverageGapPrioritization()
    result = runner.prioritize_from_spec_file(
        spec_path=args.spec_path,
        repository_root=args.repository_root,
    )
    output = runner.write_output(
        result,
        repository_root=args.repository_root,
        output_path=args.output_path,
    )
    print(json.dumps({
        "backlog_status": result.manifest["backlog_status"],
        "backlog_item_count": len(result.manifest["backlog_items"]),
        "output_path": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
