"""Governed binding of typed waiting-period mechanics to registered evidence.

This binder is intentionally narrow: it validates one resolved scalar waiting-period
mechanic against approved generic source registrations and the reusable
``WaitingPeriodMechanic`` contract. Schedule-selected values are permitted only
when separate authoritative evidence resolves the scalar value. The binder does
not publish facts or infer customer-specific values.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodDurationUnit,
    WaitingPeriodMechanic,
    WaitingPeriodMemberBasis,
    WaitingPeriodModification,
    WaitingPeriodModificationType,
    WaitingPeriodScopeType,
    WaitingPeriodStartBasis,
    WaitingPeriodSumInsuredEnhancementEffect,
    WaitingPeriodType,
    WaitingPeriodValueSource,
)


class WaitingPeriodBindingError(ValueError):
    """Raised when a reviewed waiting-period binding is incomplete or unsafe."""


@dataclass(frozen=True)
class WaitingPeriodBindingResult:
    manifest: Mapping[str, Any]


_ALLOWED_EVIDENCE_ROLES = frozenset({"mechanism", "schedule_value_resolution"})


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WaitingPeriodBindingError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise WaitingPeriodBindingError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodBindingError(f"{label} must be non-empty text")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise WaitingPeriodBindingError(f"{label} must be repository-relative")
    return path.as_posix()


def _load_json(root: Path, relative_path: str, label: str) -> Mapping[str, Any]:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise WaitingPeriodBindingError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise WaitingPeriodBindingError(f"{label} not found: {relative_path}")
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WaitingPeriodBindingError(f"{label} is not valid JSON") from exc


def _enum(enum_type, value: object, label: str):
    try:
        return enum_type(_text(value, label))
    except ValueError as exc:
        raise WaitingPeriodBindingError(f"{label} has unsupported value {value!r}") from exc


def _optional_enum(enum_type, value: object, label: str):
    if value is None:
        return None
    return _enum(enum_type, value, label)


def _modification(raw: object, index: int) -> WaitingPeriodModification:
    item = _mapping(raw, f"mechanic.modifications[{index}]")
    return WaitingPeriodModification(
        modification_type=_enum(
            WaitingPeriodModificationType,
            item.get("modification_type"),
            f"mechanic.modifications[{index}].modification_type",
        ),
        condition=_text(item.get("condition"), f"mechanic.modifications[{index}].condition"),
        resulting_duration_value=item.get("resulting_duration_value"),
        resulting_duration_unit=_optional_enum(
            WaitingPeriodDurationUnit,
            item.get("resulting_duration_unit"),
            f"mechanic.modifications[{index}].resulting_duration_unit",
        ),
        evidence_reference_ids=tuple(
            _text(value, f"mechanic.modifications[{index}].evidence_reference_ids[]")
            for value in _items(
                item.get("evidence_reference_ids", []),
                f"mechanic.modifications[{index}].evidence_reference_ids",
            )
        ),
    )


def _mechanic(raw: object, evidence_reference_ids: tuple[str, ...]) -> WaitingPeriodMechanic:
    item = _mapping(raw, "binding_spec.mechanic")
    return WaitingPeriodMechanic(
        waiting_period_type=_enum(
            WaitingPeriodType,
            item.get("waiting_period_type"),
            "mechanic.waiting_period_type",
        ),
        duration_value=item.get("duration_value"),
        duration_unit=_enum(
            WaitingPeriodDurationUnit,
            item.get("duration_unit"),
            "mechanic.duration_unit",
        ),
        start_basis=_enum(
            WaitingPeriodStartBasis,
            item.get("start_basis"),
            "mechanic.start_basis",
        ),
        applies_to=tuple(
            _text(value, "mechanic.applies_to[]")
            for value in _items(item.get("applies_to"), "mechanic.applies_to")
        ),
        evidence_reference_ids=evidence_reference_ids,
        exclusions_or_exceptions=tuple(
            _text(value, "mechanic.exclusions_or_exceptions[]")
            for value in _items(
                item.get("exclusions_or_exceptions", []),
                "mechanic.exclusions_or_exceptions",
            )
        ),
        modifications=tuple(
            _modification(raw_modification, index)
            for index, raw_modification in enumerate(
                _items(item.get("modifications", []), "mechanic.modifications")
            )
        ),
        schedule_dependency=item.get("schedule_dependency"),
        continuity_dependency=item.get("continuity_dependency"),
        scope_type=_enum(
            WaitingPeriodScopeType,
            item.get("scope_type", "POLICY_WIDE"),
            "mechanic.scope_type",
        ),
        scope_reference=item.get("scope_reference"),
        value_source=_enum(
            WaitingPeriodValueSource,
            item.get("value_source", "PRODUCT_FIXED"),
            "mechanic.value_source",
        ),
        member_waiting_basis=_optional_enum(
            WaitingPeriodMemberBasis,
            item.get("member_waiting_basis"),
            "mechanic.member_waiting_basis",
        ),
        sum_insured_enhancement_effect=_optional_enum(
            WaitingPeriodSumInsuredEnhancementEffect,
            item.get("sum_insured_enhancement_effect"),
            "mechanic.sum_insured_enhancement_effect",
        ),
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


class WaitingPeriodBinding:
    """Binds one reviewed scalar waiting-period mechanic to exact registered evidence."""

    def bind_from_spec_file(
        self,
        *,
        spec_path: str | Path,
        repository_root: str | Path,
        bound_at: str | None = None,
    ) -> WaitingPeriodBindingResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Binding specification was not found: {path}")
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WaitingPeriodBindingError("binding specification is not valid JSON") from exc
        return self.bind(
            spec=_mapping(spec, "binding_spec"),
            repository_root=repository_root,
            bound_at=bound_at,
        )

    def bind(
        self,
        *,
        spec: Mapping[str, Any],
        repository_root: str | Path,
        bound_at: str | None = None,
    ) -> WaitingPeriodBindingResult:
        root = Path(repository_root).resolve()
        if spec.get("schema_version") != "1.0":
            raise WaitingPeriodBindingError("schema_version must be 1.0")
        if spec.get("binding_type") != "waiting_period_binding_v1":
            raise WaitingPeriodBindingError("binding_type must be waiting_period_binding_v1")
        if spec.get("reviewed_by_human") is not True:
            raise WaitingPeriodBindingError("reviewed_by_human must be true")

        bundle_path = _safe_relative_path(
            spec.get("generic_source_bundle_path"),
            "generic_source_bundle_path",
        )
        bundle = _load_json(root, bundle_path, "generic_source_bundle")
        if bundle.get("registration_type") != "generic_source_registration_bundle_v1":
            raise WaitingPeriodBindingError("generic source bundle is not review-ready")
        context = _mapping(
            bundle.get("product_context"),
            "generic_source_bundle.product_context",
        )
        if context.get("source_scope") != "reusable_generic":
            raise WaitingPeriodBindingError(
                "generic source bundle must use reusable_generic scope"
            )

        sources = {
            _text(source.get("document_id"), "source.document_id"): source
            for source in (
                _mapping(raw, "generic_source_bundle.sources[]")
                for raw in _items(bundle.get("sources"), "generic_source_bundle.sources")
            )
        }
        registrations: dict[str, Mapping[str, Any]] = {}
        candidate_indexes: dict[str, dict[str, Mapping[str, Any]]] = {}

        raw_selections = _items(
            spec.get("evidence_selections"),
            "binding_spec.evidence_selections",
        )
        if not raw_selections:
            raise WaitingPeriodBindingError("evidence_selections must not be empty")

        evidence: list[dict[str, Any]] = []
        evidence_reference_ids: list[str] = []
        role_counts = {role: 0 for role in _ALLOWED_EVIDENCE_ROLES}

        for index, raw_selection in enumerate(raw_selections):
            selection = _mapping(raw_selection, f"evidence_selections[{index}]")
            role = _text(selection.get("role"), f"evidence_selections[{index}].role")
            if role not in _ALLOWED_EVIDENCE_ROLES:
                raise WaitingPeriodBindingError(f"unsupported evidence role {role!r}")
            role_counts[role] += 1

            document_id = _text(
                selection.get("document_id"),
                f"evidence_selections[{index}].document_id",
            )
            candidate_id = _text(
                selection.get("candidate_id"),
                f"evidence_selections[{index}].candidate_id",
            )
            expected_hash = _text(
                selection.get("candidate_text_sha256"),
                f"evidence_selections[{index}].candidate_text_sha256",
            )

            source = sources.get(document_id)
            if source is None:
                raise WaitingPeriodBindingError(f"unregistered source {document_id!r}")
            if source.get("authority_role") != "primary_legal":
                raise WaitingPeriodBindingError(
                    "waiting-period mechanic requires primary_legal evidence"
                )

            if document_id not in registrations:
                registration_path = _safe_relative_path(
                    source.get("registration_output_path"),
                    "source.registration_output_path",
                )
                registration = _load_json(
                    root,
                    registration_path,
                    f"registration[{document_id}]",
                )
                registrations[document_id] = registration
                candidate_indexes[document_id] = {
                    _text(candidate.get("candidate_id"), "candidate.candidate_id"): candidate
                    for candidate in (
                        _mapping(raw, "registration.evidence_review.candidates[]")
                        for raw in _items(
                            _mapping(
                                registration.get("evidence_review"),
                                "registration.evidence_review",
                            ).get("candidates"),
                            "registration.evidence_review.candidates",
                        )
                    )
                }

            candidate = candidate_indexes[document_id].get(candidate_id)
            if candidate is None:
                raise WaitingPeriodBindingError(
                    f"candidate {candidate_id!r} not found for {document_id}"
                )
            actual_hash = _text(candidate.get("text_sha256"), "candidate.text_sha256")
            if actual_hash != expected_hash:
                raise WaitingPeriodBindingError(
                    f"candidate text hash mismatch for {document_id}:{candidate_id}"
                )

            evidence_reference_id = f"{document_id}:{candidate_id}:{actual_hash}"
            evidence_reference_ids.append(evidence_reference_id)
            evidence.append(
                {
                    "role": role,
                    "document_id": document_id,
                    "candidate_id": candidate_id,
                    "candidate_text_sha256": actual_hash,
                    "source_page": candidate.get("source_page"),
                    "source_char_range": candidate.get("source_char_range"),
                }
            )

        if role_counts["mechanism"] != 1:
            raise WaitingPeriodBindingError(
                "waiting-period binding requires exactly one mechanism evidence selection"
            )
        if role_counts["schedule_value_resolution"] > 1:
            raise WaitingPeriodBindingError(
                "waiting-period binding permits at most one schedule_value_resolution selection"
            )

        mechanic = _mechanic(spec.get("mechanic"), tuple(evidence_reference_ids))
        if mechanic.value_source is WaitingPeriodValueSource.POLICY_SCHEDULE_SELECTED:
            if role_counts["schedule_value_resolution"] != 1:
                raise WaitingPeriodBindingError(
                    "POLICY_SCHEDULE_SELECTED scalar requires exactly one schedule_value_resolution evidence selection"
                )
            resolution_status = "resolved_from_authoritative_schedule_evidence"
        else:
            if role_counts["schedule_value_resolution"]:
                raise WaitingPeriodBindingError(
                    "PRODUCT_FIXED mechanic must not bind schedule_value_resolution evidence"
                )
            resolution_status = "resolved_from_mechanism_evidence"

        mechanic_payload = _serialize(asdict(mechanic))
        manifest = {
            "schema_version": "1.0",
            "binding_type": "waiting_period_binding_v1",
            "binding_status": "reviewed_waiting_period_bound_not_published",
            "resolution_status": resolution_status,
            "product_context": {
                "insurer_id": context.get("insurer_id"),
                "product_id": context.get("product_id"),
                "product_display_name": context.get("product_display_name"),
            },
            "generic_source_bundle_path": bundle_path,
            "binding_id": _text(spec.get("binding_id"), "binding_id"),
            "mechanic": mechanic_payload,
            "evidence": evidence,
            "publication_status": "bound_not_published",
            "bound_at": bound_at or datetime.now(timezone.utc).isoformat(),
            "reviewed_by_human": True,
            "guardrails": [
                "A resolved scalar waiting-period mechanic requires exact registered primary-legal evidence.",
                "Schedule-selected scalar values require separate authoritative schedule-value-resolution evidence.",
                "Unresolved Schedule-selected option domains cannot be manufactured by this binder.",
                "The binding does not publish or infer customer-specific eligibility.",
            ],
        }
        return WaitingPeriodBindingResult(manifest=manifest)

    def write_output(
        self,
        result: WaitingPeriodBindingResult,
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
            raise WaitingPeriodBindingError(
                "output_path must remain under repository_root"
            ) from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(result.manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target


__all__ = [
    "WaitingPeriodBinding",
    "WaitingPeriodBindingError",
    "WaitingPeriodBindingResult",
]
