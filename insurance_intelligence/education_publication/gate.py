"""Deterministic gate for governed customer-education publication."""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping

from insurance_intelligence.contracts.education_publication import (
    CUSTOMER_EDUCATION,
    EDUCATION_PUBLICATION_STATUS,
    EducationPublicationInput,
    EducationPublicationRecord,
    build_education_example,
    validate_education_publication_record,
)


class EducationPublicationGateError(ValueError):
    """Raised when reviewed education cannot be published safely."""


_APPROVED_REVIEW_DECISION = "approve_for_governed_generic_concept_creation"

_AFFIRMATIVE_CLAIM_PAYMENT_PATTERNS = (
    re.compile(r"\bclaim\s+(?:will|shall)\s+be\s+(?:paid|approved)\b", re.I),
    re.compile(r"\binsurer\s+(?:will|shall)\s+pay\b", re.I),
    re.compile(r"\bclaim\s+(?:is|will\s+be)\s+guaranteed\b", re.I),
    re.compile(r"\bfully\s+covered\b", re.I),
)
_RECOMMENDATION_PATTERNS = (
    re.compile(r"\b(?:should|must|ought\s+to)\s+(?:buy|choose|purchase|switch|select|pick)\b", re.I),
    re.compile(r"\b(?:best|better|ideal|right)\s+(?:plan|policy|product|option|choice)\b", re.I),
    re.compile(r"\b(?:i|we)\s+(?:would\s+)?recommend\b", re.I),
)


def _text(mapping: Mapping[str, Any], field: str, *, prefix: str = "") -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise EducationPublicationGateError(f"{prefix}{field} must be a non-empty string")
    return value.strip()


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EducationPublicationGateError(f"{label} must be an object")
    return value


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _receipt_id(*parts: str) -> str:
    return "education_receipt_" + sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]


def _customer_content(values: tuple[str, ...]) -> str:
    return " ".join(value for value in values if value)


def _reject_prohibited_customer_language(values: tuple[str, ...]) -> None:
    text = _customer_content(values)
    if any(pattern.search(text) for pattern in _AFFIRMATIVE_CLAIM_PAYMENT_PATTERNS):
        raise EducationPublicationGateError(
            "affirmative claim-payment or coverage-guarantee language is not publishable as education"
        )
    if any(pattern.search(text) for pattern in _RECOMMENDATION_PATTERNS):
        raise EducationPublicationGateError(
            "recommendation language is not publishable as generic education"
        )


