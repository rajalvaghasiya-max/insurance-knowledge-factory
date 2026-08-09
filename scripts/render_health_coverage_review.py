"""Render the current governed Health insurance intelligence coverage review artifact."""
from __future__ import annotations

from pathlib import Path

from insurance_intelligence.coverage_registry.health_current import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.coverage_registry.reporting import (
    build_coverage_review_report,
    render_coverage_review_markdown,
)

OUTPUT_PATH = Path("docs/architecture/HEALTH_INSURANCE_INTELLIGENCE_COVERAGE_REVIEW.md")


def write_health_coverage_review(output_path: Path = OUTPUT_PATH) -> Path:
    """Render the current review using canonical UTF-8/LF bytes on every platform."""

    report = build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    rendered = render_coverage_review_markdown(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(rendered)
    return output_path


def main() -> None:
    print(write_health_coverage_review())


if __name__ == "__main__":
    main()
