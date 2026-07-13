from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.customer_document_intelligence.interpretation_packet import (
    InterpretationPacketAssembler,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Assemble a governed customer-document interpretation packet "
            "from a customer fact and Understanding Asset match."
        )
    )
    parser.add_argument("--customer-fact", required=True)
    parser.add_argument("--understanding-match", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    fact_path = Path(args.customer_fact)
    match_path = Path(args.understanding_match)
    output_path = Path(args.output)

    fact = json.loads(fact_path.read_text(encoding="utf-8"))
    match = json.loads(match_path.read_text(encoding="utf-8"))
    packet = InterpretationPacketAssembler().assemble(
        customer_fact=fact,
        understanding_match=match,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )

    print("=" * 72)
    print("CUSTOMER DOCUMENT INTERPRETATION PACKET")
    print("=" * 72)
    print(f"Customer Fact    : {fact_path}")
    print(f"Understanding    : {match_path}")
    print(f"Output           : {output_path}")
    print(f"Packet ID        : {packet['packet_id']}")
    print(f"Answer Readiness : {packet['answer_readiness']}")


if __name__ == "__main__":
    main()
