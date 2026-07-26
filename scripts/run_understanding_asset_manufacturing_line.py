"""Run Department V Understanding Asset Manufacturing Line."""

from __future__ import annotations

import argparse
from pathlib import Path

from knowledge_domains.health.understanding_manufacturing.understanding_asset_manufacturing_line import (
    UnderstandingAssetManufacturingLine,
)


DEFAULT_MEANING_DIR = Path("knowledge/factory/meaning_assets")
DEFAULT_PRIMITIVE_DIR = Path("knowledge/factory/learning_primitives")
DEFAULT_PATH_DIR = Path("knowledge/factory/learning_paths")
DEFAULT_OUTPUT = Path("knowledge/factory/understanding_assets")


def _latest(pattern_dir: Path, pattern: str, instruction: str) -> Path:
    candidates = sorted(pattern_dir.glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"No matching asset found in {pattern_dir}. {instruction}")
    return candidates[-1]


def _resolve_meaning_asset() -> Path:
    return _latest(
        DEFAULT_MEANING_DIR,
        "*meaning_asset*.json",
        "Add a meaning asset or pass --meaning-asset explicitly.",
    )


def _resolve_learning_primitive_asset() -> Path:
    return _latest(
        DEFAULT_PRIMITIVE_DIR,
        "*_learning_primitive_manufacturing_asset.json",
        "Run: python -m scripts.run_learning_primitive_manufacturing_line first, or pass --learning-primitive-asset.",
    )


def _resolve_learning_path_asset() -> Path:
    return _latest(
        DEFAULT_PATH_DIR,
        "*_learning_path_manufacturing_asset.json",
        "Run: python -m scripts.run_learning_path_manufacturing_line first, or pass --learning-path-asset.",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Understanding Asset Manufacturing Line v1.0")
    parser.add_argument("--meaning-asset", default=None, help="Path to meaning asset JSON.")
    parser.add_argument("--learning-primitive-asset", default=None, help="Path to learning primitive collection JSON.")
    parser.add_argument("--learning-path-asset", default=None, help="Path to learning path collection JSON.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT), help="Directory for manufactured outputs.")
    parser.add_argument("--factory-version", default="1.0", help="Factory version to record.")
    args = parser.parse_args()

    meaning_asset_path = Path(args.meaning_asset) if args.meaning_asset else _resolve_meaning_asset()
    primitive_asset_path = Path(args.learning_primitive_asset) if args.learning_primitive_asset else _resolve_learning_primitive_asset()
    path_asset_path = Path(args.learning_path_asset) if args.learning_path_asset else _resolve_learning_path_asset()
    output_dir = Path(args.output_dir)

    result = UnderstandingAssetManufacturingLine(
        meaning_asset_path=meaning_asset_path,
        learning_primitive_asset_path=primitive_asset_path,
        learning_path_asset_path=path_asset_path,
        output_dir=output_dir,
        factory_version=args.factory_version,
    ).run()

    print("\n" + "=" * 70)
    print("UNDERSTANDING ASSET MANUFACTURING LINE")
    print("=" * 70)
    print(f"Meaning Asset            : {meaning_asset_path}")
    print(f"Learning Primitive Asset : {primitive_asset_path}")
    print(f"Learning Path Asset      : {path_asset_path}")
    print(f"Output                   : {output_dir}")
    for key, path in result.items():
        print(f"{key.title():13}: {path}")


if __name__ == "__main__":
    main()
