"""CLI runner for P2.6-A generic feature applicability reviews."""
from __future__ import annotations
import argparse
import json
from factory_core.canonical.feature_applicability import FeatureApplicabilityReviewer


def main() -> int:
    parser = argparse.ArgumentParser(description='Create a read-only generic feature applicability assessment.')
    parser.add_argument('--repository-root', required=True)
    parser.add_argument('--spec-path', required=True)
    parser.add_argument('--output-path', required=True)
    args = parser.parse_args()
    reviewer = FeatureApplicabilityReviewer()
    result = reviewer.review_from_spec_file(spec_path=args.spec_path, repository_root=args.repository_root)
    output = reviewer.write_output(result, repository_root=args.repository_root, output_path=args.output_path)
    print(json.dumps({
        'assessment_status': result.assessment['assessment_status'],
        'feature_count': len(result.assessment['features']),
        'binding_eligible_feature_count': sum(1 for f in result.assessment['features'] if f['eligible_for_evidence_binding']),
        'output_path': str(output),
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
