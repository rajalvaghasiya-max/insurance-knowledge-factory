"""Disposable Product #11 Gate B probe support.

This file lives only on the non-merge smoke branch. It exists to make the
corrected origin resolver and blindness boundary directly falsifiable before
Gate B is frozen.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup


IDENTITY_STOPWORDS = {
    "insurance", "general", "company", "limited", "ltd", "co",
    "the", "of", "india",
}
EXCLUDED_EXTERNAL_HOSTS = {
    "facebook.com", "linkedin.com", "youtube.com", "youtu.be",
    "twitter.com", "x.com", "instagram.com", "google.com",
    "google.co.in", "goo.gl",
}
DOMAIN_RE = re.compile(
    r"(?i)(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9.-]*\.(?:co\.in|com|in|org|net))"
)


class BoundaryViolation(RuntimeError):
    pass


def opaque(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def host_key(value: str) -> str:
    raw = value.strip().lower()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    host = (urlparse(raw).hostname or "").lower().strip(".")
    return host[4:] if host.startswith("www.") else host


def is_irdai_host(host: str) -> bool:
    return host == "irdai.gov.in" or host.endswith(".irdai.gov.in")


def identity_tokens(value: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]+", value.lower()))
    return {token for token in tokens if token not in IDENTITY_STOPWORDS}


def matches_candidate(candidate_name: str, surface: str) -> bool:
    required = identity_tokens(candidate_name)
    return bool(required) and required.issubset(identity_tokens(surface))


def candidate_scoped_domains(html: str, candidate_name: str) -> list[tuple[int, str, str]]:
    """Return only candidate-matched scopes carrying exactly one external domain.

    A candidate with no qualifying scope returns an empty list. A scope with
    multiple external domains is deliberately not accepted as a unique origin.
    """
    soup = BeautifulSoup(html, "lxml")
    scopes: list[tuple[int, str, str]] = []
    for element in soup.find_all(
        ["tr", "li", "article", "section", "div", "td", "tbody", "table"]
    ):
        if not matches_candidate(candidate_name, element.get_text(" ", strip=True)):
            continue
        domains: set[str] = set()
        for match in DOMAIN_RE.finditer(str(element)):
            host = host_key(match.group(1))
            if host and not is_irdai_host(host) and host not in EXCLUDED_EXTERNAL_HOSTS:
                domains.add(host)
        if len(domains) == 1:
            scopes.append((len(str(element)), element.name, next(iter(domains))))
    return scopes


def resolve_candidate_origin(html_pages: list[str], candidate_name: str) -> tuple[str | None, str | None]:
    """Resolve the smallest unique candidate-scoped external domain, or not found."""
    best: tuple[int, str, str] | None = None
    for html in html_pages:
        scopes = candidate_scoped_domains(html, candidate_name)
        if not scopes:
            continue
        candidate_best = sorted(scopes, key=lambda item: (item[0], item[1]))[0]
        if best is None or (candidate_best[0], candidate_best[1]) < (best[0], best[1]):
            best = candidate_best
    if best is None:
        return None, None
    _, tag, host = best
    return "https://" + host + "/", tag


@dataclass
class BlindBoundaryAudit:
    counters: dict[str, int] = field(default_factory=lambda: {
        "raw_regulator_destination_urls_crossing_boundary": 0,
        "raw_insurer_origins_crossing_boundary": 0,
        "raw_insurer_destination_urls_crossing_boundary": 0,
        "anchor_text_crossing_boundary": 0,
        "body_text_crossing_boundary": 0,
        "page_titles_crossing_boundary": 0,
        "screenshots_crossing_boundary": 0,
    })

    _forbidden_key_to_counter = {
        "raw_regulator_destination_url": "raw_regulator_destination_urls_crossing_boundary",
        "raw_insurer_origin": "raw_insurer_origins_crossing_boundary",
        "raw_insurer_destination_url": "raw_insurer_destination_urls_crossing_boundary",
        "anchor_text": "anchor_text_crossing_boundary",
        "body_text": "body_text_crossing_boundary",
        "page_title": "page_titles_crossing_boundary",
        "screenshot": "screenshots_crossing_boundary",
    }

    def guard(self, payload: Any) -> Any:
        violations: list[str] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    counter = self._forbidden_key_to_counter.get(str(key))
                    if counter and item not in (None, "", [], {}):
                        self.counters[counter] += 1
                        violations.append(str(key))
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(payload)
        if violations:
            raise BoundaryViolation(
                "blind boundary rejected forbidden fields: " + ",".join(sorted(set(violations)))
            )
        return payload

    def safe_json(self, label: str, payload: Any) -> str:
        guarded = self.guard(payload)
        return label + json.dumps(guarded, sort_keys=True)


def run_self_tests() -> dict[str, bool]:
    candidate = "Example General Insurance Company Limited"
    present_html = """
    <table><tr><td>Example General Insurance Company Limited</td>
    <td>Website: https://example-insurer.invalid.com</td></tr></table>
    """
    absent_html = """
    <table><tr><td>Example General Insurance Company Limited</td>
    <td>Registered office only; no website signal</td></tr></table>
    """
    ambiguous_html = """
    <table><tr><td>Example General Insurance Company Limited</td>
    <td>https://one.invalid.com https://two.invalid.com</td></tr></table>
    """

    present_origin, _ = resolve_candidate_origin([present_html], candidate)
    absent_origin, _ = resolve_candidate_origin([absent_html], candidate)
    ambiguous_origin, _ = resolve_candidate_origin([ambiguous_html], candidate)

    audit = BlindBoundaryAudit()
    blocked = False
    try:
        audit.guard({
            "raw_insurer_destination_url": "https://semantic.example/product/policy-wording",
            "anchor_text": "Policy wording",
        })
    except BoundaryViolation:
        blocked = True

    return {
        "unique_signal_resolves": present_origin is not None,
        "absent_signal_returns_not_found": absent_origin is None,
        "ambiguous_signal_returns_not_found": ambiguous_origin is None,
        "boundary_violation_blocks": blocked,
        "boundary_counter_incremented": (
            audit.counters["raw_insurer_destination_urls_crossing_boundary"] == 1
            and audit.counters["anchor_text_crossing_boundary"] == 1
        ),
    }
