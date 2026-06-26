"""
PolicyScna Factory SDK v1.2 — Factory Certification

Central certification object for all production lines.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CertificationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class CertificationGateResult:
    gate_name: str
    status: CertificationStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class FactoryCertification:
    certification_id: str
    asset_id: str
    engine: str
    production_line: str
    status: CertificationStatus
    quality_score: float
    gates: List[CertificationGateResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    certification_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "certification_id": self.certification_id,
            "asset_id": self.asset_id,
            "engine": self.engine,
            "production_line": self.production_line,
            "status": self.status.value,
            "quality_score": self.quality_score,
            "gates": [gate.to_dict() for gate in self.gates],
            "gates_passed": [gate.gate_name for gate in self.gates if gate.status == CertificationStatus.PASSED],
            "gates_failed": [gate.gate_name for gate in self.gates if gate.status == CertificationStatus.FAILED],
            "warnings": self.warnings,
            "errors": self.errors,
            "certification_version": self.certification_version,
        }

    @classmethod
    def from_gate_names(
        cls,
        *,
        certification_id: str,
        asset_id: str,
        engine: str,
        production_line: str,
        quality_score: float,
        gates_passed: Optional[List[str]] = None,
        gates_failed: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
    ) -> "FactoryCertification":
        gates: List[CertificationGateResult] = []
        for gate in gates_passed or []:
            gates.append(CertificationGateResult(gate_name=gate, status=CertificationStatus.PASSED))
        for gate in gates_failed or []:
            gates.append(CertificationGateResult(gate_name=gate, status=CertificationStatus.FAILED))

        status = CertificationStatus.PASSED
        if gates_failed or errors:
            status = CertificationStatus.FAILED
        elif warnings or quality_score < 90:
            status = CertificationStatus.NEEDS_REVIEW

        return cls(
            certification_id=certification_id,
            asset_id=asset_id,
            engine=engine,
            production_line=production_line,
            status=status,
            quality_score=quality_score,
            gates=gates,
            warnings=warnings or [],
            errors=errors or [],
        )
