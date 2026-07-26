from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .gmvs_models import GMVSReport


class GMVSReportWriter:
    """Writes GMVS reports as JSON and a readable text summary."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def write(self, report: GMVSReport) -> tuple[Path, Path]:
        output_dir = (
            self.repo_root
            / "knowledge"
            / "factory"
            / "gmvs"
            / report.concept_id
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / "gmvs_report.json"
        summary_path = output_dir / "gmvs_summary.txt"

        self._write_json(json_path, report)
        self._write_summary(summary_path, report)

        return json_path, summary_path

    @staticmethod
    def _write_json(output_path: Path, report: GMVSReport) -> None:
        output_path.write_text(
            json.dumps(asdict(report), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _write_summary(output_path: Path, report: GMVSReport) -> None:
        lines = [
            "=" * 70,
            "GMVS — GOLDEN MANUFACTURING VALIDATION SYSTEM",
            "=" * 70,
            f"Report ID           : {report.report_id}",
            f"Concept             : {report.concept_name} ({report.concept_id})",
            f"GMVS Version        : {report.version}",
            f"Factory Version     : {report.factory_version}",
            f"Validation Scope    : {report.validation_scope}",
            f"Created At          : {report.created_at}",

            "",
            "VALIDATION RESULTS",
            "-" * 70,
            (
                f"Architecture        : {report.architecture_validation.status} "
                f"({report.architecture_validation.score})"
            ),
            (
                f"Readiness           : {report.readiness_validation.status} "
                f"({report.readiness_validation.score})"
            ),
            (
                f"Manufacturing       : {report.manufacturing_validation.status} "
                f"({report.manufacturing_validation.score})"
            ),
            (
                f"Reuse               : {report.reuse_analysis.status} "
                f"({report.reuse_analysis.score})"
            ),
            (
                f"Governance          : {report.governance_validation.status} "
                f"({report.governance_validation.score})"
            ),
            "",
            "FACTORY SCORECARD",
            "-" * 70,
            f"Factory Stability   : {report.scorecard.factory_stability_score}",
            f"Factory Maturity    : {report.scorecard.factory_maturity}",
            f"Overall Rating      : {report.scorecard.overall_rating}",
            f"Manufacturing State : {report.scorecard.manufacturing_status}",
            "",
            "RECOMMENDATIONS",
            "-" * 70,
        ]

        for index, recommendation in enumerate(report.recommendations, start=1):
            lines.append(f"{index}. {recommendation}")

        lines.extend(
            [
                "",
                f"GMVS Certification : {report.certification_status}",
                "=" * 70,
            ]
        )

        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
