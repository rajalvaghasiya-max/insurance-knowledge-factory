"""Generic CLI for reviewed official-policy currentness evidence.

The operator supplies the reviewed product-page observation and rationale. This
wrapper records evidence through DocumentCurrentnessEvidenceRecord; it does not
set temporal status or authorize publication/entitlement.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from factory_core.governance.document_currentness_evidence import (
    DocumentCurrentnessEvidenceRecord,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record reviewed evidence that an official product page links the observed policy wording."
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--registration-path", required=True)
    parser.add_argument("--observation-record-path", required=True)
    parser.add_argument("--linked-document-url", required=True)
    parser.add_argument("--observed-text", required=True)
    parser.add_argument("--review-rationale", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--link-label", default="Policy Wording")
    args = parser.parse_args()

    reviewed_at = datetime.now(timezone.utc).isoformat()
    spec = {
        "schema_version": "1.0",
        "record_type": "document_currentness_evidence_record_v1",
        "reviewed_by_human": True,
        "registered_document": {"registration_path": args.registration_path},
        "source_observation": {"observation_record_path": args.observation_record_path},
        "evidence_items": [
            {
                "evidence_type": "official_product_page_document_link",
                "evidence_status": "supports_currentness_review",
                "verification": "retained_official_html_manual_review",
                "observed_text": args.observed_text,
                "evidence_reference": args.observation_record_path,
                "linked_document_url": args.linked_document_url,
                "link_label": args.link_label,
            }
        ],
        "reviewed_at": reviewed_at,
        "review_rationale": args.review_rationale,
    }

    policy = DocumentCurrentnessEvidenceRecord()
    result = policy.build(spec=spec, repository_root=Path(args.repository_root))
    output = policy.write_output(
        result,
        repository_root=Path(args.repository_root),
        output_path=args.output_path,
    )
    record = result.record
    print("=" * 70)
    print("OFFICIAL POLICY CURRENTNESS EVIDENCE")
    print("=" * 70)
    print(f"Output               : {output}")
    print(f"Registered version   : {record['registered_document']['document_version_id']}")
    print(f"Observation          : {record['source_observation']['observation_id']}")
    print(f"Evidence conclusion  : {record['currentness_evidence_conclusion']}")
    print(f"Positive evidence    : {record['positive_currentness_evidence_count']}")
    print("NOTE: evidence only; temporal decision remains separate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
