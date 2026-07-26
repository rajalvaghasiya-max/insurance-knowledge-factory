"""
PolicyScna Factory SDK v1.3 — Factory Inspector

The Factory Inspector is the governance layer for production lines.
It does not manufacture assets. It inspects whether manufactured outputs
respect Factory Engineering Standards (FES), Law 0, Law 1, and department
boundaries.

Design goal:
    Production lines should not certify themselves blindly.
    The SDK should inspect their asset, report, certification and event outputs
    using reusable, deterministic checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass, asdict
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from .factory_certification import (
    CertificationGateResult,
    CertificationStatus,
    FactoryCertification,
)


def _plain(value: Any) -> Any:
    """Convert dataclasses/enums/nested containers into plain Python data."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {k: _plain(v) for k, v in asdict(value).items()}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _plain(value.to_dict())
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _get(data: Any, key: str, default: Any = None) -> Any:
    plain = _plain(data)
    if isinstance(plain, Mapping):
        return plain.get(key, default)
    return default


@dataclass(frozen=True)
class InspectionIssue:
    """One issue discovered by the Factory Inspector."""

    severity: str
    gate_name: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "gate_name": self.gate_name,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class FactoryInspectionResult:
    """Result of inspecting one production-line run."""

    status: CertificationStatus
    gates: List[CertificationGateResult]
    issues: List[InspectionIssue] = field(default_factory=list)
    quality_score: float = 0.0
    inspector_version: str = "1.3"

    @property
    def gates_passed(self) -> List[str]:
        return [gate.gate_name for gate in self.gates if gate.status == CertificationStatus.PASSED]

    @property
    def gates_failed(self) -> List[str]:
        return [gate.gate_name for gate in self.gates if gate.status == CertificationStatus.FAILED]

    @property
    def warnings(self) -> List[str]:
        return [issue.message for issue in self.issues if issue.severity == "warning"]

    @property
    def errors(self) -> List[str]:
        return [issue.message for issue in self.issues if issue.severity == "error"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "quality_score": self.quality_score,
            "gates": [gate.to_dict() for gate in self.gates],
            "gates_passed": self.gates_passed,
            "gates_failed": self.gates_failed,
            "issues": [issue.to_dict() for issue in self.issues],
            "warnings": self.warnings,
            "errors": self.errors,
            "inspector_version": self.inspector_version,
        }

    def to_certification(
        self,
        *,
        certification_id: str,
        asset_id: str,
        engine: str,
        production_line: str,
    ) -> FactoryCertification:
        """Convert inspection result into a standard FactoryCertification."""
        return FactoryCertification(
            certification_id=certification_id,
            asset_id=asset_id,
            engine=engine,
            production_line=production_line,
            status=self.status,
            quality_score=self.quality_score,
            gates=self.gates,
            warnings=self.warnings,
            errors=self.errors,
            certification_version="1.3",
        )


