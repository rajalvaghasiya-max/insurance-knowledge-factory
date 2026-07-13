from __future__ import annotations

import argparse
import json

from factory_core.governance.document_classification import DocumentClassificationPolicy


def main() -> int:
    parser = argparse.ArgumentParser(description="P2.5-F3 document classification and reuse-policy manifest")
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    runner = DocumentClassificationPolicy()
    result = runner.classify_from_spec_file(spec_path=args.spec_path, repository_root=args.repository_root)
    output = runner.write_output(result, repository_root=args.repository_root, output_path=args.output_path)
    print(json.dumps({
        "classification_status": result.manifest["classification_status"],
        "document_count": len(result.manifest["documents"]),
        "classifications": [
            {"document_id": item["document_id"], "classification": item["classification"], "reuse_action": item["reuse_action"]}
            for item in result.manifest["documents"]
        ],
        "output_path": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
