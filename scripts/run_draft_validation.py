from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.customer_document_intelligence.draft_validation import (
    DraftValidationEngine,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-bundle", required=True)
    parser.add_argument("--verbalizer-request", required=True)
    parser.add_argument("--verbalized-draft", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    bundle = json.loads(Path(args.content_bundle).read_text(encoding="utf-8"))
    request = json.loads(Path(args.verbalizer_request).read_text(encoding="utf-8"))
    draft = json.loads(Path(args.verbalized_draft).read_text(encoding="utf-8"))

    result = DraftValidationEngine().validate_draft(
        bundle=bundle, request=request, draft=draft
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )

    print("=" * 72)
    print("LLM DRAFT VALIDATION AND APPROVAL GATE")
    print("=" * 72)
    print(f"Output           : {output}")
    print(f"Validation ID    : {result['validation_id']}")
    print(f"Validation State : {result['validation_state']}")
    print(f"Findings         : {result['finding_count']}")
    print(f"Customer Answer  : {result['customer_answer_state']}")
    print(f"Publication      : {result['publication_state']}")


if __name__ == "__main__":
    main()