def _validate_source_asset(asset: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if asset.get("asset_type") != "meaning_asset":
        raise EducationPublicationGateError("source asset must be a meaning_asset")
    if asset.get("schema_version") != "meaning_asset_v1.0":
        raise EducationPublicationGateError(
            "source asset must use meaning_asset_v1.0"
        )
    if asset.get("review_status") != "approved_governed_generic_concept":
        raise EducationPublicationGateError(
            "source meaning asset is not approved governed generic concept knowledge"
        )

    certification = _mapping(asset.get("certification"), "certification")
    if certification.get("status") != "governed_source_approved":
        raise EducationPublicationGateError(
            "source meaning asset is not governed-source approved"
        )
    if certification.get("human_reviewed") is not True:
        raise EducationPublicationGateError(
            "source meaning asset must be human reviewed"
        )

    governance = _mapping(asset.get("governance"), "governance")
    expected = {
        "concept_scope": "generic_insurance_concept",
        "publication_state": "not_published",
        "customer_answer_state": "not_created",
        "entitlement_state": "not_evaluated",
        "recommendation_state": "not_created",
    }
    for field, value in expected.items():
        if governance.get(field) != value:
            raise EducationPublicationGateError(
                f"governance.{field} must be {value!r}"
            )

    review = _mapping(governance.get("review_decision"), "governance.review_decision")
    if review.get("decision") != _APPROVED_REVIEW_DECISION:
        raise EducationPublicationGateError(
            "source review decision does not authorize governed generic concept creation"
        )
    if certification.get("review_decision_id") != review.get("review_decision_id"):
        raise EducationPublicationGateError(
            "certification and governance review decision IDs must match"
        )

    evidence = asset.get("evidence")
    refs = asset.get("evidence_refs")
    if not isinstance(evidence, list) or not evidence:
        raise EducationPublicationGateError("source meaning asset requires evidence")
    if not isinstance(refs, list) or not refs:
        raise EducationPublicationGateError("source meaning asset requires evidence_refs")
    evidence_ids: list[str] = []
    for index, item in enumerate(evidence):
        entry = _mapping(item, f"evidence[{index}]")
        evidence_id = _text(entry, "evidence_id", prefix=f"evidence[{index}].")
        evidence_ids.append(evidence_id)
        scope = entry.get("extracted_content_scope", entry.get("evidence_scope"))
        if scope != "generic_insurance_concept":
            raise EducationPublicationGateError(
                "education publication requires generic-insurance-concept evidence scope"
            )
        if entry.get("hosting_document_scope") == "product_specific" and (
            entry.get("product_context_excluded") is not True
        ):
            raise EducationPublicationGateError(
                "product-hosted education evidence must explicitly exclude product context"
            )
    if refs != evidence_ids:
        raise EducationPublicationGateError(
            "evidence_refs must exactly match source evidence IDs"
        )
    return governance, review


def _examples(asset: Mapping[str, Any]):
    raw = asset.get("policy_examples")
    if not isinstance(raw, list) or not raw:
        raise EducationPublicationGateError(
            "source meaning asset requires reviewed policy_examples"
        )
    examples = []
    for index, item in enumerate(raw):
        example = _mapping(item, f"policy_examples[{index}]")
        source_example = _mapping(
            example.get("source_example"),
            f"policy_examples[{index}].source_example",
        )
        examples.append(
            build_education_example(
                scenario=_text(
                    source_example,
                    "scenario",
                    prefix=f"policy_examples[{index}].source_example.",
                ),
                result=_text(
                    source_example,
                    "result",
                    prefix=f"policy_examples[{index}].source_example.",
                ),
                boundary=_text(
                    source_example,
                    "boundary",
                    prefix=f"policy_examples[{index}].source_example.",
                ),
            )
        )
    return tuple(examples)


def create_education_publication(
    publication_input: EducationPublicationInput,
) -> EducationPublicationRecord:
    """Create one immutable education-only publication record."""
    if not isinstance(publication_input, EducationPublicationInput):
        raise EducationPublicationGateError(
            "publication_input must be an EducationPublicationInput"
        )

    asset = _mapping(publication_input.meaning_asset, "meaning_asset")
    governance, review = _validate_source_asset(asset)
    examples = _examples(asset)

    definition = _text(asset, "core_meaning")
    plain = _text(asset, "functional_behaviour")
    practical = _text(asset, "business_purpose")
    product_boundary = _text(
        governance, "product_specific_boundary", prefix="governance."
    )
    customer_boundary = _text(
        governance, "customer_document_boundary", prefix="governance."
    )

    constraints = asset.get("constraints")
    if not isinstance(constraints, list):
        raise EducationPublicationGateError("constraints must be a list")
    limitations = tuple(
        item.strip()
        for item in constraints
        if isinstance(item, str)
        and item.strip()
        and item.strip() not in {product_boundary, customer_boundary}
    )
    if len(limitations) != len(set(limitations)):
        raise EducationPublicationGateError("education limitations must be unique")

    customer_text = (
        definition,
        plain,
        practical,
        *limitations,
        product_boundary,
        customer_boundary,
        *(
            value
            for example in examples
            for value in (example.scenario, example.result, example.boundary)
        ),
    )
    _reject_prohibited_customer_language(tuple(customer_text))

    concept_id = _text(asset, "concept_id")
    canonical_name = _text(asset, "canonical_name")
    source_asset_id = _text(asset, "asset_id")
    source_asset_digest = _canonical_digest(asset)
    source_record_id = _text(
        governance, "source_governed_record_id", prefix="governance."
    )
    source_knowledge_version = _text(
        governance, "source_knowledge_version", prefix="governance."
    )
    review_decision_id = _text(
        review, "review_decision_id", prefix="governance.review_decision."
    )
    evidence_refs = tuple(str(value).strip() for value in asset["evidence_refs"])

    content_digest = _canonical_digest(
        {
            "concept_id": concept_id,
            "canonical_name": canonical_name,
            "definition": definition,
            "plain_language_explanation": plain,
            "practical_implication": practical,
            "examples": [
                {
                    "scenario": item.scenario,
                    "result": item.result,
                    "boundary": item.boundary,
                }
                for item in examples
            ],
            "limitations": limitations,
            "product_specific_boundary": product_boundary,
            "customer_document_boundary": customer_boundary,
            "evidence_references": evidence_refs,
        }
    )
    receipt = _receipt_id(
        publication_input.publication_id,
        source_asset_id,
        source_asset_digest,
        review_decision_id,
        content_digest,
        publication_input.publication_authority,
    )

    return validate_education_publication_record(
        EducationPublicationRecord(
            contract_version=publication_input.contract_version,
            publication_id=publication_input.publication_id,
            publication_status=EDUCATION_PUBLICATION_STATUS,
            allowed_uses=(CUSTOMER_EDUCATION,),
            concept_id=concept_id,
            canonical_name=canonical_name,
            definition=definition,
            plain_language_explanation=plain,
            practical_implication=practical,
            examples=examples,
            limitations=limitations,
            product_specific_boundary=product_boundary,
            customer_document_boundary=customer_boundary,
            evidence_references=evidence_refs,
            source_asset_id=source_asset_id,
            source_asset_digest=source_asset_digest,
            source_governed_record_id=source_record_id,
            source_knowledge_version=source_knowledge_version,
            review_decision_id=review_decision_id,
            publication_authority=publication_input.publication_authority,
            publication_receipt_id=receipt,
        )
    )


__all__ = [
    "EducationPublicationGateError",
    "create_education_publication",
]
