"""Governed match between a customer-document fact and a certified Understanding Asset."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


class ConceptUnderstandingMatchError(ValueError):
    """Raised when a customer fact or Understanding Asset violates the match contract."""


class ConceptUnderstandingMatcher:
    VERSION = "1.0"
    SCHEMA_VERSION = "1.0"
    RECORD_TYPE = "health_customer_fact_understanding_match_v1"

    MATCHED = "matched"
    NOT_MATCHABLE = "not_matchable"
    ASSET_NOT_FOUND = "asset_not_found"
    CONCEPT_MISMATCH = "concept_mismatch"
    ALLOWED_STATUSES = {
        MATCHED,
        NOT_MATCHABLE,
        ASSET_NOT_FOUND,
        CONCEPT_MISMATCH,
    }

    def match_from_path(
        self,
        *,
        customer_fact: Mapping[str, Any],
        understanding_asset_path: str | Path,
    ) -> dict[str, Any]:
        path = Path(understanding_asset_path)
        if not path.is_file():
            return self._build(
                customer_fact=customer_fact,
                understanding_asset=None,
                understanding_asset_path=str(path),
                status=self.ASSET_NOT_FOUND,
                status_reason="understanding_asset_file_not_found",
            )

        asset = json.loads(path.read_text(encoding="utf-8"))
        return self.match(
            customer_fact=customer_fact,
            understanding_asset=asset,
            understanding_asset_path=str(path),
        )

    def match(
        self,
        *,
        customer_fact: Mapping[str, Any],
        understanding_asset: Mapping[str, Any],
        understanding_asset_path: str | None = None,
    ) -> dict[str, Any]:
        self._validate_customer_fact_envelope(customer_fact)
        self._validate_understanding_asset_envelope(understanding_asset)

        if (
            customer_fact.get("status") != "extracted"
            or customer_fact.get("fact_scope") != "customer_specific"
        ):
            return self._build(
                customer_fact=customer_fact,
                understanding_asset=understanding_asset,
                understanding_asset_path=understanding_asset_path,
                status=self.NOT_MATCHABLE,
                status_reason="customer_fact_is_not_extracted_customer_specific_fact",
            )

        if customer_fact.get("concept_id") != understanding_asset.get("concept_id"):
            return self._build(
                customer_fact=customer_fact,
                understanding_asset=understanding_asset,
                understanding_asset_path=understanding_asset_path,
                status=self.CONCEPT_MISMATCH,
                status_reason="customer_fact_concept_does_not_match_understanding_asset",
            )

        if understanding_asset.get("status") != "certified_candidate":
            return self._build(
                customer_fact=customer_fact,
                understanding_asset=understanding_asset,
                understanding_asset_path=understanding_asset_path,
                status=self.NOT_MATCHABLE,
                status_reason="understanding_asset_is_not_certified_candidate",
            )

        return self._build(
            customer_fact=customer_fact,
            understanding_asset=understanding_asset,
            understanding_asset_path=understanding_asset_path,
            status=self.MATCHED,
            status_reason="customer_fact_concept_matches_certified_understanding_asset",
        )

    def _build(
        self,
        *,
        customer_fact: Mapping[str, Any],
        understanding_asset: Mapping[str, Any] | None,
        understanding_asset_path: str | None,
        status: str,
        status_reason: str,
    ) -> dict[str, Any]:
        self._validate_customer_fact_envelope(customer_fact)
        if status not in self.ALLOWED_STATUSES:
            raise ConceptUnderstandingMatchError("unsupported match status")

        traceability = (
            self._understanding_traceability(understanding_asset)
            if understanding_asset is not None
            else None
        )

        record = {
            "schema_version": self.SCHEMA_VERSION,
            "record_type": self.RECORD_TYPE,
            "contract_version": self.VERSION,
            "match_id": self._match_id(
                customer_fact_id=str(customer_fact["fact_id"]),
                status=status,
                understanding_asset_id=(
                    str(understanding_asset.get("asset_id"))
                    if understanding_asset is not None
                    else None
                ),
            ),
            "status": status,
            "status_reason": status_reason,
            "concept_id": customer_fact.get("concept_id"),
            "customer_fact": {
                "fact_id": customer_fact["fact_id"],
                "fact_scope": customer_fact["fact_scope"],
                "field_key": customer_fact["field_key"],
                "status": customer_fact["status"],
                "normalized_value": customer_fact.get("normalized_value"),
                "source_document_id": customer_fact["source"]["source_document_id"],
                "source_sha256": customer_fact["source"]["sha256"],
            },
            "understanding_asset": (
                {
                    "asset_id": understanding_asset.get("asset_id"),
                    "asset_type": understanding_asset.get("asset_type"),
                    "status": understanding_asset.get("status"),
                    "concept_id": understanding_asset.get("concept_id"),
                    "path": understanding_asset_path,
                    "traceability": traceability,
                }
                if understanding_asset is not None
                else None
            ),
            "publication_state": "not_published",
            "customer_answer_state": "not_created",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
            "guardrails": [
                "match_artifact_not_customer_answer",
                "match_artifact_not_entitlement_decision",
                "match_artifact_not_recommendation",
                "generic_and_customer_scope_remain_separate",
            ],
        }
        self.validate(record)
        return record

    @classmethod
    def validate(cls, record: Mapping[str, Any]) -> None:
        if not isinstance(record, Mapping):
            raise ConceptUnderstandingMatchError("match record must be an object")
        if record.get("schema_version") != cls.SCHEMA_VERSION:
            raise ConceptUnderstandingMatchError("schema_version must be 1.0")
        if record.get("record_type") != cls.RECORD_TYPE:
            raise ConceptUnderstandingMatchError("unsupported record_type")
        if record.get("contract_version") != cls.VERSION:
            raise ConceptUnderstandingMatchError("unsupported contract_version")
        match_id = record.get("match_id")
        if not isinstance(match_id, str) or not match_id.startswith("cumatch_"):
            raise ConceptUnderstandingMatchError("match_id must start with cumatch_")
        if record.get("status") not in cls.ALLOWED_STATUSES:
            raise ConceptUnderstandingMatchError("unsupported status")
        if not isinstance(record.get("status_reason"), str) or not record["status_reason"].strip():
            raise ConceptUnderstandingMatchError("status_reason must be non-empty")
        if record.get("concept_id") != "deductible":
            raise ConceptUnderstandingMatchError("concept_id must be deductible")

        customer_fact = record.get("customer_fact")
        if not isinstance(customer_fact, Mapping):
            raise ConceptUnderstandingMatchError("customer_fact must be an object")
        if customer_fact.get("fact_scope") != "customer_specific":
            raise ConceptUnderstandingMatchError("customer_fact.fact_scope must be customer_specific")
        if not isinstance(customer_fact.get("fact_id"), str) or not customer_fact["fact_id"].startswith("cdfact_"):
            raise ConceptUnderstandingMatchError("customer_fact.fact_id must start with cdfact_")
        if not isinstance(customer_fact.get("source_sha256"), str) or len(customer_fact["source_sha256"]) != 64:
            raise ConceptUnderstandingMatchError("customer_fact.source_sha256 must be SHA-256")

        status = record["status"]
        asset = record.get("understanding_asset")
        if status == cls.ASSET_NOT_FOUND:
            if asset is not None:
                raise ConceptUnderstandingMatchError("asset_not_found must not include understanding_asset")
        else:
            if not isinstance(asset, Mapping):
                raise ConceptUnderstandingMatchError("understanding_asset must be present")
            if not isinstance(asset.get("asset_id"), str) or not asset["asset_id"].startswith("ua_"):
                raise ConceptUnderstandingMatchError("understanding_asset.asset_id must start with ua_")
            if asset.get("asset_type") != "understanding_asset":
                raise ConceptUnderstandingMatchError("understanding_asset.asset_type mismatch")

        if status == cls.MATCHED:
            if customer_fact.get("status") != "extracted":
                raise ConceptUnderstandingMatchError("matched record requires extracted customer fact")
            if asset.get("concept_id") != record.get("concept_id"):
                raise ConceptUnderstandingMatchError("matched record requires concept equality")
            if asset.get("status") != "certified_candidate":
                raise ConceptUnderstandingMatchError("matched record requires certified_candidate asset")
            traceability = asset.get("traceability")
            if not isinstance(traceability, Mapping):
                raise ConceptUnderstandingMatchError("matched record requires traceability")
            for key in (
                "meaning_asset_id",
                "learning_primitive_collection_id",
                "learning_path_collection_id",
                "source_evidence_refs",
            ):
                if key not in traceability:
                    raise ConceptUnderstandingMatchError(
                        f"matched traceability missing {key}"
                    )

        required_states = {
            "publication_state": "not_published",
            "customer_answer_state": "not_created",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }
        for key, expected in required_states.items():
            if record.get(key) != expected:
                raise ConceptUnderstandingMatchError(f"{key} must be {expected}")

    @staticmethod
    def _validate_customer_fact_envelope(customer_fact: Mapping[str, Any]) -> None:
        if not isinstance(customer_fact, Mapping):
            raise ConceptUnderstandingMatchError("customer_fact must be an object")
        if customer_fact.get("record_type") != "health_customer_document_fact_v1":
            raise ConceptUnderstandingMatchError("unsupported customer fact record_type")
        if customer_fact.get("concept_id") != "deductible":
            raise ConceptUnderstandingMatchError("customer fact concept_id must be deductible")
        if not isinstance(customer_fact.get("fact_id"), str) or not customer_fact["fact_id"].startswith("cdfact_"):
            raise ConceptUnderstandingMatchError("customer fact fact_id must start with cdfact_")
        source = customer_fact.get("source")
        if not isinstance(source, Mapping):
            raise ConceptUnderstandingMatchError("customer fact source must be an object")
        sha = source.get("sha256")
        if not isinstance(sha, str) or len(sha) != 64:
            raise ConceptUnderstandingMatchError("customer fact source sha256 must be valid")

    @staticmethod
    def _validate_understanding_asset_envelope(asset: Mapping[str, Any]) -> None:
        if not isinstance(asset, Mapping):
            raise ConceptUnderstandingMatchError("understanding_asset must be an object")
        if asset.get("asset_type") != "understanding_asset":
            raise ConceptUnderstandingMatchError("asset_type must be understanding_asset")
        if not isinstance(asset.get("asset_id"), str) or not asset["asset_id"].startswith("ua_"):
            raise ConceptUnderstandingMatchError("asset_id must start with ua_")
        if not isinstance(asset.get("concept_id"), str) or not asset["concept_id"].strip():
            raise ConceptUnderstandingMatchError("understanding asset concept_id required")

    @staticmethod
    def _understanding_traceability(asset: Mapping[str, Any]) -> dict[str, Any]:
        trace = asset.get("traceability")
        if not isinstance(trace, Mapping):
            return {}
        return {
            "meaning_asset_id": trace.get("meaning_asset_id"),
            "learning_primitive_collection_id": trace.get("learning_primitive_collection_id"),
            "learning_path_collection_id": trace.get("learning_path_collection_id"),
            "source_evidence_refs": list(trace.get("source_evidence_refs") or []),
        }

    @staticmethod
    def _match_id(
        *,
        customer_fact_id: str,
        status: str,
        understanding_asset_id: str | None,
    ) -> str:
        material = {
            "customer_fact_id": customer_fact_id,
            "status": status,
            "understanding_asset_id": understanding_asset_id,
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:20]
        return f"cumatch_{digest}"
