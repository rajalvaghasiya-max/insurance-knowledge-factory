"""Generic governed publication-decision orchestration from data specifications."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from insurance_intelligence.contracts.publication_decision import (
    PublicationDecisionResult,
    build_publication_boundary_authorization,
    build_publication_decision_input,
)
from insurance_intelligence.publication_decision.evaluator import evaluate_publication_decision
from insurance_intelligence.rule_certification.conditional_copayment import (
    build_conditional_copayment_certification_cases,
    run_conditional_copayment_certification_cases,
)


class GovernedPublicationSpecError(ValueError):
    """Raised when a governed publication specification is invalid or unsupported."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedPublicationSpecError(f"{label} must be a non-empty string")
    return value.strip()


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise GovernedPublicationSpecError(f"{label} must be a JSON object")
    return value


def _strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise GovernedPublicationSpecError(f"{label} must be a JSON array")
    result = tuple(_text(item, f"{label}[]") for item in value)
    if len(result) != len(set(result)):
        raise GovernedPublicationSpecError(f"{label} values must be unique")
    return result


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise GovernedPublicationSpecError(f"{label} must be repository-relative")
    return path.as_posix()


def load_governed_publication_spec(
    *, publication_spec_path: str | Path, repository_root: str | Path
) -> Mapping[str, Any]:
    root = Path(repository_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"repository_root was not found: {root}")
    relative = _safe_relative(str(publication_spec_path), "publication_spec_path")
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise GovernedPublicationSpecError(
            "publication_spec_path must remain under repository_root"
        ) from exc
    if not path.is_file():
        raise FileNotFoundError(f"publication spec was not found: {relative}")
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GovernedPublicationSpecError("publication spec must be valid JSON") from exc
    spec = _mapping(spec, "publication_spec")
    if spec.get("schema_version") != "1.0":
        raise GovernedPublicationSpecError("unsupported publication spec schema_version")
    if spec.get("publication_spec_type") != "governed_assertion_publication_v1":
        raise GovernedPublicationSpecError("unsupported publication_spec_type")
    return spec


def build_governed_publication_context(
    *, publication_spec_path: str | Path, repository_root: str | Path
):
    spec = load_governed_publication_spec(
        publication_spec_path=publication_spec_path,
        repository_root=repository_root,
    )
    certification = _mapping(spec.get("certification"), "certification")
    strategy = _text(certification.get("strategy"), "certification.strategy")
    if strategy != "conditional_copayment_binding_v1":
        raise GovernedPublicationSpecError(
            f"unsupported certification strategy: {strategy}"
        )
    binding_path = _safe_relative(
        certification.get("binding_manifest_path"),
        "certification.binding_manifest_path",
    )
    assertion_ids = _strings(certification.get("assertion_ids"), "certification.assertion_ids")
    if len(assertion_ids) != 1:
        raise GovernedPublicationSpecError(
            "governed_assertion_publication_v1 currently requires exactly one assertion_id"
        )
    bundle = build_conditional_copayment_certification_cases(
        binding_manifest_path=binding_path,
        repository_root=repository_root,
        assertion_ids=assertion_ids,
    )
    if len(bundle.cases) != 1:
        raise GovernedPublicationSpecError("publication spec must resolve exactly one certification case")
    case = bundle.cases[0]
    result = run_conditional_copayment_certification_cases(bundle)[0]
    return spec, case, result


def build_governed_publication_decision(
    *, publication_spec_path: str | Path, repository_root: str | Path
) -> PublicationDecisionResult:
    spec, case, certification = build_governed_publication_context(
        publication_spec_path=publication_spec_path,
        repository_root=repository_root,
    )
    decision = _mapping(spec.get("publication_decision"), "publication_decision")
    boundary = _mapping(
        decision.get("boundary_authorization"),
        "publication_decision.boundary_authorization",
    )
    resolved_tokens = _strings(
        boundary.get("resolved_boundary_tokens"),
        "publication_decision.boundary_authorization.resolved_boundary_tokens",
    )
    authorization = build_publication_boundary_authorization(
        authorization_id=_text(boundary.get("authorization_id"), "authorization_id"),
        governed_subject_reference=certification.governed_subject_reference,
        certification_id=certification.certification_id,
        resolved_boundary_tokens=resolved_tokens,
        authorization_authority=_text(
            boundary.get("authorization_authority"), "authorization_authority"
        ),
        trace_references=_strings(
            boundary.get("trace_references"),
            "publication_decision.boundary_authorization.trace_references",
        ),
    )
    limitation_tokens = tuple(
        token.casefold()
        for token in _strings(
            decision.get("resolved_limitation_tokens"),
            "publication_decision.resolved_limitation_tokens",
        )
    )
    retained_limitations = tuple(
        item
        for item in certification.limitations
        if not any(token in item.casefold() for token in limitation_tokens)
    )
    evidence_refs = tuple(
        package.evidence_id for package in case.evidence_output.evidence_packages
    )
    return evaluate_publication_decision(
        build_publication_decision_input(
            decision_id=_text(decision.get("decision_id"), "publication_decision.decision_id"),
            governed_subject_reference=certification.governed_subject_reference,
            certification_result=certification,
            requested_status=_text(
                decision.get("requested_status"), "publication_decision.requested_status"
            ),
            decision_reasons=_strings(
                decision.get("decision_reasons"), "publication_decision.decision_reasons"
            ),
            limitations=retained_limitations,
            evidence_trace_references=evidence_refs,
            decision_authority=_text(
                decision.get("decision_authority"), "publication_decision.decision_authority"
            ),
            boundary_authorization=authorization,
        )
    )


__all__ = [
    "GovernedPublicationSpecError",
    "build_governed_publication_context",
    "build_governed_publication_decision",
    "load_governed_publication_spec",
]
