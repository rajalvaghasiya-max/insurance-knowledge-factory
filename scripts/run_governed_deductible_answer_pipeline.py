from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.customer_document_intelligence.end_to_end_answer_pipeline import (
    GovernedDeductibleAnswerPipeline,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete governed deductible answer pipeline from parsed "
            "customer document to delivery artifact."
        )
    )
    parser.add_argument("--parsed-document", required=True)
    parser.add_argument("--understanding-asset", required=True)
    parser.add_argument("--llm-response-file", required=True)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--provider-name", default="offline_response_file")
    parser.add_argument("--model-name", default="unspecified")
    args = parser.parse_args()

    output_dir = Path(args.output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    run = GovernedDeductibleAnswerPipeline().run_from_files(
        parsed_document_path=args.parsed_document,
        understanding_asset_path=args.understanding_asset,
        llm_response_path=args.llm_response_file,
        provider_metadata={
            "provider": args.provider_name,
            "model": args.model_name,
            "transport": "offline_response_file",
        },
    )

    filenames = {
        "candidate_document": "01_candidate_document.json",
        "customer_fact": "02_customer_fact.json",
        "understanding_match": "03_understanding_match.json",
        "interpretation_packet": "04_interpretation_packet.json",
        "route_decision": "05_answer_route.json",
        "approved_content_bundle": "06_approved_content_bundle.json",
        "verbalizer_request": "07_verbalizer_request.json",
        "verbalized_draft": "08_verbalized_draft.json",
        "validation_result": "09_validation_result.json",
        "delivery_artifact": "10_delivery_artifact.json",
    }
    for key, filename in filenames.items():
        (output_dir / filename).write_text(
            json.dumps(
                run["artifacts"][key],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    run_path = output_dir / "00_pipeline_run.json"
    run_path.write_text(
        json.dumps(
            run,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    delivery = run["artifacts"]["delivery_artifact"]
    print("=" * 72)
    print("GOVERNED DEDUCTIBLE ANSWER PIPELINE")
    print("=" * 72)
    print(f"Run ID          : {run['run_id']}")
    print(f"Run Status      : {run['status']}")
    print(f"Output Directory: {output_dir}")
    print(f"Customer Fact   : {run['artifacts']['customer_fact']['status']}")
    print(f"Match           : {run['artifacts']['understanding_match']['status']}")
    print(f"Route           : {run['artifacts']['route_decision']['route']}")
    print(f"Validation      : {delivery['validation_state']}")
    print(f"Delivery        : {delivery['delivery_state']}")
    print(f"Publication     : {delivery['publication_state']}")


if __name__ == "__main__":
    main()
