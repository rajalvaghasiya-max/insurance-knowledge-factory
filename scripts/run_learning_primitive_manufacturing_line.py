"""Run Department V Learning Primitive Manufacturing Line."""

from __future__ import annotations

import argparse
from pathlib import Path

from knowledge_domains.health.understanding_manufacturing.learning_primitive_manufacturing_line import (
    LearningPrimitiveManufacturingLine,
)


DEFAULT_INPUT = Path("knowledge/factory/meaning_assets/copay_meaning_asset.json")
DEFAULT_OUTPUT = Path("knowledge/factory/learning_primitives")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Learning Primitive Manufacturing Line v1.0")
    parser.add_argument("--meaning-asset", default=str(DEFAULT_INPUT), help="Path to meaning asset JSON.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT), help="Directory for manufactured outputs.")
    parser.add_argument("--factory-version", default="1.0", help="Factory version to record.")
    args = parser.parse_args()

    input_path = Path(args.meaning_asset)
    output_dir = Path(args.output_dir)

    result = LearningPrimitiveManufacturingLine(
        input_path=input_path,
        output_dir=output_dir,
        factory_version=args.factory_version,
    ).run()

    print("\n" + "=" * 70)
    print("LEARNING PRIMITIVE MANUFACTURING LINE")
    print("=" * 70)
    print(f"Input : {input_path}")
    print(f"Output: {output_dir}")
    for key, path in result.items():
        print(f"{key.title():13}: {path}")


if __name__ == "__main__":
    main()
