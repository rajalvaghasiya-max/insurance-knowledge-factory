"""P2.8-B — read-only coverage-gap prioritisation.

Builds a reviewed research backlog from a registry-backed evidence coverage
register. It does not infer facts, publish knowledge, mutate coverage inputs,
or evaluate policy rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


class CoverageGapPrioritizationError(ValueError):
    """Raised when a prioritisation input is incomplete or inconsistent."""


@dataclass(frozen=True)
class CoverageGapPrioritizationResult:
    manifest: Mapping[str, Any]


_ALLOWED_TIERS = {"critical", "high", "medium", "low"}
_ALLOWED_COVERAGE_STATES = {"applicability_reviewed", "not_assessed"}


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CoverageGapPrioritizationError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CoverageGapPrioritizationError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CoverageGapPrioritizationError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise CoverageGapPrioritizationError(f"{label} must be a safe repository-relative path")
    return path.as_posix()


def _load_json(root: Path, relative_path: str, label: str) -> tuple[Mapping[str, Any], str]:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise CoverageGapPrioritizationError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise FileNotFoundError(f"{label} was not found: {relative_path}")
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CoverageGapPrioritizationError(f"{label} is not valid UTF-8 JSON") from exc
    return _mapping(parsed, label), sha256(raw).hexdigest()


class CoverageGapPrioritization:
    """Builds a separately persisted, reviewed research backlog."""

    def prioritize_from_spec_file(
        self, *, spec_path: str | Path, repository_root: str | Path
    ) -> CoverageGapPrioritizationResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Coverage-gap prioritisation specification was not found: {path}")
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CoverageGapPrioritizationError(
                "Coverage-gap prioritisation specification is not valid UTF-8 JSON"
            ) from exc
        return self.prioritize(spec=_mapping(parsed, "prioritization_spec"), repository_root=repository_root)

    def prioritize(
        self,
        *,
        spec: Mapping[str, Any],
        repository_root: str | Path,
        prioritized_at: str | None = None,
    ) -> CoverageGapPrioritizationResult:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")
        if spec.get("schema_version") != "1.0":
            raise CoverageGapPrioritizationError("prioritization_spec.schema_version must be 1.0")
        if spec.get("prioritization_type") != "coverage_gap_prioritization_v1":
            raise CoverageGapPrioritizationError("prioritization_spec.prioritization_type is invalid")
        if spec.get("reviewed_by_human") is not True:
            raise CoverageGapPrioritizationError("prioritization_spec.reviewed_by_human must be true")

        register_path = _safe_relative_path(spec.get("coverage_register_path"), "coverage_register_path")
        register, register_sha = _load_json(root, register_path, "coverage_register")
        if register.get("register_type") != "registry_backed_evidence_coverage_register_v1":
            raise CoverageGapPrioritizationError("coverage_register type is invalid")
        if register.get("register_status") != "read_only_coverage_register_built":
            raise CoverageGapPrioritizationError("coverage_register was not built successfully")

        concepts_by_product: dict[str, dict[str, Mapping[str, Any]]] = {}
        for raw_product in _items(register.get("products"), "coverage_register.products"):
            product = _mapping(raw_product, "coverage_register.product")
            product_version_id = _text(product.get("product_version_id"), "coverage_register.product_version_id")
            if product_version_id in concepts_by_product:
                raise CoverageGapPrioritizationError("coverage_register.product_version_id must be unique")
            concepts: dict[str, Mapping[str, Any]] = {}
            for raw_concept in _items(product.get("concepts"), "coverage_register.product.concepts"):
                concept = _mapping(raw_concept, "coverage_register.concept")
                concept_id = _text(concept.get("concept_id"), "coverage_register.concept_id")
                if concept_id in concepts:
                    raise CoverageGapPrioritizationError("coverage_register.concept_id must be unique per product")
                concepts[concept_id] = concept
            concepts_by_product[product_version_id] = concepts

        raw_items = _items(spec.get("backlog_items"), "backlog_items")
        if not raw_items:
            raise CoverageGapPrioritizationError("backlog_items must be non-empty")

        seen_pairs: set[tuple[str, str]] = set()
        seen_orders: set[int] = set()
        output_items: list[dict[str, Any]] = []
        for index, raw_item in enumerate(raw_items):
            item = _mapping(raw_item, f"backlog_items[{index}]")
            product_version_id = _text(item.get("product_version_id"), "backlog_item.product_version_id")
            concept_id = _text(item.get("concept_id"), "backlog_item.concept_id")
            pair = (product_version_id, concept_id)
            if pair in seen_pairs:
                raise CoverageGapPrioritizationError("backlog_items must not repeat a product/concept pair")
            seen_pairs.add(pair)

            order = item.get("priority_order")
            if not isinstance(order, int) or isinstance(order, bool) or order < 1:
                raise CoverageGapPrioritizationError("backlog_item.priority_order must be a positive integer")
            if order in seen_orders:
                raise CoverageGapPrioritizationError("backlog_item.priority_order must be unique")
            seen_orders.add(order)

            tier = _text(item.get("priority_tier"), "backlog_item.priority_tier")
            if tier not in _ALLOWED_TIERS:
                raise CoverageGapPrioritizationError("backlog_item.priority_tier is invalid")
            research_goal = _text(item.get("research_goal"), "backlog_item.research_goal")
            rationale = _text(item.get("rationale"), "backlog_item.rationale")
            preconditions = [
                _text(value, "backlog_item.preconditions[]")
                for value in _items(item.get("preconditions", []), "backlog_item.preconditions")
            ]

            product_concepts = concepts_by_product.get(product_version_id)
            if product_concepts is None:
                raise CoverageGapPrioritizationError(
                    f"backlog product version is absent from coverage register: {product_version_id}"
                )
            source_concept = product_concepts.get(concept_id)
            if source_concept is None:
                raise CoverageGapPrioritizationError(
                    f"backlog concept is absent from coverage register: {product_version_id}:{concept_id}"
                )
            coverage_state = _text(source_concept.get("coverage_state"), "coverage_register.concept.coverage_state")
            authority = _text(source_concept.get("knowledge_authority_status"), "coverage_register.concept.knowledge_authority_status")
            if authority == "authoritative" or coverage_state == "authoritative":
                raise CoverageGapPrioritizationError(
                    f"authoritative concept cannot be entered as an evidence-research gap: {product_version_id}:{concept_id}"
                )
            if coverage_state not in _ALLOWED_COVERAGE_STATES:
                raise CoverageGapPrioritizationError(
                    f"unsupported source coverage state for backlog item: {coverage_state}"
                )

            output_items.append({
                "priority_order": order,
                "priority_tier": tier,
                "product_version_id": product_version_id,
                "concept_id": concept_id,
                "coverage_state": coverage_state,
                "knowledge_authority_status": authority,
                "applicability_status": _text(source_concept.get("applicability_status"), "coverage_register.concept.applicability_status"),
                "review_integrity_status": _text(source_concept.get("review_integrity_status"), "coverage_register.concept.review_integrity_status"),
                "gap_reason": source_concept.get("gap_reason"),
                "source_next_evidence_requirement": source_concept.get("next_evidence_requirement"),
                "research_goal": research_goal,
                "rationale": rationale,
                "preconditions": preconditions,
            })

        if sorted(seen_orders) != list(range(1, len(output_items) + 1)):
            raise CoverageGapPrioritizationError(
                "backlog_item.priority_order must be consecutive beginning at 1"
            )

        output_items.sort(key=lambda value: value["priority_order"])
        return CoverageGapPrioritizationResult(manifest={
            "schema_version": "1.0",
            "prioritization_type": "coverage_gap_prioritization_v1",
            "backlog_status": "reviewed_coverage_gaps_prioritized",
            "prioritized_at": prioritized_at or datetime.now(timezone.utc).isoformat(),
            "source_coverage_register_path": register_path,
            "source_coverage_register_sha256": register_sha,
            "backlog_items": output_items,
            "guardrails": [
                "Prioritisation is derived read-only from a governed coverage register and does not create, publish, or alter knowledge.",
                "Priority is explicitly reviewed in the input specification; the builder does not infer business importance or calculate opaque scores.",
                "Authoritative concepts cannot be represented as evidence-research gaps.",
                "Unknown pending evidence and not assessed remain distinct source states in the research backlog.",
                "A backlog item specifies research intent only; it does not establish a product fact or authorize publication.",
            ],
        })

    def write_output(
        self,
        result: CoverageGapPrioritizationResult,
        *,
        repository_root: str | Path,
        output_path: str | Path,
    ) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative_path(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise CoverageGapPrioritizationError("output_path must remain under repository_root") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target
