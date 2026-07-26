from __future__ import annotations

from knowledge_domains.health.mental_model_transformation.mental_model_transformation_line import (
    MentalModelTransformationLine,
)


def main() -> None:
    line = MentalModelTransformationLine()
    summary = line.run_from_reports_dir("knowledge/factory/distillation/reports")

    print("\n" + "=" * 70)
    print("MENTAL MODEL TRANSFORMATION LINE")
    print("=" * 70)
    print(f"Reports considered : {summary['reports_considered']}")
    print(f"Assets manufactured: {summary['assets_manufactured']}")
    print(f"Summary           : {summary['summary_path']}")
    print("-" * 70)
    for output in summary["outputs"]:
        print(output["asset"])


if __name__ == "__main__":
    main()
