from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from factory_core.governance.governed_readiness import (
    ASSESSMENT_VERSION,
    assessment_from_mapping,
)


COVERAGE_VERSION = "0.2"
GOVERNED_READINESS_VERSION = ASSESSMENT_VERSION


EXPECTED_FIELDS = {
    "metadata": [
        "product_name",
        "uin",
    ],
    "eligibility": [
        "adult_entry_age",
        "dependent_child_entry_age",
    ],
    "sum_insured_options": [
        "values",
    ],
    "waiting_periods": [
        "pre_existing_disease_waiting_period",
        "specified_disease_waiting_period",
        "initial_waiting_period",
        "delivery_newborn_waiting_period",
        "bariatric_surgery_waiting_period",
    ],
    "product_facts": [
        "copay",
        "room_rent_limit",
    ],
    "core_benefits": [
        "in_patient_treatment",
        "day_care_treatment",
        "ayush_treatment",
        "pre_hospitalization",
        "post_hospitalization",
        "domiciliary_hospitalization",
        "home_care_treatment",
        "road_ambulance",
        "air_ambulance",
        "organ_donor_expenses",
        "automatic_restoration",
        "delivery_newborn_cover",
        "bariatric_surgery",
        "hospital_cash",
        "wellness_program",
    ],
    "discounts": [
        "long_term_discount",
        "wellness_discount",
        "online_discount",
    ],
    "optional_covers": [
        "buy_back_ped_waiting_period",
    ],
}


SECTION_WEIGHTS = {
    "metadata": 15,
    "eligibility": 8,
    "sum_insured_options": 8,
    "waiting_periods": 20,
    "product_facts": 15,
    "core_benefits": 22,
    "discounts": 6,
    "optional_covers": 6,
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_present(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        if not value.strip():
            return False
        if "XXXXX" in value.upper():
            return False
        return True

    if isinstance(value, list):
        return len(value) > 0

    if isinstance(value, dict):
        if not value:
            return False

        if value.get("validated") is False:
            return False

        if "value" in value:
            return is_present(value.get("value"))

        return True

    return True


def score_section(section_name: str, data: dict[str, Any]) -> dict[str, Any]:
    expected = EXPECTED_FIELDS[section_name]
    section_data = data.get(section_name, {})

    present = []
    missing = []

    for field in expected:
        value = section_data.get(field) if isinstance(section_data, dict) else None

        if is_present(value):
            present.append(field)
        else:
            missing.append(field)

    coverage = round((len(present) / len(expected)) * 100, 2) if expected else 100

    return {
        "coverage": coverage,
        "present_count": len(present),
        "expected_count": len(expected),
        "present_fields": present,
        "missing_fields": missing,
    }


def calculate_weighted_score(sections: dict[str, Any]) -> float:
    total_weight = 0
    weighted_score = 0.0

    for section_name, section_report in sections.items():
        weight = SECTION_WEIGHTS.get(section_name, 0)
        total_weight += weight
        weighted_score += section_report["coverage"] * weight

    if total_weight == 0:
        return 0.0

    return round(weighted_score / total_weight, 2)


def determine_status(score: float) -> str:
    if score >= 90:
        return "READY"
    if score >= 75:
        return "USABLE_WITH_REVIEW"
    if score >= 50:
        return "PARTIAL"
    return "INCOMPLETE"


def load_validation_report(entity_id: str) -> dict[str, Any] | None:
    insurer_slug, product_slug = entity_id.split(":")

    path = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "validation"
        / "product_intelligence_validation_report.json"
    )

    if path.exists():
        return load_json(path)

    return None


def load_governed_readiness(entity_id: str) -> dict[str, Any]:
    """Load and validate a separately materialized governed-readiness assessment.

    Legacy product-intelligence presence MUST NOT be used to synthesize governed
    readiness. Absence therefore fails closed as NOT_ASSESSED. When an assessment
    exists, its summary status is derived by the generic governed-readiness
    contract rather than trusted from JSON.
    """
    insurer_slug, product_slug = entity_id.split(":")
    path = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "governance"
        / "governed_readiness.json"
    )

    if not path.exists():
        return {
            "readiness_version": GOVERNED_READINESS_VERSION,
            "status": "NOT_ASSESSED",
            "assessment_file": None,
            "source_governance": "NOT_ASSESSED",
            "semantic_review": "NOT_ASSESSED",
            "applicability": "NOT_ASSESSED",
            "publication_eligibility": "NOT_ASSESSED",
            "publication_state": "NOT_ASSESSED",
            "unresolved_residue": [],
            "evidence_references": [],
            "note": (
                "No governed-readiness assessment is materialized. Legacy intelligence "
                "coverage must not be interpreted as governed or publication readiness."
            ),
        }

    raw = load_json(path)
    assessment = assessment_from_mapping(raw, expected_entity_id=entity_id)

    return {
        "readiness_version": assessment.assessment_version,
        "status": assessment.status,
        "assessment_file": str(path.relative_to(BASE_DIR)).replace("\\", "/"),
        "source_governance": assessment.source_governance,
        "semantic_review": assessment.semantic_review,
        "applicability": assessment.applicability,
        "publication_eligibility": assessment.publication_eligibility,
        "publication_state": assessment.publication_state,
        "unresolved_residue": list(assessment.unresolved_residue),
        "evidence_references": list(assessment.evidence_references),
        "note": assessment.note,
    }


