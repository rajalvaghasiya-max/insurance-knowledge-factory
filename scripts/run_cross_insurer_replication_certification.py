from __future__ import annotations

import argparse
import json

from factory_core.canonical.cross_insurer_replication_certification import (
    CrossInsurerReplicationCertification,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Certify a reviewed cross-insurer replication milestone."
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    runner = CrossInsurerReplicationCertification()
    result = runner.certify_from_spec_file(
        spec_path=args.spec_path,
        repository_root=args.repository_root,
    )
    output = runner.write_output(
        result,
        repository_root=args.repository_root,
        output_path=args.output_path,
    )
    print(json.dumps({
        "certification_status": result.manifest["certification_status"],
        "replication_count": len(result.manifest["replications"]),
        "receipt_integrity": [item["receipt_integrity"] for item in result.manifest["replications"]],
        "output_path": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
