from __future__ import annotations

import subprocess
import sys


HEALTH_TRUST_PIPELINE_TESTS = [
    "tests/health/test_governed_fact_selection.py",
    "tests/health/test_canonical_fact_materialization.py",
    "tests/health/test_fact_publication_eligibility.py",
    "tests/health/test_publication_review_packet.py",
    "tests/health/test_publication_review_decision_submission.py",
    "tests/health/test_governed_product_knowledge_package.py",
    "tests/health/test_governed_product_knowledge_content_review.py",
    "tests/health/test_governed_reusable_product_knowledge_records.py",
    "tests/health/test_health_trust_pipeline_certification.py",
]


def main() -> int:
    print("=" * 72)
    print("HEALTH TRUST PIPELINE CERTIFICATION")
    print("=" * 72)
    print("Running canonical Health trust pipeline test gate...")
    print()

    command = [sys.executable, "-m", "pytest", "-q", *HEALTH_TRUST_PIPELINE_TESTS]
    result = subprocess.run(command, check=False)

    print()
    if result.returncode == 0:
        print("=" * 72)
        print("HEALTH TRUST PIPELINE CERTIFICATION PASSED")
        print("=" * 72)
    else:
        print("=" * 72)
        print("HEALTH TRUST PIPELINE CERTIFICATION FAILED")
        print("=" * 72)

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
