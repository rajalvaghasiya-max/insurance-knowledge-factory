"""Generic multi-span binding for unresolved waiting-period option domains.

This wrapper extends the proven ``waiting_period_option_domain_binding_v1`` contract
only where a material waiting-period mechanic spans more than one registered evidence
candidate. It reuses the v1 binder for the base domain and validates every additional
mechanism candidate against the same governed primary-legal source registration.

The wrapper does not select a Schedule value, publish facts, or infer customer-specific
eligibility.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from factory_core.canonical.waiting_period_option_domain_binding import (
    WaitingPeriodOptionDomainBinding,
    WaitingPeriodOptionDomainBindingError,
    WaitingPeriodOptionDomainBindingResult,
)


class WaitingPeriodOptionDomainMultispanBindingError(ValueError):
    """Raised when a multi-span option-domain binding is incomplete or unsafe."""


@dataclass(frozen=True)
class WaitingPeriodOptionDomainMultispanBindingResult:
    manifest: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WaitingPeriodOptionDomainMultispanBindingError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise WaitingPeriodOptionDomainMultispanBindingError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodOptionDomainMultispanBindingError(f"{label} must be non-empty text")
    return value.strip()


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise WaitingPeriodOptionDomainMultispanBindingError(f"{label} must be repository-relative")
    return path.as_posix()


def _load(root: Path, relative_path: str, label: str) -> Mapping[str, Any]:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise WaitingPeriodOptionDomainMultispanBindingError(
            f"{label} must remain under repository_root"
        ) from exc
    if not path.is_file():
        raise WaitingPeriodOptionDomainMultispanBindingError(f"{label} not found: {relative_path}")
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WaitingPeriodOptionDomainMultispanBindingError(f"{label} is not valid JSON") from exc


def _selection_identity(selection: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        _text(selection.get("document_id"), "selection.document_id"),
        _text(selection.get("candidate_id"), "selection.candidate_id"),
        _text(selection.get("candidate_text_sha256"), "selection.candidate_text_sha256"),
    )


class WaitingPeriodOptionDomainMultispanBinding:
    """Bind an unresolved Schedule domain with one or more mechanism evidence spans."""

    def bind_from_spec_file(
        self,
        *,
        spec_path: str | Path,
        repository_root: str | Path,
        bound_at: str | None = None,
    ) -> WaitingPeriodOptionDomainMultispanBindingResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Binding specification was not found: {path}")
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WaitingPeriodOptionDomainMultispanBindingError(
                "binding specification is not valid JSON"
            ) from exc
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
    ) -> WaitingPeriodOptionDomainMultispanBindingResult:
        root = Path(repository_root).resolve()
        if spec.get("schema_version") != "1.0":
            raise WaitingPeriodOptionDomainMultispanBindingError("schema_version must be 1.0")
        if spec.get("binding_type") != "waiting_period_option_domain_multispan_binding_v1":
            raise WaitingPeriodOptionDomainMultispanBindingError(
                "binding_type must be waiting_period_option_domain_multispan_binding_v1"
            )
        if spec.get("reviewed_by_human") is not True:
            raise WaitingPeriodOptionDomainMultispanBindingError("reviewed_by_human must be true")

        selections = [
            _mapping(item, "evidence_selections[]")
            for item in _items(spec.get("evidence_selections"), "binding_spec.evidence_selections")
        ]
        mechanism_selections = [item for item in selections if item.get("role") == "mechanism"]
        option_domain_selections = [item for item in selections if item.get("role") == "option_domain"]
        unsupported_roles = {
            _text(item.get("role"), "evidence_selections[].role")
            for item in selections
            if item.get("role") not in {"mechanism", "option_domain"}
        }
        if unsupported_roles:
            raise WaitingPeriodOptionDomainMultispanBindingError(
                f"unsupported evidence roles: {sorted(unsupported_roles)!r}"
            )
        if not mechanism_selections or len(option_domain_selections) != 1:
            raise WaitingPeriodOptionDomainMultispanBindingError(
                "multi-span option-domain binding requires one or more mechanism selections and exactly one option_domain selection"
            )

        identities = [_selection_identity(item) for item in selections]
        if len(set(identities)) != len(identities):
            raise WaitingPeriodOptionDomainMultispanBindingError(
                "duplicate evidence selections are not permitted"
            )

        base_spec = dict(spec)
        base_spec["binding_type"] = "waiting_period_option_domain_binding_v1"
        base_spec["evidence_selections"] = [
            dict(mechanism_selections[0]),
            dict(option_domain_selections[0]),
        ]
        try:
            base_result: WaitingPeriodOptionDomainBindingResult = (
                WaitingPeriodOptionDomainBinding().bind(
                    spec=base_spec,
                    repository_root=root,
                    bound_at=bound_at,
                )
            )
        except WaitingPeriodOptionDomainBindingError as exc:
            raise WaitingPeriodOptionDomainMultispanBindingError(str(exc)) from exc

        bundle_path = _safe_relative(
            spec.get("generic_source_bundle_path"), "generic_source_bundle_path"
        )
        bundle = _load(root, bundle_path, "generic_source_bundle")
        sources = {
            _text(source.get("document_id"), "source.document_id"): source
            for source in (
                _mapping(raw, "generic_source_bundle.sources[]")
                for raw in _items(bundle.get("sources"), "generic_source_bundle.sources")
            )
        }
        registration_cache: dict[str, Mapping[str, Any]] = {}
        candidate_cache: dict[str, dict[str, Mapping[str, Any]]] = {}

        evidence: list[dict[str, Any]] = []
        refs: list[str] = []
        for index, selection in enumerate(selections):
            role = _text(selection.get("role"), f"evidence_selections[{index}].role")
            document_id, candidate_id, expected_hash = _selection_identity(selection)
            source = sources.get(document_id)
            if source is None:
                raise WaitingPeriodOptionDomainMultispanBindingError(
                    f"unregistered source {document_id!r}"
                )
            if source.get("authority_role") != "primary_legal":
                raise WaitingPeriodOptionDomainMultispanBindingError(
                    "waiting-period option domain requires primary_legal evidence"
                )
            if document_id not in registration_cache:
                registration_path = _safe_relative(
                    source.get("registration_output_path"), "source.registration_output_path"
                )
                registration = _load(root, registration_path, f"registration[{document_id}]")
                registration_cache[document_id] = registration
                review = _mapping(
                    registration.get("evidence_review"), "registration.evidence_review"
                )
                candidate_cache[document_id] = {
                    _text(candidate.get("candidate_id"), "candidate.candidate_id"): candidate
                    for candidate in (
                        _mapping(raw, "registration.evidence_review.candidates[]")
                        for raw in _items(
                            review.get("candidates"), "registration.evidence_review.candidates"
                        )
                    )
                }
            candidate = candidate_cache[document_id].get(candidate_id)
            if candidate is None:
                raise WaitingPeriodOptionDomainMultispanBindingError(
                    f"candidate {candidate_id!r} not found for {document_id}"
                )
            actual_hash = _text(candidate.get("text_sha256"), "candidate.text_sha256")
            if actual_hash != expected_hash:
                raise WaitingPeriodOptionDomainMultispanBindingError(
                    f"candidate text hash mismatch for {document_id}:{candidate_id}"
                )
            refs.append(f"{document_id}:{candidate_id}:{actual_hash}")
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

        manifest = dict(base_result.manifest)
        domain = dict(_mapping(manifest.get("option_domain"), "binding_manifest.option_domain"))
        domain["evidence_reference_ids"] = refs
        manifest.update(
            {
                "binding_type": "waiting_period_option_domain_multispan_binding_v1",
                "option_domain": domain,
                "evidence": evidence,
                "mechanism_evidence_span_count": len(mechanism_selections),
            }
        )
        manifest["guardrails"] = list(manifest.get("guardrails", [])) + [
            "Material mechanic semantics may span multiple exact primary-legal candidates; every candidate remains independently hash-bound."
        ]
        return WaitingPeriodOptionDomainMultispanBindingResult(manifest=manifest)

    def write_output(
        self,
        result: WaitingPeriodOptionDomainMultispanBindingResult,
        *,
        repository_root: str | Path,
        output_path: str | Path,
    ) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise WaitingPeriodOptionDomainMultispanBindingError(
                "output_path must remain under repository_root"
            ) from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(result.manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target


__all__ = [
    "WaitingPeriodOptionDomainMultispanBinding",
    "WaitingPeriodOptionDomainMultispanBindingError",
    "WaitingPeriodOptionDomainMultispanBindingResult",
]
