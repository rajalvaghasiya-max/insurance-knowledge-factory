from __future__ import annotations

import argparse
import json

from factory_core.canonical.evidence_coverage_register import EvidenceCoverageRegister


def main() -> int:
    parser = argparse.ArgumentParser(description="Build P2.8 read-only evidence coverage register.")
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    runner = EvidenceCoverageRegister()
    result = runner.build_from_spec_file(
        spec_path=args.spec_path,
        repository_root=args.repository_root,
    )
    output = runner.write_output(
        result,
        repository_root=args.repository_root,
        output_path=args.output_path,
    )
    product_count = len(result.manifest["products"])
    concept_count = sum(len(product["concepts"]) for product in result.manifest["products"])
    print(json.dumps({
        "register_status": result.manifest["register_status"],
        "product_count": product_count,
        "concept_count": concept_count,
        "output_path": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
