"""Governed customer-document fact contract for Health.

This contract represents a fact found in a specific customer's document. It is
not reusable product knowledge, a customer-facing answer, an entitlement
decision, or a recommendation.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence


class CustomerDocumentFactError(ValueError):
    """Raised when a customer-document fact violates the contract."""


class CustomerDocumentFactContract:
    VERSION = "1.0"
    SCHEMA_VERSION = "1.0"
    RECORD_TYPE = "health_customer_document_fact_v1"

    FACT_SCOPE = "customer_specific"
    CONCEPT_ID = "deductible"
    FIELD_KEY = "customer_selected_deductible"
    RELATED_PRODUCT_FIELD_KEY = "currency_deductible_option"

    EXTRACTED = "extracted"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    BLOCKED = "blocked"
    ALLOWED_STATUSES = {EXTRACTED, NOT_FOUND, AMBIGUOUS, BLOCKED}

    ALLOWED_CUSTOMER_DOCUMENT_TYPES = {
        "policy_schedule",
        "quote",
        "renewal_notice",
        "endorsement",
    }

    _SHA256_RE = re.compile(r"[0-9a-f]{64}")

    @classmethod
    def build(
        cls,
        *,
        source: Mapping[str, Any],
        status: str,
        normalized_value: Mapping[str, Any] | None,
        evidence_items: Sequence[Mapping[str, Any]],
        candidate_ids: Sequence[str],
        distinct_candidate_values: Sequence[int],
        status_reason: str,
    ) -> dict[str, Any]:
        cls._validate_source(source)
        if status not in cls.ALLOWED_STATUSES:
            raise CustomerDocumentFactError("unsupported customer-document fact status")
        cls._require_nonempty(status_reason, "status_reason")

        sorted_candidate_ids = sorted(set(candidate_ids))
        sorted_values = sorted(set(distinct_candidate_values))
        evidence = [dict(item) for item in evidence_items]
        evidence.sort(
            key=lambda item: (
                item.get("page_number", 0),
                item.get("character_start", 0),
                item.get("candidate_id", ""),
            )
        )

        fact_id = cls._fact_id(
            source_sha256=str(source["sha256"]),
            status=status,
            normalized_value=normalized_value,
            candidate_ids=sorted_candidate_ids,
            distinct_values=sorted_values,
        )

        record = {
            "schema_version": cls.SCHEMA_VERSION,
            "record_type": cls.RECORD_TYPE,
            "contract_version": cls.VERSION,
            "fact_id": fact_id,
            "fact_scope": cls.FACT_SCOPE,
            "concept_id": cls.CONCEPT_ID,
            "field_key": cls.FIELD_KEY,
            "related_product_field_key": cls.RELATED_PRODUCT_FIELD_KEY,
            "status": status,
            "status_reason": status_reason,
            "source": dict(source),
            "normalized_value": dict(normalized_value) if normalized_value is not None else None,
            "candidate_count": len(sorted_candidate_ids),
            "supporting_candidate_ids": sorted_candidate_ids,
            "distinct_candidate_values": sorted_values,
            "evidence_items": evidence,
            "publication_state": "not_published",
            "customer_answer_state": "not_created",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
            "guardrails": [
                "customer_document_fact_not_product_fact",
                "customer_document_fact_not_customer_answer",
                "customer_document_fact_not_entitlement_decision",
                "customer_document_fact_not_recommendation",
            ],
        }
        cls.validate(record)
        return record

    @classmethod
    def validate(cls, record: Mapping[str, Any]) -> None:
        if not isinstance(record, Mapping):
            raise CustomerDocumentFactError("customer-document fact must be an object")
        if record.get("schema_version") != cls.SCHEMA_VERSION:
            raise CustomerDocumentFactError("schema_version must be 1.0")
        if record.get("record_type") != cls.RECORD_TYPE:
            raise CustomerDocumentFactError("unsupported record_type")
        if record.get("contract_version") != cls.VERSION:
            raise CustomerDocumentFactError("unsupported contract_version")
        cls._require_prefixed(record.get("fact_id"), "cdfact_", "fact_id")
        if record.get("fact_scope") != cls.FACT_SCOPE:
            raise CustomerDocumentFactError("fact_scope must be customer_specific")
        if record.get("concept_id") != cls.CONCEPT_ID:
            raise CustomerDocumentFactError("concept_id must be deductible")
        if record.get("field_key") != cls.FIELD_KEY:
            raise CustomerDocumentFactError(
                "field_key must be customer_selected_deductible"
            )
        if record.get("related_product_field_key") != cls.RELATED_PRODUCT_FIELD_KEY:
            raise CustomerDocumentFactError(
                "related_product_field_key must be currency_deductible_option"
            )

        status = record.get("status")
        if status not in cls.ALLOWED_STATUSES:
            raise CustomerDocumentFactError("unsupported status")
        cls._require_nonempty(record.get("status_reason"), "status_reason")

        source = record.get("source")
        if not isinstance(source, Mapping):
            raise CustomerDocumentFactError("source must be an object")
        cls._validate_source(source)

        candidate_ids = record.get("supporting_candidate_ids")
        if not isinstance(candidate_ids, list) or not all(
            isinstance(item, str) and item.startswith("excand_")
            for item in candidate_ids
        ):
            raise CustomerDocumentFactError(
                "supporting_candidate_ids must contain excand_ identifiers"
            )
        if len(candidate_ids) != len(set(candidate_ids)):
            raise CustomerDocumentFactError("supporting_candidate_ids must be unique")
        if record.get("candidate_count") != len(candidate_ids):
            raise CustomerDocumentFactError(
                "candidate_count must equal supporting_candidate_ids length"
            )

        values = record.get("distinct_candidate_values")
        if not isinstance(values, list) or not all(
            isinstance(item, int) and not isinstance(item, bool) and item > 0
            for item in values
        ):
            raise CustomerDocumentFactError(
                "distinct_candidate_values must contain positive integers"
            )
        if values != sorted(set(values)):
            raise CustomerDocumentFactError(
                "distinct_candidate_values must be sorted and unique"
            )

        evidence_items = record.get("evidence_items")
        if not isinstance(evidence_items, list):
            raise CustomerDocumentFactError("evidence_items must be a list")
        for item in evidence_items:
            cls._validate_evidence_item(item)

        normalized = record.get("normalized_value")
        if status == cls.EXTRACTED:
            cls._validate_currency(normalized)
            if len(values) != 1:
                raise CustomerDocumentFactError(
                    "extracted fact must have exactly one distinct value"
                )
            if normalized["value"] != values[0]:
                raise CustomerDocumentFactError(
                    "normalized_value must match distinct candidate value"
                )
            if not candidate_ids or not evidence_items:
                raise CustomerDocumentFactError(
                    "extracted fact requires candidate and evidence lineage"
                )
        else:
            if normalized is not None:
                raise CustomerDocumentFactError(
                    "non-extracted fact must not set normalized_value"
                )

        if status == cls.NOT_FOUND and (candidate_ids or values or evidence_items):
            raise CustomerDocumentFactError(
                "not_found fact must not contain deductible candidates"
            )
        if status == cls.AMBIGUOUS and len(values) < 2:
            raise CustomerDocumentFactError(
                "ambiguous fact requires at least two distinct values"
            )

        required_states = {
            "publication_state": "not_published",
            "customer_answer_state": "not_created",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }
        for key, expected in required_states.items():
            if record.get(key) != expected:
                raise CustomerDocumentFactError(f"{key} must be {expected}")

    @classmethod
    def _fact_id(
        cls,
        *,
        source_sha256: str,
        status: str,
        normalized_value: Mapping[str, Any] | None,
        candidate_ids: Sequence[str],
        distinct_values: Sequence[int],
    ) -> str:
        material = {
            "source_sha256": source_sha256,
            "fact_scope": cls.FACT_SCOPE,
            "concept_id": cls.CONCEPT_ID,
            "field_key": cls.FIELD_KEY,
            "status": status,
            "normalized_value": dict(normalized_value) if normalized_value else None,
            "candidate_ids": list(candidate_ids),
            "distinct_values": list(distinct_values),
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:20]
        return f"cdfact_{digest}"

    @classmethod
    def _validate_source(cls, source: Mapping[str, Any]) -> None:
        sha = source.get("sha256")
        if not isinstance(sha, str) or not cls._SHA256_RE.fullmatch(sha):
            raise CustomerDocumentFactError(
                "source.sha256 must be a lowercase 64-character SHA-256"
            )
        if source.get("source_document_id") != f"sha256:{sha}":
            raise CustomerDocumentFactError(
                "source.source_document_id must equal sha256:<source.sha256>"
            )
        cls._require_nonempty(source.get("document_type"), "source.document_type")
        cls._require_nonempty(source.get("source_url"), "source.source_url")
        cls._require_nonempty(
            source.get("relative_archive_path"),
            "source.relative_archive_path",
        )
        cls._require_nonempty(
            source.get("provenance_status"),
            "source.provenance_status",
        )

    @classmethod
    def _validate_evidence_item(cls, item: Any) -> None:
        if not isinstance(item, Mapping):
            raise CustomerDocumentFactError("evidence item must be an object")
        cls._require_prefixed(item.get("candidate_id"), "excand_", "candidate_id")
        cls._require_positive_int(item.get("page_number"), "page_number")
        cls._require_nonnegative_int(item.get("character_start"), "character_start")
        cls._require_nonnegative_int(item.get("character_end"), "character_end")
        if item["character_end"] < item["character_start"]:
            raise CustomerDocumentFactError(
                "evidence character_end must be >= character_start"
            )
        cls._require_nonempty(item.get("text"), "evidence text")
        cls._validate_currency(item.get("normalized_value"))

    @staticmethod
    def _validate_currency(value: Any) -> None:
        if not isinstance(value, Mapping):
            raise CustomerDocumentFactError("normalized value must be an object")
        if value.get("kind") != "currency" or value.get("unit") != "INR":
            raise CustomerDocumentFactError("normalized value must be INR currency")
        amount = value.get("value")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            raise CustomerDocumentFactError(
                "normalized currency value must be a positive integer"
            )
        raw_text = value.get("raw_text")
        if raw_text is not None and (
            not isinstance(raw_text, str) or not raw_text.strip()
        ):
            raise CustomerDocumentFactError(
                "normalized currency raw_text must be non-empty when present"
            )

    @staticmethod
    def _require_nonempty(value: Any, name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise CustomerDocumentFactError(f"{name} must be a non-empty string")

    @classmethod
    def _require_prefixed(cls, value: Any, prefix: str, name: str) -> None:
        cls._require_nonempty(value, name)
        if not value.startswith(prefix):
            raise CustomerDocumentFactError(f"{name} must start with {prefix}")

    @staticmethod
    def _require_positive_int(value: Any, name: str) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise CustomerDocumentFactError(f"{name} must be a positive integer")

    @staticmethod
    def _require_nonnegative_int(value: Any, name: str) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise CustomerDocumentFactError(
                f"{name} must be a non-negative integer"
            )
