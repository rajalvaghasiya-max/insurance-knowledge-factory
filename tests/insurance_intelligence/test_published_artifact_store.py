from __future__ import annotations

from pathlib import Path

from insurance_intelligence.authoritative_publication.star_health import (
    build_star_room_rent_authoritative_publication,
)
from insurance_intelligence.evidence.published_artifact_store import (
    load_published_evidence_source,
    persist_published_evidence_source,
)
from insurance_intelligence.evidence.published_materialization import PublishedEvidenceSource
from insurance_intelligence.rule_certification.star_health_room_rent import (
    build_star_comprehensive_room_rent_case,
)


def _source() -> PublishedEvidenceSource:
    case = build_star_comprehensive_room_rent_case()
    return PublishedEvidenceSource(
        publication=build_star_room_rent_authoritative_publication(),
        certified_evidence=case.evidence_output,
    )


def test_published_evidence_source_round_trips_through_frozen_json(tmp_path: Path):
    source = _source()
    publication_path = tmp_path / "publication.json"
    evidence_path = tmp_path / "evidence.json"

    persist_published_evidence_source(
        source=source,
        publication_path=publication_path,
        certified_evidence_path=evidence_path,
    )
    loaded = load_published_evidence_source(
        publication_path=publication_path,
        certified_evidence_path=evidence_path,
    )

    assert loaded == source
    assert publication_path.read_text(encoding="utf-8").endswith("\n")
    assert evidence_path.read_text(encoding="utf-8").endswith("\n")


def test_published_evidence_persistence_is_byte_deterministic(tmp_path: Path):
    source = _source()
    one_pub = tmp_path / "one" / "publication.json"
    one_evidence = tmp_path / "one" / "evidence.json"
    two_pub = tmp_path / "two" / "publication.json"
    two_evidence = tmp_path / "two" / "evidence.json"

    persist_published_evidence_source(
        source=source,
        publication_path=one_pub,
        certified_evidence_path=one_evidence,
    )
    persist_published_evidence_source(
        source=source,
        publication_path=two_pub,
        certified_evidence_path=two_evidence,
    )

    assert one_pub.read_bytes() == two_pub.read_bytes()
    assert one_evidence.read_bytes() == two_evidence.read_bytes()
