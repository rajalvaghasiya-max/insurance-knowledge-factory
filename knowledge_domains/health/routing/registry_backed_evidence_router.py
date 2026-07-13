from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from knowledge_domains.health.routing.evidence_router import EvidenceRouter


class RegistryBackedEvidenceRouter:
    """Route Health-field evidence from scoped Department IV component collections.

    This adapter deliberately does not scan folders, infer product identity from paths,
    or create insurance facts. It turns already-classified components into evidence
    candidates while preserving upstream provenance.
    """

    VERSION = "1.0"
    EXECUTION_REGISTRY_NAME = "department_iv_execution_registry.json"

    def __init__(self, base_router: EvidenceRouter | None = None) -> None:
        self.base_router = base_router or EvidenceRouter()

    def resolve_routing_plan(
        self,
        *,
        entity_id: str,
        field: str,
        factory_dir: str | Path,
        factory_input_registry_path: str | Path,
    ) -> dict[str, Any]:
        factory_root = self._resolve_path(factory_dir)
        execution_path = factory_root / self.EXECUTION_REGISTRY_NAME
        execution_registry = self._load_json(execution_path)
        input_registry = self._load_json(self._resolve_path(factory_input_registry_path))
        input_documents = {
            str(item.get("document_id")): item
            for item in input_registry.get("documents", [])
            if isinstance(item, dict)
        }

        if execution_registry.get("entity_id") != entity_id:
            raise ValueError(
                "Department IV execution registry entity does not match requested entity: "
                f"{execution_registry.get('entity_id')!r} != {entity_id!r}"
            )

        priority_sources = self.base_router.get_priority_sources(field)
        rejected_counts = {
            "incomplete_department_iv_record": 0,
            "unsupported_source_type": 0,
            "inactive_component": 0,
            "no_field_signal": 0,
            "missing_component_collection": 0,
        }
        candidates: list[dict[str, Any]] = []

        for record in execution_registry.get("records", []):
            if not isinstance(record, dict) or record.get("status") != "completed":
                rejected_counts["incomplete_department_iv_record"] += 1
                continue

            document_id = str(record.get("document_id") or "")
            factory_document = input_documents.get(document_id)
            if not document_id or factory_document is None:
                rejected_counts["incomplete_department_iv_record"] += 1
                continue

            source_type = str(record.get("document_type") or factory_document.get("document_type") or "")
            if source_type not in priority_sources:
                rejected_counts["unsupported_source_type"] += 1
                continue

            collection_path = self._resolve_path(
                ((record.get("classifier") or {}).get("collection_path") or "")
            )
            if not collection_path.exists():
                rejected_counts["missing_component_collection"] += 1
                continue

            collection = self._load_json(collection_path)
            for component in collection.get("components", []):
                if not isinstance(component, dict):
                    continue
                if component.get("status") != "active":
                    rejected_counts["inactive_component"] += 1
                    continue

                text_for_routing = self._routing_text(component)
                field_hits = self.base_router.find_field_hits(field, text_for_routing)
                if not field_hits:
                    rejected_counts["no_field_signal"] += 1
                    continue

                candidates.append(
                    self._build_candidate(
                        entity_id=entity_id,
                        field=field,
                        priority_sources=priority_sources,
                        source_type=source_type,
                        document=factory_document,
                        component=component,
                        collection_path=collection_path,
                        field_hits=field_hits,
                    )
                )

        candidates.sort(
            key=lambda item: (
                -int(item["routing_score"]),
                int(item["priority"]),
                int(item["source"].get("section_order") or 999999),
                item["classified_component_id"],
            )
        )
        evidence_bundles = self._build_bundles(candidates)

        return {
            "schema_version": "1.0",
            "adapter_version": self.VERSION,
            "router_version": self.base_router.VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "entity_id": entity_id,
            "field": field,
            "factory_dir": self._relative_or_absolute(factory_root),
            "department_iv_execution_registry": self._relative_or_absolute(execution_path),
            "factory_input_registry": self._relative_or_absolute(self._resolve_path(factory_input_registry_path)),
            "priority_sources": priority_sources,
            "candidate_count": len(candidates),
            "evidence_count": len(candidates),
            "bundle_count": len(evidence_bundles),
            "rejected_counts": rejected_counts,
            "candidates": candidates,
            "evidence_records": candidates,
            "evidence_bundles": evidence_bundles,
            "notes": [
                "Consumes explicit Department IV classified component collections; it does not scan folders or rediscover documents.",
                "Candidates retain original raw-PDF lineage through the registry-backed factory input document.",
                "Null page/line values are preserved as unknown and are never inferred by this adapter.",
                "This routing plan selects evidence candidates only; it does not extract, validate, or publish insurance facts.",
            ],
        }

    def write_routing_plan(self, plan: dict[str, Any], factory_dir: str | Path) -> Path:
        factory_root = self._resolve_path(factory_dir)
        output_dir = factory_root / "routing_plans"
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_entity = str(plan["entity_id"]).replace(":", "_").replace("/", "_").replace("\\", "_").lower()
        safe_field = str(plan["field"]).replace("/", "_").replace("\\", "_").lower()
        output_path = output_dir / f"{safe_entity}_{safe_field}_registry_backed_routing_plan.json"
        output_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def _build_candidate(
        self,
        *,
        entity_id: str,
        field: str,
        priority_sources: list[str],
        source_type: str,
        document: dict[str, Any],
        component: dict[str, Any],
        collection_path: Path,
        field_hits: list[str],
    ) -> dict[str, Any]:
        priority = priority_sources.index(source_type)
        raw_text = self._routing_text(component)
        score, breakdown = self.base_router.score_evidence(
            source_type=source_type,
            priority=priority,
            match_reason="strong_product_match",
            field_hits=field_hits,
            raw_text=raw_text,
        )
        quality = component.get("quality") if isinstance(component.get("quality"), dict) else {}
        quality_score = float(quality.get("quality_score") or 0.0)
        quality_bonus = min(5, max(0, int(quality_score // 20)))
        breakdown["component_quality"] = quality_bonus
        breakdown["active_component"] = 3
        score += quality_bonus + 3

        source = component.get("source") if isinstance(component.get("source"), dict) else {}
        classified_component_id = str(component.get("classified_component_id") or "")
        document_id = str(document.get("document_id") or source.get("document_id") or "")
        stable_material = "|".join([entity_id, field, document_id, classified_component_id])
        evidence_id = "evc_" + hashlib.sha256(stable_material.encode("utf-8")).hexdigest()[:24]
        location_status = "page_available" if source.get("page_number") is not None else "page_unknown_section_available"

        return {
            "evidence_id": evidence_id,
            "entity_id": entity_id,
            "field": field,
            "document_id": document_id,
            "source_document_id": document.get("source_document_id"),
            "document_hash": document.get("document_hash"),
            "logical_document_key": document.get("logical_document_key"),
            "artifact_type": "classified_component_evidence",
            "source_type": source_type,
            "document_type": source_type,
            "evidence_role": document.get("evidence_role"),
            "authority_score": document.get("authority_score"),
            "priority": priority,
            "routing_score": score,
            "scoring_breakdown": breakdown,
            "match_reason": "registry_backed_product_evidence_intake",
            "matched_aliases": [],
            "field_hits": field_hits,
            "classified_component_id": classified_component_id,
            "normalized_component_id": component.get("normalized_component_id"),
            "component_id": component.get("component_id"),
            "component_type": component.get("component_type"),
            "classified_type": component.get("classified_type"),
            "component_status": component.get("status"),
            "text": component.get("text"),
            "normalized_text": component.get("normalized_text"),
            "display_text": component.get("display_text"),
            "title_hint": component.get("title_hint"),
            "parent_title_hint": component.get("parent_title_hint"),
            "source": source,
            "page": source.get("page_number"),
            "section": source.get("section_id"),
            "location_status": location_status,
            "component_collection_path": self._relative_or_absolute(collection_path),
            "processed_document_path": document.get("relative_path"),
            "raw_evidence_relative_path": document.get("raw_evidence_relative_path"),
            "raw_evidence_path": document.get("raw_evidence_path"),
            "source_url": document.get("source_url"),
            "source_page_url": document.get("source_page_url"),
            "parse_id": document.get("parse_id"),
            "quality_audit_id": document.get("quality_audit_id"),
            "confidence": self.base_router.routing_confidence(score),
            "status": "candidate",
            "selected_reasons": self._selected_reasons(source_type, field_hits, location_status),
        }

    @staticmethod
    def _routing_text(component: dict[str, Any]) -> str:
        return "\n".join(
            str(component.get(key) or "")
            for key in ("text", "normalized_text", "display_text", "title_hint", "parent_title_hint")
        )

    @staticmethod
    def _selected_reasons(source_type: str, field_hits: list[str], location_status: str) -> list[str]:
        reasons = [
            "Product association supplied by registry-backed evidence intake",
            f"Classified component is active and supplied by Department IV ({source_type})",
            "Contains field keywords: " + ", ".join(field_hits[:5]),
        ]
        if location_status == "page_unknown_section_available":
            reasons.append("Page location is unavailable in the classified component; section-level provenance is retained")
        return reasons

    def _build_bundles(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bundles: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            document_id = str(candidate["document_id"])
            bundle = bundles.setdefault(
                document_id,
                {
                    "bundle_id": "bundle_" + hashlib.sha256(document_id.encode("utf-8")).hexdigest()[:24],
                    "document_id": document_id,
                    "entity_id": candidate["entity_id"],
                    "field": candidate["field"],
                    "source_type": candidate["source_type"],
                    "authority_score": candidate["authority_score"],
                    "best_evidence_id": candidate["evidence_id"],
                    "best_routing_score": candidate["routing_score"],
                    "component_candidates": [],
                },
            )
            bundle["component_candidates"].append(
                {
                    "evidence_id": candidate["evidence_id"],
                    "classified_component_id": candidate["classified_component_id"],
                    "routing_score": candidate["routing_score"],
                    "field_hits": candidate["field_hits"],
                    "section": candidate["section"],
                    "page": candidate["page"],
                    "location_status": candidate["location_status"],
                }
            )
            if candidate["routing_score"] > bundle["best_routing_score"]:
                bundle["best_evidence_id"] = candidate["evidence_id"]
                bundle["best_routing_score"] = candidate["routing_score"]

        return sorted(bundles.values(), key=lambda item: (-item["best_routing_score"], item["document_id"]))

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Required registry/artifact does not exist: {path}")
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object at {path}")
        return data

    @staticmethod
    def _resolve_path(path_value: str | Path) -> Path:
        path = Path(path_value)
        return path if path.is_absolute() else (BASE_DIR / path).resolve()

    @staticmethod
    def _relative_or_absolute(path: Path) -> str:
        try:
            return str(path.resolve().relative_to(BASE_DIR.resolve())).replace("\\", "/")
        except ValueError:
            return str(path)
