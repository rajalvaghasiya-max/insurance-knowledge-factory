"""CLI runner for P1.5a-1 product identity references."""
from __future__ import annotations
import argparse
from pathlib import Path
from factory_core.governance.product_identity_reference import ProductIdentityReference

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a non-mutating durable product identity reference record."
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    policy = ProductIdentityReference()
    result = policy.build_from_spec_file(
        spec_path=Path(args.spec_path),
        repository_root=Path(args.repository_root),
    )
    output = policy.write_output(
        result,
        repository_root=Path(args.repository_root),
        output_path=args.output_path,
    )
    identity = result.manifest["product_identity"]
    print("=" * 70)
    print("PRODUCT IDENTITY REFERENCE")
    print("=" * 70)
    print(f"Output : {output}")
    print(f"Product: {identity['entity_id']}")
    print(f"UIN    : {identity['uin']}")
    print(f"Status : {result.manifest['identity_resolution_status']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
