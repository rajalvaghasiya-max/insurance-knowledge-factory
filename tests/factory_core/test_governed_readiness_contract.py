from __future__ import annotations

import pytest

from factory_core.governance.governed_readiness import (
    GovernedReadinessContractError,
    assessment_from_mapping,
    build_governed_readiness_assessment,
)


ENTITY = "test_insurer:test_product"


def test_unassessed_dimensions_derive_not_assessed():
    assessment = build_governed_readiness_assessment(
        entity_id=ENTITY,
        source_governance="NOT_ASSESSED",
        semantic_review="NOT_ASSESSED",
        applicability="NOT_ASSESSED",
        publication_eligibility="NOT_ASSESSED",
        publication_state="NOT_ASSESSED",
    )

    assert assessment.status == "NOT_ASSESSED"


def test_fully_resolved_not_published_derives_ready_for_publication_review():
    assessment = build_governed_readiness_assessment(
        entity_id=ENTITY,
        source_governance="CURRENT_GOVERNED",
        semantic_review="COMPLETE",
        applicability="RESOLVED",
        publication_eligibility="ELIGIBLE",
        publication_state="NOT_PUBLISHED",
        evidence_references=("governance/source.json", "governance/review.json"),
    )

    assert assessment.status == "READY_FOR_PUBLICATION_REVIEW"


def test_unresolved_residue_prevents_ready_status():
    assessment = build_governed_readiness_assessment(
        entity_id=ENTITY,
        source_governance="CURRENT_GOVERNED",
        semantic_review="COMPLETE",
        applicability="RESOLVED",
        publication_eligibility="ELIGIBLE",
        publication_state="NOT_PUBLISHED",
        unresolved_residue=("PED duration requires policy schedule binding",),
        evidence_references=("governance/review.json",),
    )

    assert assessment.status == "REVIEW_REQUIRED"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_governance", "CURRENTNESS_UNRESOLVED"),
        ("semantic_review", "CONFLICTING"),
        ("applicability", "UNRESOLVED"),
        ("publication_eligibility", "INELIGIBLE"),
    ],
)
def test_material_blockers_derive_blocked(field, value):
    values = {
        "source_governance": "CURRENT_GOVERNED",
        "semantic_review": "COMPLETE",
        "applicability": "RESOLVED",
        "publication_eligibility": "ELIGIBLE",
        "publication_state": "NOT_PUBLISHED",
    }
    values[field] = value

    assessment = build_governed_readiness_assessment(
        entity_id=ENTITY,
        evidence_references=("governance/evidence.json",),
        **values,
    )

    assert assessment.status == "BLOCKED"


def test_published_requires_fully_resolved_prerequisites():
    with pytest.raises(
        GovernedReadinessContractError,
        match="publication_state PUBLISHED requires",
    ):
        build_governed_readiness_assessment(
            entity_id=ENTITY,
            source_governance="CURRENT_GOVERNED",
            semantic_review="PARTIAL",
            applicability="RESOLVED",
            publication_eligibility="ELIGIBLE",
            publication_state="PUBLISHED",
            evidence_references=("governance/publication.json",),
        )


def test_assessed_state_requires_evidence_reference():
    with pytest.raises(
        GovernedReadinessContractError,
        match="requires at least one evidence_reference",
    ):
        build_governed_readiness_assessment(
            entity_id=ENTITY,
            source_governance="CURRENT_GOVERNED",
            semantic_review="COMPLETE",
            applicability="RESOLVED",
            publication_eligibility="ELIGIBLE",
            publication_state="NOT_PUBLISHED",
        )


def test_mapping_rejects_asserted_summary_status():
    data = {
        "entity_id": ENTITY,
        "source_governance": "CURRENT_GOVERNED",
        "semantic_review": "COMPLETE",
        "applicability": "RESOLVED",
        "publication_eligibility": "ELIGIBLE",
        "publication_state": "NOT_PUBLISHED",
        "unresolved_residue": [],
        "evidence_references": ["governance/review.json"],
        "status": "PUBLISHED",
    }

    with pytest.raises(
        GovernedReadinessContractError,
        match="unknown governed-readiness field.*status",
    ):
        assessment_from_mapping(data, expected_entity_id=ENTITY)


def test_mapping_rejects_entity_mismatch():
    data = {
        "entity_id": "other:product",
        "source_governance": "CURRENT_GOVERNED",
        "semantic_review": "COMPLETE",
        "applicability": "RESOLVED",
        "publication_eligibility": "ELIGIBLE",
        "publication_state": "NOT_PUBLISHED",
        "unresolved_residue": [],
        "evidence_references": ["governance/review.json"],
    }

    with pytest.raises(GovernedReadinessContractError, match="entity_id must match"):
        assessment_from_mapping(data, expected_entity_id=ENTITY)
