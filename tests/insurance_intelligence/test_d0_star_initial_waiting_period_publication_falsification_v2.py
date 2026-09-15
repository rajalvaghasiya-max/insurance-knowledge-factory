from pathlib import Path

from insurance_intelligence.authoritative_publication.governed import (
    build_governed_authoritative_publication,
)
from insurance_intelligence.publication_decision.governed import (
    build_governed_publication_decision,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PUBLICATION_SPEC_PATH = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/publication/"
    "star_initial_waiting_period_publication_spec.json"
)


def test_star_initial_waiting_period_reaches_authoritative_publication() -> None:
    """D0 falsification: the real governed Star waiting-period case must publish end to end."""
    decision = build_governed_publication_decision(
        publication_spec_path=PUBLICATION_SPEC_PATH,
        repository_root=REPOSITORY_ROOT,
    )

    assert decision.decision_status == "PUBLISH"
    assert decision.publication_permitted is True
    assert decision.failures == ()
    assert decision.certification_trace_references

    publication = build_governed_authoritative_publication(
        publication_spec_path=PUBLICATION_SPEC_PATH,
        repository_root=REPOSITORY_ROOT,
    )
    assert publication.publication_status == "PUBLISHED"
    assert publication.governed_projection.topic_id == "waiting_period"
    assert len(publication.governed_projection.semantic_components) == 6
