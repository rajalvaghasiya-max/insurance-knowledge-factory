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


def test_governed_publication_does_not_require_boundary_authorization_when_none_is_resolvable() -> None:
    """D0 falsification: optional contract authorization must remain optional in the data builder.

    The Star initial waiting-period certification has no machine-resolvable
    `bound_not_published` limitation. The versioned publication-decision contract permits
    boundary_authorization=None, so the governed spec builder must not require an
    authorization object simply because another publication family needed one.
    """
    decision = build_governed_publication_decision(
        publication_spec_path=PUBLICATION_SPEC_PATH,
        repository_root=REPOSITORY_ROOT,
    )

    assert decision.requested_status == "PUBLISH"
    assert decision.decision_status == "PUBLISH"
    assert decision.publication_permitted is True
    assert decision.authorization_id is None
    assert decision.resolved_certification_limitations == ()
