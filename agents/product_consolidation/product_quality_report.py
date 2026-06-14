import json
from pathlib import Path
from datetime import datetime, timezone

from config.settings import BASE_DIR
from storage.registry_store import load_json, save_json


class ProductQualityReport:
    """
    Product Master Quality Report v0.1

    Reads canonical product master JSON files and creates:
    - reports/product_quality_report.json
    - reports/product_quality_report.md
    """

    VERSION = "0.1.1"

    def __init__(self):
        self.product_master_dir = (
            BASE_DIR / "knowledge_domains" / "product" / "product_master"
        )
        self.reports_dir = BASE_DIR / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def run(self) -> dict:
        products = self.load_product_master_files()

        report_items = []
        summary = {
            "products": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            "missing_uin": 0,
            "missing_exclusions": 0,
            "missing_waiting_periods": 0,
            "missing_financial_values": 0,
            "needs_pdf_enrichment": 0,
            "review_generic_page": 0,
        }

        for product in products:
            item = self.evaluate_product(product)
            report_items.append(item)

            summary["products"] += 1
            summary[f"{item['grade']}_confidence"] += 1

            if item["checks"]["missing_uin"]:
                summary["missing_uin"] += 1

            if item["checks"]["missing_exclusions"]:
                summary["missing_exclusions"] += 1

            if item["checks"]["missing_waiting_periods"]:
                summary["missing_waiting_periods"] += 1

            if item["checks"]["missing_financial_values"]:
                summary["missing_financial_values"] += 1

            if item["recommendation"] == "NEEDS_PDF_ENRICHMENT":
                summary["needs_pdf_enrichment"] += 1

            if item["recommendation"] == "REVIEW_GENERIC_PAGE":
                summary["review_generic_page"] += 1

        report = {
            "generated_at": self.utc_now_iso(),
            "agent": "product_quality_report",
            "agent_version": self.VERSION,
            "source_dir": str(self.product_master_dir),
            "summary": summary,
            "products": report_items,
        }

        json_path = self.reports_dir / "product_quality_report.json"
        md_path = self.reports_dir / "product_quality_report.md"

        save_json(json_path, report)
        self.write_markdown_report(md_path, report)

        return {
            "status": "completed",
            "products_scanned": summary["products"],
            "high_confidence": summary["high_confidence"],
            "medium_confidence": summary["medium_confidence"],
            "low_confidence": summary["low_confidence"],
            "missing_uin": summary["missing_uin"],
            "missing_exclusions": summary["missing_exclusions"],
            "missing_waiting_periods": summary["missing_waiting_periods"],
            "missing_financial_values": summary["missing_financial_values"],
            "needs_pdf_enrichment": summary["needs_pdf_enrichment"],
            "review_generic_page": summary["review_generic_page"],
            "json_report": str(json_path),
            "markdown_report": str(md_path),
        }

    def load_product_master_files(self) -> list[dict]:
        products = []

        if not self.product_master_dir.exists():
            return products

        for file_path in sorted(self.product_master_dir.glob("*.json")):
            if file_path.name.startswith("_"):
                continue

            product = load_json(file_path, default={})

            if product:
                products.append(product)

        return products

    def evaluate_product(self, product: dict) -> dict:
        product_id = product.get("product_id", "")
        product_name = product.get("product_name", "")
        insurer_id = product.get("insurer_id", "")
        product_key = product.get("product_key", "")

        uins = product.get("uins", [])
        benefits = product.get("benefits", [])
        exclusions = product.get("exclusions", [])
        waiting_periods = product.get("waiting_periods", [])
        source_signal_files = product.get("source_signal_files", [])
        financial_values_count = self.count_financial_values(product)

        removed_noise_items = (
            product.get("quality", {}).get("removed_noise_items", 0)
        )

        checks = {
            "missing_uin": len(uins) == 0,
            "few_benefits": len(benefits) < 5,
            "too_many_benefits": len(benefits) > 50,
            "missing_exclusions": len(exclusions) == 0,
            "missing_waiting_periods": len(waiting_periods) == 0,
            "missing_financial_values": financial_values_count == 0,
            "single_source": len(source_signal_files) <= 1,
            "no_noise_removed": removed_noise_items == 0,
        }

        score = self.calculate_score(
            checks=checks,
            benefits_count=len(benefits),
            exclusions_count=len(exclusions),
            waiting_period_count=len(waiting_periods),
            financial_values_count=financial_values_count,
        )

        grade = self.grade_score(score)

        recommendation = self.recommend_action(
            checks=checks,
            grade=grade,
            benefits_count=len(benefits),
        )

        return {
            "product_id": product_id,
            "product_key": product_key,
            "insurer_id": insurer_id,
            "product_name": product_name,
            "confidence_score": score,
            "grade": grade,
            "counts": {
                "uins": len(uins),
                "benefits": len(benefits),
                "exclusions": len(exclusions),
                "waiting_periods": len(waiting_periods),
                "financial_values": financial_values_count,
                "sources": len(source_signal_files),
                "removed_noise_items": removed_noise_items,
            },
            "checks": checks,
            "recommendation": recommendation,
        }

    def count_financial_values(self, product: dict) -> int:
        financial_signals = product.get("financial_signals", {})

        total = 0

        for value in financial_signals.values():
            if isinstance(value, list):
                total += len(value)

        return total

    def calculate_score(
        self,
        checks: dict,
        benefits_count: int,
        exclusions_count: int,
        waiting_period_count: int,
        financial_values_count: int,
    ) -> int:
        score = 100

        if checks["missing_uin"]:
            score -= 15

        if checks["few_benefits"]:
            score -= 10

        if checks["too_many_benefits"]:
            score -= 10

        if checks["missing_exclusions"]:
            score -= 15

        if checks["missing_waiting_periods"]:
            score -= 10

        if checks["missing_financial_values"]:
            score -= 10

        if checks["single_source"]:
            score -= 10

        if checks["no_noise_removed"]:
            score -= 5

        return max(0, min(100, score))

    def grade_score(self, score: int) -> str:
        if score >= 85:
            return "high"

        if score >= 70:
            return "medium"

        return "low"

    def recommend_action(
        self,
        checks: dict,
        grade: str,
        benefits_count: int,
    ) -> str:
        """
        Recommendation priority v0.1.1

        Practical rule:
        - If UIN is missing and we only have one source, the real fix is PDF enrichment.
        - UIN is usually found in brochure / policy wording / sales literature PDFs.
        """

        if checks["too_many_benefits"]:
            return "REVIEW_GENERIC_PAGE"

        if checks["missing_exclusions"] or checks["missing_waiting_periods"]:
            return "NEEDS_PDF_ENRICHMENT"

        if checks["missing_uin"] and checks["single_source"]:
            return "NEEDS_PDF_ENRICHMENT"

        if checks["missing_uin"]:
            return "NEEDS_UIN_EXTRACTION"

        if checks["missing_financial_values"]:
            return "NEEDS_FINANCIAL_ENRICHMENT"

        if grade == "low":
            return "MANUAL_REVIEW"

        return "READY"

    def write_markdown_report(self, path: Path, report: dict) -> None:
        summary = report["summary"]

        lines = []
        lines.append("# Product Master Quality Report")
        lines.append("")
        lines.append(f"Generated: {report['generated_at']}")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Products scanned: {summary['products']}")
        lines.append(f"- High confidence: {summary['high_confidence']}")
        lines.append(f"- Medium confidence: {summary['medium_confidence']}")
        lines.append(f"- Low confidence: {summary['low_confidence']}")
        lines.append(f"- Missing UIN: {summary['missing_uin']}")
        lines.append(f"- Missing exclusions: {summary['missing_exclusions']}")
        lines.append(f"- Missing waiting periods: {summary['missing_waiting_periods']}")
        lines.append(f"- Missing financial values: {summary['missing_financial_values']}")
        lines.append(f"- Needs PDF enrichment: {summary['needs_pdf_enrichment']}")
        lines.append(f"- Review generic page: {summary['review_generic_page']}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for item in report["products"]:
            counts = item["counts"]
            checks = item["checks"]

            lines.append(f"## {item['product_name']}")
            lines.append("")
            lines.append(f"- Product ID: `{item['product_id']}`")
            lines.append(f"- Insurer: `{item['insurer_id']}`")
            lines.append(f"- Confidence: {item['confidence_score']} ({item['grade'].upper()})")
            lines.append(f"- Recommendation: **{item['recommendation']}**")
            lines.append("")
            lines.append("### Counts")
            lines.append("")
            lines.append(f"- UINs: {counts['uins']}")
            lines.append(f"- Benefits: {counts['benefits']}")
            lines.append(f"- Exclusions: {counts['exclusions']}")
            lines.append(f"- Waiting periods: {counts['waiting_periods']}")
            lines.append(f"- Financial values: {counts['financial_values']}")
            lines.append(f"- Source files: {counts['sources']}")
            lines.append(f"- Removed noise items: {counts['removed_noise_items']}")
            lines.append("")
            lines.append("### Issues")
            lines.append("")

            issue_lines = self.issue_lines(checks)

            if issue_lines:
                lines.extend(issue_lines)
            else:
                lines.append("- No major issues detected.")

            lines.append("")
            lines.append("---")
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")

    def issue_lines(self, checks: dict) -> list[str]:
        mapping = {
            "missing_uin": "Missing UIN",
            "few_benefits": "Very few benefits extracted",
            "too_many_benefits": "Too many benefits; possible generic page contamination",
            "missing_exclusions": "Missing exclusions",
            "missing_waiting_periods": "Missing waiting periods",
            "missing_financial_values": "Missing financial values",
            "single_source": "Only one source file available; needs brochure / policy wording enrichment",
            "no_noise_removed": "No noise removed; review if cleanup rules were triggered correctly",
        }

        lines = []

        for key, label in mapping.items():
            if checks.get(key):
                lines.append(f"- ⚠ {label}")

        return lines


def main():
    report_agent = ProductQualityReport()
    result = report_agent.run()

    print()
    print("=" * 70)
    print("PRODUCT MASTER QUALITY REPORT")
    print("=" * 70)

    print(f"Products scanned          : {result['products_scanned']}")
    print(f"High confidence           : {result['high_confidence']}")
    print(f"Medium confidence         : {result['medium_confidence']}")
    print(f"Low confidence            : {result['low_confidence']}")
    print(f"Missing UIN               : {result['missing_uin']}")
    print(f"Missing exclusions        : {result['missing_exclusions']}")
    print(f"Missing waiting periods   : {result['missing_waiting_periods']}")
    print(f"Missing financial values  : {result['missing_financial_values']}")
    print(f"Needs PDF enrichment      : {result['needs_pdf_enrichment']}")
    print(f"Review generic page       : {result['review_generic_page']}")

    print()
    print("Saved:")
    print(result["json_report"])
    print(result["markdown_report"])
    print("=" * 70)


if __name__ == "__main__":
    main()
