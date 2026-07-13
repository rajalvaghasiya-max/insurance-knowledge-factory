from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from knowledge_domains.health.customer_document_intelligence.constrained_llm_verbalizer import (
    ConstrainedLLMVerbalizer,
)
from knowledge_domains.health.customer_document_intelligence.verbalizer_request import (
    VerbalizerRequestAssembler,
)


def _response_file_callable(path: Path):
    def call(_: Mapping[str, Any]) -> str:
        return path.read_text(encoding="utf-8")
    return call


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a constrained verbalizer request and ingest one provider "
            "response as an unvalidated draft. No network provider is called."
        )
    )
    parser.add_argument("--content-bundle", required=True)
    parser.add_argument("--response-file", required=True)
    parser.add_argument("--request-output", required=True)
    parser.add_argument("--draft-output", required=True)
    parser.add_argument("--provider-name", default="offline_response_file")
    parser.add_argument("--model-name", default="unspecified")
    args = parser.parse_args()

    bundle_path = Path(args.content_bundle)
    response_path = Path(args.response_file)
    request_path = Path(args.request_output)
    draft_path = Path(args.draft_output)

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    request = VerbalizerRequestAssembler().assemble(bundle)
    draft = ConstrainedLLMVerbalizer().verbalize(
        request=request,
        llm_callable=_response_file_callable(response_path),
        provider_metadata={
            "provider": args.provider_name,
            "model": args.model_name,
            "transport": "offline_response_file",
        },
    )

    request_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            request,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    draft_path.write_text(
        json.dumps(
            draft,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("=" * 72)
    print("CONSTRAINED LLM VERBALIZER")
    print("=" * 72)
    print(f"Content Bundle  : {bundle_path}")
    print(f"Response File   : {response_path}")
    print(f"Request Output  : {request_path}")
    print(f"Draft Output    : {draft_path}")
    print(f"Request ID      : {request['request_id']}")
    print(f"Draft ID        : {draft['draft_id']}")
    print(f"Word Count      : {draft['word_count']}")
    print(f"Validation      : {draft['validation_state']}")
    print(f"Customer Answer : {draft['customer_answer_state']}")


if __name__ == "__main__":
    main()
