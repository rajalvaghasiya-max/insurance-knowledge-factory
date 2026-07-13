"""Create a Meaning Asset from a governed generic concept record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.concept_knowledge.governed_concept_to_meaning_asset import (
    GovernedConceptToMeaningAssetAdapter,
)


DEFAULT_INPUT = Path(
    "knowledge/factory/generic_concepts/deductible/"
    "governed_generic_concept_record_v0_2.json"
)
DEFAULT_OUTPUT = Path(
    "knowledge/factory/meaning_assets/deductible_meaning_asset.json"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adapt a governed generic concept record to Meaning Asset v1.0"
    )
    parser.add_argument(
        "--input-path",
        default=str(DEFAULT_INPUT),
        help="Governed generic concept record JSON.",
    )
    parser.add_argument(
        "--output-path",
        default=str(DEFAULT_OUTPUT),
        help="Meaning Asset JSON output.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)

    if not input_path.is_file():
        raise FileNotFoundError(input_path)

    record = json.loads(input_path.read_text(encoding="utf-8"))
    asset = GovernedConceptToMeaningAssetAdapter.build(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asset, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("=" * 72)
    print("GOVERNED CONCEPT TO MEANING ASSET")
    print("=" * 72)
    print(f"Concept          : {asset['concept_id']}")
    print(f"Meaning Asset ID : {asset['asset_id']}")
    print(f"Governed Record  : {asset['governance']['source_governed_record_id']}")
    print(f"Evidence Refs    : {len(asset['evidence_refs'])}")
    print(f"Publication      : {asset['governance']['publication_state']}")
    print(f"Customer Answer  : {asset['governance']['customer_answer_state']}")
    print(f"Output           : {output_path}")


if __name__ == "__main__":
    main()
