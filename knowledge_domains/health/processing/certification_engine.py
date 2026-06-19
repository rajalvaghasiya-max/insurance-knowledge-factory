from __future__ import annotations

from .processing_models import CertificationReport, stable_id, utc_now


class DepartmentCertificationEngine:
    """
    Department III — Document Processing
    Engine: Department Certification Engine

    Responsibility:
        Create a certification report for the manufactured asset before handover.
    """

    VERSION = "2.0"

    def certify(self, *, document_id: str, asset_id: str, validation: dict, quality_score: float) -> CertificationReport:
        passed_gates = validation.get("passed_gates", [])
        failed_gates = validation.get("failed_gates", [])
        status = "certified" if validation.get("status") == "passed" and quality_score >= 85 else "not_certified"
        if validation.get("status") == "passed" and quality_score >= 95:
            summary = "Department III asset is certified and ready for Department IV handover."
        elif status == "certified":
            summary = "Department III asset is certified with caution; review quality notes before high-stakes use."
        else:
            summary = "Department III asset is not certified; fix failed gates before Department IV handover."
        return CertificationReport(
            report_type="department_certification_report",
            report_id=stable_id("cert", f"document_processing|{document_id}|{asset_id}|{self.VERSION}"),
            report_version=self.VERSION,
            created_at=utc_now(),
            department="department_03_document_processing",
            document_id=document_id,
            asset_id=asset_id,
            certification_status=status,
            passed_gates=passed_gates,
            failed_gates=failed_gates,
            gate_results=validation.get("gate_results", {}),
            summary=summary,
        )
