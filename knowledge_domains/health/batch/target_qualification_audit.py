"""Read-only target qualification audit for governed repeatability proofs."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from config.settings import BASE_DIR

AUDIT_VERSION = "1.0"
_POLICY_WORDING = "policy_wording"
_SUPPORTING_TYPES = {"customer_information_sheet", "prospectus", "brochure"}
_STATUSES = (
    "qualified_for_repeatability_proof",
    "evidence_only_not_qualified",
    "excluded_variant_mismatch",
    "missing_provenance",
)
_UIN_PATTERN = re.compile(r"\b[A-Z]{3,}[A-Z0-9]*V\d{6}\b")


class TargetQualificationAuditError(ValueError):
    """Raised when a required audit input is malformed."""


class TargetQualificationAudit:
    """Inspect retained registry-backed policy wordings without changing any evidence."""

    def __init__(
        self,
        *,
        base_dir: Path | None = None,
        insurer_id: str = "bajaj_allianz_general",
        registry_path: str | Path = "registry/pdf_registry.json",
        report_path: str | Path = "reports/bajaj_policy_wording_target_qualification_audit_v1.json",
    ) -> None:
        self.base_dir = (base_dir or BASE_DIR).resolve()
        self.insurer_id = self._nonempty(insurer_id, "insurer_id")
        self.registry_path = self._safe_path(registry_path, "registry_path")
        self.report_path = self._safe_path(report_path, "report_path")

    def build(self, *, generated_at: str | None = None) -> dict[str, Any]:
        registry = self._load_json(self.registry_path, "pdf_registry")
        by_url = registry.get("by_url")
        if not isinstance(by_url, dict):
            raise TargetQualificationAuditError("pdf_registry.by_url must be an object")

        records = [
            item for item in by_url.values()
            if isinstance(item, dict)
            and item.get("insurer_id") == self.insurer_id
            and item.get("document_type") == _POLICY_WORDING
        ]
        if not records:
            raise TargetQualificationAuditError(
                f"no policy_wording records found for insurer_id={self.insurer_id}"
            )

        rows = [self._audit_record(item, all_records=by_url.values()) for item in records]
        rows.sort(key=lambda item: (str(item["source_url"]).lower(), str(item["sha256"])))
        counts = Counter(row["qualification_status"] for row in rows)
        report = {
            "schema_version": "1.0",
            "audit_type": "repeatability_target_qualification_audit_v1",
            "audit_version": AUDIT_VERSION,
            "audit_status": "read_only_observed_not_published",
            "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
            "insurer_id": self.insurer_id,
            "document_type_scope": _POLICY_WORDING,
            "candidate_count": len(rows),
            "qualification_counts": {status: counts.get(status, 0) for status in _STATUSES},
            "candidates": rows,
            "guardrails": [
                "This audit is read-only. It does not download documents, create source observations, repair provenance, register product identity, or publish facts.",
                "A downloader registry record and a prior unchanged check are historical retrieval lineage, not a current-entitlement decision.",
                "A same-source-page supporting document is accepted only when its UIN matches the policy wording UIN; otherwise the pairing is a variant mismatch.",
                "Qualification identifies an entry candidate for a governed proof. It does not establish product identity, temporal compatibility, legal entitlement, or customer-facing truth.",
            ],
        }
        target = self.base_dir / self.report_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"report": report, "report_path": target}

    def _audit_record(self, record: dict[str, Any], *, all_records: Any) -> dict[str, Any]:
        source_url = self._nonempty(record.get("url"), "policy_wording.url")
        sha256 = self._nonempty(record.get("sha256"), "policy_wording.sha256")
        archive_path = self._resolve_local_path(record.get("current_local_path") or record.get("local_path"))
        raw_exists = bool(archive_path and archive_path.is_file())
        actual_sha256 = self._sha256(archive_path) if raw_exists and archive_path else None
        raw_integrity = "passed" if actual_sha256 == sha256 else ("missing" if not raw_exists else "failed")

        source_page_url = record.get("source_page_url")
        official_source_url = bool(isinstance(source_url, str) and source_url.startswith(("http://", "https://")))
        source_page_artifact = self._resolve_local_path(record.get("source_html_file"))
        source_page_artifact_exists = bool(source_page_artifact and source_page_artifact.is_file())
        registry_lineage = bool(record.get("last_unchanged_check") or record.get("versions"))
        observed = self._find_hardened_observation(sha256)

        identity = self._extract_identity(archive_path) if raw_exists and archive_path else {
            "extractable": False, "uins": [], "page_count": None, "error": "raw_pdf_missing"
        }
        support = self._find_support(record, all_records, identity.get("uins", []))

        blockers: list[str] = []
        if raw_integrity != "passed":
            blockers.append(f"raw_pdf_integrity_{raw_integrity}")
        if not official_source_url:
            blockers.append("official_source_url_missing")
        if not identity["extractable"]:
            blockers.append("product_variant_identity_not_extractable")
        if not source_page_artifact_exists:
            blockers.append("retained_source_page_artifact_missing")
        if not registry_lineage:
            blockers.append("downloader_registry_lineage_missing")
        if not observed:
            blockers.append("hardened_source_observation_missing")
        if support["status"] == "variant_mismatch":
            blockers.append("supporting_source_variant_mismatch")
        elif support["status"] != "matched":
            blockers.append("matching_supporting_source_missing")

        if support["status"] == "variant_mismatch":
            qualification_status = "excluded_variant_mismatch"
        elif raw_integrity != "passed" or not official_source_url or not identity["extractable"]:
            qualification_status = "evidence_only_not_qualified"
        elif not source_page_artifact_exists or not registry_lineage or not observed:
            qualification_status = "missing_provenance"
        elif support["status"] != "matched":
            qualification_status = "evidence_only_not_qualified"
        else:
            qualification_status = "qualified_for_repeatability_proof"

        return {
            "source_url": source_url,
            "source_page_url": source_page_url,
            "sha256": sha256,
            "document_type": _POLICY_WORDING,
            "archive_path": self._relative(archive_path) if archive_path else None,
            "raw_pdf": {"exists": raw_exists, "integrity": raw_integrity, "actual_sha256": actual_sha256},
            "identity_probe": identity,
            "source_page_artifact": {
                "declared_path": self._relative(source_page_artifact) if source_page_artifact else None,
                "exists": source_page_artifact_exists,
            },
            "downloader_registry_lineage": {
                "present": registry_lineage,
                "last_checked_at": record.get("last_checked_at"),
                "last_unchanged_check_present": isinstance(record.get("last_unchanged_check"), dict),
            },
            "hardened_source_observation_present": observed,
            "supporting_source": support,
            "qualification_status": qualification_status,
            "blockers": sorted(set(blockers)),
        }

    def _find_support(self, policy: dict[str, Any], all_records: Any, policy_uins: list[str]) -> dict[str, Any]:
        same_page: list[dict[str, Any]] = []
        for item in all_records:
            if not isinstance(item, dict) or item is policy:
                continue
            if item.get("insurer_id") != self.insurer_id or item.get("document_type") not in _SUPPORTING_TYPES:
                continue
            if item.get("source_page_url") == policy.get("source_page_url"):
                same_page.append(item)
        matches: list[dict[str, Any]] = []
        mismatches: list[dict[str, Any]] = []
        for item in same_page:
            path = self._resolve_local_path(item.get("current_local_path") or item.get("local_path"))
            probe = self._extract_identity(path) if path and path.is_file() else {"uins": []}
            summary = {"document_type": item.get("document_type"), "url": item.get("url"), "sha256": item.get("sha256"), "uins": probe.get("uins", [])}
            if policy_uins and set(policy_uins).intersection(probe.get("uins", [])):
                matches.append(summary)
            else:
                mismatches.append(summary)
        if matches:
            return {"status": "matched", "documents": matches}
        if mismatches:
            return {"status": "variant_mismatch", "documents": mismatches}
        return {"status": "missing", "documents": []}

    def _find_hardened_observation(self, sha256: str) -> bool:
        root = self.base_dir / "knowledge" / "factory" / "registry_backed"
        if not root.is_dir():
            return False
        for path in root.glob("**/source_observations/*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if self._contains_sha(payload, sha256):
                return True
        return False

    def _contains_sha(self, value: Any, target: str) -> bool:
        if isinstance(value, dict):
            return any(self._contains_sha(item, target) for item in value.values())
        if isinstance(value, list):
            return any(self._contains_sha(item, target) for item in value)
        return value == target

    def _extract_identity(self, path: Path) -> dict[str, Any]:
        try:
            with fitz.open(path) as document:
                pages = min(len(document), 3)
                text = "\n".join((document[index].get_text("text") or "") for index in range(pages))
                uins = sorted(set(_UIN_PATTERN.findall(text.upper())))
                return {
                    "extractable": bool(uins),
                    "uins": uins,
                    "page_count": len(document),
                    "first_page_text_sha256": hashlib.sha256((document[0].get_text("text") or "").encode("utf-8")).hexdigest() if len(document) else None,
                    "error": None,
                }
        except (fitz.FileDataError, OSError, RuntimeError, ValueError) as exc:
            return {"extractable": False, "uins": [], "page_count": None, "first_page_text_sha256": None, "error": str(exc)}

    def _resolve_local_path(self, raw: Any) -> Path | None:
        if not isinstance(raw, str) or not raw.strip():
            return None
        normalized = raw.replace("\\", "/")
        marker = "/archive/"
        if marker in normalized:
            normalized = "archive/" + normalized.split(marker, 1)[1]
        candidate = Path(normalized)
        if candidate.is_absolute():
            return None
        return (self.base_dir / candidate).resolve()

    def _relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.base_dir).as_posix()
        except ValueError:
            return path.as_posix()

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _safe_path(self, value: str | Path, label: str) -> str:
        raw = self._nonempty(str(value), label)
        path = Path(raw)
        if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
            raise TargetQualificationAuditError(f"{label} must be a safe repository-relative path")
        return path.as_posix()

    def _load_json(self, relative_path: str, label: str) -> dict[str, Any]:
        path = (self.base_dir / relative_path).resolve()
        if not path.is_file():
            raise TargetQualificationAuditError(f"{label} file is missing: {relative_path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TargetQualificationAuditError(f"{label} is not valid JSON: {relative_path}") from exc
        if not isinstance(payload, dict):
            raise TargetQualificationAuditError(f"{label} must be a JSON object")
        return payload

    @staticmethod
    def _nonempty(value: Any, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise TargetQualificationAuditError(f"{label} must be a non-empty string")
        return value.strip()
