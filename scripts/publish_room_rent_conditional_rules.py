"""CLI for controlled publication of verified room-rent conditional rules."""
from __future__ import annotations

import argparse

from knowledge_domains.health.room_rent_conditional_rule_publisher import (
    RoomRentConditionalRulePublisher,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish verified room-rent conditional rules.")
    parser.add_argument("--shadow-rules-path", required=True)
    parser.add_argument("--verification-report-path", required=True)
    parser.add_argument("--legacy-triage-path", required=True)
    parser.add_argument("--factory-dir", required=True)
    args = parser.parse_args()
    result = RoomRentConditionalRulePublisher().publish_from_shadow(
        shadow_rules_path=args.shadow_rules_path,
        verification_report_path=args.verification_report_path,
        legacy_triage_path=args.legacy_triage_path,
        factory_dir=args.factory_dir,
    )
    print("=" * 70)
    print("ROOM-RENT CONDITIONAL-RULE PUBLICATION")
    print("=" * 70)
    print("Publication passed     : True")
    print(f"Authoritative rules    : {len(result.rule_ids)}")
    print(f"Rules artifact         : {result.authoritative_rules_path}")
    print(f"Publication receipt    : {result.publication_receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
