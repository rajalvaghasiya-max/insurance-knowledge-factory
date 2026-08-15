from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


PORTFOLIO_AUDIT_VERSION = "0.2"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_coverage_reports(domain: str) -> list[Path]:
    root = BASE_DIR / "knowledge" / domain

    if not root.exists():
        raise FileNotFoundError(f"Domain folder not found: {root}")

    return sorted(root.rglob("coverage/product_coverage_report.json"))


def entity_from_report_path(path: Path, domain: str) -> str:
    relative = path.relative_to(BASE_DIR / "knowledge" / domain)
    parts = relative.parts

    if len(parts) < 4:
        return "unknown:unknown"

    return f"{parts[0]}:{parts[1]}"


def summarize_products(reports: list[dict[str, Any]]) -> dict[str, Any]:
    status_counter = Counter()
    validator_status_counter = Counter()
    governed_readiness_counter = Counter()

    total_coverage = 0.0
    total_validator_score = 0.0
    validator_score_count = 0

    for report in reports:
        status_counter[report.get("coverage_status", "UNKNOWN")] += 1
        total_coverage += float(report.get("overall_coverage", 0))

        quality = report.get("quality", {})
        validator_status_counter[quality.get("validator_status", "UNKNOWN")] += 1

        governed = report.get("governed_readiness")
        if isinstance(governed, dict):
            governed_status = governed.get("status", "NOT_ASSESSED")
        else:
            governed_status = "NOT_ASSESSED"
        governed_readiness_counter[governed_status] += 1

        validator_score = quality.get("validator_score")
        if isinstance(validator_score, (int, float)):
            total_validator_score += float(validator_score)
            validator_score_count += 1

    total_products = len(reports)

    return {
        "total_products": total_products,
        "legacy_coverage_status_counts": dict(status_counter),
        "coverage_status_counts": dict(status_counter),
        "governed_readiness_status_counts": dict(governed_readiness_counter),
        "validator_status_counts": dict(validator_status_counter),
        "average_legacy_intelligence_coverage": (
            round(total_coverage / total_products, 2) if total_products else 0
        ),
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
        {"field": field, "missing_in_products": count}
        for field, count in counter.most_common()
    ]


def summarize_section_coverage(reports: list[dict[str, Any]]) -> dict[str, Any]:
    section_totals = defaultdict(float)
    section_counts = defaultdict(int)

    for report in reports:
        for section_name, section_data in report.get("sections", {}).items():
            coverage = section_data.get("coverage")
            if isinstance(coverage, (int, float)):
                section_totals[section_name] += float(coverage)
                section_counts[section_name] += 1

    return {
        section_name: {
            "average_coverage": round(
                section_totals[section_name] / section_counts[section_name], 2
            ),
            "products_counted": section_counts[section_name],
        }
        for section_name in sorted(section_totals)
    }


def products_requiring_attention(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    attention = []

    for report in reports:
        quality = report.get("quality", {})
        governed = report.get("governed_readiness")
        governed_status = (
            governed.get("status", "NOT_ASSESSED")
            if isinstance(governed, dict)
            else "NOT_ASSESSED"
        )

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
            or governed_status not in {"READY", "PUBLISHED"}
        )

        if requires_attention:
            attention.append(
                {
                    "entity_id": report.get("entity_id"),
                    "overall_coverage": coverage,
                    "coverage_status": coverage_status,
                    "governed_readiness_status": governed_status,
                    "validator_status": validator_status,
                    "validator_score": quality.get("validator_score"),
                    "error_count": error_count,
                    "warning_count": warning_count,
                    "missing_fields": report.get("missing_fields", []),
                }
            )

    attention.sort(
        key=lambda x: (
            x.get("governed_readiness_status") in {"READY", "PUBLISHED"},
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
        return ["No product coverage reports found. Run product-level coverage audits first."]

    readiness_counts = portfolio_summary.get("governed_readiness_status_counts", {})
    not_assessed = readiness_counts.get("NOT_ASSESSED", 0)
    if not_assessed:
        recommendations.append(
            f"Materialize governed-readiness assessments for {not_assessed} product(s); legacy coverage percentages do not establish current or publication readiness."
        )

    if attention:
        recommendations.append(
            "Review products requiring attention before customer/advisor-facing use of governed product facts."
        )

    if top_missing_fields:
        top = top_missing_fields[0]
        recommendations.append(
            f"Prioritize legacy extractor improvement for '{top['field']}', missing in {top['missing_in_products']} product(s), without treating extraction completeness as governed readiness."
        )

    avg_coverage = portfolio_summary.get("average_legacy_intelligence_coverage", 0)
    if avg_coverage < 80:
        recommendations.append(
            "Legacy intelligence coverage is below target; improve extraction coverage independently of governed-readiness work."
        )

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
        "reporting_semantics": {
            "legacy_intelligence_coverage": (
                "Field-presence/completeness metric from historical product intelligence artifacts."
            ),
            "governed_readiness": (
                "Separate governed/current/applicability/publication-readiness assessment; never inferred from legacy coverage."
            ),
        },
        "portfolio_summary": portfolio_summary,
        "section_coverage_summary": section_summary,
        "top_missing_fields": top_missing_fields,
        "products_requiring_attention": attention,
        "products": [
            {
                "entity_id": r.get("entity_id"),
                "overall_coverage": r.get("overall_coverage"),
                "coverage_status": r.get("coverage_status"),
                "governed_readiness_status": (
                    r.get("governed_readiness", {}).get("status", "NOT_ASSESSED")
                    if isinstance(r.get("governed_readiness"), dict)
                    else "NOT_ASSESSED"
                ),
                "validator_status": r.get("quality", {}).get("validator_status"),
                "validator_score": r.get("quality", {}).get("validator_score"),
                "missing_fields_count": len(r.get("missing_fields", [])),
                "source_file": r.get("_source_file"),
            }
            for r in reports
        ],
        "recommendations": build_recommendations(
            portfolio_summary, top_missing_fields, attention
        ),
    }

    out_dir = BASE_DIR / "knowledge" / domain / "portfolio"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "portfolio_coverage_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report["output_file"] = str(out_path.relative_to(BASE_DIR)).replace("\\", "/")
    return report


def print_report(report: dict[str, Any]):
    summary = report["portfolio_summary"]

    print("=" * 70)
    print("PORTFOLIO COVERAGE AUDIT")
    print("=" * 70)
    print(f"Domain                 : {report['domain']}")
    print(f"Version                : {report['portfolio_audit_version']}")
    print(f"Products               : {summary['total_products']}")
    print(f"Avg Legacy Coverage    : {summary['average_legacy_intelligence_coverage']}%")
    print(f"Avg Validator Score    : {summary['average_validator_score']}")
    print(f"Output                 : {report['output_file']}")
    print("-" * 70)

    print("Legacy Coverage Status Counts:")
    for status, count in summary["legacy_coverage_status_counts"].items():
        print(f"  {status}: {count}")

    print("Governed Readiness Status Counts:")
    for status, count in summary["governed_readiness_status_counts"].items():
        print(f"  {status}: {count}")

    print("-" * 70)

    print("Products Requiring Attention:")
    for item in report["products_requiring_attention"][:20]:
        print(
            f"  {item['entity_id']} | legacy_coverage={item['overall_coverage']} | "
            f"legacy_status={item['coverage_status']} | governed={item['governed_readiness_status']} | "
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
