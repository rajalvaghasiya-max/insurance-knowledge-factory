from __future__ import annotations

import argparse
import json

from factory_core.canonical.generic_source_registration import GenericSourceRegistration


def main() -> int:
    parser = argparse.ArgumentParser(description="P2.5-G generic source registration")
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--bundle-output-path", required=True)
    args = parser.parse_args()

    runner = GenericSourceRegistration()
    result = runner.register_from_spec_file(
        spec_path=args.spec_path,
        repository_root=args.repository_root,
    )
    bundle_path = runner.write_outputs(
        result,
        repository_root=args.repository_root,
        bundle_output_path=args.bundle_output_path,
    )
    print(json.dumps({
        "registration_status": result.bundle["registration_status"],
        "source_count": len(result.bundle["sources"]),
        "bundle_output_path": str(bundle_path),
        "sources": [
            {
                "document_id": source["document_id"],
                "authority_role": source["authority_role"],
                "candidate_count": source["evidence_candidate_count"],
            }
            for source in result.bundle["sources"]
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
