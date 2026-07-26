"""CLI for read-only Health room-rent shadow assembly."""
from __future__ import annotations

import argparse

from knowledge_domains.health.routing.room_rent_conditional_rule_shadow import (
    RoomRentConditionalRuleShadowRunner,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build non-authoritative room-rent conditional-rule shadow artifacts.")
    parser.add_argument("--triage-path", required=True, help="Persisted reviewed room-rent triage JSON.")
    parser.add_argument("--factory-dir", required=True, help="Registry-backed product factory directory.")
    args = parser.parse_args()
    result = RoomRentConditionalRuleShadowRunner().run_from_triage_file(
        triage_path=args.triage_path,
        factory_dir=args.factory_dir,
    )
    print("=" * 70)
    print("ROOM-RENT CONDITIONAL-RULE SHADOW MODE")
    print("=" * 70)
    print(f"Verification passed    : {result.verification_passed}")
    print(f"Assembled rules        : {result.rule_count}")
    print(f"Unassembled fragments  : {result.unassembled_fragment_count}")
    print(f"Shadow rules           : {result.conditional_rules_path}")
    print(f"Verification report    : {result.verification_report_path}")
    return 0 if result.verification_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
