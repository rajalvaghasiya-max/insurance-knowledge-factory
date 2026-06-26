"""
PolicyScna Factory SDK v1.0 — Determinism Utilities

Utility for running a production line twice and comparing deterministic outputs.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Type

from factory_sdk_hashing import canonicalize_for_hash, stable_hash
from factory_production_line import FactoryProductionLine


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def compare_assets_ignoring_volatile(first: Dict[str, Any], second: Dict[str, Any]) -> bool:
    return canonicalize_for_hash(first, remove_volatile_keys=True) == canonicalize_for_hash(second, remove_volatile_keys=True)


def run_determinism_check(
    production_line_cls: Type[FactoryProductionLine],
    *,
    input_path: Path,
    temp_dir: Path,
    factory_version: str = "1.0",
) -> Dict[str, Any]:
    """Run the same production line twice and compare manufactured assets."""
    first_dir = temp_dir / "determinism_first"
    second_dir = temp_dir / "determinism_second"

    if first_dir.exists():
        shutil.rmtree(first_dir)
    if second_dir.exists():
        shutil.rmtree(second_dir)

    first = production_line_cls(input_path=input_path, output_dir=first_dir, factory_version=factory_version).run()
    second = production_line_cls(input_path=input_path, output_dir=second_dir, factory_version=factory_version).run()

    first_asset = load_json(first["asset"])
    second_asset = load_json(second["asset"])
    passed = compare_assets_ignoring_volatile(first_asset, second_asset)

    return {
        "determinism_status": "passed" if passed else "failed",
        "first_asset_path": str(first["asset"]),
        "second_asset_path": str(second["asset"]),
        "first_hash": stable_hash(first_asset, prefix="asset", remove_volatile_keys=True),
        "second_hash": stable_hash(second_asset, prefix="asset", remove_volatile_keys=True),
    }
