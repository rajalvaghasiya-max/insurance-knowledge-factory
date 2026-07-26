"""
Example production line for Factory SDK v1.0.

This is intentionally simple. It proves the SDK lifecycle works before we refactor
real Department III/IV engines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from factory_production_line import FactoryProductionLine
from factory_sdk_hashing import stable_hash
from factory_sdk_models import ProductionLineContract, utc_now_iso


class EchoProductionLine(FactoryProductionLine):
    contract = ProductionLineContract(
        engine_name="EchoProductionLine",
        department="factory_sdk_examples",
        production_line="echo_asset_manufacturing",
        consumes="example_input_asset",
        manufactures="example_echo_asset",
        customer_department="factory_sdk_tests",
        engine_version="1.0",
        rules_version="1.0",
        schema_version="example_echo_asset_v1.0",
        deterministic=True,
        certification_required=True,
        department_boundary="example_only_no_business_logic",
    )

    def manufacture(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "input_asset_id": raw_input.get("asset_id", "unknown"),
            "content": raw_input.get("content", {}),
            "rules_version": self.contract.rules_version,
        }
        asset_id = stable_hash(payload, prefix="echo")
        return {
            "asset_id": asset_id,
            "asset_type": self.contract.manufactures,
            "schema_version": self.contract.schema_version,
            "engine_version": self.contract.engine_version,
            "rules_version": self.contract.rules_version,
            "factory_version": self.factory_version,
            "manufactured_at": utc_now_iso(),
            "manufactured_by": self.contract.engine_name,
            "input_assets": [raw_input.get("asset_id", str(self.input_path))],
            "source_evidence": raw_input.get("source_evidence", []),
            "status": "active",
            "department_boundary": self.contract.department_boundary,
            "payload": payload,
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Factory SDK echo production line.")
    parser.add_argument("--input", required=True, help="Path to example input JSON.")
    parser.add_argument("--output-dir", required=True, help="Directory for manufactured outputs.")
    args = parser.parse_args()

    result = EchoProductionLine(input_path=Path(args.input), output_dir=Path(args.output_dir)).run()
    for name, path in result.items():
        print(f"{name:14}: {path}")
