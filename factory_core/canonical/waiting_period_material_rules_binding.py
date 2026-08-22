"""Generic binding wrapper for material waiting-period rules."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from factory_core.canonical.waiting_period_binding import WaitingPeriodBinding
from factory_core.canonical.waiting_period_multispan_binding import WaitingPeriodMultispanBinding


class WaitingPeriodMaterialRulesBindingError(ValueError):
    pass


@dataclass(frozen=True)
class WaitingPeriodMaterialRulesBindingResult:
    manifest: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WaitingPeriodMaterialRulesBindingError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise WaitingPeriodMaterialRulesBindingError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodMaterialRulesBindingError(f"{label} must be non-empty text")
    return value.strip()


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise WaitingPeriodMaterialRulesBindingError(f"{label} must be repository-relative")
    return path.as_posix()


def _bind_base(path: Path, root: Path, bound_at: str | None) -> Mapping[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Base binding specification was not found: {path}")
    spec = _mapping(json.loads(path.read_text(encoding="utf-8")), "base_binding_spec")
    binding_type = spec.get("binding_type")
    if binding_type == "waiting_period_binding_v1":
        return WaitingPeriodBinding().bind(spec=spec, repository_root=root, bound_at=bound_at).manifest
    if binding_type == "waiting_period_multispan_binding_v1":
        return WaitingPeriodMultispanBinding().bind(spec=spec, repository_root=root, bound_at=bound_at).manifest
    raise WaitingPeriodMaterialRulesBindingError(f"unsupported base waiting-period binding type {binding_type!r}")


class WaitingPeriodMaterialRulesBinding:
    def bind_from_spec_file(self, *, spec_path: str | Path, repository_root: str | Path, bound_at: str | None = None) -> WaitingPeriodMaterialRulesBindingResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Binding specification was not found: {path}")
        return self.bind(spec=_mapping(json.loads(path.read_text(encoding="utf-8")), "binding_spec"), repository_root=repository_root, bound_at=bound_at)

    def bind(self, *, spec: Mapping[str, Any], repository_root: str | Path, bound_at: str | None = None) -> WaitingPeriodMaterialRulesBindingResult:
        root = Path(repository_root).resolve()
        if spec.get("schema_version") != "1.0" or spec.get("binding_type") != "waiting_period_material_rules_binding_v1":
            raise WaitingPeriodMaterialRulesBindingError("unsupported material-rules binding contract")
        if spec.get("reviewed_by_human") is not True:
            raise WaitingPeriodMaterialRulesBindingError("reviewed_by_human must be true")
        base_path = _safe_relative(spec.get("base_binding_spec_path"), "base_binding_spec_path")
        base_manifest = dict(_bind_base((root / base_path).resolve(), root, bound_at))
        evidence_by_candidate = {
            _text(item.get("candidate_id"), "binding_evidence.candidate_id"): item
            for item in (_mapping(raw, "binding_evidence") for raw in _items(base_manifest.get("evidence"), "binding_manifest.evidence"))
        }
        rules = []
        seen_ids: set[str] = set()
        for index, raw in enumerate(_items(spec.get("material_rules"), "material_rules")):
            item = _mapping(raw, f"material_rules[{index}]")
            rule_id = _text(item.get("rule_id"), f"material_rules[{index}].rule_id")
            if rule_id in seen_ids:
                raise WaitingPeriodMaterialRulesBindingError("material rule IDs must be unique")
            seen_ids.add(rule_id)
            rule_type = _text(item.get("rule_type"), f"material_rules[{index}].rule_type")
            if rule_type not in {"RELATIONSHIP_LONGER_OF", "APPLICABILITY_CONDITION", "POST_WAIT_CONDITION"}:
                raise WaitingPeriodMaterialRulesBindingError(f"unsupported rule_type {rule_type!r}")
            candidate_ids = tuple(_text(v, "evidence_candidate_ids[]") for v in _items(item.get("evidence_candidate_ids"), "evidence_candidate_ids"))
            if not candidate_ids or len(candidate_ids) != len(set(candidate_ids)):
                raise WaitingPeriodMaterialRulesBindingError("material rule evidence candidates must be non-empty and unique")
            for candidate_id in candidate_ids:
                if candidate_id not in evidence_by_candidate:
                    raise WaitingPeriodMaterialRulesBindingError(f"material rule references unbound candidate {candidate_id!r}")
            related = item.get("related_waiting_period_type")
            if rule_type == "RELATIONSHIP_LONGER_OF" and not isinstance(related, str):
                raise WaitingPeriodMaterialRulesBindingError("RELATIONSHIP_LONGER_OF requires related_waiting_period_type")
            if rule_type in {"APPLICABILITY_CONDITION", "POST_WAIT_CONDITION"} and related is not None:
                raise WaitingPeriodMaterialRulesBindingError(f"{rule_type} must not define related_waiting_period_type")
            rules.append({"rule_id": rule_id, "rule_type": rule_type, "statement": _text(item.get("statement"), f"material_rules[{index}].statement"), "related_waiting_period_type": related, "evidence_candidate_ids": list(candidate_ids)})
        if not rules:
            raise WaitingPeriodMaterialRulesBindingError("material_rules must not be empty")
        manifest = dict(base_manifest)
        manifest.update({"binding_type": "waiting_period_material_rules_binding_v1", "binding_id": _text(spec.get("binding_id"), "binding_id"), "base_binding_spec_path": base_path, "material_rules": rules, "material_rules_status": "reviewed_material_rules_bound_not_published"})
        manifest["guardrails"] = list(manifest.get("guardrails", [])) + ["Material rules are certified separately and do not alter the resolved scalar duration.", "Material rules do not publish or determine customer-specific claim outcomes."]
        return WaitingPeriodMaterialRulesBindingResult(manifest=manifest)

    def write_output(self, result: WaitingPeriodMaterialRulesBindingResult, *, repository_root: str | Path, output_path: str | Path) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative(str(output_path), "output_path")
        target = (root / relative).resolve()
        target.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target


__all__ = ["WaitingPeriodMaterialRulesBinding", "WaitingPeriodMaterialRulesBindingError", "WaitingPeriodMaterialRulesBindingResult"]
