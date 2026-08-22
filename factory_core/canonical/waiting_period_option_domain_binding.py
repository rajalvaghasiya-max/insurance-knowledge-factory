"""Governed binding for unresolved Schedule-selected waiting-period option domains."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodDurationUnit,
    WaitingPeriodScopeType,
    WaitingPeriodType,
    WaitingPeriodValueSource,
)
from insurance_intelligence.benefits.waiting_period_option_domain import (
    WaitingPeriodDurationOption,
    WaitingPeriodDurationOptionDomain,
)


class WaitingPeriodOptionDomainBindingError(ValueError):
    """Raised when an unresolved option-domain binding is incomplete or unsafe."""


@dataclass(frozen=True)
class WaitingPeriodOptionDomainBindingResult:
    manifest: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WaitingPeriodOptionDomainBindingError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise WaitingPeriodOptionDomainBindingError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodOptionDomainBindingError(f"{label} must be non-empty text")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise WaitingPeriodOptionDomainBindingError(f"{label} must be repository-relative")
    return path.as_posix()


def _load_json(root: Path, relative_path: str, label: str) -> Mapping[str, Any]:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise WaitingPeriodOptionDomainBindingError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise WaitingPeriodOptionDomainBindingError(f"{label} not found: {relative_path}")
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WaitingPeriodOptionDomainBindingError(f"{label} is not valid JSON") from exc


def _enum(enum_type, value: object, label: str):
    try:
        return enum_type(_text(value, label))
    except ValueError as exc:
        raise WaitingPeriodOptionDomainBindingError(f"{label} has unsupported value {value!r}") from exc


def _domain(raw: object, evidence_reference_ids: tuple[str, ...]) -> WaitingPeriodDurationOptionDomain:
    item = _mapping(raw, "binding_spec.option_domain")
    options = tuple(
        WaitingPeriodDurationOption(
            duration_value=_mapping(raw_option, "option_domain.options[]").get("duration_value"),
            duration_unit=_enum(
                WaitingPeriodDurationUnit,
                _mapping(raw_option, "option_domain.options[]").get("duration_unit"),
                "option_domain.options[].duration_unit",
            ),
        )
        for raw_option in _items(item.get("options"), "option_domain.options")
    )
    return WaitingPeriodDurationOptionDomain(
        waiting_period_type=_enum(WaitingPeriodType, item.get("waiting_period_type"), "option_domain.waiting_period_type"),
        options=options,
        applies_to=tuple(_text(value, "option_domain.applies_to[]") for value in _items(item.get("applies_to"), "option_domain.applies_to")),
        evidence_reference_ids=evidence_reference_ids,
        schedule_dependency=_text(item.get("schedule_dependency"), "option_domain.schedule_dependency"),
        scope_type=_enum(WaitingPeriodScopeType, item.get("scope_type", "POLICY_WIDE"), "option_domain.scope_type"),
        scope_reference=item.get("scope_reference"),
        value_source=_enum(WaitingPeriodValueSource, item.get("value_source", "POLICY_SCHEDULE_SELECTED"), "option_domain.value_source"),
    )


def _serialize(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


class WaitingPeriodOptionDomainBinding:
    """Bind one unresolved Schedule-selectable duration domain to exact evidence."""

    def bind_from_spec_file(self, *, spec_path: str | Path, repository_root: str | Path, bound_at: str | None = None) -> WaitingPeriodOptionDomainBindingResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Binding specification was not found: {path}")
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WaitingPeriodOptionDomainBindingError("binding specification is not valid JSON") from exc
        return self.bind(spec=_mapping(spec, "binding_spec"), repository_root=repository_root, bound_at=bound_at)

    def bind(self, *, spec: Mapping[str, Any], repository_root: str | Path, bound_at: str | None = None) -> WaitingPeriodOptionDomainBindingResult:
        root = Path(repository_root).resolve()
        if spec.get("schema_version") != "1.0":
            raise WaitingPeriodOptionDomainBindingError("schema_version must be 1.0")
        if spec.get("binding_type") != "waiting_period_option_domain_binding_v1":
            raise WaitingPeriodOptionDomainBindingError("binding_type must be waiting_period_option_domain_binding_v1")
        if spec.get("reviewed_by_human") is not True:
            raise WaitingPeriodOptionDomainBindingError("reviewed_by_human must be true")

        bundle_path = _safe_relative_path(spec.get("generic_source_bundle_path"), "generic_source_bundle_path")
        bundle = _load_json(root, bundle_path, "generic_source_bundle")
        if bundle.get("registration_type") != "generic_source_registration_bundle_v1":
            raise WaitingPeriodOptionDomainBindingError("generic source bundle is not review-ready")
        context = _mapping(bundle.get("product_context"), "generic_source_bundle.product_context")
        if context.get("source_scope") != "reusable_generic":
            raise WaitingPeriodOptionDomainBindingError("generic source bundle must use reusable_generic scope")

        sources = {
            _text(source.get("document_id"), "source.document_id"): source
            for source in (_mapping(raw, "generic_source_bundle.sources[]") for raw in _items(bundle.get("sources"), "generic_source_bundle.sources"))
        }
        selections = _items(spec.get("evidence_selections"), "binding_spec.evidence_selections")
        roles = [
            _text(_mapping(item, "evidence_selections[]").get("role"), "evidence_selections[].role")
            for item in selections
        ]
        if sorted(roles) != ["mechanism", "option_domain"]:
            raise WaitingPeriodOptionDomainBindingError("option-domain binding requires exactly one mechanism and one option_domain evidence selection")

        registrations: dict[str, Mapping[str, Any]] = {}
        candidate_indexes: dict[str, dict[str, Mapping[str, Any]]] = {}
        evidence: list[dict[str, Any]] = []
        refs: list[str] = []

        for index, raw_selection in enumerate(selections):
            selection = _mapping(raw_selection, f"evidence_selections[{index}]")
            role = _text(selection.get("role"), f"evidence_selections[{index}].role")
            document_id = _text(selection.get("document_id"), f"evidence_selections[{index}].document_id")
            candidate_id = _text(selection.get("candidate_id"), f"evidence_selections[{index}].candidate_id")
            expected_hash = _text(selection.get("candidate_text_sha256"), f"evidence_selections[{index}].candidate_text_sha256")
            source = sources.get(document_id)
            if source is None:
                raise WaitingPeriodOptionDomainBindingError(f"unregistered source {document_id!r}")
            if source.get("authority_role") != "primary_legal":
                raise WaitingPeriodOptionDomainBindingError("waiting-period option domain requires primary_legal evidence")
            if document_id not in registrations:
                registration_path = _safe_relative_path(source.get("registration_output_path"), "source.registration_output_path")
                registration = _load_json(root, registration_path, f"registration[{document_id}]")
                registrations[document_id] = registration
                review = _mapping(registration.get("evidence_review"), "registration.evidence_review")
                candidate_indexes[document_id] = {
                    _text(candidate.get("candidate_id"), "candidate.candidate_id"): candidate
                    for candidate in (_mapping(raw, "registration.evidence_review.candidates[]") for raw in _items(review.get("candidates"), "registration.evidence_review.candidates"))
                }
            candidate = candidate_indexes[document_id].get(candidate_id)
            if candidate is None:
                raise WaitingPeriodOptionDomainBindingError(f"candidate {candidate_id!r} not found for {document_id}")
            actual_hash = _text(candidate.get("text_sha256"), "candidate.text_sha256")
            if actual_hash != expected_hash:
                raise WaitingPeriodOptionDomainBindingError(f"candidate text hash mismatch for {document_id}:{candidate_id}")
            ref = f"{document_id}:{candidate_id}:{actual_hash}"
            refs.append(ref)
            evidence.append({
                "role": role,
                "document_id": document_id,
                "candidate_id": candidate_id,
                "candidate_text_sha256": actual_hash,
                "source_page": candidate.get("source_page"),
                "source_char_range": candidate.get("source_char_range"),
            })

        domain = _domain(spec.get("option_domain"), tuple(refs))
        manifest = {
            "schema_version": "1.0",
            "binding_type": "waiting_period_option_domain_binding_v1",
            "binding_status": "reviewed_waiting_period_option_domain_bound_not_published",
            "resolution_status": "unresolved_schedule_option_domain",
            "product_context": {
                "insurer_id": context.get("insurer_id"),
                "product_id": context.get("product_id"),
                "product_display_name": context.get("product_display_name"),
            },
            "generic_source_bundle_path": bundle_path,
            "binding_id": _text(spec.get("binding_id"), "binding_id"),
            "option_domain": _serialize(asdict(domain)),
            "evidence": evidence,
            "publication_status": "bound_not_published",
            "policy_instance_resolution_status": "not_resolved_without_schedule_selection",
            "bound_at": bound_at or datetime.now(timezone.utc).isoformat(),
            "reviewed_by_human": True,
            "guardrails": [
                "The option domain preserves all authoritative Schedule-selectable durations.",
                "No duration option is selected without policy-instance Schedule evidence.",
                "The binding does not publish or infer customer-specific eligibility.",
            ],
        }
        return WaitingPeriodOptionDomainBindingResult(manifest=manifest)

    def write_output(self, result: WaitingPeriodOptionDomainBindingResult, *, repository_root: str | Path, output_path: str | Path) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative_path(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise WaitingPeriodOptionDomainBindingError("output_path must remain under repository_root") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target


__all__ = ["WaitingPeriodOptionDomainBinding", "WaitingPeriodOptionDomainBindingError", "WaitingPeriodOptionDomainBindingResult"]
