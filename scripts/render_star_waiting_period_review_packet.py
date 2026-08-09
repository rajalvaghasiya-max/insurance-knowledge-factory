"""Render the Star Comprehensive waiting-period evidence review packet."""
from __future__ import annotations

from pathlib import Path

from insurance_intelligence.benefits.waiting_period_evidence_audit import (
    audit_all_waiting_period_candidates,
    load_registered_source,
)

REGISTERED_SOURCE_PATH = Path(
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_source_registration/policy_wording_registration.json"
)
OUTPUT_PATH = Path(
    "docs/architecture/STAR_COMPREHENSIVE_WAITING_PERIOD_REVIEW_PACKET.md"
)


def _render() -> str:
    results = audit_all_waiting_period_candidates(load_registered_source(REGISTERED_SOURCE_PATH))
    first = results[0]
    lines = [
        "# Star Comprehensive Waiting-Period Review Packet",
        "",
        "## Governance Status",
        "",
        "This packet is evidence-review material only. No candidate is approved, published, or available for runtime waiting-period automation by this artifact.",
        "",
        f"- Document ID: `{first.document_id}`",
        f"- Document version: `{first.document_version_id}`",
        f"- Document SHA256: `{first.document_sha256}`",
        f"- Storage locator: `{first.storage_locator}`",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"## {result.waiting_period_type.value}",
                "",
                f"Marker: `{result.marker}`",
                f"Audit status: `{result.status.value}`",
                f"Candidate count: {len(result.candidates)}",
                "",
            ]
        )
        if not result.candidates:
            lines.extend(["No registered candidate contains this marker.", ""])
            continue
        for candidate in result.candidates:
            lines.extend(
                [
                    f"### {candidate.candidate_id} — source page {candidate.source_page}",
                    "",
                    f"Candidate text SHA256: `{candidate.text_sha256}`",
                    "",
                    "```text",
                    candidate.excerpt.rstrip(),
                    "```",
                    "",
                ]
            )
    lines.extend(
        [
            "## Review Decision",
            "",
            "For each waiting-period type, a reviewer must identify the exact base exclusion clause and reject optional-cover, definition-only, or other repeated-marker occurrences before a governed product publication can be created.",
            "",
            "Until that review is recorded, the Health Coverage Registry remains `NOT_AUTOMATED` for Star Comprehensive waiting periods.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(_render())
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
