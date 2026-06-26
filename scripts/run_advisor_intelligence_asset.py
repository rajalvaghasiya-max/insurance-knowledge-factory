import argparse
from pathlib import Path

from knowledge_factory.advisor_intelligence.advisor_intelligence_asset_builder import (
    AdvisorIntelligenceAssetBuilder,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--concept", default="copay")
    args = parser.parse_args()

    outputs = AdvisorIntelligenceAssetBuilder(Path.cwd()).build(args.concept)

    print("=" * 70)
    print("ADVISOR INTELLIGENCE ASSET")
    print("=" * 70)
    print(f"Concept        : {args.concept}")
    print(f"Status         : {outputs['status']}")
    print(f"Score          : {outputs['score']}")
    print(f"Asset          : {outputs['asset']}")
    print(f"Certification  : {outputs['certification']}")
    print(f"Summary        : {outputs['summary']}")
    print("=" * 70)


if __name__ == "__main__":
    main()