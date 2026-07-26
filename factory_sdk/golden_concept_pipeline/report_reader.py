from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .pipeline_models import SourceDistillationReport


class DistillationReportReader:
    """Reads KDE distillation reports from files into GCMP source models."""

    def read_file(self, path: str | Path) -> SourceDistillationReport:
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return SourceDistillationReport.from_dict(data, source_path=str(p))

    def read_dir(self, path: str | Path, concept_id: str | None = None) -> List[SourceDistillationReport]:
        p = Path(path)
        reports: List[SourceDistillationReport] = []
        for file in sorted(p.glob("*_distillation_report.json")):
            report = self.read_file(file)
            if concept_id is None or report.concept_id == concept_id:
                reports.append(report)
        return reports
