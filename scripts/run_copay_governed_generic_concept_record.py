"""Create the governed generic Copay concept record v0.2."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple

from knowledge_domains.health.concept_knowledge.governed_generic_concept_record import (
    GovernedGenericConceptRecordContract,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_copay_mechanism(parsed_json: Any) -> Tuple[str, int, str]:
    pages = parsed_json.get("pages")
    if not isinstance(pages, list):
        raise ValueError("Parsed policy wording must contain a pages list")

    candidates = []
    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        text = str(page.get("text") or "")
        normalized = " ".join(text.split())
        lower = normalized.lower()

        start_marker = "voluntary co-payment discount"
        start = lower.find(start_marker)
        if start < 0:
            continue

        excerpt = normalized[start:]
        stop = excerpt.lower().find("29. deductions in case of cancellation")
        if stop > 0:
            excerpt = excerpt[:stop]

        required_phrases = (
            "insured shall bear",
            "eligible claim amount payable under this policy",
        )
        excerpt_lower = excerpt.lower()
        if all(phrase in excerpt_lower for phrase in required_phrases):
            page_number = int(page.get("page_number") or index + 1)
            locator = f"$.pages[{index}].text"
            candidates.append((locator, page_number, excerpt.strip()))

    if not candidates:
        raise ValueError(
            "No bounded voluntary copay mechanism found in parsed policy wording"
        )

    return max(candidates, key=lambda item: len(item[2]))


def build_record(
    *,
    source_pdf_relative: str,
    parsed_path_relative: str,
    source_sha256: str,
    evidence_locator: str,
    evidence_page: int,
    evidence_text: str,
    reviewer_identity: str,
    reviewed_at: str,
    created_by: str,
    created_at: str,
) -> Dict[str, Any]:
    return GovernedGenericConceptRecordContract.create_record(
        concept_id="copay",
        concept_name="Copay",
        domain="health_insurance",
        definition=(
            "A copay is a policy cost-sharing condition under which the insured "
            "bears a stated percentage of an amount determined under the applicable "
            "policy terms when the copay applies."
        ),
        plain_language_explanation=(
            "When an applicable copay condition is triggered, the customer bears "
            "the stated percentage of the policy-defined calculation base. The "
            "percentage, calculation base, and scope must be checked in the "
            "applicable policy and customer documents."
        ),
        practical_implication=(
            "A copay can increase the customer's out-of-pocket share for a covered "
            "claim or benefit. It may be mandatory, optional, or conditional, and "
            "it does not by itself establish what the insurer will finally pay."
        ),
        simple_example={
            "policy_defined_calculation_base": 90000,
            "copay_percentage": 20,
            "insured_borne_copay_amount": 18000,
            "remaining_amount_for_insurer_assessment": 72000,
            "boundary": (
                "Illustrative only. This assumes the policy terms establish a "
                "20% copay on a calculation base of 90000. It does not establish "
                "claim entitlement or guarantee payment of the remaining amount."
            ),
        },
        common_misunderstandings=[
            "A copay does not automatically apply to every claim.",
            "A copay percentage does not necessarily apply to the total hospital bill.",
            "The insurer does not automatically pay the entire remaining percentage.",
            "A copay is not always voluntary and is not always mandatory.",
            "Another copay or deductible may also apply if the policy terms provide for it.",
        ],
        limitations=[
            "This record does not state any insurer-specific or product-specific copay.",
            "It does not determine whether a copay applies to a customer's policy or claim.",
            "It does not determine the policy-defined calculation base.",
            "It does not determine claim admissibility, settlement, entitlement, or recommendation.",
        ],
        product_specific_boundary=(
            "The percentage, mandatory or voluntary status, calculation base, "
            "applicability conditions, sequencing, stacking, waiver, and affected "
            "benefits must come from governed product knowledge and applicable "
            "policy wording."
        ),
        customer_document_boundary=(
            "A customer's selected or applicable copay must be verified from the "
            "policy schedule, proposal, endorsement, certificate, or other applicable "
            "customer document."
        ),
        related_concepts=[
            "deductible",
            "admissible_claim",
            "eligible_claim_amount",
            "sum_insured",
            "non_payable_expense",
        ],
        source_evidence=[{
            "evidence_id": "copay_bajaj_my_health_care_voluntary_mechanism_v1",
            "source_type": "insurer_policy_wording_generic_mechanism",
            "source_title": "My Health Care Plan 1 Policy Wording",
            "publisher": "Bajaj General Insurance Limited",
            "source_locator": (
                f"{parsed_path_relative}::{evidence_locator}::page={evidence_page}"
            ),
            "source_document_path": source_pdf_relative,
            "source_sha256": source_sha256,
            "evidence_text": evidence_text,
            "hosting_document_scope": "product_specific",
            "extracted_content_scope": "generic_insurance_concept",
            "product_context_excluded": True,
        }],
        review_decision={
            "review_decision_id": "gcrev_copay_v1",
            "decision": "approve_for_governed_generic_concept_creation",
            "reviewer_identity": reviewer_identity,
            "reviewed_at": reviewed_at,
            "rationale": (
                "The bounded policy-wording mechanism was reviewed for generic "
                "copay meaning only. Product-specific percentages, discount "
                "entitlements, applicability, insurer liability, and customer "
                "selection remain excluded."
            ),
        },
        knowledge_version="1.0",
        created_by=created_by,
        created_at=created_at,
        factory_signature={
            "factory": "PolicyScna Knowledge Factory",
            "engine_version": "0.2",
            "rules_version": "governed_generic_concept_rules_v0.2",
            "schema_version": "0.2",
            "deterministic": True,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the governed generic Copay concept record v0.2"
    )
    parser.add_argument("--source-pdf-path", required=True)
    parser.add_argument("--parsed-policy-wording-path", required=True)
    parser.add_argument("--reviewer-identity", required=True)
    parser.add_argument("--reviewed-at", required=True)
    parser.add_argument("--created-by", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument(
        "--output-path",
        default=(
            "knowledge/factory/generic_concepts/copay/"
            "governed_generic_concept_record_v0_2.json"
        ),
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
    evidence_locator, evidence_page, evidence_text = find_copay_mechanism(parsed)
    source_sha256 = sha256_file(source_pdf)

    record = build_record(
        source_pdf_relative=source_pdf_relative,
        parsed_path_relative=parsed_path_relative,
        source_sha256=source_sha256,
        evidence_locator=evidence_locator,
        evidence_page=evidence_page,
        evidence_text=evidence_text,
        reviewer_identity=args.reviewer_identity,
        reviewed_at=args.reviewed_at,
        created_by=args.created_by,
        created_at=args.created_at,
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
    print(f"Evidence page: {evidence_page}")
    print(f"Evidence path: {evidence_locator}")
    print(f"Output       : {output}")
    print(f"Publication  : {record['publication_state']}")
    print(f"Answer state : {record['customer_answer_state']}")


if __name__ == "__main__":
    main()
