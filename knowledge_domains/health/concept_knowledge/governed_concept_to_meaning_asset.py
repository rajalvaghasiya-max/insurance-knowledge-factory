"""Deterministic adapter from a governed generic concept record to Meaning Asset v1.0."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Dict, Mapping

from .governed_generic_concept_record import (
    GovernedGenericConceptRecordContract,
    GenericConceptValidationError,
)


class GovernedConceptToMeaningAssetAdapter:
    """Map approved governed concept knowledge into the existing Meaning Asset contract."""

    ADAPTER_VERSION = "1.0"
    OUTPUT_SCHEMA_VERSION = "meaning_asset_v1.0"

    @classmethod
    def build(cls, record: Mapping[str, Any]) -> Dict[str, Any]:
        GovernedGenericConceptRecordContract.validate_record(record)

        record_id = cls._required_text(record, "record_id")
        concept_id = cls._required_text(record, "concept_id")
        concept_name = cls._required_text(record, "concept_name")

        if record.get("publication_state") != "not_published":
            raise GenericConceptValidationError(
                "meaning asset creation requires publication_state='not_published'"
            )
        if record.get("customer_answer_state") != "not_created":
            raise GenericConceptValidationError(
                "meaning asset creation requires customer_answer_state='not_created'"
            )
        if record.get("recommendation_state") != "not_created":
            raise GenericConceptValidationError(
                "meaning asset creation requires recommendation_state='not_created'"
            )
        if record.get("entitlement_state") != "not_evaluated":
            raise GenericConceptValidationError(
                "meaning asset creation requires entitlement_state='not_evaluated'"
            )

        evidence = deepcopy(list(record.get("source_evidence", [])))
        evidence_refs = [str(item["evidence_id"]) for item in evidence]
        review_decision = deepcopy(dict(record["review_decision"]))

        asset_identity = {
            "adapter_version": cls.ADAPTER_VERSION,
            "output_schema_version": cls.OUTPUT_SCHEMA_VERSION,
            "governed_record_id": record_id,
            "knowledge_version": record.get("knowledge_version"),
            "evidence_refs": evidence_refs,
            "review_decision_id": review_decision.get("review_decision_id"),
        }
        asset_id = f"meaning_{concept_id}_{cls._stable_hash(asset_identity, 16)}"

        related = list(record.get("related_concepts", []))
        profile = cls._meaning_profile(record)

        simple_example = deepcopy(dict(record.get("simple_example", {})))
        policy_examples = cls._build_examples(simple_example)

        meaning_asset: Dict[str, Any] = {
            "asset_id": asset_id,
            "asset_type": "meaning_asset",
            "schema_version": cls.OUTPUT_SCHEMA_VERSION,
            "asset_version": "1.0",
            "concept_id": concept_id,
            "canonical_name": concept_name,
            "aliases": [concept_name],
            "category": profile["category"],
            "core_meaning": record["definition"],
            "business_purpose": record["practical_implication"],
            "functional_behaviour": record["plain_language_explanation"],
            "trigger": profile["trigger"],
            "inputs": list(profile["inputs"]),
            "outputs": list(profile["outputs"]),
            "calculation_basis": profile["calculation_basis"],
            "dependencies": list(profile["dependencies"]),
            "constraints": list(record["limitations"]) + [
                record["product_specific_boundary"],
                record["customer_document_boundary"],
            ],
            "exceptions": list(profile["exceptions"]),
            "relationships": {
                "depends_on": list(profile["depends_on"]),
                "related_to": related,
                "commonly_confused_with": list(profile["commonly_confused_with"]),
            },
            "misinterpretations": [
                {
                    "misinterpretation": text,
                    "actual_meaning": record["definition"],
                }
                for text in record["common_misunderstandings"]
            ],
            "policy_examples": policy_examples,
            "confidence": {
                "canonical_confidence": 1.0,
                "requires_review": False,
                "review_basis": "approved_governed_generic_concept_record",
            },
            "evidence_refs": evidence_refs,
            "evidence": evidence,
            "review_status": "approved_governed_generic_concept",
            "certification": {
                "status": "governed_source_approved",
                "human_reviewed": True,
                "review_decision_id": review_decision["review_decision_id"],
            },
            "governance": {
                "source_governed_record_id": record_id,
                "source_record_type": record["record_type"],
                "source_schema_version": record["schema_version"],
                "source_knowledge_version": record["knowledge_version"],
                "concept_scope": record["concept_scope"],
                "publication_state": record["publication_state"],
                "customer_answer_state": record["customer_answer_state"],
                "entitlement_state": record["entitlement_state"],
                "recommendation_state": record["recommendation_state"],
                "review_decision": review_decision,
                "product_specific_boundary": record["product_specific_boundary"],
                "customer_document_boundary": record["customer_document_boundary"],
            },
            "factory_signature": {
                "factory": "PolicyScna Knowledge Factory",
                "production_line": "GovernedConceptToMeaningAssetAdapter",
                "adapter_version": cls.ADAPTER_VERSION,
                "schema_version": cls.OUTPUT_SCHEMA_VERSION,
                "deterministic": True,
            },
            "notes": [
                "This adapter restructures approved governed concept content.",
                "It does not publish content, create a customer answer, determine "
                "entitlement, or make a recommendation.",
            ],
        }

        cls.validate_output(meaning_asset)
        return meaning_asset

    @classmethod
    def validate_output(cls, asset: Mapping[str, Any]) -> None:
        for field in (
            "asset_id",
            "asset_type",
            "schema_version",
            "concept_id",
            "canonical_name",
            "core_meaning",
            "business_purpose",
            "functional_behaviour",
            "trigger",
            "calculation_basis",
            "review_status",
        ):
            cls._required_text(asset, field)

        if asset["asset_type"] != "meaning_asset":
            raise ValueError("asset_type must be 'meaning_asset'")
        if asset["schema_version"] != cls.OUTPUT_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {cls.OUTPUT_SCHEMA_VERSION!r}"
            )

        governance = asset.get("governance")
        if not isinstance(governance, Mapping):
            raise ValueError("governance must be an object")

        expected = {
            "publication_state": "not_published",
            "customer_answer_state": "not_created",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }
        for field, value in expected.items():
            if governance.get(field) != value:
                raise ValueError(f"governance.{field} must be {value!r}")

        evidence = asset.get("evidence")
        evidence_refs = asset.get("evidence_refs")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("evidence must be a non-empty list")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            raise ValueError("evidence_refs must be a non-empty list")

        expected_refs = [str(item["evidence_id"]) for item in evidence]
        if evidence_refs != expected_refs:
            raise ValueError("evidence_refs must exactly match evidence IDs")

    @classmethod
    def _build_examples(
        cls,
        simple_example: Mapping[str, Any],
    ) -> list[Dict[str, Any]]:
        if not simple_example:
            return []

        example = deepcopy(dict(simple_example))
        scenario = cls._required_text(example, "scenario")
        result = cls._required_text(example, "result")
        boundary = cls._required_text(example, "boundary")

        return [{
            "scenario": scenario,
            "result": f"{result} {boundary}",
            "source_example": example,
        }]

    @staticmethod
    def _meaning_profile(record: Mapping[str, Any]) -> Dict[str, Any]:
        profile = record.get("meaning_profile")
        if not isinstance(profile, Mapping):
            raise GenericConceptValidationError(
                "meaning_profile is required for governed meaning-asset creation"
            )
        GovernedGenericConceptRecordContract._validate_meaning_profile(profile)
        return deepcopy(dict(profile))

    @staticmethod
    def _required_text(mapping: Mapping[str, Any], field: str) -> str:
        value = mapping.get(field)
        if value is None or not str(value).strip():
            raise ValueError(f"{field} is required")
        return str(value).strip()

    @staticmethod
    def _stable_hash(payload: Any, length: int) -> str:
        raw = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:length]
