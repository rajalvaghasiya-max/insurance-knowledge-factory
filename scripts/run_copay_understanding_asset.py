from __future__ import annotations

from knowledge_domains.health.understanding.understanding_asset_builder import build_copay_understanding_asset


def main() -> None:
    outputs = build_copay_understanding_asset(".")
    print("=" * 70)
    print("COPAY UNDERSTANDING ASSET")
    print("=" * 70)
    print("Status        : PASS")
    print(f"Asset         : {outputs['asset']}")
    print(f"Certification : {outputs['certification']}")
    print(f"Event         : {outputs['event']}")
    print(f"Summary       : {outputs['summary']}")


if __name__ == "__main__":
    main()
