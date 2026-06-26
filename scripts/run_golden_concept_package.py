from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_factory.golden_concept_package.golden_concept_package_assembler import GoldenConceptPackageAssembler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Golden Concept Package Assembly")
    parser.add_argument("--concept", default="copay")
    parser.add_argument("--concept-name", default=None)
    args = parser.parse_args()

    outputs = GoldenConceptPackageAssembler(repo_root=Path.cwd()).run(args.concept, args.concept_name)
    package = json.loads(Path(outputs["package"]).read_text(encoding="utf-8"))
    cert = package["package_certification"]
    coverage = package["coverage_analysis"]

    print("=" * 70)
    print("GOLDEN CONCEPT PACKAGE ASSEMBLY")
    print("=" * 70)
    print(f"Concept              : {package['concept_id']}")
    print(f"Package              : {outputs['package']}")
    print(f"Certification Status : {cert['status']}")
    print(f"Certification Score  : {cert['score']}")
    print(f"Maturity             : {package['maturity_level']}")
    print("-" * 70)
    for key, value in coverage.items():
        if key != "overall":
            print(f"{key:28}: {value}")
    print(f"{'overall':28}: {coverage['overall']}")
    print("-" * 70)
    gaps = package["gap_analysis"]
    print(f"Missing assets       : {gaps.get('missing_assets', [])}")
    print(f"Next actions         : {gaps.get('next_best_actions', [])}")
    print("=" * 70)


if __name__ == "__main__":
    main()
