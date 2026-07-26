from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from knowledge_domains.health.knowledge_manufacturing.knowledge_component_normalizer_models import (
    NORMALIZER_VERSION,
    NORMALIZED_COMPONENT_COLLECTION_CONTRACT_VERSION,
    KnowledgeComponentNormalizerReport,
    NormalizationDecision,
    NormalizedComponent,
    NormalizedKnowledgeComponentCollection,
    stable_id,
    utc_now,
)


class KnowledgeComponentNormalizer:
    """Normalize raw Knowledge Components without insurance semantic interpretation.

    This machine performs document-understanding cleanup only:
    - Unicode/whitespace normalization
    - continuation merging for wrapped fragments
    - metadata/noise detection
    - duplicate consolidation while preserving provenance
    - adjacency links for downstream Topic Composition
    """

    ENGINE_NAME = "KnowledgeComponentNormalizer"
    DEPARTMENT = "department_04_knowledge_manufacturing"
    PRODUCTION_LINE = "knowledge_component_manufacturing"

    FOOTER_PATTERNS = [
        re.compile(r"^product\s+name\s*:\s*.*product\s+uin\s*:", re.I),
        re.compile(r"^activ\s+one\s+policy\s+wording$", re.I),
        re.compile(r"^policy\s+wording$", re.I),
        re.compile(r"^page\s+\d+\s+(of|/)\s+\d+$", re.I),
        re.compile(r"^\d+\s*/\s*\d+$"),
    ]

    HEADER_PATTERNS = [
        re.compile(r"^section\s+[a-z]\b", re.I),
        re.compile(r"^annexure\s+[ivxlcdm]+\b", re.I),
        re.compile(r"^appendix\s+[a-z]\b", re.I),
    ]

    NUMBERED_DEFINITION_RE = re.compile(r"(?:^|\n|\s)(\d{1,3})\.\s*([^:\n]{2,90}):")

    def normalize_unicode(self, text: str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFKC", text)
        replacements = {
            "ﬁ": "fi",
            "ﬂ": "fl",
            "\u00a0": " ",
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
            "–": "-",
            "—": "-",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def key_text(self, text: str) -> str:
        text = self.normalize_unicode(text).lower()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^a-z0-9%₹$./()<> -]+", "", text)
        return text.strip()

    def is_metadata_or_noise(self, text: str) -> tuple[str | None, str | None]:
        key = self.key_text(text)

        match_text = self.normalize_unicode(text).lower()
        match_text = re.sub(r"\s+", " ", match_text).strip()

        if not key:
            return "noise", "empty_or_whitespace"
        if len(key) <= 2 and key not in {"no", "or"}:
            return "noise", "too_short"
        if key in {"or", "and", "the", "of", "to"}:
            return "noise", "connector_only"

        for pattern in self.FOOTER_PATTERNS:
            if pattern.search(match_text):
                return "metadata", "repeated_header_footer_or_product_identity"

        return None, None

    def looks_like_continuation(self, previous: dict[str, Any], current: dict[str, Any]) -> bool:
        """Detect wrapped fragments that should remain one component.

        This is intentionally conservative and domain-independent.
        """
        prev_text = self.normalize_unicode(previous.get("text", ""))
        cur_text = self.normalize_unicode(current.get("text", ""))
        if not prev_text or not cur_text:
            return False

        previous_kind, _ = self.is_metadata_or_noise(prev_text)
        current_kind, _ = self.is_metadata_or_noise(cur_text)

        if previous_kind is not None or current_kind is not None:
            return False

        prev_type = previous.get("component_type")
        cur_type = current.get("component_type")
        if cur_type in {"title", "reference", "noise", "metadata", "table"}:
            return False
        if prev_type in {"title", "reference", "noise", "metadata", "table"}:
            return False

        # Same source section is the safest merge signal.
        prev_source = previous.get("source") or {}
        cur_source = current.get("source") or {}
        same_section = prev_source.get("section_id") == cur_source.get("section_id")
        adjacent_order = (cur_source.get("section_order") or 0) == (prev_source.get("section_order") or 0)
        if not same_section and not adjacent_order:
            return False

        # Continue if current starts lowercase or previous does not end with sentence/definition boundary.
        starts_lower = bool(re.match(r"^[a-z,;)]", cur_text))
        prev_open = not bool(re.search(r"[.:;!?)]\s*$", prev_text))
        current_is_connector = bool(re.match(r"^(and|or|but|however|provided|subject to|wherever|which|that)\b", cur_text, re.I))

        # Avoid merging when current clearly starts a new numbered definition.
        starts_new_numbered_definition = bool(re.match(r"^\d{1,3}\.\s*[^:]{2,90}:", cur_text))
        if starts_new_numbered_definition:
            return False

        return starts_lower or prev_open or current_is_connector

    def split_numbered_definitions(self, component: dict[str, Any]) -> list[dict[str, Any]]:
        """Split only obvious multiple numbered definitions inside one raw component.

        This is still structural because it relies on numbering + colon pattern, not insurance meaning.
        """
        text = self.normalize_unicode(component.get("text", ""))
        matches = list(self.NUMBERED_DEFINITION_RE.finditer(text))
        if len(matches) <= 1:
            return [component]

        parts: list[dict[str, Any]] = []
        for idx, match in enumerate(matches):
            start = match.start(1)
            end = matches[idx + 1].start(1) if idx + 1 < len(matches) else len(text)
            part_text = text[start:end].strip()
            if not part_text:
                continue
            clone = dict(component)
            clone["text"] = part_text
            clone["normalized_text"] = self.key_text(part_text)
            clone["component_id"] = f"{component.get('component_id')}_split_{idx+1}"
            clone["original_component_ids"] = list(
                component.get("original_component_ids")
                or [component.get("component_id")]
            )
            clone["component_type"] = "list_item"
            clone.setdefault("notes", [])
            clone["notes"] = list(clone.get("notes", [])) + [
                "Split from multi-definition raw component by Knowledge Component Normalizer."
            ]
            parts.append(clone)
        return parts or [component]

    def preprocess_components(self, raw_components: list[dict[str, Any]]) -> list[dict[str, Any]]:
        expanded: list[dict[str, Any]] = []
        for comp in raw_components:
            expanded.extend(self.split_numbered_definitions(comp))
        return expanded

    def merge_wrapped_components(self, components: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
        merged: list[dict[str, Any]] = []
        merge_count = 0
        for comp in components:
            comp = dict(comp)
            comp["text"] = self.normalize_unicode(comp.get("text", ""))
            if not comp["text"]:
                continue
            if merged and self.looks_like_continuation(merged[-1], comp):
                prev = merged[-1]
                prev["text"] = self.normalize_unicode(prev.get("text", "") + " " + comp.get("text", ""))
                prev["normalized_text"] = self.key_text(prev["text"])
                prev.setdefault("merged_component_ids", [])
                prev["merged_component_ids"].append(comp.get("component_id"))
                prev.setdefault("references", [])
                prev["references"].extend(comp.get("references") or [])
                prev.setdefault("notes", [])
                prev["notes"].append(
                    f"Merged wrapped continuation component {comp.get('component_id')} during normalization."
                )
                merge_count += 1
            else:
                comp["normalized_text"] = self.key_text(comp.get("text", ""))
                comp["merged_component_ids"] = []
                merged.append(comp)
        return merged, merge_count

    def build_duplicate_index(self, components: list[dict[str, Any]]) -> dict[str, list[int]]:
        groups: dict[str, list[int]] = defaultdict(list)
        for idx, comp in enumerate(components):
            key = self.key_text(comp.get("text", ""))
            if key:
                groups[key].append(idx)
        return {k: v for k, v in groups.items() if len(v) > 1}

    def normalize_component(
        self,
        comp: dict[str, Any],
        normalized_sequence: int,
        duplicate_group_id: str | None,
        duplicate_count: int,
        duplicate_representative: bool,
    ) -> NormalizedComponent:
        text = self.normalize_unicode(comp.get("text", ""))
        normalized_text = self.key_text(text)
        original_type = comp.get("component_type", "paragraph")
        component_type = original_type if original_type in {
            "title", "paragraph", "list_item", "table", "note", "reference", "metadata", "noise"
        } else "paragraph"

        status = "active"
        decisions: list[NormalizationDecision] = []

        noise_type, noise_reason = self.is_metadata_or_noise(text)
        if noise_type == "metadata":
            component_type = "metadata"
            status = "metadata"
            decisions.append(NormalizationDecision("mark_metadata", noise_reason or "metadata_pattern", 0.95))
        elif noise_type == "noise":
            component_type = "noise"
            status = "noise"
            decisions.append(NormalizationDecision("mark_noise", noise_reason or "noise_pattern", 0.9))

        if duplicate_group_id and not duplicate_representative and status == "active":
            status = "duplicate_shadow"
            decisions.append(
                NormalizationDecision(
                    "consolidate_duplicate",
                    "Duplicate text retained as shadow component with provenance preserved.",
                    0.95,
                )
            )

        if comp.get("merged_component_ids"):
            decisions.append(
                NormalizationDecision(
                    "merge_wrapped_fragments",
                    f"Merged {len(comp.get('merged_component_ids') or [])} continuation fragment(s).",
                    0.85,
                )
            )

        # Downgrade false titles: long lowercase sentence-like fragments are not strong titles.
        if component_type == "title":
            if len(text.split()) > 14 and not re.search(r"[:?]$", text.strip()):
                component_type = "paragraph"
                decisions.append(
                    NormalizationDecision(
                        "downgrade_title_to_paragraph",
                        "Long sentence-like title fragment is likely wrapped paragraph text.",
                        0.8,
                    )
                )

        source = comp.get("source") or {}
        signals = dict(comp.get("signals") or {})
        signals.update({
            "normalizer_version": NORMALIZER_VERSION,
            "normalized_word_count": len(normalized_text.split()),
            "duplicate_group_id": duplicate_group_id,
            "duplicate_occurrence_count": duplicate_count,
        })

        quality = dict(comp.get("quality") or {})
        if status in {"noise", "metadata"}:
            quality["quality_score"] = min(float(quality.get("quality_score", 70.0)), 70.0)
            quality["confidence"] = min(float(quality.get("confidence", 0.7)), 0.7)
        elif status == "duplicate_shadow":
            quality["quality_score"] = min(float(quality.get("quality_score", 85.0)), 85.0)

        original_ids = list(
            comp.get("original_component_ids")
            or [comp.get("component_id")]
        )
        original_ids.extend(
            list(comp.get("merged_component_ids") or [])
        )
        original_ids = [x for x in original_ids if x]
        norm_id_seed = "|".join([
            comp.get("document_id", ""),
            comp.get("processed_document_asset_id") or "",
            str(normalized_sequence),
            normalized_text[:160],
        ])

        notes = list(comp.get("notes") or []) + [
            "Normalized Knowledge Component. No insurance semantic interpretation performed."
        ]

        return NormalizedComponent(
            component_id=comp.get("component_id"),
            component_version=comp.get("component_version", "1.0"),
            normalized_component_id=stable_id("nkcomp", norm_id_seed),
            normalized_component_version="1.0",
            component_type=component_type,  # type: ignore[arg-type]
            original_component_type=original_type,
            status=status,  # type: ignore[arg-type]
            document_id=comp.get("document_id", ""),
            processed_document_asset_id=comp.get("processed_document_asset_id"),
            sequence=int(comp.get("sequence", normalized_sequence)),
            normalized_sequence=normalized_sequence,
            text=text,
            normalized_text=normalized_text,
            display_text=text,
            title_hint=comp.get("title_hint"),
            source=source,
            original_component_ids=original_ids,
            merged_component_ids=list(comp.get("merged_component_ids") or []),
            duplicate_group_id=duplicate_group_id,
            duplicate_representative=duplicate_representative,
            duplicate_occurrence_count=duplicate_count,
            parent_title_hint=comp.get("title_hint"),
            signals=signals,
            quality=quality,
            references=list(comp.get("references") or []),
            normalization_decisions=decisions,
            notes=notes,
        )

    def validate(self, components: list[NormalizedComponent]) -> tuple[str, list[dict[str, Any]]]:
        warnings: list[dict[str, Any]] = []
        if not components:
            warnings.append({"type": "empty_collection", "severity": "critical", "message": "No components produced."})
            return "failed", warnings
        missing_provenance = sum(1 for c in components if not c.source or not c.source.get("section_id"))
        if missing_provenance:
            warnings.append({
                "type": "missing_provenance",
                "severity": "medium",
                "message": f"{missing_provenance} normalized components do not have section provenance.",
            })
        ids = [c.normalized_component_id for c in components]
        duplicate_ids = len(ids) - len(set(ids))
        if duplicate_ids:
            warnings.append({
                "type": "duplicate_normalized_ids",
                "severity": "critical",
                "message": f"{duplicate_ids} duplicate normalized component IDs detected.",
            })
            return "failed", warnings
        return "passed", warnings

    def compute_quality(self, statistics: dict[str, Any], validation_status: str) -> float:
        score = 100.0
        if validation_status != "passed":
            score -= 30
        raw = max(statistics.get("raw_components_received", 1), 1)
        duplicate_shadow_rate = statistics.get("duplicate_shadow_components", 0) / raw
        noise_rate = statistics.get("noise_components", 0) / raw
        metadata_rate = statistics.get("metadata_components", 0) / raw
        # Duplicates/metadata are not failures, but too many indicate noisy source material.
        score -= min(duplicate_shadow_rate * 20, 8)
        score -= min(noise_rate * 25, 10)
        score -= min(metadata_rate * 12, 5)
        if statistics.get("components_merged", 0) > 0:
            score += min(statistics["components_merged"] / raw * 5, 2)
        return round(max(min(score, 100.0), 0.0), 2)

    def normalize(self, raw_collection: dict[str, Any], source_path: str | None = None) -> tuple[NormalizedKnowledgeComponentCollection, KnowledgeComponentNormalizerReport]:
        raw_components = list(raw_collection.get("components") or [])
        document_id = raw_collection.get("document_id", "")
        processed_document_asset_id = raw_collection.get("processed_document_asset_id")
        source_collection_id = raw_collection.get("collection_id")

        expanded = self.preprocess_components(raw_components)
        merged, merge_count = self.merge_wrapped_components(expanded)
        duplicate_index_raw = self.build_duplicate_index(merged)

        duplicate_by_index: dict[int, tuple[str, int, bool]] = {}
        duplicate_index: dict[str, Any] = {}
        for key, indexes in duplicate_index_raw.items():
            group_id = stable_id("dupgrp", key)
            duplicate_index[group_id] = {
                "normalized_text": key,
                "occurrence_count": len(indexes),
                "representative_sequence": indexes[0] + 1,
                "component_indexes": [i + 1 for i in indexes],
            }
            for pos, idx in enumerate(indexes):
                duplicate_by_index[idx] = (group_id, len(indexes), pos == 0)

        normalized_components: list[NormalizedComponent] = []
        for idx, comp in enumerate(merged):
            dup_group_id, dup_count, dup_rep = duplicate_by_index.get(idx, (None, 1, True))
            normalized = self.normalize_component(
                comp,
                normalized_sequence=len(normalized_components) + 1,
                duplicate_group_id=dup_group_id,
                duplicate_count=dup_count,
                duplicate_representative=dup_rep,
            )
            normalized_components.append(normalized)

        # Add adjacency after final ordering is known.
        for i, comp in enumerate(normalized_components):
            comp.previous_component_id = normalized_components[i - 1].normalized_component_id if i > 0 else None
            comp.next_component_id = normalized_components[i + 1].normalized_component_id if i + 1 < len(normalized_components) else None

        status_counts = Counter(c.status for c in normalized_components)
        type_counts = Counter(c.component_type for c in normalized_components)
        cross_refs = sum(len(c.references) for c in normalized_components)
        duplicate_shadow_components = status_counts.get("duplicate_shadow", 0)
        noise_components = status_counts.get("noise", 0)
        metadata_components = status_counts.get("metadata", 0)
        active_components = status_counts.get("active", 0)

        statistics = {
            "raw_components_received": len(raw_components),
            "components_after_definition_split": len(expanded),
            "normalized_components_created": len(normalized_components),
            "components_merged": merge_count,
            "duplicate_groups": len(duplicate_index),
            "duplicate_shadow_components": duplicate_shadow_components,
            "noise_components": noise_components,
            "metadata_components": metadata_components,
            "active_components": active_components,
            "component_type_counts": dict(type_counts),
            "status_counts": dict(status_counts),
            "cross_references_preserved": cross_refs,
            "average_words_per_component": round(
                sum(len(c.normalized_text.split()) for c in normalized_components) / max(len(normalized_components), 1), 2
            ),
            "max_words_per_component": max((len(c.normalized_text.split()) for c in normalized_components), default=0),
            "title_to_paragraph_ratio": round(
                type_counts.get("title", 0) / max(type_counts.get("paragraph", 1), 1), 2
            ),
            "department_boundary": "normalized_components_only_no_semantic_insurance_interpretation",
        }

        validation_status, validation_warnings = self.validate(normalized_components)
        warnings = list(validation_warnings)
        if duplicate_shadow_components:
            warnings.append({
                "type": "duplicate_consolidation",
                "severity": "low",
                "message": f"{duplicate_shadow_components} duplicate components retained as duplicate_shadow with provenance preserved.",
            })
        if metadata_components:
            warnings.append({
                "type": "metadata_detected",
                "severity": "low",
                "message": f"{metadata_components} components marked as metadata/header/footer.",
            })

        quality_score = self.compute_quality(statistics, validation_status)
        collection_id = stable_id(
            "nkcc",
            "|".join([document_id, processed_document_asset_id or "", source_collection_id or "", str(len(normalized_components))]),
        )
        report_id = stable_id("kcnr", collection_id + utc_now())

        collection = NormalizedKnowledgeComponentCollection(
            asset_type="normalized_knowledge_component_collection",
            collection_id=collection_id,
            collection_version="1.0",
            contract_version=NORMALIZED_COMPONENT_COLLECTION_CONTRACT_VERSION,
            created_at=utc_now(),
            department=self.DEPARTMENT,
            production_line=self.PRODUCTION_LINE,
            engine=self.ENGINE_NAME,
            document_id=document_id,
            processed_document_asset_id=processed_document_asset_id,
            source_collection_id=source_collection_id,
            source_collection_path=source_path,
            components=normalized_components,
            duplicate_index=duplicate_index,
            noise_index={
                "noise_component_ids": [c.normalized_component_id for c in normalized_components if c.status == "noise"],
                "metadata_component_ids": [c.normalized_component_id for c in normalized_components if c.status == "metadata"],
            },
            statistics=statistics,
            quality={"quality_score": quality_score},
            validation={"status": validation_status, "warnings": validation_warnings},
        )

        report = KnowledgeComponentNormalizerReport(
            report_type="knowledge_component_normalizer_report",
            report_id=report_id,
            report_version="1.0",
            created_at=utc_now(),
            department=self.DEPARTMENT,
            production_line=self.PRODUCTION_LINE,
            engine=self.ENGINE_NAME,
            document_id=document_id,
            processed_document_asset_id=processed_document_asset_id,
            source_collection_id=source_collection_id,
            source_collection_path=source_path,
            normalized_collection_id=collection_id,
            normalized_collection_path=None,
            raw_components_received=len(raw_components),
            normalized_components_created=len(normalized_components),
            components_merged=merge_count,
            duplicate_groups=len(duplicate_index),
            duplicate_shadow_components=duplicate_shadow_components,
            noise_components=noise_components,
            metadata_components=metadata_components,
            active_components=active_components,
            cross_references_preserved=cross_refs,
            warnings=warnings,
            quality_score=quality_score,
            validation_status=validation_status,
            statistics=statistics,
            department_boundary=statistics["department_boundary"],
        )
        return collection, report


class KnowledgeComponentNormalizerRunner:
    def __init__(self, project_root: Path, output_dir: Path | None = None):
        self.project_root = project_root
        self.output_dir = output_dir if output_dir is not None else project_root / "knowledge" / "factory" / "normalized_knowledge_components"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.normalizer = KnowledgeComponentNormalizer()

    def run(self, component_collection_path: Path) -> dict[str, Any]:
        with component_collection_path.open("r", encoding="utf-8") as f:
            raw_collection = json.load(f)

        collection, report = self.normalizer.normalize(
            raw_collection,
            source_path=str(component_collection_path),
        )

        stem = f"{collection.document_id}_{collection.processed_document_asset_id}_{collection.collection_id}"
        collection_path = self.output_dir / f"{stem}_normalized_component_collection.json"
        report_path = self.output_dir / f"{stem}_normalizer_report.json"
        report.normalized_collection_path = str(collection_path)

        with collection_path.open("w", encoding="utf-8") as f:
            json.dump(collection.to_dict(), f, indent=2, ensure_ascii=False)
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

        return {
            "collection": collection,
            "report": report,
            "collection_path": collection_path,
            "report_path": report_path,
        }
