"""Authoritative publication adapter for the bounded Bajaj lab/radiology co-pay case."""
from __future__ import annotations

from pathlib import Path

from insurance_intelligence.authoritative_publication.gate import create_authoritative_publication
from insurance_intelligence.contracts.authoritative_publication import (
    AuthoritativePublicationRecord,
    build_authoritative_publication_input,
    build_governed_publication_projection,
    build_governed_semantic_component,
)
from insurance_intelligence.contracts.semantic import build_governed_semantic_attribute
from insurance_intelligence.publication_decision.bajaj import (
    build_bajaj_lab_copay_publication_context,
    build_bajaj_lab_copay_publication_decision,
)

PUBLICATION_AUTHORITY = "governed authoritative publication authority"


def _package_for_component(case, component_id: str):
    suffix = f":{component_id}"
    matches = tuple(
        package
        for package in case.evidence_output.evidence_packages
        if package.normalized_fact_reference.endswith(suffix)
        or package.evidence_id.endswith(suffix)
    )
    if len(matches) != 1:
        raise ValueError(f"expected exactly one evidence package for component {component_id}")
    return matches[0]


def build_bajaj_lab_copay_authoritative_publication(
    *, repository_root: str | Path
) -> AuthoritativePublicationRecord:
    case, _ = build_bajaj_lab_copay_publication_context(repository_root=repository_root)
    decision = build_bajaj_lab_copay_publication_decision(repository_root=repository_root)

    obligation = _package_for_component(case, "obligation_value")
    trigger = _package_for_component(case, "trigger_condition")
    scope = _package_for_component(case, "applicability_scope")

    components = (
        build_governed_semantic_component(
            component_id="obligation_value",
            status="SATISFIED",
            evidence_references=(obligation.evidence_id,),
            semantic_attributes=(
                build_governed_semantic_attribute(
                    key="rate",
                    value=obligation.claim,
                    evidence_references=(obligation.evidence_id,),
                ),
            ),
        ),
        build_governed_semantic_component(
            component_id="trigger_condition",
            status="SATISFIED",
            evidence_references=(trigger.evidence_id,),
            semantic_attributes=(
                build_governed_semantic_attribute(
                    key="trigger_condition",
                    value=trigger.claim,
                    evidence_references=(trigger.evidence_id,),
                ),
            ),
        ),
        build_governed_semantic_component(
            component_id="applicability_scope",
            status="SATISFIED",
            evidence_references=(scope.evidence_id,),
            semantic_attributes=(
                build_governed_semantic_attribute(
                    key="applicability_scope",
                    value=scope.claim,
                    evidence_references=(scope.evidence_id,),
                ),
            ),
        ),
    )
    projection = build_governed_publication_projection(
        projection_id="publication-projection:bajaj-my-health-care-v2:lab-radiology-copay",
        governed_subject_reference=decision.governed_subject_reference,
        certification_id=decision.certification_id,
        topic_id=decision.topic_id,
        topic_version=decision.topic_version,
        semantic_components=components,
        limitations=decision.limitations,
        evidence_trace_references=decision.evidence_trace_references,
        certification_trace_references=decision.certification_trace_references,
    )
    return create_authoritative_publication(
        build_authoritative_publication_input(
            publication_id="authoritative-publication:bajaj-my-health-care-v2:lab-radiology-copay",
            publication_decision=decision,
            governed_projection=projection,
            publication_authority=PUBLICATION_AUTHORITY,
        )
    )


__all__ = ["build_bajaj_lab_copay_authoritative_publication"]
