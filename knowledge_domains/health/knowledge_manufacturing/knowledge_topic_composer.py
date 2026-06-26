"""
PolicyScna Department IV - Knowledge Topic Composer v1.0

Mission:
    Transform a Classified Knowledge Component Collection into a Knowledge
    Topic Collection by grouping related classified components into
    advisor-conversation topics.

Boundary:
    This engine composes document-level roles into self-contained topics.
    It does not perform concept recognition, canonicalization, ontology mapping,
    recommendation logic, or insurance semantic interpretation.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from knowledge_domains.health.knowledge_manufacturing.knowledge_topic_composer_models import (
    COMPOSER_VERSION,
    CONTRACT_VERSION,
    DEPARTMENT_BOUNDARY,
    AdvisorConversationSlots,
    KnowledgeTopic,
    KnowledgeTopicCollection,
    KnowledgeTopicComposerReport,
    TopicCompositionDecision,
    stable_hash,
    utc_now_iso,
)


TOPIC_START_ROLES = {"title", "definition", "procedure", "table"}
SUPPORTING_ROLES = {"paragraph", "rule", "condition", "limit", "exception", "example", "reference", "note", "list_item"}
SKIPPED_ROLES = {"noise", "metadata"}


class KnowledgeTopicComposer:
    """Composes classified components into advisor-conversation Knowledge Topics."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = Path(project_root or Path.cwd())
        self.output_dir = self.project_root / "knowledge" / "factory" / "knowledge_topics"

    def compose_file(self, classified_collection_path: Path, dry_run: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        classified_collection_path = Path(classified_collection_path)
        with classified_collection_path.open("r", encoding="utf-8") as f:
            source_collection = json.load(f)

        collection = self.compose_collection(source_collection, str(classified_collection_path))
        report = self.build_report(source_collection, collection, str(classified_collection_path))

        if not dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            collection_path = self._collection_path(collection)
            report_path = self._report_path(collection, report)
            report["topic_collection_path"] = str(collection_path)

            with collection_path.open("w", encoding="utf-8") as f:
                json.dump(collection, f, ensure_ascii=False, indent=2)
            with report_path.open("w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        return collection, report

    def compose_collection(self, source_collection: Dict[str, Any], source_path: str = "") -> Dict[str, Any]:
        components = source_collection.get("components", [])
        document_id = source_collection.get("document_id", "unknown_document")
        processed_document_asset_id = source_collection.get("processed_document_asset_id", "unknown_processed_document")
        source_collection_id = source_collection.get("collection_id", "unknown_classified_collection")

        collection_id = stable_hash(
            f"topics|{document_id}|{processed_document_asset_id}|{source_collection_id}|{len(components)}",
            "ktcc",
        )

        groups = self._build_topic_groups(components)
        topics: List[KnowledgeTopic] = []

        for index, group in enumerate(groups, start=1):
            topic = self._manufacture_topic(
                group=group,
                topic_sequence=index,
                collection_id=collection_id,
                document_id=document_id,
                processed_document_asset_id=processed_document_asset_id,
                source_collection_id=source_collection_id,
            )
            topics.append(topic)

        collection = KnowledgeTopicCollection(
            asset_type="knowledge_topic_collection",
            collection_id=collection_id,
            collection_version="1.0",
            contract_version=CONTRACT_VERSION,
            created_at=utc_now_iso(),
            department="department_04_knowledge_manufacturing",
            production_line="knowledge_topic_composition",
            engine="KnowledgeTopicComposer",
            document_id=document_id,
            processed_document_asset_id=processed_document_asset_id,
            source_classified_collection_id=source_collection_id,
            source_classified_collection_path=source_path,
            topics=topics,
        )
        return collection.to_dict()

    def _build_topic_groups(self, components: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        groups: List[List[Dict[str, Any]]] = []
        current: List[Dict[str, Any]] = []

        for component in components:
            role = component.get("classified_type", component.get("component_type", "unknown"))
            status = component.get("status", "active")
            if role in SKIPPED_ROLES or status in {"noise", "duplicate_shadow"}:
                continue

            if not current:
                current = [component]
                continue

            if self._should_start_new_topic(component, current):
                groups.append(current)
                current = [component]
            else:
                current.append(component)

        if current:
            groups.append(current)

        return groups

    def _should_start_new_topic(self, component: Dict[str, Any], current: List[Dict[str, Any]]) -> bool:
        role = component.get("classified_type", "unknown")
        current_roles = [c.get("classified_type", "unknown") for c in current]
        current_len = len(current)

        text = component.get("display_text") or component.get("text") or ""
        norm = component.get("normalized_text") or self._normalize_text(text)
        previous = current[-1]
        prev_source = previous.get("source", {}) or {}
        this_source = component.get("source", {}) or {}

        # Strong new definitions usually begin a new advisor conversation.
        if role == "definition" and current_len >= 1:
            if self._looks_like_numbered_term(norm) or self._extract_topic_name(component):
                return True

        # Strong heading/procedure/table after a mature topic starts a new topic.
        if role in {"title", "procedure", "table"} and current_len >= 2:
            return True

        # A new parent title with a strong role usually starts a new topic.
        if role in TOPIC_START_ROLES and self._parent_changed(component, previous) and current_len >= 1:
            return True

        # Section jump plus strong starter is a boundary.
        if role in TOPIC_START_ROLES:
            prev_order = prev_source.get("section_order")
            this_order = this_source.get("section_order")
            if isinstance(prev_order, int) and isinstance(this_order, int) and this_order > prev_order + 1:
                return True

        # Oversized topics should close when another strong candidate appears.
        if current_len >= 8 and role in {"definition", "title", "procedure"}:
            return True

        # Multiple numbered definitions accidentally merged upstream: start a new topic.
        if role == "definition" and self._contains_multiple_numbered_terms(norm):
            return True

        return False

    def _manufacture_topic(
        self,
        group: List[Dict[str, Any]],
        topic_sequence: int,
        collection_id: str,
        document_id: str,
        processed_document_asset_id: str,
        source_collection_id: str,
    ) -> KnowledgeTopic:
        topic_name = self._derive_topic_name(group, topic_sequence)
        topic_type = self._derive_topic_type(group)
        primary_question = self._primary_question(topic_name, topic_type)
        component_ids = [c.get("component_id", "") for c in group if c.get("component_id")]
        classified_ids = [c.get("classified_component_id", "") for c in group if c.get("classified_component_id")]
        role_counts = Counter(c.get("classified_type", "unknown") for c in group)
        slots = self._build_conversation_slots(group)
        evidence = self._collect_evidence(group)
        references = self._collect_references(group)
        cohesion_score = self._cohesion_score(group)
        completeness_score = self._completeness_score(role_counts)
        validation_status = "passed" if cohesion_score >= 70.0 and completeness_score >= 55.0 else "needs_review"
        topic_id = stable_hash(
            f"{collection_id}|{topic_sequence}|{topic_name}|{','.join(classified_ids[:5])}|{len(group)}",
            "ktopic",
        )

        decisions = [
            TopicCompositionDecision(
                action="compose_topic",
                reason="Grouped classified components into one advisor-conversation topic.",
                confidence=round(cohesion_score / 100.0, 2),
            ).to_dict()
        ]

        return KnowledgeTopic(
            topic_id=topic_id,
            topic_version="1.0",
            topic_sequence=topic_sequence,
            topic_name=topic_name,
            topic_type=topic_type,
            primary_business_question=primary_question,
            advisor_explanation_goal=f"Explain {topic_name} as one self-contained advisor conversation.",
            status="active" if validation_status == "passed" else "needs_review",
            lifecycle_stage="composed",
            document_id=document_id,
            processed_document_asset_id=processed_document_asset_id,
            source_classified_collection_id=source_collection_id,
            component_ids=component_ids,
            classified_component_ids=classified_ids,
            component_count=len(group),
            active_component_count=sum(1 for c in group if c.get("status", "active") == "active"),
            component_role_counts=dict(role_counts),
            advisor_conversation_slots=slots,
            evidence=evidence,
            references=references,
            relationships={
                "parent_topic_id": None,
                "child_topic_ids": [],
                "related_topic_ids": [],
                "prerequisite_topic_ids": [],
                "dependent_topic_ids": [],
                "relationship_status": "not_resolved_in_v1",
            },
            quality={
                "cohesion_score": cohesion_score,
                "completeness_score": completeness_score,
                "confidence": round(min(cohesion_score, completeness_score) / 100.0, 2),
                "validation_status": validation_status,
                "warnings": self._topic_warnings(group, role_counts, cohesion_score, completeness_score),
            },
            composition={
                "composer_version": COMPOSER_VERSION,
                "boundary": DEPARTMENT_BOUNDARY,
                "composition_strategy": "rule_based_advisor_conversation_grouping",
                "decisions": decisions,
            },
            notes=[
                "Knowledge Topic composed from classified components.",
                "No concept recognition, canonicalization, or insurance semantic interpretation performed.",
            ],
        )

    def _build_conversation_slots(self, group: List[Dict[str, Any]]) -> AdvisorConversationSlots:
        slots = AdvisorConversationSlots()
        for component in group:
            role = component.get("classified_type", "unknown")
            cid = component.get("classified_component_id") or component.get("component_id") or ""
            if role == "title":
                slots.title.append(cid)
            elif role == "definition":
                slots.definition.append(cid)
            elif role == "rule":
                slots.rules.append(cid)
            elif role == "condition":
                slots.conditions.append(cid)
            elif role == "limit":
                slots.limits.append(cid)
            elif role == "exception":
                slots.exceptions.append(cid)
            elif role == "example":
                slots.examples.append(cid)
            elif role == "procedure":
                slots.procedures.append(cid)
            elif role == "reference":
                slots.references.append(cid)
            elif role == "note":
                slots.notes.append(cid)
            else:
                slots.supporting_details.append(cid)
        return slots

    def _derive_topic_name(self, group: List[Dict[str, Any]], sequence: int) -> str:
        for component in group:
            name = self._extract_topic_name(component)
            if name:
                return name
        for component in group:
            title_hint = component.get("parent_title_hint") or component.get("title_hint")
            if title_hint and not self._is_generic_title(title_hint):
                return self._clean_topic_name(title_hint)
        first = group[0].get("display_text") or group[0].get("text") or ""
        return self._clean_topic_name(first[:80]) or f"Topic {sequence}"

    def _extract_topic_name(self, component: Dict[str, Any]) -> Optional[str]:
        text = component.get("display_text") or component.get("text") or ""
        text = re.sub(r"\s+", " ", text).strip()
        # Numbered definition: 12. Day Care Centre: means...
        match = re.match(r"^\s*(?:\d+\.?\s*)?([A-Z][A-Za-z0-9 /&(),.'\-]{2,80}?):\s+", text)
        if match:
            candidate = match.group(1).strip()
            if not self._is_generic_title(candidate):
                return self._clean_topic_name(candidate)
        # Heading-like short text.
        role = component.get("classified_type") or component.get("component_type")
        if role == "title" and len(text.split()) <= 12:
            return self._clean_topic_name(text)
        return None

    def _derive_topic_type(self, group: List[Dict[str, Any]]) -> str:
        roles = Counter(c.get("classified_type", "unknown") for c in group)
        if roles.get("procedure", 0):
            return "procedure_topic"
        if roles.get("definition", 0):
            return "definition_topic"
        if roles.get("table", 0):
            return "table_topic"
        if roles.get("exception", 0) > roles.get("condition", 0):
            return "exception_topic"
        if roles.get("limit", 0):
            return "limit_topic"
        if roles.get("condition", 0):
            return "condition_topic"
        return "general_topic"

    def _primary_question(self, topic_name: str, topic_type: str) -> str:
        if topic_type == "procedure_topic":
            return f"How does {topic_name} work?"
        if topic_type == "exception_topic":
            return f"What is excluded or restricted under {topic_name}?"
        if topic_type == "limit_topic":
            return f"What limits apply to {topic_name}?"
        if topic_type == "condition_topic":
            return f"What conditions apply to {topic_name}?"
        return f"What is {topic_name}?"

    def _collect_evidence(self, group: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        evidence: List[Dict[str, Any]] = []
        seen = set()
        for component in group:
            source = component.get("source", {}) or {}
            key = (
                source.get("document_id"),
                source.get("section_id"),
                source.get("section_order"),
                source.get("page_number"),
            )
            if key in seen:
                continue
            seen.add(key)
            evidence.append({
                "document_id": source.get("document_id"),
                "processed_document_asset_id": source.get("processed_document_asset_id"),
                "source_document_type": source.get("source_document_type"),
                "authority_score": source.get("authority_score"),
                "section_id": source.get("section_id"),
                "section_order": source.get("section_order"),
                "page_number": source.get("page_number"),
                "page_label": source.get("page_label"),
                "component_ids": [c.get("classified_component_id") for c in group if (c.get("source", {}) or {}).get("section_id") == source.get("section_id")],
            })
        return evidence

    def _collect_references(self, group: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        refs: List[Dict[str, Any]] = []
        seen = set()
        for component in group:
            for ref in component.get("references", []) or []:
                key = ref.get("reference_id") or (ref.get("text"), ref.get("normalized_target"))
                if key in seen:
                    continue
                seen.add(key)
                refs.append(ref)
        return refs

    def _cohesion_score(self, group: List[Dict[str, Any]]) -> float:
        if not group:
            return 0.0
        score = 65.0
        sections = {(c.get("source", {}) or {}).get("section_id") for c in group}
        parents = {c.get("parent_title_hint") or c.get("title_hint") for c in group if c.get("parent_title_hint") or c.get("title_hint")}
        roles = {c.get("classified_type", "unknown") for c in group}
        if len(sections) <= 2:
            score += 10
        elif len(sections) <= 4:
            score += 4
        else:
            score -= min(15, len(sections))
        if len(parents) <= 2:
            score += 8
        elif len(parents) > 5:
            score -= 8
        if "definition" in roles:
            score += 7
        if roles.intersection({"condition", "limit", "exception", "example", "reference", "rule"}):
            score += 5
        if len(group) > 12:
            score -= min(15, len(group) - 12)
        return round(max(0.0, min(100.0, score)), 2)

    def _completeness_score(self, role_counts: Counter) -> float:
        score = 40.0
        if role_counts.get("definition") or role_counts.get("title"):
            score += 25
        if role_counts.get("rule") or role_counts.get("condition"):
            score += 12
        if role_counts.get("limit"):
            score += 8
        if role_counts.get("exception"):
            score += 7
        if role_counts.get("reference"):
            score += 5
        if role_counts.get("example"):
            score += 3
        return round(max(0.0, min(100.0, score)), 2)

    def _topic_warnings(self, group: List[Dict[str, Any]], role_counts: Counter, cohesion: float, completeness: float) -> List[Dict[str, Any]]:
        warnings: List[Dict[str, Any]] = []
        if cohesion < 70:
            warnings.append({"type": "low_cohesion", "severity": "medium", "message": "Topic cohesion score is below 70."})
        if completeness < 55:
            warnings.append({"type": "incomplete_topic", "severity": "medium", "message": "Topic may not answer a complete business question."})
        if len(group) > 12:
            warnings.append({"type": "oversized_topic", "severity": "medium", "message": "Topic has many components and may need splitting."})
        if not (role_counts.get("definition") or role_counts.get("title")):
            warnings.append({"type": "weak_topic_starter", "severity": "low", "message": "Topic has no title or definition component."})
        return warnings

    def build_report(self, source_collection: Dict[str, Any], collection: Dict[str, Any], source_path: str) -> Dict[str, Any]:
        topics = collection.get("topics", [])
        source_components = source_collection.get("components", [])
        skipped = [c for c in source_components if c.get("classified_type") in SKIPPED_ROLES or c.get("status") in {"noise", "duplicate_shadow"}]
        assigned = sum(t.get("component_count", 0) for t in topics)
        incomplete = sum(1 for t in topics if t.get("quality", {}).get("validation_status") != "passed")
        component_counts = [t.get("component_count", 0) for t in topics]
        cohesion_scores = [t.get("quality", {}).get("cohesion_score", 0.0) for t in topics]
        topic_type_counts = Counter(t.get("topic_type", "unknown") for t in topics)
        warnings: List[Dict[str, Any]] = []
        if incomplete:
            warnings.append({
                "type": "incomplete_topics_present",
                "severity": "medium",
                "message": f"{incomplete} topic(s) need review.",
            })

        quality_score = self._report_quality_score(topics, incomplete)
        validation_status = "passed" if topics and quality_score >= 85.0 else "needs_review"
        report_id = stable_hash(
            f"topic_report|{collection.get('collection_id')}|{len(topics)}|{assigned}|{incomplete}",
            "ktcr",
        )
        topic_collection_path = str(self._collection_path(collection))
        stats = {
            "classified_components_received": len(source_components),
            "components_assigned": assigned,
            "components_skipped": len(skipped),
            "topic_type_counts": dict(topic_type_counts),
            "average_components_per_topic": self._average(component_counts),
            "largest_topic_component_count": max(component_counts) if component_counts else 0,
            "smallest_topic_component_count": min(component_counts) if component_counts else 0,
            "average_cohesion_score": self._average(cohesion_scores),
            "department_boundary": DEPARTMENT_BOUNDARY,
        }

        report = KnowledgeTopicComposerReport(
            report_type="knowledge_topic_composer_report",
            report_id=report_id,
            report_version="1.0",
            created_at=utc_now_iso(),
            department="department_04_knowledge_manufacturing",
            production_line="knowledge_topic_composition",
            engine="KnowledgeTopicComposer",
            document_id=collection.get("document_id", "unknown_document"),
            processed_document_asset_id=collection.get("processed_document_asset_id", "unknown_processed_document"),
            source_classified_collection_id=collection.get("source_classified_collection_id", "unknown_classified_collection"),
            source_classified_collection_path=source_path,
            topic_collection_id=collection.get("collection_id", "unknown_topic_collection"),
            topic_collection_path=topic_collection_path,
            classified_components_received=len(source_components),
            components_assigned=assigned,
            components_skipped=len(skipped),
            topics_created=len(topics),
            active_topics=sum(1 for t in topics if t.get("status") == "active"),
            incomplete_topics=incomplete,
            orphan_components=max(0, len(source_components) - len(skipped) - assigned),
            average_components_per_topic=self._average(component_counts),
            largest_topic_component_count=max(component_counts) if component_counts else 0,
            smallest_topic_component_count=min(component_counts) if component_counts else 0,
            average_cohesion_score=self._average(cohesion_scores),
            topic_type_counts=dict(topic_type_counts),
            warnings=warnings,
            quality_score=quality_score,
            validation_status=validation_status,
            department_boundary=DEPARTMENT_BOUNDARY,
            statistics=stats,
            next_stage="concept_recognition",
        )
        return report.to_dict()

    def _collection_path(self, collection: Dict[str, Any]) -> Path:
        name = (
            f"{collection.get('document_id')}_"
            f"{collection.get('processed_document_asset_id')}_"
            f"{collection.get('collection_id')}_"
            "knowledge_topic_collection.json"
        )
        return self.output_dir / name

    def _report_path(self, collection: Dict[str, Any], report: Dict[str, Any]) -> Path:
        name = (
            f"{collection.get('document_id')}_"
            f"{collection.get('processed_document_asset_id')}_"
            f"{collection.get('collection_id')}_"
            "topic_composer_report.json"
        )
        return self.output_dir / name

    @staticmethod
    def _average(values: List[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    @staticmethod
    def _report_quality_score(topics: List[Dict[str, Any]], incomplete: int) -> float:
        if not topics:
            return 0.0
        avg_cohesion = sum(t.get("quality", {}).get("cohesion_score", 0.0) for t in topics) / len(topics)
        penalty = min(30.0, incomplete * 2.0)
        return round(max(0.0, min(100.0, avg_cohesion - penalty)), 2)

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9%₹$./()<>'\-\s]+", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _looks_like_numbered_term(normalized_text: str) -> bool:
        return bool(re.match(r"^\s*\d+\.?\s+[a-z][a-z0-9 /&()'\-]{2,70}\s+(means|refers|is|a|an)\b", normalized_text))

    @staticmethod
    def _contains_multiple_numbered_terms(normalized_text: str) -> bool:
        return len(re.findall(r"\b\d+\.\s+[a-z][a-z0-9 /&()'\-]{2,50}\s+(means|refers|is|a|an)\b", normalized_text)) > 1

    @staticmethod
    def _parent_changed(component: Dict[str, Any], previous: Dict[str, Any]) -> bool:
        current_parent = component.get("parent_title_hint") or component.get("title_hint")
        previous_parent = previous.get("parent_title_hint") or previous.get("title_hint")
        if not current_parent or not previous_parent:
            return False
        return KnowledgeTopicComposer._clean_topic_name(current_parent) != KnowledgeTopicComposer._clean_topic_name(previous_parent)

    @staticmethod
    def _clean_topic_name(value: str) -> str:
        value = re.sub(r"\s+", " ", value or "").strip(" :-–—\t\n")
        value = re.sub(r"^\d+\.?\s*", "", value)
        return value[:120].strip() or "Untitled Topic"

    @staticmethod
    def _is_generic_title(value: str) -> bool:
        norm = KnowledgeTopicComposer._normalize_text(value)
        generic = {
            "section a preamble", "section b definitions", "definitions", "annexure", "annexure i",
            "annexure ii", "annexure iii", "policy wording", "activ one", "product benefit table",
        }
        return norm in generic or len(norm) <= 1
