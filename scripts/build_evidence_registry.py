from __future__ import annotations

import argparse

from knowledge_domains.health.evidence.evidence_registry import EvidenceRegistry


def main():
    parser = argparse.ArgumentParser(description="Build Evidence Registry for raw evidence artifacts.")
    parser.add_argument(
        "--entity-id",
        action="append",
        dest="entity_ids",
        help="Entity ID to include. Can be used multiple times. Defaults to known router entities.",
    )
    parser.add_argument(
        "--base-roots",
        nargs="*",
        default=["knowledge", "parsed", "archive"],
        help="Base roots to scan.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Build registry in memory but do not write JSON file.",
    )

    args = parser.parse_args()

    registry_service = EvidenceRegistry()
    registry = registry_service.build_registry(
        entity_ids=args.entity_ids,
        base_roots=args.base_roots,
        write=not args.no_write,
    )

    print()
    print("=" * 70)
    print("EVIDENCE REGISTRY")
    print("=" * 70)
    print(f"Version     : {registry['registry_version']}")
    print(f"Generated   : {registry['generated_at']}")
    print(f"Entities    : {', '.join(registry['entity_ids'])}")
    print(f"Documents   : {registry['document_count']}")
    print(f"Rejected    : {registry['rejected_counts']}")
    print(f"Output      : {registry_service.paths.registry_path}")

    for doc in registry["documents"][:25]:
        entities = ", ".join(doc.get("entity_ids", []))
        print(
            f"[{doc['document_type']}] "
            f"[authority={doc['authority_score']}] "
            f"[{entities}] "
            f"{doc['relative_path']}"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()
