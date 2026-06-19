from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from knowledge_domains.health.routing.evidence_router import EvidenceRouter


@dataclass(frozen=True)
class RegistryPaths:
    registry_dir: Path
    registry_path: Path


class EvidenceRegistry:
    """
    Evidence Registry v0.1

    Purpose:
        Build and query a stable catalog of RAW evidence artifacts.

    Why this exists:
        EvidenceRouter v0.5 proved that filesystem scanning works, but the
        Knowledge Factory needs a persistent catalog so later agents do not
        repeatedly rediscover the same documents.

    Registry output:
        knowledge/registry/evidence_registry.json

    Notes:
        - This intentionally reuses EvidenceRouter v0.5 classification logic.
        - Derived artifacts are excluded using the router's evidence-only filter.
        - Current implementation is file-backed JSON. Later this can move to
          Postgres/Supabase without changing downstream contract much.
    """

    VERSION = "0.1"

    AUTHORITY_SCORES = {
        "policy_wording": 100,
        "customer_information_sheet": 90,
        "cis": 90,
        "prospectus": 75,
        "brochure": 60,
        "webpage": 45,
    }

    DEFAULT_BASE_ROOTS = ["knowledge", "parsed", "archive"]

    def __init__(self, registry_path: Path | None = None):
        self.router = EvidenceRouter()
        self.paths = self.get_registry_paths(registry_path)

    def get_registry_paths(self, registry_path: Path | None = None) -> RegistryPaths:
        if registry_path is None:
            registry_dir = BASE_DIR / "knowledge" / "registry"
            registry_path = registry_dir / "evidence_registry.json"
        else:
            registry_path = Path(registry_path)
            registry_dir = registry_path.parent
        return RegistryPaths(registry_dir=registry_dir, registry_path=registry_path)

    def build_registry(
        self,
        *,
        entity_ids: list[str] | None = None,
        base_roots: list[str] | None = None,
        write: bool = True,
    ) -> dict[str, Any]:
        base_roots = base_roots or self.DEFAULT_BASE_ROOTS
        entity_ids = entity_ids or sorted(self.router.PRODUCT_ALIASES_BY_ENTITY.keys())

        rejected_counts: dict[str, int] = {
            "excluded_derived_artifact": 0,
            "unsupported_file_type": 0,
            "not_entity_match": 0,
            "blocked_context": 0,
            "duplicate_document": 0,
        }

        records: list[dict[str, Any]] = []
        seen_document_ids: set[str] = set()

        for root_str in base_roots:
            root = BASE_DIR / root_str
            if not root.exists():
                continue

            for path in self.router.iter_supported_files(root):
                if self.router.is_excluded_derived_artifact(path):
                    rejected_counts["excluded_derived_artifact"] += 1
                    continue

                raw_text = self.router.read_small_text(path)
                matched_entities = self.match_entities(path, raw_text, entity_ids)

                if not matched_entities:
                    rejected_counts["not_entity_match"] += 1
                    continue

                source_type = self.router.classify_source_type(path, raw_text)
                record = self.build_document_record(
                    path=path,
                    source_type=source_type,
                    matched_entities=matched_entities,
                    raw_text=raw_text,
                )

                if record["document_id"] in seen_document_ids:
                    rejected_counts["duplicate_document"] += 1
                    continue

                seen_document_ids.add(record["document_id"])
                records.append(record)

        records = sorted(
            records,
            key=lambda item: (
                item["entity_ids"][0] if item["entity_ids"] else "",
                -item["authority_score"],
                item["relative_path"],
            ),
        )

        registry = {
            "registry_version": self.VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "base_roots": base_roots,
            "entity_ids": entity_ids,
            "document_count": len(records),
            "rejected_counts": rejected_counts,
            "documents": records,
        }

        if write:
            self.paths.registry_dir.mkdir(parents=True, exist_ok=True)
            with self.paths.registry_path.open("w", encoding="utf-8") as file:
                json.dump(registry, file, indent=2, ensure_ascii=False)

        return registry

    def match_entities(self, path: Path, raw_text: str, entity_ids: list[str]) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        blocked_any = False

        for entity_id in entity_ids:
            match_result = self.router.path_matches_entity(path, entity_id, raw_text)
            if match_result.get("matched"):
                matches.append(
                    {
                        "entity_id": entity_id,
                        "match_reason": match_result.get("reason"),
                        "matched_aliases": match_result.get("matched_aliases", []),
                    }
                )
            elif match_result.get("reason") == "blocked_context":
                blocked_any = True

        # Keep blocked visibility inside the record matching function only for future use.
        # The builder currently counts unmatched files as not_entity_match.
        _ = blocked_any
        return matches

    def build_document_record(
        self,
        *,
        path: Path,
        source_type: str,
        matched_entities: list[dict[str, Any]],
        raw_text: str,
    ) -> dict[str, Any]:
        relative_path = str(path.relative_to(BASE_DIR)).replace("\\", "/")
        document_hash = self.file_hash(path)
        logical_document_key = self.router.logical_document_key(path, source_type)
        document_id = self.stable_id("doc", f"{logical_document_key}|{document_hash[:16]}")
        source_url = self.extract_source_url(path)
        authority_score = self.AUTHORITY_SCORES.get(source_type, 30)
        evidence_role = self.router.RAW_EVIDENCE_ROLES.get(source_type, "source_evidence")

        return {
            "document_id": document_id,
            "artifact_type": "raw_evidence",
            "document_type": source_type,
            "source_type": source_type,
            "evidence_role": evidence_role,
            "authority_score": authority_score,
            "entity_ids": [item["entity_id"] for item in matched_entities],
            "entity_matches": matched_entities,
            "relative_path": relative_path,
            "path": str(path),
            "source_url": source_url,
            "document_hash": document_hash,
            "logical_document_key": logical_document_key,
            "file_size_bytes": self.safe_file_size(path),
            "modified_at": self.safe_modified_at(path),
            "effective_date": None,
            "version_label": None,
            "status": "active",
            "registry_notes": self.registry_notes(source_type, raw_text),
        }

    def load_registry(self) -> dict[str, Any]:
        if not self.paths.registry_path.exists():
            raise FileNotFoundError(
                f"Evidence registry not found: {self.paths.registry_path}. "
                "Run: python -m scripts.build_evidence_registry"
            )
        with self.paths.registry_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def query(
        self,
        *,
        entity_id: str,
        document_types: list[str] | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        registry = self.load_registry()
        document_types = document_types or []

        documents = []
        for doc in registry.get("documents", []):
            if status and doc.get("status") != status:
                continue
            if entity_id not in doc.get("entity_ids", []):
                continue
            if document_types and doc.get("document_type") not in document_types:
                continue
            documents.append(doc)

        documents = sorted(
            documents,
            key=lambda item: (-item.get("authority_score", 0), item.get("relative_path", "")),
        )

        return {
            "registry_version": registry.get("registry_version"),
            "entity_id": entity_id,
            "document_types": document_types,
            "document_count": len(documents),
            "documents": documents,
        }

    def extract_source_url(self, path: Path) -> str | None:
        if path.suffix.lower() != ".json":
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            return None

        possible_keys = [
            "source_url",
            "source-url",
            "url",
            "page_url",
            "page-url",
            "download_url",
            "download-url",
            "final_url",
            "final-url",
        ]

        found = self.find_first_key(data, possible_keys)
        return str(found) if found else None

    def find_first_key(self, obj: Any, keys: list[str]) -> Any:
        normalized_keys = {key.lower().replace("_", "-") for key in keys}

        if isinstance(obj, dict):
            for key, value in obj.items():
                key_norm = str(key).lower().replace("_", "-")
                if key_norm in normalized_keys and isinstance(value, (str, int, float)):
                    return value
            for value in obj.values():
                found = self.find_first_key(value, keys)
                if found:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = self.find_first_key(item, keys)
                if found:
                    return found
        return None

    def registry_notes(self, source_type: str, raw_text: str) -> list[str]:
        notes: list[str] = []
        if source_type == "policy_wording":
            notes.append("Highest authority source for legal interpretation")
        elif source_type in {"customer_information_sheet", "cis"}:
            notes.append("Regulatory summary source")
        elif source_type == "prospectus":
            notes.append("Product disclosure source")
        elif source_type == "brochure":
            notes.append("Marketing disclosure source; verify against policy wording")
        elif source_type == "webpage":
            notes.append("Published web source; useful for latest public product page")

        if self.router.looks_like_metadata(raw_text):
            notes.append("Metadata-like artifact; use as supporting evidence only")

        return notes

    def file_hash(self, path: Path) -> str:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    digest.update(chunk)
        except Exception:
            digest.update(str(path).encode("utf-8"))
        return digest.hexdigest()

    def stable_id(self, prefix: str, value: str) -> str:
        digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:20]
        return f"{prefix}_{digest}"

    def safe_file_size(self, path: Path) -> int:
        try:
            return path.stat().st_size
        except OSError:
            return 0

    def safe_modified_at(self, path: Path) -> str | None:
        try:
            return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        except OSError:
            return None
