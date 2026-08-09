"""Render the governed Health insurance intelligence coverage review artifact."""
from __future__ import annotations

from pathlib import Path

from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.coverage_registry.reporting import (
    build_coverage_review_report,
    render_coverage_review_markdown,
)

OUTPUT_PATH = Path("docs/architecture/HEALTH_INSURANCE_INTELLIGENCE_COVERAGE_REVIEW.md")


def main() -> None:
    report = build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render_coverage_review_markdown(report), encoding="utf-8")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
