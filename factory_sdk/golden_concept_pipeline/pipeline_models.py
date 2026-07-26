from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib
import json


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(data: Any, length: int = 24) -> str:
    return hashlib.sha256(stable_json(data).encode("utf-8")).hexdigest()[:length]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SourceOpportunity:
    asset_type: str
    reason: str
    priority: str = "medium"
    target_department: str = "unassigned"

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SourceOpportunity":
        return SourceOpportunity(
            asset_type=str(data.get("asset_type", "unknown")),
            reason=str(data.get("reason", "")),
            priority=str(data.get("priority", "medium")),
            target_department=str(data.get("target_department", "unassigned")),
        )


@dataclass(frozen=True)
class SourceDistillationReport:
    distillation_id: str
    observation_id: str
    concept_id: str
    observation_title: str
    knowledge_potential: float
    opportunities: List[SourceOpportunity]
    relationships: List[str] = field(default_factory=list)
    confidence: float = 0.0
    review_required: bool = False
    source_path: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict[str, Any], source_path: str | None = None) -> "SourceDistillationReport":
        observation = data.get("observation", {}) or {}
        kp = data.get("knowledge_potential", {}) or {}
        return SourceDistillationReport(
            distillation_id=str(data.get("distillation_id", "unknown")),
            observation_id=str(observation.get("observation_id", "unknown")),
            concept_id=str(observation.get("concept_id", "unknown")),
            observation_title=str(observation.get("title", "")),
            knowledge_potential=float(kp.get("overall", 0.0)),
            opportunities=[SourceOpportunity.from_dict(o) for o in data.get("manufacturing_opportunities", [])],
            relationships=sorted({str(x) for x in data.get("relationships", [])}),
            confidence=float(data.get("confidence", 0.0)),
            review_required=bool(data.get("review_required", False)),
            source_path=source_path,
        )


