"""Contracts for governed customer-education publication.

Education publication is intentionally distinct from authoritative operative-product
publication. It authorizes reviewed generic concept education for explanation use only;
it does not certify product mechanics, entitlement, claim payment, recommendation, or
customer-specific applicability.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

SUPPORTED_CONTRACT_VERSION = "1.0"
EDUCATION_PUBLICATION_STATUS = "EDUCATION_AUTHORITATIVE"

CUSTOMER_EDUCATION = "CUSTOMER_EDUCATION"
OPERATIVE_PRODUCT_FACT = "OPERATIVE_PRODUCT_FACT"
EDUCATION_REQUEST_USES = frozenset({CUSTOMER_EDUCATION, OPERATIVE_PRODUCT_FACT})


class EducationPublicationContractError(ValueError):
    """Raised when an education-publication contract is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EducationPublicationContractError(f"{label} must be a non-empty string")
    return value.strip()


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise EducationPublicationContractError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class EducationExample:
    scenario: str
    result: str
    boundary: str


def build_education_example(*, scenario: str, result: str, boundary: str) -> EducationExample:
    return EducationExample(
        scenario=_text(scenario, "example.scenario"),
        result=_text(result, "example.result"),
        boundary=_text(boundary, "example.boundary"),
    )


@dataclass(frozen=True)
class EducationPublicationInput:
    contract_version: str
    publication_id: str
    meaning_asset: Mapping[str, Any]
    publication_authority: str


def build_education_publication_input(
    *,
    publication_id: str,
    meaning_asset: Mapping[str, Any],
    publication_authority: str,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> EducationPublicationInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise EducationPublicationContractError(
            f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}"
        )
    if not isinstance(meaning_asset, Mapping):
        raise EducationPublicationContractError("meaning_asset must be a mapping")
    return EducationPublicationInput(
        contract_version=contract_version,
        publication_id=_text(publication_id, "publication_id"),
        meaning_asset=deepcopy(dict(meaning_asset)),
        publication_authority=_text(publication_authority, "publication_authority"),
    )


@dataclass(frozen=True)
class EducationPublicationRecord:
    contract_version: str
    publication_id: str
    publication_status: str
    allowed_uses: tuple[str, ...]
    concept_id: str
    canonical_name: str
    definition: str
    plain_language_explanation: str
    practical_implication: str
    examples: tuple[EducationExample, ...]
    limitations: tuple[str, ...]
    product_specific_boundary: str
    customer_document_boundary: str
    evidence_references: tuple[str, ...]
    source_asset_id: str
    source_asset_digest: str
    source_governed_record_id: str
    source_knowledge_version: str
    review_decision_id: str
    publication_authority: str
    publication_receipt_id: str


def validate_education_publication_record(
    record: EducationPublicationRecord,
) -> EducationPublicationRecord:
    if not isinstance(record, EducationPublicationRecord):
        raise EducationPublicationContractError(
            "record must be an EducationPublicationRecord"
        )
    if record.contract_version != SUPPORTED_CONTRACT_VERSION:
        raise EducationPublicationContractError("unsupported contract_version")
    if record.publication_status != EDUCATION_PUBLICATION_STATUS:
        raise EducationPublicationContractError("unsupported education publication status")
    if record.allowed_uses != (CUSTOMER_EDUCATION,):
        raise EducationPublicationContractError(
            "education publication may authorize CUSTOMER_EDUCATION only"
        )
    for label, value in (
        ("publication_id", record.publication_id),
        ("concept_id", record.concept_id),
        ("canonical_name", record.canonical_name),
        ("definition", record.definition),
        ("plain_language_explanation", record.plain_language_explanation),
        ("practical_implication", record.practical_implication),
        ("product_specific_boundary", record.product_specific_boundary),
        ("customer_document_boundary", record.customer_document_boundary),
        ("source_asset_id", record.source_asset_id),
        ("source_asset_digest", record.source_asset_digest),
        ("source_governed_record_id", record.source_governed_record_id),
        ("source_knowledge_version", record.source_knowledge_version),
        ("review_decision_id", record.review_decision_id),
        ("publication_authority", record.publication_authority),
        ("publication_receipt_id", record.publication_receipt_id),
    ):
        _text(value, label)
    if len(record.source_asset_digest) != 64:
        raise EducationPublicationContractError(
            "source_asset_digest must be a sha256 hex digest"
        )
    if not record.evidence_references:
        raise EducationPublicationContractError(
            "education publication requires evidence references"
        )
    _unique(record.evidence_references, "evidence_references")
    if not record.examples:
        raise EducationPublicationContractError(
            "education publication requires at least one reviewed example"
        )
    if any(not isinstance(item, EducationExample) for item in record.examples):
        raise EducationPublicationContractError(
            "examples must contain EducationExample values"
        )
    _unique(record.limitations, "limitations")
    return record


__all__ = [
    "CUSTOMER_EDUCATION",
    "EDUCATION_PUBLICATION_STATUS",
    "EDUCATION_REQUEST_USES",
    "OPERATIVE_PRODUCT_FACT",
    "EducationExample",
    "EducationPublicationContractError",
    "EducationPublicationInput",
    "EducationPublicationRecord",
    "build_education_example",
    "build_education_publication_input",
    "validate_education_publication_record",
]
