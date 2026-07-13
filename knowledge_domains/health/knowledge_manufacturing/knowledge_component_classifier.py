"""
PolicyScna Department IV - Knowledge Component Classifier v1.0

Mission:
    Transform a Normalized Knowledge Component Collection into a Classified
    Knowledge Component Collection by assigning document-level component roles.

Boundary:
    This engine classifies document structure/intent only.
    It does not interpret insurance concepts such as benefits, covers, exclusions,
    waiting periods, or product features as insurance semantics.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from knowledge_domains.health.knowledge_manufacturing.knowledge_component_classifier_models import (
    CLASSIFIER_VERSION,
    CONTRACT_VERSION,
    DEPARTMENT_BOUNDARY,
    ClassifiedKnowledgeComponent,
    ClassifiedKnowledgeComponentCollection,
    ComponentClassification,
    ClassificationDecision,
    KnowledgeComponentClassifierReport,
    stable_hash,
    utc_now_iso,
)


class KnowledgeComponentClassifier:
    """Classifies normalized components into document-level component roles."""

    def __init__(self, project_root: Optional[Path] = None, output_dir: Optional[Path] = None) -> None:
        self.project_root = Path(project_root or Path.cwd())
        self.output_dir = Path(output_dir) if output_dir is not None else self.project_root / "knowledge" / "factory" / "classified_knowledge_components"

    def classify_file(self, normalized_collection_path: Path, dry_run: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        normalized_collection_path = Path(normalized_collection_path)
        with normalized_collection_path.open("r", encoding="utf-8") as f:
            source_collection = json.load(f)

        collection = self.classify_collection(source_collection, str(normalized_collection_path))
        report = self.build_report(source_collection, collection, str(normalized_collection_path))

        if not dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            collection_path = self._collection_path(collection)
            report_path = self._report_path(collection, report)
            report["classified_collection_path"] = str(collection_path)

            with collection_path.open("w", encoding="utf-8") as f:
                json.dump(collection, f, ensure_ascii=False, indent=2)
            with report_path.open("w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        return collection, report

    def classify_collection(self, source_collection: Dict[str, Any], source_path: str = "") -> Dict[str, Any]:
        components = source_collection.get("components", [])
        document_id = source_collection.get("document_id", "unknown_document")
        processed_document_asset_id = source_collection.get("processed_document_asset_id", "unknown_processed_document")
        source_collection_id = source_collection.get("collection_id", "unknown_normalized_collection")

        collection_id = stable_hash(
            f"classified|{document_id}|{processed_document_asset_id}|{source_collection_id}|{len(components)}",
            "ckcc",
        )

        classified_components: List[ClassifiedKnowledgeComponent] = []
        for index, component in enumerate(components, start=1):
            classification = self.classify_component(component)
            classified_id = stable_hash(
                f"{collection_id}|{component.get('normalized_component_id') or component.get('component_id')}|{index}|{classification.classified_type}",
                "ckcomp",
            )
            notes = list(component.get("notes", []))
            notes.append("Classified Knowledge Component. No insurance semantic interpretation performed.")

            classified_components.append(
                ClassifiedKnowledgeComponent(
                    classified_component_id=classified_id,
                    classified_component_version="1.0",
                    normalized_component_id=component.get("normalized_component_id", component.get("component_id", "")),
                    normalized_component_version=component.get("normalized_component_version", "1.0"),
                    component_id=component.get("component_id", ""),
                    component_version=component.get("component_version", "1.0"),
                    component_type=component.get("component_type", "unknown"),
                    original_component_type=component.get("original_component_type", component.get("component_type", "unknown")),
                    classified_type=classification.classified_type,
                    status=component.get("status", "active"),
                    document_id=component.get("document_id", document_id),
                    processed_document_asset_id=component.get("processed_document_asset_id", processed_document_asset_id),
                    sequence=int(component.get("sequence", index) or index),
                    normalized_sequence=int(component.get("normalized_sequence", index) or index),
                    classified_sequence=index,
                    text=component.get("text", ""),
                    normalized_text=component.get("normalized_text", self._normalize_text(component.get("text", ""))),
                    display_text=component.get("display_text", component.get("text", "")),
                    title_hint=component.get("title_hint"),
                    source=component.get("source", {}),
                    original_component_ids=list(component.get("original_component_ids", [])),
                    merged_component_ids=list(component.get("merged_component_ids", [])),
                    duplicate_group_id=component.get("duplicate_group_id"),
                    duplicate_representative=bool(component.get("duplicate_representative", True)),
                    duplicate_occurrence_count=int(component.get("duplicate_occurrence_count", 1) or 1),
                    previous_component_id=component.get("previous_component_id"),
                    next_component_id=component.get("next_component_id"),
                    previous_classified_component_id=None,
                    next_classified_component_id=None,
                    parent_title_hint=component.get("parent_title_hint"),
                    signals=dict(component.get("signals", {})),
                    quality=dict(component.get("quality", {})),
                    references=list(component.get("references", [])),
                    normalization_decisions=list(component.get("normalization_decisions", [])),
                    classification=classification,
                    notes=notes,
                )
            )

        # Populate classified adjacency without modifying original adjacency.
        for i, component in enumerate(classified_components):
            if i > 0:
                component.previous_classified_component_id = classified_components[i - 1].classified_component_id
            if i + 1 < len(classified_components):
                component.next_classified_component_id = classified_components[i + 1].classified_component_id

        collection = ClassifiedKnowledgeComponentCollection(
            asset_type="classified_knowledge_component_collection",
            collection_id=collection_id,
            collection_version="1.0",
            contract_version=CONTRACT_VERSION,
            created_at=utc_now_iso(),
            department="department_04_knowledge_manufacturing",
            production_line="knowledge_component_manufacturing",
            engine="KnowledgeComponentClassifier",
            document_id=document_id,
            processed_document_asset_id=processed_document_asset_id,
            source_normalized_collection_id=source_collection_id,
            source_normalized_collection_path=source_path,
            components=classified_components,
        )
        return collection.to_dict()

    def classify_component(self, component: Dict[str, Any]) -> ComponentClassification:
        original_type = component.get("component_type", "unknown")
        status = component.get("status", "active")
        text = component.get("display_text") or component.get("text") or ""
        normalized_text = component.get("normalized_text") or self._normalize_text(text)
        signals = component.get("signals", {}) or {}

        reasons: List[str] = []
        decisions: List[ClassificationDecision] = []

        def decision(kind: str, reason: str, confidence: float) -> ComponentClassification:
            reasons.append(reason)
            decisions.append(ClassificationDecision("classify_component", reason, confidence))
            return ComponentClassification(
                classified_type=kind,
                original_component_type=original_type,
                confidence=confidence,
                reasons=reasons,
                decisions=decisions,
            )

        if status == "noise" or original_type == "noise" or signals.get("is_noise_like"):
            return decision("noise", "Component already marked as noise by upstream production line.", 0.95)

        if self._is_metadata(normalized_text):
            return decision("metadata", "Recognized document metadata/footer pattern.", 0.95)

        if original_type == "table" or signals.get("is_table_like"):
            return decision("table", "Component has table structural signal.", 0.95)

        if original_type == "reference" or signals.get("contains_cross_reference") or self._contains_reference(normalized_text):
            return decision("reference", "Component contains cross-reference language.", 0.90)

        if self._is_note(normalized_text):
            return decision("note", "Component starts with note/important/caution marker.", 0.90)

        if self._is_example(normalized_text):
            return decision("example", "Component contains example/illustration marker.", 0.90)

        if self._is_definition(normalized_text):
            return decision("definition", "Component matches definition pattern such as numbered term plus means/refers/is.", 0.88)

        if self._is_condition(normalized_text):
            return decision("condition", "Component contains conditional language.", 0.86)

        if self._is_exception(normalized_text):
            return decision("exception", "Component contains exclusion/exception/not-applicable language.", 0.86)

        if self._is_limit(normalized_text):
            return decision("limit", "Component contains limit, percentage, amount, maximum, or duration language.", 0.84)

        if self._is_procedure(normalized_text):
            return decision("procedure", "Component contains procedural action language.", 0.84)

        if self._is_rule(normalized_text):
            return decision("rule", "Component contains mandatory/obligation/entitlement language.", 0.82)

        if original_type == "title" or signals.get("is_heading_like"):
            return decision("title", "Component has title/heading structural signal.", 0.82)

        if original_type == "list_item" or signals.get("is_list_like"):
            return decision("list_item", "Component has list item structural signal but no stronger role matched.", 0.78)

        if original_type == "paragraph":
            return decision("paragraph", "Component is paragraph text with no stronger role matched.", 0.76)

        return decision("unknown", "No confident document-level classification matched.", 0.50)

    def build_report(self, source_collection: Dict[str, Any], collection: Dict[str, Any], source_path: str) -> Dict[str, Any]:
        components = collection.get("components", [])
        counts = Counter(c.get("classified_type", "unknown") for c in components)
        status_counts = Counter(c.get("status", "active") for c in components)
        low_confidence = sum(1 for c in components if (c.get("classification", {}).get("confidence", 0.0) < 0.75))
        warnings: List[Dict[str, Any]] = []
        if low_confidence:
            warnings.append({
                "type": "low_confidence_classification",
                "severity": "medium",
                "message": f"{low_confidence} component(s) have classification confidence below 0.75.",
            })

        quality_score = self._quality_score(total=len(components), low_confidence=low_confidence)
        validation_status = "passed" if components and quality_score >= 90.0 else "needs_review"

        report_id = stable_hash(
            f"report|{collection.get('collection_id')}|{len(components)}|{','.join(sorted(counts))}",
            "kclr",
        )
        classified_collection_path = str(self._collection_path(collection))
        statistics = {
            "normalized_components_received": len(source_collection.get("components", [])),
            "classified_components_created": len(components),
            "status_counts": dict(status_counts),
            "classification_type_counts": dict(counts),
            "low_confidence_components": low_confidence,
            "average_words_per_component": self._average_words(components),
            "max_words_per_component": self._max_words(components),
            "department_boundary": DEPARTMENT_BOUNDARY,
        }

        report = KnowledgeComponentClassifierReport(
            report_type="knowledge_component_classifier_report",
            report_id=report_id,
            report_version="1.0",
            created_at=utc_now_iso(),
            department="department_04_knowledge_manufacturing",
            production_line="knowledge_component_manufacturing",
            engine="KnowledgeComponentClassifier",
            document_id=collection.get("document_id", "unknown_document"),
            processed_document_asset_id=collection.get("processed_document_asset_id", "unknown_processed_document"),
            source_normalized_collection_id=collection.get("source_normalized_collection_id", "unknown_normalized_collection"),
            source_normalized_collection_path=source_path,
            classified_collection_id=collection.get("collection_id", "unknown_classified_collection"),
            classified_collection_path=classified_collection_path,
            normalized_components_received=len(source_collection.get("components", [])),
            classified_components_created=len(components),
            active_components=status_counts.get("active", 0),
            duplicate_shadow_components=status_counts.get("duplicate_shadow", 0),
            noise_components=counts.get("noise", 0),
            metadata_components=counts.get("metadata", 0),
            classification_type_counts=dict(counts),
            low_confidence_components=low_confidence,
            warnings=warnings,
            quality_score=quality_score,
            validation_status=validation_status,
            department_boundary=DEPARTMENT_BOUNDARY,
            statistics=statistics,
            next_stage="knowledge_topic_composition",
        )
        return report.to_dict()

    def _collection_path(self, collection: Dict[str, Any]) -> Path:
        name = (
            f"{collection.get('document_id')}_"
            f"{collection.get('processed_document_asset_id')}_"
            f"{collection.get('collection_id')}_"
            "classified_component_collection.json"
        )
        return self.output_dir / name

    def _report_path(self, collection: Dict[str, Any], report: Dict[str, Any]) -> Path:
        name = (
            f"{collection.get('document_id')}_"
            f"{collection.get('processed_document_asset_id')}_"
            f"{collection.get('collection_id')}_"
            "classifier_report.json"
        )
        return self.output_dir / name

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[\u2018\u2019]", "'", text)
        text = re.sub(r"[\u201c\u201d]", '"', text)
        text = re.sub(r"[^a-z0-9%₹$./()<>\-\s]+", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _is_metadata(text: str) -> bool:
        return bool(
            re.search(r"\b(product name|product uin|uin|policy wording|version|irda|irdai registration|cin)\b", text)
            and len(text.split()) <= 30
        )

    @staticmethod
    def _contains_reference(text: str) -> bool:
        return bool(re.search(r"\b(refer|appendix|annexure|section|clause|schedule|table)\b", text))

    @staticmethod
    def _is_note(text: str) -> bool:
        return bool(re.match(r"^(note|important|caution|please note|provided always)", text))

    @staticmethod
    def _is_example(text: str) -> bool:
        return bool(re.search(r"\b(example|illustration|for instance|e\.g\.)\b", text))

    @staticmethod
    def _is_definition(text: str) -> bool:
        return bool(
            re.match(r"^(\d+\.|[a-z]\.)?\s*[a-z][a-z0-9 /()\-]{2,80}\s+(means|mean|refers to|is defined as|shall mean|means and includes|is a|are)\b", text)
            or re.match(r"^\d+\.\s*[a-z][a-z0-9 /()\-]{2,80}:\s+", text)
        )

    @staticmethod
    def _is_condition(text: str) -> bool:
        return bool(re.search(r"\b(provided that|subject to|if|only if|where|when|unless|provided always|applicable if|condition)\b", text))

    @staticmethod
    def _is_exception(text: str) -> bool:
        return bool(re.search(r"\b(excluded|exclusion|not covered|not payable|not applicable|shall not|will not be liable|except)\b", text))

    @staticmethod
    def _is_limit(text: str) -> bool:
        return bool(re.search(r"\b(up to|maximum|max|min|minimum|limit|limited to|sum insured|percentage|%|₹|rs\.?|inr|days|hours|months|years)\b", text))

    @staticmethod
    def _is_procedure(text: str) -> bool:
        return bool(re.search(r"\b(submit|notify|inform|file|upload|call|contact|send|provide documents|claim form|process|procedure)\b", text))

    @staticmethod
    def _is_rule(text: str) -> bool:
        return bool(re.search(r"\b(shall|must|will be|will have to|has to|required to|payable|eligible|liable|responsible)\b", text))

    @staticmethod
    def _quality_score(total: int, low_confidence: int) -> float:
        if total <= 0:
            return 0.0
        penalty = (low_confidence / total) * 20.0
        return round(max(0.0, 100.0 - penalty), 2)

    @staticmethod
    def _average_words(components: Iterable[Dict[str, Any]]) -> float:
        counts = [len((c.get("normalized_text") or c.get("display_text") or "").split()) for c in components]
        if not counts:
            return 0.0
        return round(sum(counts) / len(counts), 2)

    @staticmethod
    def _max_words(components: Iterable[Dict[str, Any]]) -> int:
        counts = [len((c.get("normalized_text") or c.get("display_text") or "").split()) for c in components]
        return max(counts) if counts else 0
