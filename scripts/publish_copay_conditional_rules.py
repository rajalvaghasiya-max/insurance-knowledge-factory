"""CLI for parity-gated publication of authoritative copay conditional rules."""
from __future__ import annotations

import argparse

from knowledge_domains.health.conditional_rule_publisher import HealthConditionalRulePublisher


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish certified authoritative copay conditional rules.")
    parser.add_argument("--shadow-rules-path", required=True)
    parser.add_argument("--parity-report-path", required=True)
    parser.add_argument("--legacy-triage-path", required=True)
    parser.add_argument("--factory-dir", required=True)
    parser.add_argument("--expected-rule-count", required=True, type=int)
    args = parser.parse_args()

    result = HealthConditionalRulePublisher().publish_from_shadow(
        shadow_rules_path=args.shadow_rules_path,
        parity_report_path=args.parity_report_path,
        legacy_triage_path=args.legacy_triage_path,
        factory_dir=args.factory_dir,
        expected_rule_count=args.expected_rule_count,
    )
    print("=" * 70)
    print("COPAY CONDITIONAL-RULE AUTHORITY PUBLICATION")
    print("=" * 70)
    print("Publication passed     : True")
    print(f"Authoritative rules   : {len(result.rule_ids)}")
    print(f"Rules artifact        : {result.authoritative_rules_path}")
    print(f"Publication receipt   : {result.publication_receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
