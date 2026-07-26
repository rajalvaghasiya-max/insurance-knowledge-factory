"""Run Department V Learning Path Manufacturing Line."""

from __future__ import annotations

import argparse
from pathlib import Path

from knowledge_domains.health.understanding_manufacturing.learning_path_manufacturing_line import (
    LearningPathManufacturingLine,
)


DEFAULT_INPUT_DIR = Path("knowledge/factory/learning_primitives")
DEFAULT_OUTPUT = Path("knowledge/factory/learning_paths")


def _resolve_default_input() -> Path:
    candidates = sorted(DEFAULT_INPUT_DIR.glob("*_learning_primitive_manufacturing_asset.json"))
    if not candidates:
        raise FileNotFoundError(
            f"No learning primitive asset found in {DEFAULT_INPUT_DIR}. "
            "Run: python -m scripts.run_learning_primitive_manufacturing_line first, "
            "or pass --learning-primitive-asset explicitly."
        )
    return candidates[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Learning Path Manufacturing Line v1.0")
    parser.add_argument(
        "--learning-primitive-asset",
        default=None,
        help="Path to learning primitive collection JSON. Defaults to latest asset in knowledge/factory/learning_primitives.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT), help="Directory for manufactured outputs.")
    parser.add_argument("--factory-version", default="1.0", help="Factory version to record.")
    args = parser.parse_args()

    input_path = Path(args.learning_primitive_asset) if args.learning_primitive_asset else _resolve_default_input()
    output_dir = Path(args.output_dir)

    result = LearningPathManufacturingLine(
        input_path=input_path,
        output_dir=output_dir,
        factory_version=args.factory_version,
    ).run()

    print("\n" + "=" * 70)
    print("LEARNING PATH MANUFACTURING LINE")
    print("=" * 70)
    print(f"Input : {input_path}")
    print(f"Output: {output_dir}")
    for key, path in result.items():
        print(f"{key.title():13}: {path}")


if __name__ == "__main__":
    main()
