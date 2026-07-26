from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DocumentReaderEngine:
    """
    Department III — Document Processing
    Engine: Document Reader Engine v2.0

    Responsibility:
        Read source content into raw text and page units using deterministic methods.

    Boundary:
        This engine reads content only. It does not interpret insurance meaning.
    """

    VERSION = "2.0"

    SUPPORTED_SUFFIXES = {".json", ".txt", ".md", ".html", ".htm"}

    def read(self, loaded_document: dict[str, Any]) -> dict[str, Any]:
        path: Path = loaded_document["path"]
        suffix = loaded_document["suffix"]

        if suffix not in self.SUPPORTED_SUFFIXES:
            raise ValueError(
                f"Unsupported source type for v2.0: {suffix}. "
                "PDF/OCR support should be added as a dedicated reader engine."
            )

        raw = path.read_text(encoding="utf-8", errors="ignore")

        if suffix == ".json":
            text, pages, json_kind, warnings = self.json_to_text_and_pages(raw)
            return {
                "raw_text": text,
                "pages": pages,
                "reader_type": "json_reader_v2",
                "json_kind": json_kind,
                "warnings": warnings,
            }

        return {
            "raw_text": raw,
            "pages": [{"page_number": 1, "text": raw}],
            "reader_type": "text_reader_v2",
            "json_kind": None,
            "warnings": [],
        }

    def json_to_text_and_pages(self, raw: str) -> tuple[str, list[dict[str, Any]], str, list[dict[str, str]]]:
        try:
            data = json.loads(raw)
        except Exception as exc:
            return raw, [{"page_number": 1, "text": raw}], "invalid_json_text_fallback", [
                {"warning_type": "invalid_json", "severity": "medium", "message": str(exc)}
            ]

        if isinstance(data, dict):
            pages = self.extract_pages(data)
            if pages:
                text = "\n".join(page["text"] for page in pages if page.get("text"))
                return text, pages, "json_collection:pages", []

            for key in ("text", "full_text", "content", "raw_text", "markdown"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value, [{"page_number": 1, "text": value}], f"json_field:{key}", []

            for key in ("sections", "clauses"):
                value = data.get(key)
                if isinstance(value, list) and value:
                    text = self.flatten_json_to_text(value)
                    return text, [{"page_number": 1, "text": text}], f"json_collection:{key}", []

        text = self.flatten_json_to_text(data)
        return text, [{"page_number": 1, "text": text}], "flattened_json", []

    def extract_pages(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        pages_value = data.get("pages")
        if not isinstance(pages_value, list) or not pages_value:
            return []
        pages: list[dict[str, Any]] = []
        for idx, item in enumerate(pages_value, start=1):
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or item.get("raw_text") or ""
                number = item.get("page_number") or item.get("page") or idx
                if isinstance(text, str) and text.strip():
                    pages.append({"page_number": int(number) if str(number).isdigit() else idx, "text": text})
            elif isinstance(item, str) and item.strip():
                pages.append({"page_number": idx, "text": item})
        return pages

    def flatten_json_to_text(self, data: Any) -> str:
        parts: list[str] = []

        def walk(obj: Any, depth: int = 0) -> None:
            if depth > 20:
                return
            if isinstance(obj, dict):
                for key, value in obj.items():
                    parts.append(str(key))
                    walk(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item, depth + 1)
            elif isinstance(obj, (str, int, float, bool)):
                value = str(obj).strip()
                if value:
                    parts.append(value)

        walk(data)
        return "\n".join(parts)
