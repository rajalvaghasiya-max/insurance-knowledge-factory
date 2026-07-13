from __future__ import annotations

import argparse
import json

from factory_core.canonical.generic_legal_condition_binding import GenericLegalConditionBinding


def main() -> int:
    parser = argparse.ArgumentParser(description="P2.5-H1 reviewed generic legal condition binding")
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    runner = GenericLegalConditionBinding()
    result = runner.bind_from_spec_file(spec_path=args.spec_path, repository_root=args.repository_root)
    output_path = runner.write_output(result, repository_root=args.repository_root, output_path=args.output_path)
    print(json.dumps({
        "binding_status": result.manifest["binding_status"],
        "assertion_count": len(result.manifest["assertions"]),
        "output_path": str(output_path),
        "assertion_types": [item["assertion_type"] for item in result.manifest["assertions"]],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
