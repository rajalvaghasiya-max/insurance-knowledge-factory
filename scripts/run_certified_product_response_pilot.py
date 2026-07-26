"""Run a governed certified-product response pilot.

The initial implementation supports the Star Comprehensive conditional
co-payment pilot through a generic command name, preserving the repository rule
that product-specific runner scripts must not proliferate.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from insurance_intelligence.orchestration.star_comprehensive_pilot import (
    PRODUCT_REFERENCE,
    TOPIC,
    run_star_comprehensive_copay_pilot,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--product-reference", default=PRODUCT_REFERENCE)
    parser.add_argument("--topic", default=TOPIC)
    parser.add_argument("--question", required=True)
    parser.add_argument("--repository-root", default="knowledge/factory/registry_backed")
    parser.add_argument("--knowledge-snapshot-id", required=True)
    parser.add_argument("--trigger-status", choices=("CONFIRMED", "NOT_TRIGGERED", "UNRESOLVED"))
    args = parser.parse_args()
    if args.product_reference != PRODUCT_REFERENCE or args.topic != TOPIC:
        parser.error("the current pilot supports only Star Comprehensive conditional co-payment")
    context = {"trigger_status": args.trigger_status} if args.trigger_status else {}
    result = run_star_comprehensive_copay_pilot(
        request_id=args.request_id,
        question=args.question,
        repository_root=args.repository_root,
        knowledge_snapshot_id=args.knowledge_snapshot_id,
        customer_context=context,
    )
    payload = {
        "pilot_id": result.pilot_id,
        "request_id": result.request_id,
        "product_reference": result.product_reference,
        "topic": result.topic,
        "knowledge_snapshot_id": result.knowledge_snapshot_id,
        "decision": result.decision.decision,
        "response_status": result.response.response_status,
        "released_response_id": result.released_response_id,
        "used_llm": result.used_llm,
        "direct_answer": result.response.direct_answer,
        "sections": [asdict(item) for item in result.response.sections],
        "evidence_references": [asdict(item) for item in result.response.evidence_references],
        "limitations": result.limitations,
        "clarification_questions": result.response.clarification_questions,
    }
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
