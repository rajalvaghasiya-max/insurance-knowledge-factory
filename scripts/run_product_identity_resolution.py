"""Build the verified Product Identity Registry from product intelligence outputs."""

from __future__ import annotations

from knowledge_domains.product.identity.product_identity_resolver import (
    ProductIdentityRegistryBuilder,
)


def main() -> None:
    result = ProductIdentityRegistryBuilder().build()
    report = result["report"]
    counts = report["status_counts"]

    print("=" * 70)
    print("PRODUCT IDENTITY RESOLUTION")
    print("=" * 70)
    print(f"Scanned   : {report['scanned_intelligence_files']}")
    print(f"Verified  : {counts['verified']}")
    print(f"Probable  : {counts['probable']}")
    print(f"Ambiguous : {counts['ambiguous']}")
    print(f"Unresolved: {counts['unresolved']}")
    print(f"Registry  : {result['registry_path']}")
    print(f"Report    : {result['report_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