def audit(entity_id: str) -> dict[str, Any]:
    insurer_slug, product_slug = entity_id.split(":")

    intelligence_path = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "intelligence"
        / "product_intelligence.json"
    )

    if not intelligence_path.exists():
        raise FileNotFoundError(f"Missing product intelligence file: {intelligence_path}")

    intelligence = load_json(intelligence_path)

    sections = {}

    for section_name in EXPECTED_FIELDS:
        sections[section_name] = score_section(section_name, intelligence)

    overall_score = calculate_weighted_score(sections)
    status = determine_status(overall_score)

    all_missing = []
    for section_name, report in sections.items():
        for field in report["missing_fields"]:
            all_missing.append(f"{section_name}.{field}")

    validation_report = load_validation_report(entity_id)

    quality_status = None
    quality_score = None
    quality_errors = 0
    quality_warnings = 0

    if validation_report:
        quality_status = validation_report.get("status")
        quality_score = validation_report.get("score")
        quality_errors = validation_report.get("error_count", 0)
        quality_warnings = validation_report.get("warning_count", 0)

    governed_readiness = load_governed_readiness(entity_id)

    report = {
        "entity_id": entity_id,
        "coverage_version": COVERAGE_VERSION,
        "coverage_semantics": "LEGACY_INTELLIGENCE_FIELD_PRESENCE",
        "coverage_readiness_warning": (
            "overall_coverage and coverage_status measure legacy product-intelligence "
            "field presence only; they do not establish governed currentness, "
            "applicability, publication eligibility, or publication state."
        ),
        "input_file": str(intelligence_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "overall_coverage": overall_score,
        "coverage_status": status,
        "legacy_intelligence_coverage": {
            "overall_coverage": overall_score,
            "coverage_status": status,
            "sections": sections,
            "missing_fields": all_missing,
        },
        "governed_readiness": governed_readiness,
        "sections": sections,
        "missing_fields": all_missing,
        "quality": {
            "validator_status": quality_status,
            "validator_score": quality_score,
            "error_count": quality_errors,
            "warning_count": quality_warnings,
        },
        "recommendations": build_recommendations(
            overall_score,
            all_missing,
            quality_status,
            quality_errors,
            quality_warnings,
            governed_readiness["status"],
        ),
    }

    out_dir = BASE_DIR / "knowledge" / "health" / insurer_slug / product_slug / "coverage"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "product_coverage_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    report["output_file"] = str(out_path.relative_to(BASE_DIR)).replace("\\", "/")

    return report


def build_recommendations(
    overall_score: float,
    missing_fields: list[str],
    quality_status: str | None,
    quality_errors: int,
    quality_warnings: int,
    governed_readiness_status: str = "NOT_ASSESSED",
) -> list[str]:
    recommendations = []

    if quality_errors > 0:
        recommendations.append("Fix validator errors before treating legacy intelligence coverage as complete.")

    if quality_warnings > 0:
        recommendations.append("Review warning-level quality issues in legacy intelligence artifacts.")

    if missing_fields:
        recommendations.append("Improve legacy intelligence extraction coverage for missing fields.")

    if overall_score < 75:
        recommendations.append("Legacy intelligence coverage is incomplete; do not rely on it for comparison workflows.")

    if governed_readiness_status == "NOT_ASSESSED":
        recommendations.append(
            "Governed readiness is not assessed; do not infer current, applicable, publication-eligible, or published status from coverage percentage."
        )
    elif governed_readiness_status not in {"READY_FOR_PUBLICATION_REVIEW", "PUBLISHED"}:
        recommendations.append(
            "Governed readiness requires attention before customer/advisor-facing use of governed product facts."
        )

    return recommendations


def print_report(report: dict[str, Any]):
    print("=" * 70)
    print("PRODUCT COVERAGE AUDIT")
    print("=" * 70)
    print(f"Entity          : {report['entity_id']}")
    print(f"Version         : {report['coverage_version']}")
    print(f"Coverage        : {report['overall_coverage']}%")
    print(f"Coverage Status : {report['coverage_status']} (legacy intelligence)")
    print(f"Governed Ready  : {report['governed_readiness']['status']}")
    print(f"Quality Status  : {report['quality']['validator_status']}")
    print(f"Quality Score   : {report['quality']['validator_score']}")
    print(f"Output          : {report['output_file']}")
    print("-" * 70)

    for section, data in report["sections"].items():
        print(
            f"{section:24} "
            f"{data['coverage']:6.2f}% "
            f"({data['present_count']}/{data['expected_count']})"
        )

    print("-" * 70)

    if report["missing_fields"]:
        print("Missing Fields:")
        for field in report["missing_fields"]:
            print(f"  - {field}")
    else:
        print("Missing Fields: None")

    print("-" * 70)

    if report["recommendations"]:
        print("Recommendations:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-id", required=True)
    args = parser.parse_args()

    report = audit(args.entity_id)
    print_report(report)


if __name__ == "__main__":
    main()
