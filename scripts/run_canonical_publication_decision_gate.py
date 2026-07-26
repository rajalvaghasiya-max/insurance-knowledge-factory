from __future__ import annotations
import argparse
import json
from factory_core.canonical.canonical_publication_decision_gate import CanonicalPublicationDecisionGate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()
    gate = CanonicalPublicationDecisionGate()
    result = gate.decide_from_spec_file(spec_path=args.spec_path, repository_root=args.repository_root)
    output = gate.write_output(result, repository_root=args.repository_root, output_path=args.output_path)
    print(json.dumps({
        "decision_status": result.manifest["decision_status"],
        "eligible_assertion_count": len(result.manifest["decisions"]),
        "output_path": str(output),
        "publication_status": "unchanged_unpublished",
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
