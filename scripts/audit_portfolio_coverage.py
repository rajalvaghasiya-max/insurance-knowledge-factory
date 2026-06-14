from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


PORTFOLIO_AUDIT_VERSION = "0.1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_coverage_reports(domain: str) -> list[Path]:
    root = BASE_DIR / "knowledge" / domain

    if not root.exists():
        raise FileNotFoundError(f"Domain folder not found: {root}")

    return sorted(root.rglob("coverage/product_coverage_report.json"))


def entity_from_report_path(path: Path, domain: str) -> str:
    """
    Expected:
    knowledge/health/<insurer>/<product>/coverage/product_coverage_report.json
    """
    relative = path.relative_to(BASE_DIR / "knowledge" / domain)
    parts = relative.parts

    if len(parts) < 4:
        return "unknown:unknown"

    insurer_slug = parts[0]
    product_slug = parts[1]

    return f"{insurer_slug}:{product_slug}"


def summarize_products(reports: list[dict[str, Any]]) -> dict[str, Any]:
    status_counter = Counter()
    validator_status_counter = Counter()

    total_coverage = 0.0
    total_validator_score = 0.0
    validator_score_count = 0

    for report in reports:
        status_counter[report.get("coverage_status", "UNKNOWN")] += 1
        total_coverage += float(report.get("overall_coverage", 0))

        quality = report.get("quality", {})
        validator_status_counter[quality.get("validator_status", "UNKNOWN")] += 1

        validator_score = quality.get("validator_score")
        if isinstance(validator_score, (int, float)):
            total_validator_score += float(validator_score)
            validator_score_count += 1

    total_products = len(reports)

    return {
        "total_products": total_products,
        "coverage_status_counts": dict(status_counter),
        "validator_status_counts": dict(validator_status_counter),
        "average_coverage": round(total_coverage / total_products, 2) if total_products else 0,
        "average_validator_score": (
            round(total_validator_score / validator_score_count, 2)
            if validator_score_count
            else None
        ),
    }


