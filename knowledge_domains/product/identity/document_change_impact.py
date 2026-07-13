"""Candidate-only impact detection for changed PDF document versions.

A PDF downloader run is the technical evidence that an insurer-hosted URL served
new bytes.  This module joins that event to already-governed source-product links
and creates revalidation candidates.  It never changes product facts or product
identity records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


DOCUMENT_CHANGE_IMPACT_VERSION = "1.0"
NEW_VERSION_STATUS = "new_version_downloaded"
REGISTRY_BACKED_PROVENANCE = "download_registry_verified"


class DocumentChangeImpactBuilder:
    """Build candidate-only product revalidation work from a downloader run."""

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR

    @property
    def link_registry_path(self) -> Path:
        return self.base_dir / "registry" / "source_product_link_registry.json"

    @property
    def candidate_registry_path(self) -> Path:
        return self.base_dir / "registry" / "document_change_impact_candidates.json"

    @property
    def report_path(self) -> Path:
        return self.base_dir / "reports" / "document_change_impact_report.json"

    @property
    def pdf_run_log_dir(self) -> Path:
        return self.base_dir / "logs" / "pdf_download_runs"

    def build(self, *, run_log_path: Path | None = None) -> dict[str, Any]:
        resolved_run_log = run_log_path or self._latest_run_log()
        run_log = self._load_json(resolved_run_log)
        links = self._load_json(self.link_registry_path).get("links", [])
        changed_items = self._changed_items(run_log)
        candidates = self._build_candidates(changed_items, links)

        registry = {
            "schema_version": "1.0",
            "impact_detection_version": DOCUMENT_CHANGE_IMPACT_VERSION,
            "generated_at": self._utc_now(),
            "source_run_log": self._relative_path(resolved_run_log),
            "candidate_count": len(candidates),
            "candidates": candidates,
        }
        status_counts = Counter(item.get("status") for item in candidates)
        report = {
            "impact_detection_version": DOCUMENT_CHANGE_IMPACT_VERSION,
            "generated_at": self._utc_now(),
            "source_run_log": self._relative_path(resolved_run_log),
            "changed_document_events": len(changed_items),
            "source_product_links_scanned": len(links),
            "revalidation_candidates": len(candidates),
            "candidate_status_counts": {
                "revalidation_candidate": status_counts.get("revalidation_candidate", 0),
            },
            "registry_output": self._relative_path(self.candidate_registry_path),
        }
        self._write_json(self.candidate_registry_path, registry)
        self._write_json(self.report_path, report)
        return {
            "registry": registry,
            "report": report,
            "registry_path": self.candidate_registry_path,
            "report_path": self.report_path,
            "run_log_path": resolved_run_log,
        }

    def _build_candidates(
        self,
        changed_items: list[dict[str, Any]],
        links: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for event in changed_items:
            for link in links:
                if not self._link_is_registry_backed(link):
                    continue
                match_method = self._link_match_method(link, event)
                if match_method is None:
                    continue
                link_id = self._text(link, "source_product_link_id") or ""
                event_key = self._text(event, "url_key") or ""
                new_sha256 = self._text(event, "sha256") or ""
                dedupe_key = (link_id, event_key, new_sha256)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                candidates.append(self._make_candidate(link, event, match_method))
        return sorted(
            candidates,
            key=lambda item: (item["product_identity_id"], item["changed_document_url_key"]),
        )

    @staticmethod
    def _changed_items(run_log: dict[str, Any]) -> list[dict[str, Any]]:
        items = run_log.get("items", [])
        if not isinstance(items, list):
            return []
        return [
            item for item in items
            if isinstance(item, dict)
            and item.get("status") == NEW_VERSION_STATUS
            and isinstance(item.get("url_key"), str)
            and item.get("url_key").strip()
            and isinstance(item.get("sha256"), str)
            and item.get("sha256").strip()
            and isinstance(item.get("previous_sha256"), str)
            and item.get("previous_sha256").strip()
        ]

    @staticmethod
    def _link_is_registry_backed(link: dict[str, Any]) -> bool:
        return (
            link.get("provenance_status") == REGISTRY_BACKED_PROVENANCE
            and isinstance(link.get("pdf_registry_record"), dict)
        )

    def _link_match_method(self, link: dict[str, Any], event: dict[str, Any]) -> str | None:
        snapshot = link.get("pdf_registry_record")
        if not isinstance(snapshot, dict):
            return None
        event_url_key = self._text(event, "url_key")
        snapshot_url_key = self._text(snapshot, "url_key")
        if event_url_key and snapshot_url_key and event_url_key == snapshot_url_key:
            return "registry_url_key"

        previous_sha256 = self._text(event, "previous_sha256")
        linked_sha256 = self._text(link, "document_sha256")
        if previous_sha256 and linked_sha256 and previous_sha256 == linked_sha256:
            return "previous_version_sha256"
        return None

    def _make_candidate(
        self,
        link: dict[str, Any],
        event: dict[str, Any],
        match_method: str,
    ) -> dict[str, Any]:
        url_key = self._text(event, "url_key") or ""
        new_sha256 = self._text(event, "sha256") or ""
        product_identity_id = self._text(link, "product_identity_id") or ""
        source_product_link_id = self._text(link, "source_product_link_id") or ""
        value = f"{product_identity_id}:{source_product_link_id}:{url_key}:{new_sha256}"
        return {
            "document_change_impact_id": f"dci_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]}",
            "status": "revalidation_candidate",
            "candidate_only": True,
            "product_identity_id": product_identity_id,
            "insurer_id": link.get("insurer_id"),
            "product_uin": link.get("product_uin"),
            "source_product_link_id": source_product_link_id,
            "document_type": event.get("document_type") or link.get("document_type"),
            "logical_document_path": link.get("logical_document_path"),
            "linked_document_sha256": link.get("document_sha256"),
            "changed_document_url": event.get("url"),
            "changed_document_url_key": url_key,
            "previous_sha256": event.get("previous_sha256"),
            "new_sha256": new_sha256,
            "change_detected_at": event.get("processed_at"),
            "link_match_method": match_method,
            "required_next_action": "re_run_evidence_extraction_and_validation",
            "guardrail": "No product fact, product identity, or knowledge asset is changed automatically.",
        }

    def _latest_run_log(self) -> Path:
        candidates = sorted(self.pdf_run_log_dir.glob("pdf_download_run_*.json"))
        if not candidates:
            raise FileNotFoundError(f"No PDF download run logs found: {self.pdf_run_log_dir}")
        return candidates[-1]

    @staticmethod
    def _text(payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Required JSON file not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON file: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"JSON root must be an object: {path}")
        return payload

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.base_dir)).replace("\\", "/")
        except ValueError:
            return str(path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build document-change revalidation candidates.")
    parser.add_argument("--run-log", type=Path, help="PDF download run log to inspect.")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    DocumentChangeImpactBuilder().build(run_log_path=args.run_log)
