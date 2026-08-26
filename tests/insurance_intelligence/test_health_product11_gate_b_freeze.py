from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest
from bs4 import BeautifulSoup


ARTIFACT = Path(
    "docs/architecture/health_product11_gate_b_blind_path_discovery_2026-08-26.json"
)
STOPWORDS = {
    "insurance", "general", "company", "limited", "ltd", "co",
    "the", "of", "india",
}
DOMAIN_RE = re.compile(
    r"(?i)(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9.-]*\.(?:co\.in|com|in|org|net))"
)


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if token not in STOPWORDS
    }


def _host_key(value: str) -> str:
    raw = value.strip().lower()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    host = (urlparse(raw).hostname or "").lower().strip(".")
    return host[4:] if host.startswith("www.") else host


def _resolve_origin(html_pages: list[str], candidate_name: str) -> str | None:
    required = _tokens(candidate_name)
    best = None
    for html in html_pages:
        soup = BeautifulSoup(html, "lxml")
        for element in soup.find_all(
            ["tr", "li", "article", "section", "div", "td", "tbody", "table"]
        ):
            if not required.issubset(_tokens(element.get_text(" ", strip=True))):
                continue
            domains = {
                _host_key(match.group(1))
                for match in DOMAIN_RE.finditer(str(element))
            }
            domains.discard("irdai.gov.in")
            if len(domains) != 1:
                continue
            candidate = (len(str(element)), element.name, next(iter(domains)))
            if best is None or candidate[:2] < best[:2]:
                best = candidate
    return None if best is None else "https://" + best[2] + "/"


class BoundaryViolation(RuntimeError):
    pass


class _BoundaryAudit:
    def __init__(self) -> None:
        self.counters = {
            "raw_insurer_destination_urls_crossing_boundary": 0,
            "anchor_text_crossing_boundary": 0,
        }

    def guard(self, payload: dict) -> None:
        violated = False
        if payload.get("raw_insurer_destination_url"):
            self.counters["raw_insurer_destination_urls_crossing_boundary"] += 1
            violated = True
        if payload.get("anchor_text"):
            self.counters["anchor_text_crossing_boundary"] += 1
            violated = True
        if violated:
            raise BoundaryViolation


def test_corrected_matcher_resolves_unique_candidate_scopes_not_broad_parent() -> None:
    candidates = {
        "chola": "Cholamandalam MS General Insurance Company Limited",
        "magma": "Magma General Insurance Limited",
        "navi": "Navi General Insurance Limited",
        "shriram": "Shriram General Insurance Company Limited",
    }
    html = """
    <div class='directory'>
      <table>
        <tr><td>Cholamandalam MS General Insurance Company Limited</td><td>https://chola.example.com</td></tr>
        <tr><td>Magma General Insurance Limited</td><td>https://magma.example.com</td></tr>
        <tr><td>Navi General Insurance Limited</td><td>https://navi.example.com</td></tr>
        <tr><td>Shriram General Insurance Company Limited</td><td>https://shriram.example.com</td></tr>
      </table>
    </div>
    """
    # The broad parent contains all four domains; accepting it would reproduce
    # the original over-broad-container defect. The corrected matcher resolves
    # each candidate from a smaller unique scope instead.
    assert {
        candidate_id: _resolve_origin([html], name)
        for candidate_id, name in candidates.items()
    } == {
        "chola": "https://chola.example.com/",
        "magma": "https://magma.example.com/",
        "navi": "https://navi.example.com/",
        "shriram": "https://shriram.example.com/",
    }


def test_corrected_matcher_returns_not_found_when_origin_signal_absent() -> None:
    html = """
    <table><tr><td>Example General Insurance Company Limited</td>
    <td>Registered office only; no website signal.</td></tr></table>
    """
    assert _resolve_origin([html], "Example General Insurance Company Limited") is None


def test_corrected_matcher_returns_not_found_when_signal_is_not_unique() -> None:
    html = """
    <table><tr><td>Example General Insurance Company Limited</td>
    <td>https://one.example.com https://two.example.com</td></tr></table>
    """
    assert _resolve_origin([html], "Example General Insurance Company Limited") is None


def test_boundary_counters_are_active_and_violation_blocks() -> None:
    audit = _BoundaryAudit()
    with pytest.raises(BoundaryViolation):
        audit.guard({
            "raw_insurer_destination_url": "https://example.com/product/policy-wording",
            "anchor_text": "Policy wording",
        })
    assert audit.counters == {
        "raw_insurer_destination_urls_crossing_boundary": 1,
        "anchor_text_crossing_boundary": 1,
    }


def test_freeze_records_shriram_only_scope_not_eligible_set_viability() -> None:
    record = _artifact()
    result = record["gate_b_result"]
    scope = record["scope_of_proof"]
    assert result["resolved_candidate_ids"] == ["chola", "magma", "navi", "shriram"]
    assert result["capturable_candidate_ids_in_authoritative_run"] == ["shriram"]
    assert result["noncapturable_candidate_ids_in_authoritative_run"] == [
        "chola", "magma", "navi"
    ]
    assert result["passing_candidate_ids"] == ["shriram"]
    assert result["passing_candidate_authorized_blind_projection_count"] == 7
    assert "works for Shriram" in scope["proven"]
    assert "all four" in scope["not_proven"]


def test_freeze_pins_falsification_and_active_zero_boundary_metrics() -> None:
    record = _artifact()
    proof = record["correction_falsification_proof"]
    assert proof["unique_signal_resolves"] is True
    assert proof["absent_signal_returns_not_found"] is True
    assert proof["ambiguous_signal_returns_not_found"] is True
    assert proof["boundary_violation_blocks"] is True
    assert proof["boundary_counter_incremented"] is True

    metrics = record["blindness_and_method_metrics"]
    assert metrics["boundary_instrumentation_active"] is True
    boundary_keys = [
        "raw_regulator_destination_urls_crossing_boundary",
        "raw_insurer_origins_crossing_boundary",
        "raw_insurer_destination_urls_crossing_boundary",
        "anchor_text_crossing_boundary",
        "body_text_crossing_boundary",
        "page_titles_crossing_boundary",
        "screenshots_crossing_boundary",
    ]
    assert all(metrics[key] == 0 for key in boundary_keys)
    assert record["execution_lineage"]["authoritative_smoke_commit"] == (
        "b6bb8d66748402bf7794a0fd0662123d0570f091"
    )
    assert record["diagnostic_lineage"][
        "intermediate_corrected_smoke_authoritative_for_final_freeze"
    ] is False
    assert record["gate_decision"]["gate_c_authorized"] is True
    assert record["gate_decision"]["product_screening_authorized"] is False
