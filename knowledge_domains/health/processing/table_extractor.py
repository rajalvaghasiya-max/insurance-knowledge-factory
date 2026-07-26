from __future__ import annotations

import re

from .processing_models import ProcessedTable, SourceLocation, stable_id


class TableExtractionEngine:
    """
    Department III — Document Processing
    Engine: Table Extraction Engine v2.0

    Responsibility:
        Extract simple text tables from normalized content without interpreting values.
    """

    VERSION = "2.0"

    def extract(self, text: str, *, document_id: str) -> list[ProcessedTable]:
        lines = text.splitlines()
        blocks: list[tuple[int, int, list[str]]] = []
        current: list[str] = []
        start_idx: int | None = None

        for idx, line in enumerate(lines):
            if self.is_table_line(line):
                if start_idx is None:
                    start_idx = idx
                current.append(line.rstrip())
            else:
                if len(current) >= 2 and start_idx is not None:
                    blocks.append((start_idx, idx, current))
                current = []
                start_idx = None

        if len(current) >= 2 and start_idx is not None:
            blocks.append((start_idx, len(lines), current))

        tables: list[ProcessedTable] = []
        for order, (start, end, block) in enumerate(blocks, start=1):
            rows = [self.split_row(line) for line in block]
            max_cols = max((len(row) for row in rows), default=0)
            if max_cols < 2:
                continue
            loc = SourceLocation(document_id=document_id, start_line=start + 1, end_line=end)
            tables.append(
                ProcessedTable(
                    table_id=stable_id("tbl", f"{document_id}|{start+1}|{end}|{'|'.join(block[:2])}"),
                    order=order,
                    rows=rows,
                    row_count=len(rows),
                    column_count=max_cols,
                    source_location=loc,
                    extraction_method="heuristic_text_table_v2",
                    confidence=self.estimate_confidence(rows),
                )
            )
        return tables

    def is_table_line(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if "|" in stripped and stripped.count("|") >= 1:
            return True
        if re.search(r"\S\s{2,}\S", stripped) and len(stripped.split()) >= 3:
            return True
        if re.match(r"^\s*(?:Sr\s*No\.?|No\.|Name|Description|Type|Illness|Treatment|Body System)\b", stripped, re.IGNORECASE):
            return True
        return False

    def split_row(self, line: str) -> list[str]:
        if "|" in line:
            return [cell.strip() for cell in line.strip("|").split("|")]
        return [cell.strip() for cell in re.split(r"\s{2,}", line.strip()) if cell.strip()]

    def estimate_confidence(self, rows: list[list[str]]) -> float:
        if not rows:
            return 0.0
        widths = [len(row) for row in rows]
        consistency = widths.count(max(set(widths), key=widths.count)) / len(widths)
        return round(0.55 + (0.4 * consistency), 3)
