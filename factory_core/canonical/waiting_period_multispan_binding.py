"""Generic multi-span binding for resolved scalar waiting-period mechanics."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from factory_core.canonical.waiting_period_binding import WaitingPeriodBinding, WaitingPeriodBindingError


class WaitingPeriodMultispanBindingError(ValueError):
    pass


@dataclass(frozen=True)
class WaitingPeriodMultispanBindingResult:
    manifest: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WaitingPeriodMultispanBindingError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise WaitingPeriodMultispanBindingError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodMultispanBindingError(f"{label} must be non-empty text")
    return value.strip()


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise WaitingPeriodMultispanBindingError(f"{label} must be repository-relative")
    return path.as_posix()


def _load(root: Path, relative: str, label: str) -> Mapping[str, Any]:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise WaitingPeriodMultispanBindingError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise WaitingPeriodMultispanBindingError(f"{label} not found: {relative}")
    return _mapping(json.loads(path.read_text(encoding="utf-8")), label)


class WaitingPeriodMultispanBinding:
    def bind_from_spec_file(self, *, spec_path: str | Path, repository_root: str | Path, bound_at: str | None = None) -> WaitingPeriodMultispanBindingResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Binding specification was not found: {path}")
        return self.bind(spec=_mapping(json.loads(path.read_text(encoding="utf-8")), "binding_spec"), repository_root=repository_root, bound_at=bound_at)

    def bind(self, *, spec: Mapping[str, Any], repository_root: str | Path, bound_at: str | None = None) -> WaitingPeriodMultispanBindingResult:
        root = Path(repository_root).resolve()
        if spec.get("schema_version") != "1.0" or spec.get("binding_type") != "waiting_period_multispan_binding_v1":
            raise WaitingPeriodMultispanBindingError("unsupported scalar multispan binding contract")
        if spec.get("reviewed_by_human") is not True:
            raise WaitingPeriodMultispanBindingError("reviewed_by_human must be true")

        selections = [_mapping(raw, "evidence_selections[]") for raw in _items(spec.get("evidence_selections"), "evidence_selections")]
        if len(selections) < 2 or any(item.get("role") != "mechanism" for item in selections):
            raise WaitingPeriodMultispanBindingError("scalar multispan binding requires at least two mechanism selections")
        identities = [(_text(x.get("document_id"), "document_id"), _text(x.get("candidate_id"), "candidate_id"), _text(x.get("candidate_text_sha256"), "candidate_text_sha256")) for x in selections]
        if len(set(identities)) != len(identities):
            raise WaitingPeriodMultispanBindingError("duplicate evidence selections are not permitted")

        base_spec = dict(spec)
        base_spec["binding_type"] = "waiting_period_binding_v1"
        base_spec["evidence_selections"] = [dict(selections[0])]
        try:
            base = WaitingPeriodBinding().bind(spec=base_spec, repository_root=root, bound_at=bound_at)
        except WaitingPeriodBindingError as exc:
            raise WaitingPeriodMultispanBindingError(str(exc)) from exc

        bundle_path = _safe_relative(spec.get("generic_source_bundle_path"), "generic_source_bundle_path")
        bundle = _load(root, bundle_path, "generic_source_bundle")
        sources = {_text(s.get("document_id"), "source.document_id"): s for s in (_mapping(raw, "source") for raw in _items(bundle.get("sources"), "sources"))}
        evidence: list[dict[str, Any]] = []
        refs: list[str] = []
        registrations: dict[str, Mapping[str, Any]] = {}
        candidate_indexes: dict[str, dict[str, Mapping[str, Any]]] = {}

        for selection in selections:
            document_id = _text(selection.get("document_id"), "document_id")
            candidate_id = _text(selection.get("candidate_id"), "candidate_id")
            expected_hash = _text(selection.get("candidate_text_sha256"), "candidate_text_sha256")
            source = sources.get(document_id)
            if source is None or source.get("authority_role") != "primary_legal":
                raise WaitingPeriodMultispanBindingError("all multispan evidence must be registered primary_legal evidence")
            if document_id not in registrations:
                registration_path = _safe_relative(source.get("registration_output_path"), "registration_output_path")
                registration = _load(root, registration_path, f"registration[{document_id}]")
                registrations[document_id] = registration
                review = _mapping(registration.get("evidence_review"), "evidence_review")
                candidate_indexes[document_id] = {_text(c.get("candidate_id"), "candidate_id"): c for c in (_mapping(raw, "candidate") for raw in _items(review.get("candidates"), "candidates"))}
            candidate = candidate_indexes[document_id].get(candidate_id)
            if candidate is None or candidate.get("text_sha256") != expected_hash:
                raise WaitingPeriodMultispanBindingError(f"candidate lineage mismatch: {document_id}:{candidate_id}")
            refs.append(f"{document_id}:{candidate_id}:{expected_hash}")
            evidence.append({"role": "mechanism", "document_id": document_id, "candidate_id": candidate_id, "candidate_text_sha256": expected_hash, "source_page": candidate.get("source_page"), "source_char_range": candidate.get("source_char_range")})

        manifest = dict(base.manifest)
        mechanic = dict(_mapping(manifest.get("mechanic"), "mechanic"))
        mechanic["evidence_reference_ids"] = refs
        manifest.update({"binding_type": "waiting_period_multispan_binding_v1", "mechanic": mechanic, "evidence": evidence, "mechanism_evidence_span_count": len(selections)})
        manifest["guardrails"] = list(manifest.get("guardrails", [])) + ["Scalar mechanic semantics may span multiple exact primary-legal candidates; component certification must explicitly map each semantic to its supporting candidate IDs."]
        return WaitingPeriodMultispanBindingResult(manifest=manifest)

    def write_output(self, result: WaitingPeriodMultispanBindingResult, *, repository_root: str | Path, output_path: str | Path) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative(str(output_path), "output_path")
        target = (root / relative).resolve()
        target.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target


__all__ = ["WaitingPeriodMultispanBinding", "WaitingPeriodMultispanBindingError", "WaitingPeriodMultispanBindingResult"]
