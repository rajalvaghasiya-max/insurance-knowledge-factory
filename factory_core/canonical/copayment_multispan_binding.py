"""Generic multi-span binding for product-level co-payment rate-matrix mechanics.

The binder reuses the reviewed generic legal-condition boundary for the assertion
itself, then expands exact primary-legal evidence across multiple candidates and
attaches a typed co-payment matrix mechanic.  It does not publish the assertion or
resolve a policy / claim-instance percentage.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from factory_core.canonical.generic_legal_condition_binding import (
    GenericLegalConditionBinding,
    GenericLegalConditionBindingError,
)
from insurance_intelligence.benefits.copayment_rate_matrix import (
    CopaymentCalculationBasis,
    CopaymentRateMatrixCell,
    CopaymentRateMatrixMechanic,
)


class CopaymentMultispanBindingError(ValueError):
    """Raised when a reviewed multi-span co-payment binding is unsafe."""


@dataclass(frozen=True)
class CopaymentMultispanBindingResult:
    manifest: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CopaymentMultispanBindingError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CopaymentMultispanBindingError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CopaymentMultispanBindingError(f"{label} must be non-empty text")
    return value.strip()


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise CopaymentMultispanBindingError(f"{label} must be repository-relative")
    return path.as_posix()


def _load(root: Path, relative: str, label: str) -> Mapping[str, Any]:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise CopaymentMultispanBindingError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise CopaymentMultispanBindingError(f"{label} not found: {relative}")
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CopaymentMultispanBindingError(f"{label} is not valid JSON") from exc


def _candidate_index(registration: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    review = _mapping(registration.get("evidence_review"), "registration.evidence_review")
    result: dict[str, Mapping[str, Any]] = {}
    for raw in _items(review.get("candidates"), "registration.evidence_review.candidates"):
        candidate = _mapping(raw, "candidate")
        result[_text(candidate.get("candidate_id"), "candidate.candidate_id")] = candidate
    return result


def _serialize(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


class CopaymentMultispanBinding:
    def bind_from_spec_file(
        self,
        *,
        spec_path: str | Path,
        repository_root: str | Path,
        bound_at: str | None = None,
    ) -> CopaymentMultispanBindingResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Binding specification was not found: {path}")
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CopaymentMultispanBindingError("binding specification must be valid UTF-8 JSON") from exc
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
    ) -> CopaymentMultispanBindingResult:
        root = Path(repository_root).resolve()
        spec = _mapping(spec, "binding_spec")
        if spec.get("schema_version") != "1.0":
            raise CopaymentMultispanBindingError("schema_version must be 1.0")
        if spec.get("binding_type") != "copayment_multispan_binding_v1":
            raise CopaymentMultispanBindingError("unsupported binding_type")
        if spec.get("reviewed_by_human") is not True:
            raise CopaymentMultispanBindingError("reviewed_by_human must be true")

        assertion = _mapping(spec.get("assertion"), "assertion")
        if assertion.get("assertion_type") != "conditional_copayment_rule":
            raise CopaymentMultispanBindingError("assertion_type must be conditional_copayment_rule")
        selections = [
            _mapping(raw, "assertion.evidence_selections[]")
            for raw in _items(assertion.get("evidence_selections"), "assertion.evidence_selections")
        ]
        if len(selections) < 2:
            raise CopaymentMultispanBindingError("multispan copayment binding requires at least two selections")
        if any(item.get("role") != "mechanism" for item in selections):
            raise CopaymentMultispanBindingError("all multispan copayment selections must use role=mechanism")
        identities = [
            (
                _text(item.get("document_id"), "evidence_selection.document_id"),
                _text(item.get("candidate_id"), "evidence_selection.candidate_id"),
                _text(item.get("candidate_text_sha256"), "evidence_selection.candidate_text_sha256"),
            )
            for item in selections
        ]
        if len(identities) != len(set(identities)):
            raise CopaymentMultispanBindingError("duplicate evidence selections are not permitted")

        base_assertion = dict(assertion)
        base_assertion["evidence_selections"] = [dict(selections[0])]
        base_spec = {
            "schema_version": "1.0",
            "binding_type": "generic_legal_condition_binding_v1",
            "reviewed_by_human": True,
            "generic_source_bundle_path": spec.get("generic_source_bundle_path"),
            "assertions": [base_assertion],
        }
        try:
            base = GenericLegalConditionBinding().bind(
                spec=base_spec,
                repository_root=root,
                bound_at=bound_at,
            )
        except GenericLegalConditionBindingError as exc:
            raise CopaymentMultispanBindingError(str(exc)) from exc

        bundle_path = _safe_relative(
            spec.get("generic_source_bundle_path"), "generic_source_bundle_path"
        )
        bundle = _load(root, bundle_path, "generic_source_bundle")
        sources = {
            _text(source.get("document_id"), "source.document_id"): source
            for source in (
                _mapping(raw, "source") for raw in _items(bundle.get("sources"), "sources")
            )
        }
        registrations: dict[str, Mapping[str, Any]] = {}
        candidate_indexes: dict[str, dict[str, Mapping[str, Any]]] = {}
        bound_evidence: list[dict[str, Any]] = []
        evidence_refs: list[str] = []

        for selection in selections:
            document_id = _text(selection.get("document_id"), "document_id")
            candidate_id = _text(selection.get("candidate_id"), "candidate_id")
            expected_hash = _text(selection.get("candidate_text_sha256"), "candidate_text_sha256")
            source = sources.get(document_id)
            if source is None or source.get("authority_role") != "primary_legal":
                raise CopaymentMultispanBindingError(
                    "all multispan copayment evidence must be registered primary_legal evidence"
                )
            if document_id not in registrations:
                registration_path = _safe_relative(
                    source.get("registration_output_path"), "registration_output_path"
                )
                registration = _load(root, registration_path, f"registration[{document_id}]")
                registrations[document_id] = registration
                candidate_indexes[document_id] = _candidate_index(registration)
            candidate = candidate_indexes[document_id].get(candidate_id)
            if candidate is None or candidate.get("text_sha256") != expected_hash:
                raise CopaymentMultispanBindingError(
                    f"candidate lineage mismatch: {document_id}:{candidate_id}"
                )
            evidence_refs.append(f"{document_id}:{candidate_id}:{expected_hash}")
            bound_evidence.append(
                {
                    "role": "mechanism",
                    "document_id": document_id,
                    "document_version_id": source.get("document_version_id"),
                    "authority_role": "primary_legal",
                    "candidate_id": candidate_id,
                    "candidate_text_sha256": expected_hash,
                    "source_page": candidate.get("source_page"),
                    "source_char_range": candidate.get("source_char_range"),
                }
            )

        raw_mechanic = _mapping(spec.get("mechanic"), "mechanic")
        cells = tuple(
            CopaymentRateMatrixCell(
                plan_variant=_text(cell.get("plan_variant"), "cell.plan_variant"),
                claimed_category=_text(cell.get("claimed_category"), "cell.claimed_category"),
                percentage=cell.get("percentage"),
            )
            for cell in (
                _mapping(raw, "mechanic.cells[]")
                for raw in _items(raw_mechanic.get("cells"), "mechanic.cells")
            )
        )
        try:
            calculation_basis = CopaymentCalculationBasis(
                _text(raw_mechanic.get("calculation_basis"), "mechanic.calculation_basis")
            )
        except ValueError as exc:
            raise CopaymentMultispanBindingError("unsupported copayment calculation basis") from exc
        mechanic = CopaymentRateMatrixMechanic(
            cells=cells,
            trigger_condition=_text(raw_mechanic.get("trigger_condition"), "mechanic.trigger_condition"),
            applicability_scope=_text(raw_mechanic.get("applicability_scope"), "mechanic.applicability_scope"),
            calculation_basis=calculation_basis,
            evidence_reference_ids=tuple(evidence_refs),
            instance_resolution_dependency=_text(
                raw_mechanic.get("instance_resolution_dependency"),
                "mechanic.instance_resolution_dependency",
            ),
        )

        component_map = _mapping(
            spec.get("component_evidence_candidate_ids"),
            "component_evidence_candidate_ids",
        )
        expected_components = {
            "obligation_value",
            "trigger_condition",
            "applicability_scope",
            "calculation_basis",
        }
        if set(component_map) != expected_components:
            raise CopaymentMultispanBindingError(
                "component evidence map must exactly cover obligation_value, trigger_condition, "
                "applicability_scope, and calculation_basis"
            )
        bound_candidate_ids = {entry[1] for entry in identities}
        for component_id in sorted(expected_components):
            candidate_ids = tuple(
                _text(value, f"{component_id}[]")
                for value in _items(component_map.get(component_id), component_id)
            )
            if not candidate_ids or len(candidate_ids) != len(set(candidate_ids)):
                raise CopaymentMultispanBindingError(
                    f"component {component_id} must map to unique candidate IDs"
                )
            unknown = set(candidate_ids) - bound_candidate_ids
            if unknown:
                raise CopaymentMultispanBindingError(
                    f"component {component_id} references unbound candidates: {sorted(unknown)}"
                )

        manifest = dict(base.manifest)
        assertions = list(manifest.get("assertions", []))
        if len(assertions) != 1:
            raise CopaymentMultispanBindingError("multispan binding requires exactly one assertion")
        bound_assertion = dict(_mapping(assertions[0], "bound_assertion"))
        bound_assertion["evidence"] = bound_evidence
        manifest.update(
            {
                "binding_type": "copayment_multispan_binding_v1",
                "binding_id": _text(spec.get("binding_id"), "binding_id"),
                "assertions": [bound_assertion],
                "mechanic": _serialize(asdict(mechanic)),
                "component_evidence_candidate_ids": {
                    component_id: list(component_map[component_id])
                    for component_id in sorted(expected_components)
                },
                "mechanism_evidence_span_count": len(bound_evidence),
            }
        )
        manifest["guardrails"] = list(manifest.get("guardrails", [])) + [
            "A product-level rate matrix does not resolve one customer-specific co-payment percentage.",
            "Unlisted plan-variant / claimed-category combinations remain unresolved and must not be coerced to 0% or another value.",
            "Component certification must preserve candidate-level lineage for obligation value, trigger, applicability scope, and calculation basis.",
        ]
        return CopaymentMultispanBindingResult(manifest=manifest)

    def write_output(
        self,
        result: CopaymentMultispanBindingResult,
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
            raise CopaymentMultispanBindingError("output_path must remain under repository_root") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target


__all__ = [
    "CopaymentMultispanBinding",
    "CopaymentMultispanBindingError",
    "CopaymentMultispanBindingResult",
]
