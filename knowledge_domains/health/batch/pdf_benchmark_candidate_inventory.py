"""Create a read-only candidate inventory for the P1.6 PDF benchmark.

This is deliberately a document-structure inventory, not an extraction or
product-identity workflow. It reads official PDF registry entries and raw PDFs
in place, then labels *candidates* for manual benchmark selection.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import fitz  # PyMuPDF

from config.settings import BASE_DIR

INVENTORY_VERSION = "1.0"
DEFAULT_HEALTH_INSURERS = ("aditya_birla_health", "bajaj_allianz_general")


class PdfBenchmarkCandidateInventory:
    """Inventory official registry PDFs for benchmark selection without changing evidence."""

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR

    @property
    def pdf_registry_path(self) -> Path:
        return self.base_dir / "registry" / "pdf_registry.json"

    @property
    def output_path(self) -> Path:
        return self.base_dir / "registry" / "pdf_benchmark_candidate_inventory_v1.json"

    def build(self, *, insurer_ids: Iterable[str] | None = None) -> dict[str, Any]:
        selected_insurers = tuple(insurer_ids or DEFAULT_HEALTH_INSURERS)
        registry = self._load_json(self.pdf_registry_path)
        entries = [
            entry for entry in registry.get("by_url", {}).values()
            if isinstance(entry, dict) and entry.get("insurer_id") in selected_insurers
        ]
        entries.sort(key=lambda item: (
            str(item.get("insurer_id") or ""),
            str(item.get("document_type") or ""),
            str(item.get("url_key") or item.get("url") or ""),
        ))

        candidates = [self._assess(entry) for entry in entries]
        status_counts = Counter(candidate["inventory_status"] for candidate in candidates)
        trait_counts = Counter(
            trait for candidate in candidates for trait in candidate.get("candidate_traits", [])
        )
        document_type_counts = Counter(str(candidate.get("document_type") or "unknown") for candidate in candidates)

        payload = {
            "schema_version": "1.0",
            "inventory_version": INVENTORY_VERSION,
            "generated_at": self._utc_now(),
            "scope": {
                "insurer_ids": list(selected_insurers),
                "source_registry": self._relative_path(self.pdf_registry_path),
                "purpose": "P1.6 benchmark candidate selection only; not product fact publication.",
            },
            "summary": {
                "registry_entries_selected": len(entries),
                "raw_files_readable": status_counts.get("candidate_ready", 0),
                "missing_raw_files": status_counts.get("blocked_missing_raw_pdf", 0),
                "unreadable_files": status_counts.get("blocked_unreadable_pdf", 0),
                "document_type_counts": dict(sorted(document_type_counts.items())),
                "candidate_trait_counts": dict(sorted(trait_counts.items())),
                "selection_note": (
                    "candidate traits are screening signals only. A human must select and classify benchmark cases; "
                    "no candidate trait proves scanning, table fidelity, OCR need, or source applicability."
                ),
            },
            "candidates": candidates,
        }
        self._write_json(self.output_path, payload)
        return {"inventory": payload, "output_path": self.output_path}

    def _assess(self, entry: dict[str, Any]) -> dict[str, Any]:
        relative_path = self._relative_locator(entry)
        base = {
            "candidate_id": self._stable_id(
                "pdfbenchcand",
                f"{entry.get('insurer_id')}|{entry.get('document_type')}|{entry.get('current_sha256') or entry.get('sha256')}|{entry.get('url_key') or entry.get('url')}",
            ),
            "insurer_id": entry.get("insurer_id"),
            "document_type": entry.get("document_type"),
            "source_url": entry.get("url"),
            "source_page_url": entry.get("source_page_url"),
            "sha256": entry.get("current_sha256") or entry.get("sha256"),
            "raw_pdf_relative_path": relative_path,
            "candidate_traits": [],
            "screening_metrics": None,
            "manual_selection_required": True,
        }
        raw_path = self._resolve_archive_path(relative_path)
        if raw_path is None or not raw_path.is_file():
            return {
                **base,
                "inventory_status": "blocked_missing_raw_pdf",
                "blocker": "Raw PDF is not present locally; no structural assessment was performed.",
            }
        try:
            metrics = self._native_text_metrics(raw_path)
        except (fitz.FileDataError, RuntimeError, OSError, ValueError) as exc:
            return {
                **base,
                "inventory_status": "blocked_unreadable_pdf",
                "blocker": f"PyMuPDF could not read the local raw PDF: {exc}",
            }
        traits = self._candidate_traits(entry=entry, metrics=metrics)
        return {
            **base,
            "inventory_status": "candidate_ready",
            "candidate_traits": traits,
            "screening_metrics": metrics,
            "selection_guidance": self._guidance(traits),
        }

    @staticmethod
    def _native_text_metrics(raw_path: Path) -> dict[str, Any]:
        with fitz.open(raw_path) as document:
            page_text_lengths = [len((page.get_text("text") or "").strip()) for page in document]
        page_count = len(page_text_lengths)
        nonempty = [length for length in page_text_lengths if length > 0]
        empty_page_count = page_count - len(nonempty)
        total_characters = sum(page_text_lengths)
        return {
            "page_count": page_count,
            "total_characters": total_characters,
            "nonempty_page_ratio": round((len(nonempty) / page_count), 4) if page_count else 0.0,
            "empty_page_count": empty_page_count,
            "median_characters_per_page": PdfBenchmarkCandidateInventory._median(page_text_lengths),
        }

    @staticmethod
    def _candidate_traits(*, entry: dict[str, Any], metrics: dict[str, Any]) -> list[str]:
        traits: list[str] = []
        document_type = str(entry.get("document_type") or "")
        if document_type:
            traits.append(document_type)
        page_count = int(metrics["page_count"])
        nonempty_ratio = float(metrics["nonempty_page_ratio"])
        median_chars = float(metrics["median_characters_per_page"])
        if page_count >= 30:
            traits.append("long_document")
        if document_type in {"customer_information_sheet", "proposal_form", "prospectus"}:
            traits.append("potential_table_or_form_layout")
        if nonempty_ratio < 0.8:
            traits.append("scanned_or_image_heavy_candidate")
        elif median_chars < 250:
            traits.append("poor_native_text_candidate")
        if document_type == "brochure":
            traits.append("layout_sensitive_candidate")
        return sorted(set(traits))

    @staticmethod
    def _guidance(traits: list[str]) -> str:
        if "scanned_or_image_heavy_candidate" in traits:
            return "Prioritize for manual scan/image verification; do not infer OCR need from this screening signal alone."
        if "poor_native_text_candidate" in traits:
            return "Prioritize for native-text quality review and manual visual inspection."
        if "potential_table_or_form_layout" in traits or "layout_sensitive_candidate" in traits:
            return "Suitable for layout/table benchmark coverage; native text may still be usable for prose only."
        return "Candidate for native-text baseline coverage; manually assign benchmark traits before inclusion."

    def _relative_locator(self, entry: dict[str, Any]) -> str | None:
        value = entry.get("current_local_path") or entry.get("local_path")
        if not isinstance(value, str) or not value:
            return None
        path = Path(value)
        if path.is_absolute():
            try:
                return self._relative_path(path)
            except ValueError:
                return None
        return value.replace("\\", "/")

    def _resolve_archive_path(self, relative_path: str | None) -> Path | None:
        if not isinstance(relative_path, str) or not relative_path.startswith("archive/"):
            return None
        candidate = (self.base_dir / relative_path).resolve()
        archive_root = (self.base_dir / "archive").resolve()
        try:
            candidate.relative_to(archive_root)
        except ValueError:
            return None
        return candidate

    def _relative_path(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.base_dir.resolve())).replace("\\", "/")

    @staticmethod
    def _median(values: list[int]) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        middle = len(ordered) // 2
        if len(ordered) % 2:
            return float(ordered[middle])
        return (ordered[middle - 1] + ordered[middle]) / 2.0

    @staticmethod
    def _stable_id(prefix: str, value: str) -> str:
        return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Required JSON file not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"JSON root must be an object: {path}")
        return payload

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

