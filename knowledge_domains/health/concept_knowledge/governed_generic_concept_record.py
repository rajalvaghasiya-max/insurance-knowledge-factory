"""Governed Generic Concept Record v0.2."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
import hashlib
import json
import re
from typing import Any, Dict, Iterable, Mapping


class GenericConceptValidationError(ValueError):
    """Raised when a generic concept record violates governance rules."""


class GovernedGenericConceptRecordContract:
    RECORD_TYPE = "governed_generic_concept_record_v0_2"
    SCHEMA_VERSION = "0.2"
    CONCEPT_SCOPE = "generic_insurance_concept"
    PUBLICATION_STATE = "not_published"
    CUSTOMER_ANSWER_STATE = "not_created"
    ENTITLEMENT_STATE = "not_evaluated"
    RECOMMENDATION_STATE = "not_created"
    APPROVED_REVIEW_DECISION = "approve_for_governed_generic_concept_creation"

    ALLOWED_SOURCE_TYPES = {
        "regulator_education_material",
        "regulator_glossary",
        "insurer_glossary",
        "insurer_education_material",
        "approved_training_material",
        "insurer_policy_wording_standard_definition",
        "insurer_policy_wording_generic_mechanism",
    }

    FORBIDDEN_STRUCTURED_KEYS = {
        "insurer_id", "product_id", "product_name", "uin",
        "plan_id", "plan_name", "variant_id", "variant_name",
        "selected_option", "selected_variant", "customer_id",
        "policy_number", "proposal_number", "recommendation",
        "claim_decision", "entitlement_decision",
    }

    SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

    @classmethod
    def create_record(
        cls, *,
        concept_id: str,
        concept_name: str,
        domain: str,
        definition: str,
        plain_language_explanation: str,
        practical_implication: str,
        simple_example: Mapping[str, Any],
        common_misunderstandings: Iterable[str],
        limitations: Iterable[str],
        product_specific_boundary: str,
        customer_document_boundary: str,
        related_concepts: Iterable[str],
        source_evidence: Iterable[Mapping[str, Any]],
        review_decision: Mapping[str, Any],
        knowledge_version: str,
        created_by: str,
        created_at: str,
        factory_signature: Mapping[str, Any],
    ) -> Dict[str, Any]:
        record = {
            "record_type": cls.RECORD_TYPE,
            "schema_version": cls.SCHEMA_VERSION,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "concept_scope": cls.CONCEPT_SCOPE,
            "domain": domain,
            "definition": definition,
            "plain_language_explanation": plain_language_explanation,
            "practical_implication": practical_implication,
            "simple_example": deepcopy(dict(simple_example)),
            "common_misunderstandings": list(common_misunderstandings),
            "limitations": list(limitations),
            "product_specific_boundary": product_specific_boundary,
            "customer_document_boundary": customer_document_boundary,
            "related_concepts": sorted({str(x).strip() for x in related_concepts if str(x).strip()}),
            "source_evidence": [deepcopy(dict(x)) for x in source_evidence],
            "review_decision": deepcopy(dict(review_decision)),
            "knowledge_version": knowledge_version,
            "publication_state": cls.PUBLICATION_STATE,
            "customer_answer_state": cls.CUSTOMER_ANSWER_STATE,
            "entitlement_state": cls.ENTITLEMENT_STATE,
            "recommendation_state": cls.RECOMMENDATION_STATE,
            "created_by": created_by,
            "created_at": created_at,
            "factory_signature": deepcopy(dict(factory_signature)),
            "non_publication_guardrail": (
                "generic_concept_record_no_publication_customer_answer_"
                "entitlement_recommendation_or_claim_decision"
            ),
        }
        cls.validate_record(record)
        identity = {
            k: record[k]
            for k in (
                "record_type", "schema_version", "concept_id", "concept_scope",
                "domain", "definition", "plain_language_explanation",
                "practical_implication", "simple_example",
                "common_misunderstandings", "limitations",
                "product_specific_boundary", "customer_document_boundary",
                "related_concepts", "source_evidence", "review_decision",
                "knowledge_version",
            )
        }
        record["record_id"] = "gconcept_" + cls._stable_hash(identity, 20)
        return record

    @classmethod
    def validate_record(cls, record: Mapping[str, Any]) -> None:
        for field in (
            "concept_id", "concept_name", "domain", "definition",
            "plain_language_explanation", "practical_implication",
            "product_specific_boundary", "customer_document_boundary",
            "knowledge_version", "created_by",
        ):
            cls._require_non_empty(record, field)

        cls._validate_iso8601(record.get("created_at"), "created_at")

        expected_states = {
            "concept_scope": cls.CONCEPT_SCOPE,
            "publication_state": cls.PUBLICATION_STATE,
            "customer_answer_state": cls.CUSTOMER_ANSWER_STATE,
            "entitlement_state": cls.ENTITLEMENT_STATE,
            "recommendation_state": cls.RECOMMENDATION_STATE,
        }
        for field, expected in expected_states.items():
            if record.get(field) != expected:
                raise GenericConceptValidationError(f"{field} must be {expected!r}")

        if not isinstance(record.get("simple_example"), Mapping) or not record["simple_example"]:
            raise GenericConceptValidationError("simple_example must be a non-empty object")

        cls._require_non_empty_list(record, "common_misunderstandings")
        cls._require_non_empty_list(record, "limitations")

        evidence = record.get("source_evidence")
        if not isinstance(evidence, list) or not evidence:
            raise GenericConceptValidationError(
                "at least one authoritative source_evidence item is required"
            )
        for index, item in enumerate(evidence):
            cls._validate_evidence(item, index)

        cls._validate_review_decision(record.get("review_decision"))
        cls._validate_factory_signature(record.get("factory_signature"))
        cls._reject_forbidden_structured_context(record)

    @classmethod
    def _validate_evidence(cls, item: Any, index: int) -> None:
        if not isinstance(item, Mapping):
            raise GenericConceptValidationError(f"source_evidence[{index}] must be an object")

        for field in (
            "evidence_id", "source_type", "source_title", "publisher",
            "source_locator", "source_sha256", "evidence_text",
        ):
            cls._require_non_empty(item, field, prefix=f"source_evidence[{index}].")

        source_type = item["source_type"]
        if source_type not in cls.ALLOWED_SOURCE_TYPES:
            raise GenericConceptValidationError(
                f"source_evidence[{index}].source_type is not authoritative"
            )

        if not cls.SHA256_RE.fullmatch(str(item["source_sha256"]).lower()):
            raise GenericConceptValidationError(
                f"source_evidence[{index}].source_sha256 must be a 64-character SHA-256"
            )

        if source_type in {
            "insurer_policy_wording_standard_definition",
            "insurer_policy_wording_generic_mechanism",
        }:
            required = {
                "hosting_document_scope": "product_specific",
                "extracted_content_scope": cls.CONCEPT_SCOPE,
                "product_context_excluded": True,
            }
            for field, expected in required.items():
                if item.get(field) != expected:
                    raise GenericConceptValidationError(
                        f"source_evidence[{index}].{field} must be {expected!r}"
                    )

            cls._require_non_empty(
                item,
                "source_document_path",
                prefix=f"source_evidence[{index}].",
            )
            source_document_path = str(item["source_document_path"]).replace("\\", "/")
            if Path(source_document_path).is_absolute() or ":" in source_document_path.split("/")[0]:
                raise GenericConceptValidationError(
                    f"source_evidence[{index}].source_document_path must be repository-relative"
                )
        else:
            if item.get("evidence_scope") != cls.CONCEPT_SCOPE:
                raise GenericConceptValidationError(
                    f"source_evidence[{index}].evidence_scope must be {cls.CONCEPT_SCOPE!r}"
                )

    @classmethod
    def _validate_review_decision(cls, decision: Any) -> None:
        if not isinstance(decision, Mapping):
            raise GenericConceptValidationError("review_decision must be an object")
        for field in (
            "review_decision_id", "decision", "reviewer_identity",
            "reviewed_at", "rationale",
        ):
            cls._require_non_empty(decision, field, prefix="review_decision.")
        if decision["decision"] != cls.APPROVED_REVIEW_DECISION:
            raise GenericConceptValidationError(
                "review_decision is not approved for governed generic concept creation"
            )
        cls._validate_iso8601(decision["reviewed_at"], "review_decision.reviewed_at")

    @classmethod
    def _validate_factory_signature(cls, signature: Any) -> None:
        if not isinstance(signature, Mapping):
            raise GenericConceptValidationError("factory_signature must be an object")
        for field in ("factory", "engine_version", "rules_version", "schema_version"):
            cls._require_non_empty(signature, field, prefix="factory_signature.")
        if signature.get("deterministic") is not True:
            raise GenericConceptValidationError(
                "factory_signature.deterministic must be true"
            )

    @classmethod
    def _reject_forbidden_structured_context(cls, value: Any, path: str = "$") -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key).strip().lower() in cls.FORBIDDEN_STRUCTURED_KEYS:
                    raise GenericConceptValidationError(
                        f"product/customer-specific field is forbidden at {path}.{key}"
                    )
                cls._reject_forbidden_structured_context(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                cls._reject_forbidden_structured_context(child, f"{path}[{index}]")

    @staticmethod
    def _require_non_empty(mapping: Mapping[str, Any], field: str, prefix: str = "") -> None:
        value = mapping.get(field)
        if value is None or not str(value).strip():
            raise GenericConceptValidationError(f"{prefix}{field} is required")

    @staticmethod
    def _require_non_empty_list(mapping: Mapping[str, Any], field: str) -> None:
        value = mapping.get(field)
        if not isinstance(value, list) or not value:
            raise GenericConceptValidationError(f"{field} must be a non-empty list")
        if any(not str(x).strip() for x in value):
            raise GenericConceptValidationError(f"{field} cannot contain blank values")

    @staticmethod
    def _validate_iso8601(value: Any, field: str) -> None:
        if value is None or not str(value).strip():
            raise GenericConceptValidationError(f"{field} is required")
        text = str(value).strip()
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise GenericConceptValidationError(
                f"{field} must be an ISO-8601 timestamp"
            ) from exc

    @staticmethod
    def _stable_hash(payload: Any, length: int) -> str:
        raw = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:length]


