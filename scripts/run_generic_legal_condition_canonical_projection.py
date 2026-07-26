from __future__ import annotations

import argparse
import json

from factory_core.canonical.generic_legal_condition_canonical_projection import (
    GenericLegalConditionCanonicalProjection,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="P2.5-I canonical projection of generic legal conditions")
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    runner = GenericLegalConditionCanonicalProjection()
    result = runner.project_from_spec_file(spec_path=args.spec_path, repository_root=args.repository_root)
    output_path = runner.write_output(result, repository_root=args.repository_root, output_path=args.output_path)
    print(json.dumps({
        "projection_status": result.report["projection_status"],
        "assertion_count": len(result.bundle.assertions),
        "evidence_span_count": len(result.bundle.evidence_spans),
        "publication_statuses": sorted({item.publication_status.value for item in result.bundle.assertions}),
        "output_path": str(output_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
