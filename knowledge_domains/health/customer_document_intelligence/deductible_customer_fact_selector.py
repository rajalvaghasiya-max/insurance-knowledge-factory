"""Select a customer-specific deductible from extraction candidates."""
from __future__ import annotations

from typing import Any, Mapping

from knowledge_domains.health.extraction_primitives.extraction_candidate_contract import (
    ExtractionCandidateContract,
    ExtractionCandidateContractError,
)

from .customer_document_fact import (
    CustomerDocumentFactContract,
    CustomerDocumentFactError,
)


class DeductibleCustomerFactSelector:
    """Convert deductible evidence candidates into one governed customer fact."""

    SELECTOR_ID = "health.deductible_customer_fact_selector"
    VERSION = "1.0"

    def select(self, candidate_document: Mapping[str, Any]) -> dict[str, Any]:
        try:
            ExtractionCandidateContract.validate_document(candidate_document)
        except ExtractionCandidateContractError as exc:
            raise CustomerDocumentFactError(str(exc)) from exc

        source = dict(candidate_document["source"])
        document_type = str(source.get("document_type") or "").strip().lower()

        if (
            document_type
            not in CustomerDocumentFactContract.ALLOWED_CUSTOMER_DOCUMENT_TYPES
        ):
            return CustomerDocumentFactContract.build(
                source=source,
                status=CustomerDocumentFactContract.BLOCKED,
                normalized_value=None,
                evidence_items=[],
                candidate_ids=[],
                distinct_candidate_values=[],
                status_reason="unsupported_customer_document_type",
            )

        candidates = [
            candidate
            for candidate in candidate_document.get("candidates", [])
            if self._is_supported_deductible_candidate(candidate)
        ]
        candidates.sort(
            key=lambda item: (
                item["evidence"]["page_number"],
                item["evidence"]["character_start"],
                item["candidate_id"],
            )
        )

        if not candidates:
            return CustomerDocumentFactContract.build(
                source=source,
                status=CustomerDocumentFactContract.NOT_FOUND,
                normalized_value=None,
                evidence_items=[],
                candidate_ids=[],
                distinct_candidate_values=[],
                status_reason="no_explicit_currency_deductible_candidate",
            )

        distinct_values = sorted(
            {int(item["normalized_value"]["value"]) for item in candidates}
        )
        candidate_ids = [str(item["candidate_id"]) for item in candidates]
        evidence_items = [self._evidence_item(item) for item in candidates]

        if len(distinct_values) > 1:
            return CustomerDocumentFactContract.build(
                source=source,
                status=CustomerDocumentFactContract.AMBIGUOUS,
                normalized_value=None,
                evidence_items=evidence_items,
                candidate_ids=candidate_ids,
                distinct_candidate_values=distinct_values,
                status_reason="multiple_distinct_deductible_values_found",
            )

        normalized_value = dict(candidates[0]["normalized_value"])
        return CustomerDocumentFactContract.build(
            source=source,
            status=CustomerDocumentFactContract.EXTRACTED,
            normalized_value=normalized_value,
            evidence_items=evidence_items,
            candidate_ids=candidate_ids,
            distinct_candidate_values=distinct_values,
            status_reason="single_distinct_customer_deductible_value_found",
        )

    @staticmethod
    def _is_supported_deductible_candidate(candidate: Mapping[str, Any]) -> bool:
        attributes = candidate.get("attributes")
        value = candidate.get("normalized_value")
        return (
            isinstance(attributes, Mapping)
            and attributes.get("monetary_role_hint") == "deductible"
            and isinstance(value, Mapping)
            and value.get("kind") == "currency"
            and value.get("unit") == "INR"
            and isinstance(value.get("value"), int)
            and not isinstance(value.get("value"), bool)
            and value["value"] > 0
        )

    @staticmethod
    def _evidence_item(candidate: Mapping[str, Any]) -> dict[str, Any]:
        evidence = candidate["evidence"]
        return {
            "candidate_id": candidate["candidate_id"],
            "page_number": evidence["page_number"],
            "character_start": evidence["character_start"],
            "character_end": evidence["character_end"],
            "normalized_character_start": evidence[
                "normalized_character_start"
            ],
            "normalized_character_end": evidence["normalized_character_end"],
            "evidence_type": evidence["evidence_type"],
            "text": evidence["text"],
            "normalized_value": dict(candidate["normalized_value"]),
            "confidence": dict(candidate["confidence"]),
        }
