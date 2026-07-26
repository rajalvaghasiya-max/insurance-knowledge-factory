"""
PolicyScna Factory SDK v1.0 — Base Production Line

A lightweight base class that enforces the PolicyScna manufacturing lifecycle:
Load -> Validate -> Manufacture -> Quality Check -> Certify -> Publish.

Future engines should inherit this class and implement only the small set of hooks.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .factory_sdk_hashing import stable_hash, stable_json_dumps
from .factory_sdk_models import (
    CertificationResult,
    CertificationStatus,
    FactoryEvent,
    ManufacturingReport,
    ProductionLineContract,
    QualityWarning,
    utc_now_iso,
)


class FactoryProductionLine(ABC):
    """Base class for deterministic PolicyScna production lines."""

    contract: ProductionLineContract

    def __init__(self, *, input_path: Path, output_dir: Path, factory_version: str = "1.0") -> None:
        self.input_path = Path(input_path)
        self.output_dir = Path(output_dir)
        self.factory_version = factory_version
        self._started_at: Optional[float] = None

    # ---------------------------------------------------------------------
    # Public lifecycle
    # ---------------------------------------------------------------------
    def run(self) -> Dict[str, Path]:
        self._started_at = time.perf_counter()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        raw_input = self.load()
        self.validate_input(raw_input)

        manufactured_asset = self.manufacture(raw_input)
        certification = self.certify(raw_input, manufactured_asset)
        report = self.build_report(raw_input, manufactured_asset, certification)
        event = self.build_event(manufactured_asset, certification)

        return self.publish(manufactured_asset, report, certification, event)

    # ---------------------------------------------------------------------
    # Standard stages
    # ---------------------------------------------------------------------
    def load(self) -> Dict[str, Any]:
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input asset not found: {self.input_path}")
        with self.input_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def validate_input(self, raw_input: Dict[str, Any]) -> None:
        if not isinstance(raw_input, dict):
            raise ValueError("Input asset must be a JSON object.")

    @abstractmethod
    def manufacture(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        """Manufacture exactly one asset type. Implemented by each production line."""

    def quality_check(self, raw_input: Dict[str, Any], manufactured_asset: Dict[str, Any]) -> Tuple[float, List[QualityWarning], List[str]]:
        warnings: List[QualityWarning] = []
        errors: List[str] = []
        quality_score = 100.0

        if not manufactured_asset:
            errors.append("Manufactured asset is empty.")
            quality_score = 0.0

        if manufactured_asset.get("department_boundary") != self.contract.department_boundary:
            errors.append("Department boundary mismatch.")
            quality_score = min(quality_score, 50.0)

        return quality_score, warnings, errors

    def certify(self, raw_input: Dict[str, Any], manufactured_asset: Dict[str, Any]) -> CertificationResult:
        gates_passed: List[str] = []
        gates_failed: List[str] = []
        quality_score, warnings, errors = self.quality_check(raw_input, manufactured_asset)

        # Gate: deterministic flag declared.
        if self.contract.deterministic:
            gates_passed.append("deterministic_declared")
        else:
            gates_failed.append("deterministic_declared")
            errors.append("Production line must declare deterministic=True unless explicitly exempted.")

        # Gate: one manufactured asset type.
        if manufactured_asset.get("asset_type") == self.contract.manufactures:
            gates_passed.append("asset_type_matches_contract")
        else:
            gates_failed.append("asset_type_matches_contract")
            errors.append(
                f"Expected asset_type={self.contract.manufactures}, got {manufactured_asset.get('asset_type')}"
            )

        # Gate: department boundary.
        if manufactured_asset.get("department_boundary") == self.contract.department_boundary:
            gates_passed.append("department_boundary_preserved")
        else:
            gates_failed.append("department_boundary_preserved")

        status = CertificationStatus.PASSED
        if errors:
            status = CertificationStatus.FAILED
        elif warnings or quality_score < 90:
            status = CertificationStatus.NEEDS_REVIEW

        return CertificationResult(
            validation_status=status,
            quality_score=quality_score,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            warnings=warnings,
            errors=errors,
        )

    def build_report(
        self,
        raw_input: Dict[str, Any],
        manufactured_asset: Dict[str, Any],
        certification: CertificationResult,
    ) -> Dict[str, Any]:
        report_id = stable_hash(
            {
                "engine": self.contract.engine_name,
                "input": raw_input,
                "output": manufactured_asset,
                "rules_version": self.contract.rules_version,
            },
            prefix="freport",
        )
        report = ManufacturingReport(
            report_id=report_id,
            report_type=f"{self.contract.production_line}_manufacturing_report",
            created_at=utc_now_iso(),
            engine=self.contract.engine_name,
            department=self.contract.department,
            production_line=self.contract.production_line,
            input_asset_count=1,
            output_asset_count=1,
            quality_score=certification.quality_score,
            validation_status=certification.validation_status,
            warnings=certification.warnings,
            errors=certification.errors,
            department_boundary=self.contract.department_boundary,
            next_stage=self.contract.customer_department,
            statistics=self.build_statistics(raw_input, manufactured_asset, certification),
        )
        return report.to_dict()

    def build_statistics(
        self,
        raw_input: Dict[str, Any],
        manufactured_asset: Dict[str, Any],
        certification: CertificationResult,
    ) -> Dict[str, Any]:
        return {
            "input_asset_type": raw_input.get("asset_type"),
            "output_asset_type": manufactured_asset.get("asset_type"),
            "contract": self.contract.to_dict(),
            "gates_passed": certification.gates_passed,
            "gates_failed": certification.gates_failed,
        }

    def build_event(self, manufactured_asset: Dict[str, Any], certification: CertificationResult) -> Dict[str, Any]:
        duration_ms: Optional[int] = None
        if self._started_at is not None:
            duration_ms = int((time.perf_counter() - self._started_at) * 1000)

        event = FactoryEvent(
            event_id=stable_hash(
                {
                    "engine": self.contract.engine_name,
                    "input_path": str(self.input_path),
                    "output_asset_id": manufactured_asset.get("asset_id"),
                    "rules_version": self.contract.rules_version,
                },
                prefix="fevent",
            ),
            event_type="production_line_completed",
            created_at=utc_now_iso(),
            engine=self.contract.engine_name,
            department=self.contract.department,
            production_line=self.contract.production_line,
            status=certification.validation_status.value,
            input_assets=[str(self.input_path)],
            output_assets=[manufactured_asset.get("asset_id", "unknown")],
            duration_ms=duration_ms,
            warnings=[w.message for w in certification.warnings],
            errors=certification.errors,
        )
        return event.to_dict()

    def publish(
        self,
        manufactured_asset: Dict[str, Any],
        report: Dict[str, Any],
        certification: CertificationResult,
        event: Dict[str, Any],
    ) -> Dict[str, Path]:
        asset_id = manufactured_asset.get("asset_id") or stable_hash(manufactured_asset, prefix="asset")
        base_name = f"{asset_id}_{self.contract.production_line}"

        asset_path = self.output_dir / f"{base_name}_asset.json"
        report_path = self.output_dir / f"{base_name}_report.json"
        certification_path = self.output_dir / f"{base_name}_certification.json"
        event_path = self.output_dir / f"{base_name}_event.json"

        self._write_json(asset_path, manufactured_asset)
        self._write_json(report_path, report)
        self._write_json(certification_path, certification.to_dict())
        self._write_json(event_path, event)

        return {
            "asset": asset_path,
            "report": report_path,
            "certification": certification_path,
            "event": event_path,
        }

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        path.write_text(stable_json_dumps(data, remove_volatile_keys=False) + "\n", encoding="utf-8")
