"""Run a governed full knowledge-to-explanation certification pilot."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from insurance_intelligence.orchestration.full_cycle_certification import (
    run_full_knowledge_to_explanation_certification,
)
from insurance_intelligence.orchestration.star_comprehensive_pilot import (
    PRODUCT_REFERENCE,
    TOPIC,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-request-id", required=True)
    parser.add_argument("--response-request-id", required=True)
    parser.add_argument("--product-reference", default=PRODUCT_REFERENCE)
    parser.add_argument("--topic", default=TOPIC)
    parser.add_argument("--question", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--trigger-status", choices=("CONFIRMED", "NOT_TRIGGERED", "UNRESOLVED"))
    args = parser.parse_args()
    if args.product_reference != PRODUCT_REFERENCE or args.topic != TOPIC:
        parser.error("the current certification pilot supports only Star Comprehensive conditional co-payment")
    context = {"trigger_status": args.trigger_status} if args.trigger_status else {}
    result = run_full_knowledge_to_explanation_certification(
        repository_root=Path(args.repository_root),
        build_request_id=args.build_request_id,
        response_request_id=args.response_request_id,
        question=args.question,
        customer_context=context,
    )
    payload = {
        "certification_id": result.certification_id,
        "status": result.status,
        "product_reference": result.product_reference,
        "topic": result.topic,
        "knowledge_snapshot_id": result.knowledge_snapshot_id,
        "build_id": result.build.build_id,
        "build_receipts": [asdict(item) for item in result.build.receipts],
        "publication_ids": result.build.publication_ids,
        "response_pilot_id": result.response.pilot_id,
        "decision": result.response.decision.decision,
        "response_status": result.response.response.response_status,
        "released_response_id": result.released_response_id,
        "used_llm": result.response.used_llm,
        "direct_answer": result.response.response.direct_answer,
        "sections": [asdict(item) for item in result.response.response.sections],
        "evidence_references": [asdict(item) for item in result.response.response.evidence_references],
        "limitations": result.limitations,
        "clarification_questions": result.response.response.clarification_questions,
    }
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
