from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator, Tuple

from knowledge_domains.health.concept_knowledge.governed_generic_concept_record import (
    GovernedGenericConceptRecordContract,
)


def walk_strings(value: Any, path: str = "$") -> Iterator[Tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk_strings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_strings(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def find_deductible_definition(parsed_json: Any) -> Tuple[str, str]:
    candidates = []
    for path, text in walk_strings(parsed_json):
        normalized = " ".join(text.split())
        marker = "Deductible: means"
        if marker.lower() in normalized.lower():
            start = normalized.lower().index(marker.lower())
            excerpt = normalized[start:]
            # Stop before the next numbered definition where possible.
            for stop_marker in ("15. Dental Treatment:", "Dental Treatment: means"):
                idx = excerpt.find(stop_marker)
                if idx > 0:
                    excerpt = excerpt[:idx]
            candidates.append((path, excerpt.strip()))
    if not candidates:
        raise ValueError("No bounded 'Deductible: means' definition found in parsed JSON")
    return max(candidates, key=lambda item: len(item[1]))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the governed generic Deductible concept record v0.2"
    )
    parser.add_argument("--source-pdf-path", required=True)
    parser.add_argument(
        "--parsed-policy-wording-path",
        default="knowledge/health/aditya_birla_health/activ_one/parsed/policy_wording.json",
    )
    parser.add_argument("--reviewer-identity", required=True)
    parser.add_argument("--reviewed-at", required=True)
    parser.add_argument("--created-by", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument(
        "--output-path",
        default="knowledge/factory/generic_concepts/deductible/"
                "governed_generic_concept_record_v0_2.json",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    source_pdf = Path(args.source_pdf_path).resolve()
    parsed_path = Path(args.parsed_policy_wording_path).resolve()
    if not source_pdf.is_file():
        raise FileNotFoundError(source_pdf)
    if not parsed_path.is_file():
        raise FileNotFoundError(parsed_path)

    try:
        source_pdf_relative = source_pdf.relative_to(repo_root).as_posix()
        parsed_path_relative = parsed_path.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError(
            "Source PDF and parsed policy wording must be inside the repository"
        ) from exc

    parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
    json_path, evidence_text = find_deductible_definition(parsed)
    source_sha256 = sha256_file(source_pdf)

    record = GovernedGenericConceptRecordContract.create_record(
        concept_id="deductible",
        concept_name="Deductible",
        domain="health_insurance",
        definition=(
            "A deductible is a cost-sharing requirement that must be exhausted "
            "before benefits become payable by the insurer, subject to the policy terms."
        ),
        plain_language_explanation=(
            "A deductible is the amount, or in some benefit designs the specified "
            "time period, that applies before the insurer starts paying eligible benefits."
        ),
        practical_implication=(
            "The insured may have to bear the deductible before an eligible insurer "
            "payment begins. The exact form and frequency of the deductible must be "
            "checked in the applicable product and policy documents."
        ),
        simple_example={
            "eligible_expense": 300000,
            "deductible": 100000,
            "balance_for_insurer_assessment": 200000,
            "boundary": (
                "Illustrative only. The insurer does not automatically pay the full "
                "balance; admissibility, exclusions, limits, and policy terms still apply."
            ),
        },
        common_misunderstandings=[
            "A deductible does not automatically mean the insurer pays every amount above it.",
            "A deductible does not reduce the Sum Insured merely because it applies.",
            "Deductibles can operate differently, including per-claim, annual aggregate, "
            "rupee-based, or time-based forms, depending on policy design.",
        ],
        limitations=[
            "This record does not state any insurer-specific or product-specific deductible.",
            "It does not determine which deductible applies to a customer's policy.",
            "It does not determine claim admissibility, settlement, or entitlement.",
        ],
        product_specific_boundary=(
            "The amount, frequency, optionality, and mechanics of a deductible must come "
            "from governed product knowledge and the applicable policy wording or schedule."
        ),
        customer_document_boundary=(
            "A customer's selected deductible must be verified from the policy schedule, "
            "proposal, endorsement, or other applicable customer document."
        ),
        related_concepts=[
            "copay",
            "admissible_claim",
            "sum_insured",
            "aggregate_deductible",
            "hospital_cash",
        ],
        source_evidence=[{
            "evidence_id": "deductible_activ_one_standard_definition_v1",
            "source_type": "insurer_policy_wording_standard_definition",
            "source_title": "Activ One Policy Wording",
            "publisher": "Aditya Birla Health Insurance Co. Limited",
            "source_locator": f"{parsed_path_relative}::{json_path}",
            "source_document_path": source_pdf_relative,
            "source_sha256": source_sha256,
            "evidence_text": evidence_text,
            "hosting_document_scope": "product_specific",
            "extracted_content_scope": "generic_insurance_concept",
            "product_context_excluded": True,
        }],
        review_decision={
            "review_decision_id": "gcrev_deductible_v1",
            "decision": "approve_for_governed_generic_concept_creation",
            "reviewer_identity": args.reviewer_identity,
            "reviewed_at": args.reviewed_at,
            "rationale": (
                "The bounded standardized deductible definition was reviewed for generic "
                "concept use only. Product-specific options, values, applicability, and "
                "customer entitlement remain excluded."
            ),
        },
        knowledge_version="1.0",
        created_by=args.created_by,
        created_at=args.created_at,
        factory_signature={
            "factory": "PolicyScna Knowledge Factory",
            "engine_version": "0.2",
            "rules_version": "governed_generic_concept_rules_v0.2",
            "schema_version": "0.2",
            "deterministic": True,
        },
    )

    output = Path(args.output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("=" * 72)
    print("GOVERNED GENERIC CONCEPT RECORD")
    print("=" * 72)
    print(f"Concept      : {record['concept_id']}")
    print(f"Record ID    : {record['record_id']}")
    print(f"Source SHA256: {source_sha256}")
    print(f"Evidence path: {json_path}")
    print(f"Output       : {output}")
    print(f"Publication  : {record['publication_state']}")
    print(f"Answer state : {record['customer_answer_state']}")


if __name__ == "__main__":
    main()

