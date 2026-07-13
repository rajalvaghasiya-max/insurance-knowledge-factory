"""CLI for read-only generic copay shadow-mode integration."""
from __future__ import annotations

import argparse

from knowledge_domains.health.routing.copay_conditional_rule_shadow import (
    CopayConditionalRuleShadowRunner,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build non-authoritative generic copay shadow artifacts.")
    parser.add_argument("--triage-path", required=True, help="Persisted legacy copay evidence-triage JSON.")
    parser.add_argument("--factory-dir", required=True, help="Registry-backed product factory directory.")
    args = parser.parse_args()

    result = CopayConditionalRuleShadowRunner().run_from_triage_file(
        triage_path=args.triage_path,
        factory_dir=args.factory_dir,
    )
    print("=" * 70)
    print("COPAY CONDITIONAL-RULE SHADOW MODE")
    print("=" * 70)
    print(f"Parity passed          : {result.parity_passed}")
    print(f"Assembled rules        : {result.rule_count}")
    print(f"Unassembled fragments : {result.unassembled_fragment_count}")
    print(f"Shadow rules           : {result.conditional_rules_path}")
    print(f"Parity report          : {result.parity_report_path}")
    return 0 if result.parity_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
