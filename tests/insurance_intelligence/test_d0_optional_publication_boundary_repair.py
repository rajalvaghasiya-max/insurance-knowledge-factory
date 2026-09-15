from __future__ import annotations

from pathlib import Path

from insurance_intelligence.publication_decision.governed import (
    build_governed_publication_decision,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PUBLICATION_SPEC_PATH = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/publication/"
    "star_initial_waiting_period_publication_spec.json"
)


def test_governed_publication_allows_omitted_boundary_authorization() -> None:
    decision = build_governed_publication_decision(
        publication_spec_path=PUBLICATION_SPEC_PATH,
        repository_root=REPOSITORY_ROOT,
    )

    assert decision.requested_status == "PUBLISH"
    assert decision.authorization_id is None
    assert decision.resolved_certification_limitations == ()


def test_existing_authorized_publication_specs_remain_compatible() -> None:
    existing_spec = (
        "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/v2/"
        "governance/bajaj_my_health_care_v2_lab_radiology_copay_publication_spec.json"
    )
    decision = build_governed_publication_decision(
        publication_spec_path=existing_spec,
        repository_root=REPOSITORY_ROOT,
    )

    assert decision.authorization_id is not None
    assert decision.publication_permitted is True
