"""Generic authoritative publication builder driven by governed publication data."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from insurance_intelligence.authoritative_publication.gate import create_authoritative_publication
from insurance_intelligence.contracts.authoritative_publication import (
    AuthoritativePublicationRecord,
    build_authoritative_publication_input,
    build_governed_publication_projection,
    build_governed_semantic_component,
)
from insurance_intelligence.contracts.semantic import build_governed_semantic_attribute
from insurance_intelligence.publication_decision.governed import (
    GovernedPublicationSpecError,
    build_governed_publication_context,
    build_governed_publication_decision,
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedPublicationSpecError(f"{label} must be a non-empty string")
    return value.strip()


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise GovernedPublicationSpecError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list) or not value:
        raise GovernedPublicationSpecError(f"{label} must be a non-empty JSON array")
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        result.append(_mapping(item, f"{label}[{index}]"))
    return tuple(result)


def _package_for_component(case, component_id: str):
    suffix = f":{component_id}"
    matches = tuple(
        package
        for package in case.evidence_output.evidence_packages
        if (package.normalized_fact_reference or "").endswith(suffix)
        or package.evidence_id.endswith(suffix)
    )
    if len(matches) != 1:
        raise GovernedPublicationSpecError(
            f"expected exactly one evidence package for component {component_id}"
        )
    return matches[0]


def build_governed_authoritative_publication(
    *, publication_spec_path: str | Path, repository_root: str | Path
) -> AuthoritativePublicationRecord:
    spec, case, _ = build_governed_publication_context(
        publication_spec_path=publication_spec_path,
        repository_root=repository_root,
    )
    decision = build_governed_publication_decision(
        publication_spec_path=publication_spec_path,
        repository_root=repository_root,
    )
    publication = _mapping(
        spec.get("authoritative_publication"), "authoritative_publication"
    )
    component_specs = _items(
        publication.get("semantic_components"),
        "authoritative_publication.semantic_components",
    )
    seen_components: set[str] = set()
    seen_attributes: set[str] = set()
    components = []
    for component_spec in component_specs:
        component_id = _text(component_spec.get("component_id"), "component_id")
        attribute_key = _text(component_spec.get("attribute_key"), "attribute_key")
        if component_id in seen_components:
            raise GovernedPublicationSpecError("semantic component IDs must be unique")
        if attribute_key in seen_attributes:
            raise GovernedPublicationSpecError("semantic attribute keys must be unique")
        seen_components.add(component_id)
        seen_attributes.add(attribute_key)
        package = _package_for_component(case, component_id)
        components.append(
            build_governed_semantic_component(
                component_id=component_id,
                status="SATISFIED",
                evidence_references=(package.evidence_id,),
                semantic_attributes=(
                    build_governed_semantic_attribute(
                        key=attribute_key,
                        value=package.claim,
                        evidence_references=(package.evidence_id,),
                    ),
                ),
            )
        )
    projection = build_governed_publication_projection(
        projection_id=_text(publication.get("projection_id"), "projection_id"),
        governed_subject_reference=decision.governed_subject_reference,
        certification_id=decision.certification_id,
        topic_id=decision.topic_id,
        topic_version=decision.topic_version,
        semantic_components=tuple(components),
        limitations=decision.limitations,
        evidence_trace_references=decision.evidence_trace_references,
        certification_trace_references=decision.certification_trace_references,
    )
    return create_authoritative_publication(
        build_authoritative_publication_input(
            publication_id=_text(publication.get("publication_id"), "publication_id"),
            publication_decision=decision,
            governed_projection=projection,
            publication_authority=_text(
                publication.get("publication_authority"), "publication_authority"
            ),
        )
    )


__all__ = ["build_governed_authoritative_publication"]