@dataclass(frozen=True)
class ManufacturingTask:
    task_id: str
    concept_id: str
    asset_type: str
    target_department: str
    priority: str
    reason: str
    source_distillation_ids: List[str]
    source_observation_ids: List[str]
    dependencies: List[str] = field(default_factory=list)
    status: str = "planned"
    is_dependency_task: bool = False

    @staticmethod
    def create(
        *,
        concept_id: str,
        asset_type: str,
        target_department: str,
        priority: str,
        reason: str,
        source_distillation_ids: List[str],
        source_observation_ids: List[str],
        dependencies: List[str] | None = None,
        is_dependency_task: bool = False,
    ) -> "ManufacturingTask":
        payload = {
            "concept_id": concept_id,
            "asset_type": asset_type,
            "target_department": target_department,
            "source_distillation_ids": sorted(set(source_distillation_ids)),
            "source_observation_ids": sorted(set(source_observation_ids)),
            "is_dependency_task": is_dependency_task,
        }
        return ManufacturingTask(
            task_id=f"gmt_{stable_hash(payload)}",
            concept_id=concept_id,
            asset_type=asset_type,
            target_department=target_department,
            priority=priority,
            reason=reason,
            source_distillation_ids=sorted(set(source_distillation_ids)),
            source_observation_ids=sorted(set(source_observation_ids)),
            dependencies=sorted(set(dependencies or [])),
            is_dependency_task=is_dependency_task,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManufacturingQueue:
    queue_id: str
    concept_id: str
    source_reports: List[str]
    tasks: List[ManufacturingTask]
    created_at: str

    @staticmethod
    def create(concept_id: str, source_reports: List[str], tasks: List[ManufacturingTask]) -> "ManufacturingQueue":
        payload = {
            "concept_id": concept_id,
            "source_reports": sorted(set(source_reports)),
            "tasks": [t.to_dict() for t in sorted(tasks, key=lambda t: (t.asset_type, t.task_id))],
        }
        return ManufacturingQueue(
            queue_id=f"gq_{stable_hash(payload)}",
            concept_id=concept_id,
            source_reports=sorted(set(source_reports)),
            tasks=tasks,
            created_at=utc_now(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queue_id": self.queue_id,
            "concept_id": self.concept_id,
            "source_reports": self.source_reports,
            "tasks": [t.to_dict() for t in self.tasks],
            "task_count": len(self.tasks),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class DependencyGraph:
    graph_id: str
    concept_id: str
    nodes: List[str]
    edges: List[Dict[str, str]]
    unresolved_dependencies: List[Dict[str, str]] = field(default_factory=list)

    @staticmethod
    def create(concept_id: str, nodes: List[str], edges: List[Dict[str, str]], unresolved: List[Dict[str, str]]) -> "DependencyGraph":
        payload = {"concept_id": concept_id, "nodes": sorted(nodes), "edges": sorted(edges, key=lambda e: (e["from"], e["to"])), "unresolved": unresolved}
        return DependencyGraph(
            graph_id=f"gdg_{stable_hash(payload)}",
            concept_id=concept_id,
            nodes=sorted(nodes),
            edges=sorted(edges, key=lambda e: (e["from"], e["to"])),
            unresolved_dependencies=unresolved,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DispatchItem:
    task_id: str
    asset_type: str
    target_department: str
    production_cell: str
    dispatch_mode: str
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DispatchPlan:
    dispatch_id: str
    concept_id: str
    items: List[DispatchItem]

    @staticmethod
    def create(concept_id: str, items: List[DispatchItem]) -> "DispatchPlan":
        payload = {"concept_id": concept_id, "items": [i.to_dict() for i in sorted(items, key=lambda i: i.task_id)]}
        return DispatchPlan(dispatch_id=f"gdp_{stable_hash(payload)}", concept_id=concept_id, items=items)

    def to_dict(self) -> Dict[str, Any]:
        return {"dispatch_id": self.dispatch_id, "concept_id": self.concept_id, "items": [i.to_dict() for i in self.items], "dispatch_count": len(self.items)}


@dataclass(frozen=True)
class GoldenConceptPackage:
    package_id: str
    concept_id: str
    source_report_count: int
    task_count: int
    components_by_asset_type: Dict[str, List[str]]
    relationships: List[str]
    status: str
    created_at: str

    @staticmethod
    def create(concept_id: str, source_reports: List[SourceDistillationReport], queue: ManufacturingQueue) -> "GoldenConceptPackage":
        components: Dict[str, List[str]] = {}
        for task in queue.tasks:
            components.setdefault(task.asset_type, []).append(task.task_id)
        relationships = sorted({rel for report in source_reports for rel in report.relationships})
        payload = {"concept_id": concept_id, "components": components, "relationships": relationships, "tasks": [t.task_id for t in queue.tasks]}
        return GoldenConceptPackage(
            package_id=f"gcp_{stable_hash(payload)}",
            concept_id=concept_id,
            source_report_count=len(source_reports),
            task_count=len(queue.tasks),
            components_by_asset_type={k: sorted(v) for k, v in sorted(components.items())},
            relationships=relationships,
            status="manufacturing_ready",
            created_at=utc_now(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GoldenConceptCertification:
    certification_id: str
    concept_id: str
    status: str
    planning_status: str
    execution_status: str
    checks: Dict[str, Any]
    execution_summary: Dict[str, int]
    created_at: str

    @staticmethod
    def create(
        *,
        concept_id: str,
        planning_status: str,
        execution_status: str,
        checks: Dict[str, Any],
        execution_summary: Dict[str, int],
    ) -> "GoldenConceptCertification":
        if planning_status != "PASS" or execution_status == "FAILED":
            overall_status = "FAIL"
        elif execution_status == "COMPLETE":
            overall_status = "PASS"
        else:
            overall_status = "PASS_WITH_GAPS"

        payload = {
            "concept_id": concept_id,
            "status": overall_status,
            "planning_status": planning_status,
            "execution_status": execution_status,
            "checks": checks,
            "execution_summary": execution_summary,
        }

        return GoldenConceptCertification(
            certification_id=f"gcc_{stable_hash(payload)}",
            concept_id=concept_id,
            status=overall_status,
            planning_status=planning_status,
            execution_status=execution_status,
            checks=checks,
            execution_summary=execution_summary,
            created_at=utc_now(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
