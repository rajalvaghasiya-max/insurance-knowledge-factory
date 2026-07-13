"""Build the governed Product Identity ↔ Document Version link registry."""
from __future__ import annotations

from knowledge_domains.product.identity.source_product_linkage import SourceProductLinkageBuilder


def main() -> None:
    result = SourceProductLinkageBuilder().build()
    report = result["report"]
    counts = report["provenance_status_counts"]
    print("=" * 70)
    print("SOURCE-TO-PRODUCT LINKAGE")
    print("=" * 70)
    print(f"Identities scanned : {report['identity_count_scanned']}")
    print(f"Links              : {report['link_count']}")
    print(f"Registry matched   : {counts['download_registry_verified']}")
    print(f"Legacy unmanaged   : {counts['locally_managed_unregistered']}")
    print(f"Local files missing: {counts['local_file_missing']}")
    print(f"Registry           : {result['registry_path']}")
    print(f"Report             : {result['report_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
