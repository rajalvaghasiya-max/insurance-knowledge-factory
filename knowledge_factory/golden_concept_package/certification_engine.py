from __future__ import annotations

from typing import Any, Dict, List
from .package_models import PackageCertification, make_id, utc_now


class PackageCertificationEngine:
    def certify(self, concept_id: str, package_id: str, dependency: Dict[str, Any], consistency: Dict[str, Any], coverage_overall: str) -> PackageCertification:
        issues: List[str] = []
        if dependency["status"] == "FAIL":
            issues.extend([f"core_missing:{x}" for x in dependency.get("core_missing_assets", [])])
        if consistency["status"] == "FAIL":
            issues.extend(consistency.get("issues", []))
        if coverage_overall != "COMPLETE":
            issues.append(f"coverage:{coverage_overall}")
        if dependency["status"] == "FAIL" or consistency["status"] == "FAIL":
            status = "FAIL"
        elif coverage_overall != "COMPLETE":
            status = "PASS_WITH_GAPS"
        else:
            status = "PASS"
        score = 100
        if status == "PASS_WITH_GAPS":
            score = 75
        if status == "FAIL":
            score = 40
        payload = {"concept_id": concept_id, "package_id": package_id, "status": status, "issues": issues}
        return PackageCertification(
            certification_id=make_id("gccert", payload),
            package_id=package_id,
            concept_id=concept_id,
            status=status,
            score=score,
            checks={
                "dependency_status": dependency["status"],
                "consistency_status": consistency["status"],
                "coverage_overall": coverage_overall,
            },
            issues=issues,
            created_at=utc_now(),
        )
