"""CLI runner for P1.5a-0 document identity resolution overlays."""
from __future__ import annotations
import argparse
from pathlib import Path
from factory_core.governance.document_identity_resolution import DocumentIdentityResolutionOverlay

def main() -> int:
    parser = argparse.ArgumentParser(description="Build a non-mutating document identity resolution overlay.")
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()
    policy = DocumentIdentityResolutionOverlay()
    result = policy.build_from_spec_file(spec_path=Path(args.spec_path), repository_root=Path(args.repository_root))
    output = policy.write_output(result, repository_root=Path(args.repository_root), output_path=args.output_path)
    print("=" * 70)
    print("DOCUMENT IDENTITY RESOLUTION OVERLAY")
    print("=" * 70)
    print(f"Output : {output}")
    print(f"Product: {result.manifest['product_identity_reference']['entity_id']}")
    for item in result.manifest["documents"]:
        link = item["document_version_link"]
        decision = item["identity_resolution"]
        print(f"- {link['document_id']} | {decision['resolution_status']} | {decision['temporal_status']} | evidence_review={decision['evidence_review_eligibility']} | current_entitlement={decision['current_entitlement_publication_eligibility']}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
