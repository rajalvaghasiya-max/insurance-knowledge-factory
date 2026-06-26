from __future__ import annotations

from typing import Dict, Any
from .package_models import AssetRecord, GoldenConceptPackage, PackageCertification, CoverageAnalysis, make_id, utc_now


class GoldenConceptPackageBuilder:
    def build(self, concept_id: str, concept_name: str, inventory: Dict[str, AssetRecord], consistency: Dict[str, Any], coverage: CoverageAnalysis, gap_analysis: Dict[str, Any], certification: PackageCertification) -> GoldenConceptPackage:
        payload = {
            "concept_id": concept_id,
            "inventory": {k: v.asset_id or v.path or v.status for k, v in inventory.items()},
            "certification_status": certification.status,
        }
        package_id = make_id("gcpkg", payload)
        maturity = self._maturity(certification.status, coverage.overall)
        return GoldenConceptPackage(
            package_id=package_id,
            concept_id=concept_id,
            concept_name=concept_name,
            version="1.0",
            created_at=utc_now(),
            asset_inventory=inventory,
            cross_asset_consistency=consistency,
            coverage_analysis=coverage,
            gap_analysis=gap_analysis,
            maturity_level=maturity,
            package_certification=certification,
            factory_signature={
                "factory": "PolicyScna Knowledge Factory",
                "assembly_line": "GoldenConceptPackageAssembler",
                "version": "1.0",
                "deterministic": True,
                "created_at": utc_now(),
            },
        )

    def _maturity(self, certification_status: str, coverage_overall: str) -> str:
        if certification_status == "PASS" and coverage_overall == "COMPLETE":
            return "GOLD"
        if certification_status == "PASS_WITH_GAPS":
            return "SILVER"
        return "BRONZE"