def summarize_missing_fields(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter()

    for report in reports:
        for field in report.get("missing_fields", []):
            counter[field] += 1

    return [
        {
            "field": field,
            "missing_in_products": count,
        }
        for field, count in counter.most_common()
    ]


def summarize_section_coverage(reports: list[dict[str, Any]]) -> dict[str, Any]:
    section_totals = defaultdict(float)
    section_counts = defaultdict(int)

    for report in reports:
        sections = report.get("sections", {})

        for section_name, section_data in sections.items():
            coverage = section_data.get("coverage")

            if isinstance(coverage, (int, float)):
                section_totals[section_name] += float(coverage)
                section_counts[section_name] += 1

    summary = {}

    for section_name in sorted(section_totals):
        summary[section_name] = {
            "average_coverage": round(
                section_totals[section_name] / section_counts[section_name],
                2,
            ),
            "products_counted": section_counts[section_name],
        }

    return summary


def products_requiring_attention(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    attention = []

    for report in reports:
        quality = report.get("quality", {})

        coverage = float(report.get("overall_coverage", 0))
        coverage_status = report.get("coverage_status")
        validator_status = quality.get("validator_status")
        error_count = quality.get("error_count", 0)
        warning_count = quality.get("warning_count", 0)

        requires_attention = (
            coverage_status in ["PARTIAL", "INCOMPLETE"]
            or validator_status in ["FAIL", "REVIEW_REQUIRED"]
            or error_count > 0
            or coverage < 85
        )

        if requires_attention:
            attention.append(
                {
                    "entity_id": report.get("entity_id"),
                    "overall_coverage": coverage,
                    "coverage_status": coverage_status,
                    "validator_status": validator_status,
                    "validator_score": quality.get("validator_score"),
                    "error_count": error_count,
                    "warning_count": warning_count,
                    "missing_fields": report.get("missing_fields", []),
                }
            )

    attention.sort(
        key=lambda x: (
            x.get("error_count", 0) == 0,
            x.get("overall_coverage", 0),
        )
    )

    return attention


def build_recommendations(
    portfolio_summary: dict[str, Any],
    top_missing_fields: list[dict[str, Any]],
    attention: list[dict[str, Any]],
) -> list[str]:
    recommendations = []

    if portfolio_summary["total_products"] == 0:
        recommendations.append("No product coverage reports found. Run product-level coverage audits first.")
        return recommendations

    if attention:
        recommendations.append("Review products requiring attention before using them in advisor-facing workflows.")

    if top_missing_fields:
        top = top_missing_fields[0]
        recommendations.append(
            f"Prioritize extractor improvement for '{top['field']}', missing in {top['missing_in_products']} product(s)."
        )

    avg_coverage = portfolio_summary.get("average_coverage", 0)
    if avg_coverage < 80:
        recommendations.append("Portfolio coverage is below target. Improve extraction coverage before scaling further.")
    elif avg_coverage >= 90:
        recommendations.append("Portfolio coverage is strong. Next focus should be quality hardening and comparison intelligence.")

    return recommendations


def audit_portfolio(domain: str) -> dict[str, Any]:
    paths = find_coverage_reports(domain)

    reports = []

    for path in paths:
        report = load_json(path)

        if not report.get("entity_id"):
            report["entity_id"] = entity_from_report_path(path, domain)

        report["_source_file"] = str(path.relative_to(BASE_DIR)).replace("\\", "/")
        reports.append(report)

    portfolio_summary = summarize_products(reports)
    top_missing_fields = summarize_missing_fields(reports)
    section_summary = summarize_section_coverage(reports)
    attention = products_requiring_attention(reports)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "portfolio_audit_version": PORTFOLIO_AUDIT_VERSION,
        "domain": domain,
        "portfolio_summary": portfolio_summary,
        "section_coverage_summary": section_summary,
        "top_missing_fields": top_missing_fields,
        "products_requiring_attention": attention,
        "products": [
            {
                "entity_id": r.get("entity_id"),
                "overall_coverage": r.get("overall_coverage"),
                "coverage_status": r.get("coverage_status"),
                "validator_status": r.get("quality", {}).get("validator_status"),
                "validator_score": r.get("quality", {}).get("validator_score"),
                "missing_fields_count": len(r.get("missing_fields", [])),
                "source_file": r.get("_source_file"),
            }
            for r in reports
        ],
        "recommendations": build_recommendations(
            portfolio_summary,
            top_missing_fields,
            attention,
        ),
    }

    out_dir = BASE_DIR / "knowledge" / domain / "portfolio"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "portfolio_coverage_report.json"
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report["output_file"] = str(out_path.relative_to(BASE_DIR)).replace("\\", "/")

    return report


def print_report(report: dict[str, Any]):
    summary = report["portfolio_summary"]

    print("=" * 70)
    print("PORTFOLIO COVERAGE AUDIT")
    print("=" * 70)
    print(f"Domain              : {report['domain']}")
    print(f"Version             : {report['portfolio_audit_version']}")
    print(f"Products            : {summary['total_products']}")
    print(f"Average Coverage    : {summary['average_coverage']}%")
    print(f"Avg Validator Score : {summary['average_validator_score']}")
    print(f"Output              : {report['output_file']}")
    print("-" * 70)

    print("Coverage Status Counts:")
    for status, count in summary["coverage_status_counts"].items():
        print(f"  {status}: {count}")

    print("-" * 70)

    print("Validator Status Counts:")
    for status, count in summary["validator_status_counts"].items():
        print(f"  {status}: {count}")

    print("-" * 70)

    print("Top Missing Fields:")
    for item in report["top_missing_fields"][:10]:
        print(f"  {item['field']}: {item['missing_in_products']}")

    print("-" * 70)

    print("Products Requiring Attention:")
    for item in report["products_requiring_attention"][:20]:
        print(
            f"  {item['entity_id']} | "
            f"coverage={item['overall_coverage']} | "
            f"coverage_status={item['coverage_status']} | "
            f"validator={item['validator_status']}"
        )

    print("-" * 70)

    print("Recommendations:")
    for rec in report["recommendations"]:
        print(f"  - {rec}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default="health")
    args = parser.parse_args()

    report = audit_portfolio(args.domain)
    print_report(report)


if __name__ == "__main__":
    main()