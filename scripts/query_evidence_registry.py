from __future__ import annotations

import argparse
import json

from knowledge_domains.health.evidence.evidence_registry import EvidenceRegistry


def main():
    parser = argparse.ArgumentParser(description="Query Evidence Registry.")
    parser.add_argument("--entity-id", required=True)
    parser.add_argument(
        "--document-type",
        action="append",
        dest="document_types",
        help="Filter by document type. Can be used multiple times.",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON result.")

    args = parser.parse_args()

    registry_service = EvidenceRegistry()
    result = registry_service.query(
        entity_id=args.entity_id,
        document_types=args.document_types,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print()
    print("=" * 70)
    print("EVIDENCE REGISTRY QUERY")
    print("=" * 70)
    print(f"Entity      : {result['entity_id']}")
    print(f"Documents   : {result['document_count']}")
    if result["document_types"]:
        print("Types       : " + ", ".join(result["document_types"]))

    for doc in result["documents"][:25]:
        print(
            f"[{doc['document_type']}] "
            f"[authority={doc['authority_score']}] "
            f"[{doc['evidence_role']}] "
            f"{doc['relative_path']}"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()
