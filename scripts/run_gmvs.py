from __future__ import annotations

import argparse
from pathlib import Path

from knowledge_factory.gmvs.gmvs_report_builder import GMVSReportBuilder
from knowledge_factory.gmvs.gmvs_report_writer import GMVSReportWriter


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Golden Manufacturing Validation System (GMVS)."
    )
    parser.add_argument(
        "--concept",
        required=True,
        help="Concept identifier, for example: copay",
    )
    parser.add_argument(
        "--concept-name",
        default=None,
        help="Optional display name, for example: Copay",
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]

    builder = GMVSReportBuilder(repo_root)
    report = builder.build(
        concept_id=args.concept,
        concept_name=args.concept_name,
    )

    writer = GMVSReportWriter(repo_root)
    json_path, summary_path = writer.write(report)

    print()
    print("=" * 70)
    print("GMVS — GOLDEN MANUFACTURING VALIDATION SYSTEM")
    print("=" * 70)
    print(f"Concept             : {report.concept_name} ({report.concept_id})")
    print(f"Certification       : {report.certification_status}")
    print(f"Factory Stability   : {report.scorecard.factory_stability_score}")
    print(f"Factory Maturity    : {report.scorecard.factory_maturity}")
    print(f"Overall Rating      : {report.scorecard.overall_rating}")
    print(f"JSON Report         : {json_path}")
    print(f"Summary Report      : {summary_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()