class FactoryInspector:
    """Reusable governance checks for production-line outputs.

    The inspector is intentionally tolerant of both current SDK v1.x dict-style
    artifacts and future FactoryAsset/FactoryReport objects. This lets us adopt
    it without breaking the scanner SDK that already works.
    """

    inspector_version = "1.3"

    def inspect_run(
        self,
        *,
        contract: Any,
        asset: Any,
        report: Optional[Any] = None,
        certification: Optional[Any] = None,
        event: Optional[Any] = None,
        determinism_verified: Optional[bool] = None,
    ) -> FactoryInspectionResult:
        gates: List[CertificationGateResult] = []
        issues: List[InspectionIssue] = []

        def pass_gate(name: str, message: str = "", details: Optional[Dict[str, Any]] = None) -> None:
            gates.append(
                CertificationGateResult(
                    gate_name=name,
                    status=CertificationStatus.PASSED,
                    message=message,
                    details=details or {},
                )
            )

        def fail_gate(name: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
            gates.append(
                CertificationGateResult(
                    gate_name=name,
                    status=CertificationStatus.FAILED,
                    message=message,
                    details=details or {},
                )
            )
            issues.append(
                InspectionIssue(
                    severity="error",
                    gate_name=name,
                    message=message,
                    details=details or {},
                )
            )

        contract_d = _plain(contract)
        asset_d = _plain(asset)
        report_d = _plain(report) if report is not None else {}
        cert_d = _plain(certification) if certification is not None else {}
        event_d = _plain(event) if event is not None else {}

        expected_asset_type = contract_d.get("manufactures")
        actual_asset_type = asset_d.get("asset_type")
        if expected_asset_type and actual_asset_type == expected_asset_type:
            pass_gate("asset_type_matches_contract")
        else:
            fail_gate(
                "asset_type_matches_contract",
                "Asset type does not match production-line contract.",
                {"expected": expected_asset_type, "actual": actual_asset_type},
            )

        expected_boundary = contract_d.get("department_boundary")
        observed_boundaries = self._collect_values(
            [asset_d, report_d, cert_d, event_d],
            keys=("department_boundary",),
        )
        if expected_boundary and (not observed_boundaries or expected_boundary in observed_boundaries):
            pass_gate("department_boundary_preserved")
        else:
            fail_gate(
                "department_boundary_preserved",
                "Department boundary missing or changed in manufactured outputs.",
                {"expected": expected_boundary, "observed": sorted(observed_boundaries)},
            )

        if bool(contract_d.get("deterministic")):
            if determinism_verified is True:
                pass_gate("deterministic_verified")
            elif determinism_verified is False:
                fail_gate("deterministic_verified", "Determinism verification failed.")
            else:
                pass_gate(
                    "deterministic_declared",
                    "Production line declares determinism; runtime verification not supplied.",
                )
                issues.append(
                    InspectionIssue(
                        severity="warning",
                        gate_name="deterministic_verified",
                        message="Determinism was declared but not runtime-verified.",
                    )
                )
        else:
            fail_gate("deterministic_declared", "Production line contract is not deterministic.")

        if asset_d.get("asset_id") or asset_d.get("collection_id"):
            pass_gate("asset_identity_present")
        else:
            fail_gate("asset_identity_present", "Manufactured asset has no asset_id or collection_id.")

        source_trace = self._has_traceability(asset_d)
        if source_trace:
            pass_gate("traceability_present")
        else:
            fail_gate(
                "traceability_present",
                "Manufactured asset does not expose input/source traceability.",
            )

        if report is not None:
            if report_d.get("report_id") and report_d.get("report_type"):
                pass_gate("report_contract_present")
            else:
                fail_gate("report_contract_present", "Manufacturing report is missing report_id or report_type.")

        if certification is not None:
            cert_status = cert_d.get("validation_status") or cert_d.get("status")
            if cert_status in {"passed", CertificationStatus.PASSED.value}:
                pass_gate("certification_status_passed")
            else:
                fail_gate(
                    "certification_status_passed",
                    "Certification did not pass.",
                    {"status": cert_status},
                )

        if event is not None:
            if event_d.get("event_type") and event_d.get("status"):
                pass_gate("event_contract_present")
            else:
                fail_gate("event_contract_present", "Factory event is missing event_type or status.")

        quality_score = self._derive_quality_score(asset_d, report_d, cert_d)
        if quality_score >= 90:
            pass_gate("quality_threshold_met", details={"quality_score": quality_score})
        else:
            issues.append(
                InspectionIssue(
                    severity="warning",
                    gate_name="quality_threshold_met",
                    message="Quality score is below the default Factory threshold of 90.",
                    details={"quality_score": quality_score},
                )
            )

        status = CertificationStatus.PASSED
        if any(g.status == CertificationStatus.FAILED for g in gates):
            status = CertificationStatus.FAILED
        elif any(issue.severity == "warning" for issue in issues):
            status = CertificationStatus.NEEDS_REVIEW

        return FactoryInspectionResult(
            status=status,
            gates=gates,
            issues=issues,
            quality_score=quality_score,
            inspector_version=self.inspector_version,
        )

    @staticmethod
    def _collect_values(items: Iterable[Any], *, keys: Sequence[str]) -> set[str]:
        values: set[str] = set()

        def walk(value: Any) -> None:
            if isinstance(value, Mapping):
                for k, v in value.items():
                    if k in keys and isinstance(v, str):
                        values.add(v)
                    walk(v)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        for item in items:
            walk(item)
        return values

    @staticmethod
    def _has_traceability(asset: Mapping[str, Any]) -> bool:
        if asset.get("input_assets") or asset.get("source_evidence"):
            return True
        if asset.get("processed_document_asset_id") or asset.get("document_id"):
            return True
        components = asset.get("components")
        if isinstance(components, list) and components:
            sample = components[:10]
            return any(
                isinstance(component, Mapping)
                and (
                    component.get("processed_document_asset_id")
                    or component.get("document_id")
                    or component.get("source")
                )
                for component in sample
            )
        return False

    @staticmethod
    def _derive_quality_score(
        asset: Mapping[str, Any],
        report: Mapping[str, Any],
        certification: Mapping[str, Any],
    ) -> float:
        for container in (certification, report, asset.get("certification", {}), asset.get("quality", {})):
            value = container.get("quality_score") if isinstance(container, Mapping) else None
            if isinstance(value, (int, float)):
                return float(value)
        return 0.0
