from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class HealthDomainValidator:
    """
    Health Domain Validator v0.1.2

    Changes over v0.1.1:
        - Added validation_mode:
            fact    -> validate only supplied fact(s), no full product completeness check
            product -> validate supplied facts + required product completeness fields

    Use:
        Extractors should use validation_mode="fact"
        Product knowledge object generator should use validation_mode="product"
    """

    VERSION = "0.1.2"

    REQUIRED_FIELDS = {
        "ped_waiting_period": "critical",
        "room_rent_limit": "important",
        "copay": "important",
        "specific_disease_waiting_period": "important",
        "sub_limit": "optional",
        "restoration_benefit": "optional",
    }

    VALID_UNITS = {
        "ped_waiting_period": {"months", "days", "years"},
        "specific_disease_waiting_period": {"months", "days", "years"},
        "initial_waiting_period": {"months", "days", "years"},
        "copay": {"percent", "%"},
        "room_rent_limit": {"INR", "percent", "room_category", "text", None},
        "sub_limit": {"INR", "percent", "text", None},
    }

    VALIDATION_MODES = {"fact", "product"}

    def utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def validate_facts(
        self,
        *,
        entity_id: str,
        facts: list[dict[str, Any]],
        validation_mode: str = "product",
    ) -> dict[str, Any]:
        if validation_mode not in self.VALIDATION_MODES:
            raise ValueError(
                f"Unsupported validation_mode={validation_mode}. "
                f"Allowed: {sorted(self.VALIDATION_MODES)}"
            )

        report = {
            "validator_name": "health_domain_validator",
            "validator_version": self.VERSION,
            "entity_id": entity_id,
            "validation_mode": validation_mode,
            "validated_at": self.utc_now(),
            "summary": {
                "facts_checked": len(facts),
                "valid": 0,
                "warnings": 0,
                "errors": 0,
                "needs_review": 0,
            },
            "missing_critical_fields": [],
            "missing_important_fields": [],
            "review_recommendation": "not_evaluated",
            "results": [],
        }

        if validation_mode == "product":
            self.add_product_completeness_checks(report, facts)

        for fact in facts:
            result = self.validate_fact(fact)
            report["results"].append(result)

            status = result["status"]

            if status == "valid":
                report["summary"]["valid"] += 1
            elif status == "warning":
                report["summary"]["warnings"] += 1
            elif status == "error":
                report["summary"]["errors"] += 1
            elif status == "needs_review":
                report["summary"]["needs_review"] += 1

        report["review_recommendation"] = self.get_review_recommendation(report)

        return report

    def add_product_completeness_checks(
        self,
        report: dict[str, Any],
        facts: list[dict[str, Any]],
    ) -> None:
        present_fields = {
            fact.get("field")
            for fact in facts
            if fact.get("field")
        }

        missing_critical = []
        missing_important = []

        for field, importance in self.REQUIRED_FIELDS.items():
            if importance == "optional":
                continue

            if field not in present_fields:
                if importance == "critical":
                    missing_critical.append(field)
                elif importance == "important":
                    missing_important.append(field)

        report["missing_critical_fields"] = sorted(missing_critical)
        report["missing_important_fields"] = sorted(missing_important)

    def validate_fact(self, fact: dict[str, Any]) -> dict[str, Any]:
        messages = []

        field = fact.get("field")
        value = fact.get("value")
        unit = fact.get("unit")

        confidence = fact.get("confidence", {})
        confidence_score = confidence.get("score")

        evidence = fact.get("evidence", {})
        source = fact.get("source", {})

        if not field:
            messages.append("Missing field name.")

        if value in [None, ""]:
            messages.append("Missing value.")

        if not evidence.get("text"):
            messages.append("Missing evidence text.")

        if not source.get("source_document"):
            messages.append("Missing source document.")

        if confidence_score is None:
            messages.append("Missing confidence score.")
        elif confidence_score < 0.75:
            messages.append("Low confidence; human review recommended.")

        if field in self.VALID_UNITS:
            valid_units = self.VALID_UNITS[field]

            if unit not in valid_units:
                messages.append(
                    f"Unexpected unit for {field}: {unit}. Expected one of {sorted([str(x) for x in valid_units])}."
                )

        domain_messages = self.apply_health_rules(fact)
        messages.extend(domain_messages)

        status = "valid"

        if any("Missing" in msg for msg in messages):
            status = "error"
        elif any("Low confidence" in msg for msg in messages):
            status = "needs_review"
        elif messages:
            status = "warning"

        return {
            "fact_id": fact.get("fact_id"),
            "field": field,
            "status": status,
            "messages": messages,
            "validated_at": self.utc_now(),
        }

    def get_review_recommendation(self, report: dict[str, Any]) -> str:
        summary = report.get("summary", {})

        if report.get("missing_critical_fields"):
            return "blocked"

        if summary.get("errors", 0) > 0:
            return "blocked"

        if summary.get("needs_review", 0) > 0:
            return "needs_human_review"

        if report.get("missing_important_fields"):
            return "publish_with_warning"

        if summary.get("warnings", 0) > 0:
            return "publish_with_warning"

        return "safe_to_publish"

    def apply_health_rules(self, fact: dict[str, Any]) -> list[str]:
        messages = []

        field = fact.get("field")
        value = fact.get("value")

        if field == "ped_waiting_period":
            months = self.to_months(value, fact.get("unit"))

            if months is None:
                messages.append("PED waiting period could not be normalized to months.")
            elif months < 0:
                messages.append("PED waiting period cannot be negative.")
            elif months > 48:
                messages.append("PED waiting period unusually high; review required.")

        if field == "specific_disease_waiting_period":
            months = self.to_months(value, fact.get("unit"))

            if months is None:
                messages.append("Specific disease waiting period could not be normalized to months.")
            elif months < 0:
                messages.append("Specific disease waiting period cannot be negative.")
            elif months > 48:
                messages.append("Specific disease waiting period unusually high; review required.")

        if field == "copay":
            percentage = self.to_number(value)

            if percentage is None:
                messages.append("Copay value could not be normalized to number.")
            elif percentage < 0 or percentage > 100:
                messages.append("Copay percentage must be between 0 and 100.")

        if field == "room_rent_limit":
            if isinstance(value, str) and len(value.strip()) < 2:
                messages.append("Room rent limit text appears too short.")

        return messages

    def to_number(self, value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            cleaned = (
                value.lower()
                .replace("%", "")
                .replace("percent", "")
                .replace("months", "")
                .replace("month", "")
                .replace("days", "")
                .replace("day", "")
                .replace("years", "")
                .replace("year", "")
                .replace(",", "")
                .strip()
            )

            try:
                return float(cleaned)
            except ValueError:
                return None

        return None

    def to_months(self, value: Any, unit: str | None) -> float | None:
        number = self.to_number(value)

        if number is None:
            return None

        if unit in ["months", None]:
            return number

        if unit == "days":
            return round(number / 30, 2)

        if unit == "years":
            return number * 12

        return number


def main():
    validator = HealthDomainValidator()

    sample_fact = {
        "fact_id": "sample:ped",
        "field": "ped_waiting_period",
        "value": 36,
        "unit": "months",
        "evidence": {
            "text": "Pre-existing diseases will be covered after 36 months.",
            "page": 17,
            "section": "Waiting Periods",
        },
        "source": {
            "source_document": "policy_wording.pdf",
        },
        "confidence": {
            "score": 0.94,
        },
    }

    fact_report = validator.validate_facts(
        entity_id="sample_product",
        facts=[sample_fact],
        validation_mode="fact",
    )

    product_report = validator.validate_facts(
        entity_id="sample_product",
        facts=[sample_fact],
        validation_mode="product",
    )

    print("=" * 70)
    print("HEALTH DOMAIN VALIDATOR SANITY CHECK")
    print("=" * 70)
    print("FACT MODE")
    print(f"Facts checked             : {fact_report['summary']['facts_checked']}")
    print(f"Valid facts               : {fact_report['summary']['valid']}")
    print(f"Validation warnings       : {fact_report['summary']['warnings']}")
    print(f"Validation errors         : {fact_report['summary']['errors']}")
    print(f"Needs human review        : {fact_report['summary']['needs_review']}")
    print(f"Missing critical fields   : {len(fact_report['missing_critical_fields'])}")
    print(f"Missing important fields  : {len(fact_report['missing_important_fields'])}")
    print(f"Review recommendation     : {fact_report['review_recommendation']}")
    print("-" * 70)
    print("PRODUCT MODE")
    print(f"Facts checked             : {product_report['summary']['facts_checked']}")
    print(f"Valid facts               : {product_report['summary']['valid']}")
    print(f"Validation warnings       : {product_report['summary']['warnings']}")
    print(f"Validation errors         : {product_report['summary']['errors']}")
    print(f"Needs human review        : {product_report['summary']['needs_review']}")
    print(f"Missing critical fields   : {len(product_report['missing_critical_fields'])}")
    print(f"Missing important fields  : {len(product_report['missing_important_fields'])}")
    if product_report["missing_important_fields"]:
        print(f"Important missing         : {', '.join(product_report['missing_important_fields'])}")
    print(f"Review recommendation     : {product_report['review_recommendation']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
