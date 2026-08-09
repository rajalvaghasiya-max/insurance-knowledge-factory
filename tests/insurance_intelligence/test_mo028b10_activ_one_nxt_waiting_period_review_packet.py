from pathlib import Path

from insurance_intelligence.benefits.activ_one_nxt_waiting_period_review_packet import (
    DEFAULT_BINDING_PATH,
    DEFAULT_PROCESSED_DOCUMENT_PATH,
    build_activ_one_nxt_waiting_period_review_packet,
    write_activ_one_nxt_waiting_period_review_packet,
)


def test_review_packet_builds_from_certified_binding_and_processed_document() -> None:
    text = build_activ_one_nxt_waiting_period_review_packet()

    assert "# Activ One NXT Waiting-Period Evidence Review Packet" in text
    assert "ADIHLIP24097V012324" in text
    assert "doc_d20a8488ecb3243f6de2" in text
    assert "pdoc_72d03e57d4b49c68d69a11fc" in text
    assert "e04bc4575d35e10bc86707ceeb839adf8a59f579bd27584c1b9000201bdac217" in text


def test_review_packet_contains_all_three_waiting_period_types() -> None:
    text = build_activ_one_nxt_waiting_period_review_packet()

    assert "## INITIAL" in text
    assert "## SPECIFIC_DISEASE_PROCEDURE" in text
    assert "## PRE_EXISTING_DISEASE" in text


def test_review_packet_preserves_optional_reduction_candidates() -> None:
    text = build_activ_one_nxt_waiting_period_review_packet()

    assert "Reduction in Speci" in text or "Reduction in Specific Disease Waiting Period" in text
    assert "Reduction in Pre-Existing Disease Waiting Period" in text


def test_review_packet_keeps_publication_fail_closed() -> None:
    text = build_activ_one_nxt_waiting_period_review_packet()

    assert "Human base-clause review decision recorded: **NO**" in text
    assert "Governed waiting-period publication created: **NO**" in text
    assert "Coverage Registry promoted: **NO**" in text


def test_review_packet_writer_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"

    write_activ_one_nxt_waiting_period_review_packet(first)
    write_activ_one_nxt_waiting_period_review_packet(second)

    assert first.read_bytes() == second.read_bytes()


def test_default_inputs_exist() -> None:
    assert DEFAULT_BINDING_PATH.is_file()
    assert DEFAULT_PROCESSED_DOCUMENT_PATH.is_file()
