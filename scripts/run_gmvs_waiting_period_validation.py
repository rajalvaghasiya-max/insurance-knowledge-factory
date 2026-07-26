"""Run GMVS-001: Waiting Period through Department V.

This validation runner intentionally does not modify Department V engines.
It runs the existing D5.2, D5.3 and D5.4 production lines using a
Waiting Period golden meaning asset and writes a small validation summary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from knowledge_domains.health.understanding_manufacturing.learning_primitive_manufacturing_line import (
    LearningPrimitiveManufacturingLine,
)
from knowledge_domains.health.understanding_manufacturing.learning_path_manufacturing_line import (
    LearningPathManufacturingLine,
)
from knowledge_domains.health.understanding_manufacturing.understanding_asset_manufacturing_line import (
    UnderstandingAssetManufacturingLine,
)

MEANING_ASSET = Path(
    "knowledge/factory/golden_concepts/waiting_period/waiting_period_meaning_asset.json"
)
PRIMITIVE_OUTPUT_DIR = Path("knowledge/factory/golden_concepts/waiting_period/learning_primitives")
PATH_OUTPUT_DIR = Path("knowledge/factory/golden_concepts/waiting_period/learning_paths")
UNDERSTANDING_OUTPUT_DIR = Path("knowledge/factory/golden_concepts/waiting_period/understanding_assets")
SUMMARY_OUTPUT = Path("knowledge/factory/golden_concepts/waiting_period/gmvs_waiting_period_validation_summary.json")


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _result_asset_path(result: Dict[str, Path]) -> Path:
    # FactoryProductionLine returns asset/report/certification/event keys.
    asset_path = result.get("asset") or result.get("Asset")
    if not asset_path:
        raise RuntimeError(f"Production line result did not include asset path: {result}")
    return Path(asset_path)


def _cert_path(result: Dict[str, Path]) -> Path:
    cert_path = result.get("certification") or result.get("Certification")
    if not cert_path:
        raise RuntimeError(f"Production line result did not include certification path: {result}")
    return Path(cert_path)


def main() -> None:
    if not MEANING_ASSET.exists():
        raise FileNotFoundError(
            f"Missing Waiting Period meaning asset: {MEANING_ASSET}. "
            "Copy the GMVS-001 package into repo root first."
        )

    PRIMITIVE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PATH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    UNDERSTANDING_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    primitive_result = LearningPrimitiveManufacturingLine(
        input_path=MEANING_ASSET,
        output_dir=PRIMITIVE_OUTPUT_DIR,
        factory_version="1.0",
    ).run()
    primitive_asset = _result_asset_path(primitive_result)

    path_result = LearningPathManufacturingLine(
        input_path=primitive_asset,
        output_dir=PATH_OUTPUT_DIR,
        factory_version="1.0",
    ).run()
    path_asset = _result_asset_path(path_result)

    understanding_result = UnderstandingAssetManufacturingLine(
        meaning_asset_path=MEANING_ASSET,
        learning_primitive_asset_path=primitive_asset,
        learning_path_asset_path=path_asset,
        output_dir=UNDERSTANDING_OUTPUT_DIR,
        factory_version="1.0",
    ).run()
    understanding_asset = _result_asset_path(understanding_result)

    primitive_payload = _load_json(primitive_asset)
    path_payload = _load_json(path_asset)
    understanding_payload = _load_json(understanding_asset)
    primitive_cert = _load_json(_cert_path(primitive_result))
    path_cert = _load_json(_cert_path(path_result))
    understanding_cert = _load_json(_cert_path(understanding_result))

    summary = {
        "validation_id": "gmvs_001_waiting_period",
        "concept_id": "waiting_period",
        "concept_name": "Waiting Period",
        "objective": "Validate Department V on a time-based insurance concept without architecture changes.",
        "architecture_changes_required": 0,
        "outputs": {
            "meaning_asset": str(MEANING_ASSET),
            "learning_primitive_asset": str(primitive_asset),
            "learning_path_asset": str(path_asset),
            "understanding_asset": str(understanding_asset),
        },
        "counts": {
            "primitive_count": len(primitive_payload.get("primitives", [])),
            "path_count": len(path_payload.get("paths", [])),
            "learning_outcome_count": len(understanding_payload.get("learning_outcomes", [])),
        },
        "primitive_types": [p.get("primitive_type") for p in primitive_payload.get("primitives", [])],
        "path_types": [p.get("path_type") for p in path_payload.get("paths", [])],
        "certifications": {
            "learning_primitives": primitive_cert,
            "learning_paths": path_cert,
            "understanding_asset": understanding_cert,
        },
        "validation_notes": [
            "No Department V engine was modified for this validation run.",
            "If path certification is needs_review due missing primitive types, record that as a GMVS discovery rather than patching immediately.",
            "Waiting Period is expected to reveal whether timeline-oriented primitives are needed in a future rules enhancement.",
        ],
    }
    SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False, sort_keys=True)

    print("\n" + "=" * 70)
    print("GMVS-001 — WAITING PERIOD VALIDATION")
    print("=" * 70)
    print(f"Meaning Asset       : {MEANING_ASSET}")
    print(f"Primitive Asset     : {primitive_asset}")
    print(f"Learning Path Asset : {path_asset}")
    print(f"Understanding Asset : {understanding_asset}")
    print(f"Summary             : {SUMMARY_OUTPUT}")
    print("-" * 70)
    print(f"Primitive Count     : {summary['counts']['primitive_count']}")
    print(f"Path Count          : {summary['counts']['path_count']}")
    print(f"Architecture Changes: {summary['architecture_changes_required']}")


if __name__ == "__main__":
    main()
