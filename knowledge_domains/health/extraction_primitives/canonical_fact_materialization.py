"""Immutable, non-publishing canonical-fact materialization.

This module is downstream of governed fact selection and remains upstream of
publication, entitlement, currentness, conflict resolution, and any
customer-facing response.  It writes a portable canonical-fact *artifact*;
it does not mutate an operational fact store.

Materialization supports only canonical fields explicitly selected by the
approved Health Field Registry policy. Any non-selected input record remains
accounted for as deferred or blocked input and never becomes a canonical fact.
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Mapping

from knowledge_domains.health.field_registry.selection_policy import HealthFieldSelectionPolicy

from knowledge_domains.health.extraction_primitives.governed_fact_selection import (
    GovernedFactSelectionContract,
    GovernedFactSelectionError,
)


class CanonicalFactMaterializationError(ValueError):
    """Raised when a selection artifact cannot safely materialize facts."""


class CanonicalFactMaterializationContract:
    VERSION = "1.0"
    DOCUMENT_TYPE = "health_canonical_fact_materialization_document_v1"
    STATUS = "materialized_not_published"
    FACT_STATUS = "materialized_not_published"
    NON_PUBLICATION_GUARDRAIL = "canonical_fact_materialized_not_published"
    SELECTED = GovernedFactSelectionContract.SELECTED
    DEFERRED = GovernedFactSelectionContract.DEFERRED
    BLOCKED = GovernedFactSelectionContract.BLOCKED
    SUPPORTED_FIELD_KEYS = {"currency_sub_limit"}

    @classmethod
    def build_materialization_document(
        cls,
        selection_document: Mapping[str, Any],
        *,
        materialized_by: str,
        materialized_at: str,
    ) -> dict[str, Any]:
        """Materialize selected facts while preserving all non-selected input.

        This is intentionally a write-once artifact contract.  The caller is
        responsible for refusing to overwrite an output path.  No fact in the
        output is published or entitlement-ready.
        """
        try:
            GovernedFactSelectionContract.validate_selection_document(selection_document)
        except GovernedFactSelectionError as exc:
            raise CanonicalFactMaterializationError(str(exc)) from exc

        cls._require_non_empty("materialized_by", materialized_by)
        cls._validate_iso_timestamp(materialized_at, field_name="materialized_at")

        source = dict(selection_document["source"])
        selection_input = dict(selection_document["input"])
        selected_records = [
            record for record in selection_document["selection_records"]
            if record["selection_status"] == cls.SELECTED
        ]
        if not selected_records:
            raise CanonicalFactMaterializationError("selection document contains no selected_governed_fact records")

        facts = [
            cls._materialize_fact(record, source=source, selection_input=selection_input)
            for record in selected_records
        ]
        cls._assert_unique_fact_keys(facts)

        non_materialized = [
            cls._non_materialized_record(record)
            for record in selection_document["selection_records"]
            if record["selection_status"] != cls.SELECTED
        ]

        output = {
            "schema_version": "1.0",
            "materialization_document_type": cls.DOCUMENT_TYPE,
            "materialization_contract_version": cls.VERSION,
            "status": cls.STATUS,
            "source": source,
            "input": {
                "selection_document_type": selection_document["selection_document_type"],
                "selection_contract_version": selection_document["selection_contract_version"],
                "source_submission_id": selection_input["submission_id"],
                "selector_identity": selection_document["selector_identity"],
                "selected_at": selection_document["selected_at"],
                "selection_record_count": selection_document["selection_record_count"],
            },
            "materialized_by": materialized_by,
            "materialized_at": materialized_at,
            "materialization_id": cls._materialization_id(
                source_sha256=source["sha256"],
                materialized_by=materialized_by,
                materialized_at=materialized_at,
                fact_ids=[fact["canonical_fact_id"] for fact in facts],
            ),
            "canonical_fact_count": len(facts),
            "canonical_facts": facts,
            "non_materialized_selection_record_count": len(non_materialized),
            "non_materialized_selection_records": non_materialized,
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "non_publication_guardrail": cls.NON_PUBLICATION_GUARDRAIL,
            "limitations": [
                "This is an immutable canonical-fact materialization artifact, not a customer-facing publication or operational fact-store mutation.",
                "Every canonical fact remains bound to the selected record, immutable review submission, reviewer snapshot, and exact source SHA-256.",
                "Materialization does not establish currentness, resolve cross-document conflicts, decide policy applicability beyond the reviewed scope, or interpret legal entitlement.",
                "Non-selected records remain explicitly non-materialized and cannot become facts through this contract.",
            ],
        }
        cls.validate_materialization_document(output)
        return output

    @classmethod
    def validate_materialization_document(cls, document: Mapping[str, Any]) -> None:
        if not isinstance(document, Mapping):
            raise CanonicalFactMaterializationError("materialization document must be an object")
        if document.get("materialization_document_type") != cls.DOCUMENT_TYPE:
            raise CanonicalFactMaterializationError("unsupported materialization_document_type")
        if document.get("materialization_contract_version") != cls.VERSION:
            raise CanonicalFactMaterializationError("unsupported materialization_contract_version")
        if document.get("status") != cls.STATUS:
            raise CanonicalFactMaterializationError("materialization status must be materialized_not_published")
        if document.get("publication_state") != "not_published":
            raise CanonicalFactMaterializationError("materialization document must remain not_published")
        if document.get("entitlement_state") != "not_evaluated":
            raise CanonicalFactMaterializationError("materialization document must remain not_evaluated")
        if document.get("non_publication_guardrail") != cls.NON_PUBLICATION_GUARDRAIL:
            raise CanonicalFactMaterializationError("materialization document must block publication")

        source = document.get("source")
        if not isinstance(source, Mapping):
            raise CanonicalFactMaterializationError("source must be an object")
        cls._validate_source(source)

        inp = document.get("input")
        if not isinstance(inp, Mapping):
            raise CanonicalFactMaterializationError("input must be an object")
        if inp.get("selection_document_type") != GovernedFactSelectionContract.DOCUMENT_TYPE:
            raise CanonicalFactMaterializationError("input must reference governed fact selection v1")
        if inp.get("selection_contract_version") != GovernedFactSelectionContract.VERSION:
            raise CanonicalFactMaterializationError("input selection contract version mismatch")
        cls._require_prefixed_id("input.source_submission_id", inp.get("source_submission_id"), "rsub_")
        cls._require_non_empty("input.selector_identity", inp.get("selector_identity"))
        cls._validate_iso_timestamp(inp.get("selected_at"), field_name="input.selected_at")
        if not isinstance(inp.get("selection_record_count"), int) or inp["selection_record_count"] < 1:
            raise CanonicalFactMaterializationError("input.selection_record_count must be a positive integer")

        cls._require_non_empty("materialized_by", document.get("materialized_by"))
        cls._validate_iso_timestamp(document.get("materialized_at"), field_name="materialized_at")
        cls._require_prefixed_id("materialization_id", document.get("materialization_id"), "fmat_")

        facts = document.get("canonical_facts")
        if not isinstance(facts, list) or not facts:
            raise CanonicalFactMaterializationError("canonical_facts must be a non-empty list")
        if document.get("canonical_fact_count") != len(facts):
            raise CanonicalFactMaterializationError("canonical_fact_count must equal canonical_facts length")
        cls._assert_unique_fact_keys(facts)
        seen_ids: set[str] = set()
        for fact in facts:
            cls._validate_fact(fact, source=source, inp=inp)
            fact_id = fact["canonical_fact_id"]
            if fact_id in seen_ids:
                raise CanonicalFactMaterializationError("duplicate canonical_fact_id")
            seen_ids.add(fact_id)

        non_materialized = document.get("non_materialized_selection_records")
        if not isinstance(non_materialized, list):
            raise CanonicalFactMaterializationError("non_materialized_selection_records must be a list")
        if document.get("non_materialized_selection_record_count") != len(non_materialized):
            raise CanonicalFactMaterializationError(
                "non_materialized_selection_record_count must equal non_materialized_selection_records length"
            )
        for record in non_materialized:
            cls._validate_non_materialized_record(record, source=source, inp=inp)

        if len(facts) + len(non_materialized) != inp["selection_record_count"]:
            raise CanonicalFactMaterializationError(
                "canonical and non-materialized record counts must account for all selection records"
            )

    @classmethod
    def _materialize_fact(
        cls,
        record: Mapping[str, Any],
        *,
        source: Mapping[str, Any],
        selection_input: Mapping[str, Any],
    ) -> dict[str, Any]:
        cls._validate_selected_record_for_materialization(record, source=source, selection_input=selection_input)
        field_key = record["canonical_field_key"]
        canonical_fact_id = cls._canonical_fact_id(
            source_sha256=source["sha256"],
            selection_record_id=record["selection_record_id"],
            field_key=field_key,
        )
        return {
            "canonical_fact_id": canonical_fact_id,
            "governed_fact_id": record["governed_fact_id"],
            "entity_id": source["entity_id"],
            "canonical_field_key": field_key,
            "normalized_value": dict(record["normalized_value"]),
            "benefit_scope": record["selected_benefit_scope"],
            "applicability": {
                "sum_insured_band_scope": record.get("selected_band_scope"),
            },
            "source_document": {
                "source_document_id": source["source_document_id"],
                "sha256": source["sha256"],
                "document_type": source["document_type"],
                "source_url": source.get("source_url"),
                "source_page_url": source.get("source_page_url"),
                "relative_archive_path": source.get("relative_archive_path"),
                "provenance_status": source.get("provenance_status"),
            },
            "review_lineage": {
                "source_submission_id": record["source_submission_id"],
                "source_immutable_record_id": record["source_immutable_record_id"],
                "source_decision_record_id": record["source_decision_record_id"],
                "review_snapshot_fingerprint": record["review_snapshot_fingerprint"],
                "review_decision": record["review_decision"],
                "selection_record_id": record["selection_record_id"],
            },
            "materialization_status": cls.FACT_STATUS,
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "non_publication_guardrail": cls.NON_PUBLICATION_GUARDRAIL,
        }

    @classmethod
    def _non_materialized_record(cls, record: Mapping[str, Any]) -> dict[str, Any]:
        status = record.get("selection_status")
        if status not in {cls.DEFERRED, cls.BLOCKED}:
            raise CanonicalFactMaterializationError("non-selected input must be deferred or blocked")
        return {
            "selection_record_id": record["selection_record_id"],
            "source_submission_id": record["source_submission_id"],
            "source_immutable_record_id": record["source_immutable_record_id"],
            "source_decision_record_id": record["source_decision_record_id"],
            "source_sha256": record["source_sha256"],
            "selection_status": status,
            # Preserve the reviewed selection semantics even when the record is
            # deliberately not materialized as a canonical fact.  These fields
            # are evidence lineage, not a publication or entitlement claim.
            "normalized_value": dict(record.get("normalized_value", {})),
            "selected_role": record.get("selected_role"),
            "selected_benefit_scope": record.get("selected_benefit_scope"),
            "selected_band_scope": record.get("selected_band_scope"),
            "non_materialization_reason": record["selection_reason"],
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
        }

    @classmethod
    def _validate_selected_record_for_materialization(
        cls,
        record: Mapping[str, Any],
        *,
        source: Mapping[str, Any],
        selection_input: Mapping[str, Any],
    ) -> None:
        if record.get("selection_status") != cls.SELECTED:
            raise CanonicalFactMaterializationError("only selected_governed_fact records may materialize")
        if record.get("review_decision") != "accept":
            raise CanonicalFactMaterializationError("selected record must have accepted review decision")
        if record.get("source_sha256") != source.get("sha256"):
            raise CanonicalFactMaterializationError("selected record source SHA-256 must match materialization source")
        if record.get("source_submission_id") != selection_input.get("submission_id"):
            raise CanonicalFactMaterializationError("selected record submission lineage must match selection input")
        cls._require_prefixed_id("selection_record_id", record.get("selection_record_id"), "fsel_")
        cls._require_prefixed_id("source_immutable_record_id", record.get("source_immutable_record_id"), "rsubrec_")
        cls._require_prefixed_id("source_decision_record_id", record.get("source_decision_record_id"), "rdec_")
        cls._require_prefixed_id("governed_fact_id", record.get("governed_fact_id"), "gfact_")
        if record.get("canonical_field_key") not in HealthFieldSelectionPolicy.supported_field_keys():
            raise CanonicalFactMaterializationError("selected record has unsupported canonical_field_key")
        cls._validate_currency(record.get("normalized_value"))
        scope_error = HealthFieldSelectionPolicy.validate_selection_scope(
            field_key=record.get("canonical_field_key"),
            benefit_scope=record.get("selected_benefit_scope"),
            band_scope=record.get("selected_band_scope"),
        )
        if scope_error:
            raise CanonicalFactMaterializationError(scope_error)
        fingerprint = record.get("review_snapshot_fingerprint")
        if not cls._valid_sha(fingerprint):
            raise CanonicalFactMaterializationError("review_snapshot_fingerprint must be a valid SHA-256")
        if record.get("publication_state") != "not_published" or record.get("entitlement_state") != "not_evaluated":
            raise CanonicalFactMaterializationError("selected record must remain not_published and not_evaluated")

    @classmethod
    def _validate_fact(cls, fact: Mapping[str, Any], *, source: Mapping[str, Any], inp: Mapping[str, Any]) -> None:
        if not isinstance(fact, Mapping):
            raise CanonicalFactMaterializationError("canonical fact must be an object")
        cls._require_prefixed_id("canonical_fact_id", fact.get("canonical_fact_id"), "cfact_")
        cls._require_prefixed_id("governed_fact_id", fact.get("governed_fact_id"), "gfact_")
        if fact.get("entity_id") != source["entity_id"]:
            raise CanonicalFactMaterializationError("canonical fact entity_id must match source entity_id")
        if fact.get("canonical_field_key") not in HealthFieldSelectionPolicy.supported_field_keys():
            raise CanonicalFactMaterializationError("canonical fact has unsupported canonical_field_key")
        cls._validate_currency(fact.get("normalized_value"))
        applicability = fact.get("applicability")
        if not isinstance(applicability, Mapping) or "sum_insured_band_scope" not in applicability:
            raise CanonicalFactMaterializationError("canonical fact requires applicability.sum_insured_band_scope")
        scope_error = HealthFieldSelectionPolicy.validate_selection_scope(
            field_key=fact.get("canonical_field_key"),
            benefit_scope=fact.get("benefit_scope"),
            band_scope=applicability.get("sum_insured_band_scope"),
        )
        if scope_error:
            raise CanonicalFactMaterializationError(scope_error)
        source_document = fact.get("source_document")
        if not isinstance(source_document, Mapping):
            raise CanonicalFactMaterializationError("canonical fact requires source_document")
        for key in ("source_document_id", "sha256", "document_type"):
            cls._require_non_empty(f"source_document.{key}", source_document.get(key))
        if source_document.get("sha256") != source["sha256"]:
            raise CanonicalFactMaterializationError("canonical fact source_document SHA-256 must match source")
        lineage = fact.get("review_lineage")
        if not isinstance(lineage, Mapping):
            raise CanonicalFactMaterializationError("canonical fact requires review_lineage")
        if lineage.get("source_submission_id") != inp["source_submission_id"]:
            raise CanonicalFactMaterializationError("canonical fact submission lineage must match input")
        for key, prefix in (
            ("source_immutable_record_id", "rsubrec_"),
            ("source_decision_record_id", "rdec_"),
            ("selection_record_id", "fsel_"),
        ):
            cls._require_prefixed_id(f"review_lineage.{key}", lineage.get(key), prefix)
        if lineage.get("review_decision") != "accept":
            raise CanonicalFactMaterializationError("canonical fact must originate from accepted review")
        if not cls._valid_sha(lineage.get("review_snapshot_fingerprint")):
            raise CanonicalFactMaterializationError("canonical fact review snapshot fingerprint must be SHA-256")
        if fact.get("materialization_status") != cls.FACT_STATUS:
            raise CanonicalFactMaterializationError("canonical fact must be materialized_not_published")
        if fact.get("publication_state") != "not_published" or fact.get("entitlement_state") != "not_evaluated":
            raise CanonicalFactMaterializationError("canonical fact must remain not_published and not_evaluated")
        if fact.get("non_publication_guardrail") != cls.NON_PUBLICATION_GUARDRAIL:
            raise CanonicalFactMaterializationError("canonical fact must carry non-publication guardrail")

    @classmethod
    def _validate_non_materialized_record(cls, record: Mapping[str, Any], *, source: Mapping[str, Any], inp: Mapping[str, Any]) -> None:
        if not isinstance(record, Mapping):
            raise CanonicalFactMaterializationError("non-materialized selection record must be an object")
        cls._require_prefixed_id("non_materialized.selection_record_id", record.get("selection_record_id"), "fsel_")
        if record.get("source_submission_id") != inp["source_submission_id"]:
            raise CanonicalFactMaterializationError("non-materialized record submission lineage must match input")
        if record.get("source_sha256") != source["sha256"]:
            raise CanonicalFactMaterializationError("non-materialized record source SHA-256 must match source")
        if record.get("selection_status") not in {cls.DEFERRED, cls.BLOCKED}:
            raise CanonicalFactMaterializationError("non-materialized record must be deferred or blocked")
        cls._require_non_empty("non_materialization_reason", record.get("non_materialization_reason"))
        if record.get("publication_state") != "not_published" or record.get("entitlement_state") != "not_evaluated":
            raise CanonicalFactMaterializationError("non-materialized record must remain not_published and not_evaluated")

    @classmethod
    def _assert_unique_fact_keys(cls, facts: list[Mapping[str, Any]]) -> None:
        seen: set[tuple[Any, ...]] = set()
        for fact in facts:
            field_key = fact.get("canonical_field_key")
            try:
                include_value = HealthFieldSelectionPolicy.canonical_identity_includes_normalized_value(field_key)
            except Exception as exc:
                raise CanonicalFactMaterializationError(
                    "canonical fact has unsupported canonical_field_key"
                ) from exc
            key = (
                field_key,
                fact.get("benefit_scope"),
                cls._band_scope_for_key(fact),
                cls._normalized_currency_value_for_key(fact) if include_value else None,
            )
            if key in seen:
                raise CanonicalFactMaterializationError(
                    "duplicate canonical fact key for field, benefit scope, sum-insured band, and required value identity"
                )
            seen.add(key)

    @staticmethod
    def _normalized_currency_value_for_key(fact: Mapping[str, Any]) -> tuple[Any, Any, Any]:
        value = fact.get("normalized_value")
        if not isinstance(value, Mapping):
            return (None, None, None)
        return (value.get("kind"), value.get("unit"), value.get("value"))

    @staticmethod
    def _band_scope_for_key(fact: Mapping[str, Any]) -> Any:
        applicability = fact.get("applicability")
        if isinstance(applicability, Mapping):
            return applicability.get("sum_insured_band_scope")
        return fact.get("selected_band_scope")

    @staticmethod
    def _validate_currency(value: Any) -> None:
        if not (
            isinstance(value, Mapping)
            and value.get("kind") == "currency"
            and value.get("unit") == "INR"
            and isinstance(value.get("value"), int)
            and value["value"] > 0
        ):
            raise CanonicalFactMaterializationError("normalized_value must be a positive INR currency value")

    @staticmethod
    def _validate_source(source: Mapping[str, Any]) -> None:
        if not CanonicalFactMaterializationContract._valid_sha(source.get("sha256")):
            raise CanonicalFactMaterializationError("source.sha256 must be a valid SHA-256")
        for key in ("entity_id", "insurer_id", "document_type", "source_document_id"):
            CanonicalFactMaterializationContract._require_non_empty(f"source.{key}", source.get(key))

    @staticmethod
    def _canonical_fact_id(*, source_sha256: str, selection_record_id: str, field_key: str) -> str:
        digest = hashlib.sha256(
            f"canonical-fact|{source_sha256}|{selection_record_id}|{field_key}".encode("utf-8")
        ).hexdigest()[:16]
        return f"cfact_{digest}"

    @staticmethod
    def _materialization_id(*, source_sha256: str, materialized_by: str, materialized_at: str, fact_ids: list[str]) -> str:
        payload = "|".join([source_sha256, materialized_by, materialized_at, *sorted(fact_ids)])
        return "fmat_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _valid_sha(value: Any) -> bool:
        return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())

    @staticmethod
    def _require_non_empty(name: str, value: Any) -> None:
        if not isinstance(value, str) or not value.strip():
            raise CanonicalFactMaterializationError(f"{name} must be a non-empty string")

    @staticmethod
    def _require_prefixed_id(name: str, value: Any, prefix: str) -> None:
        if not isinstance(value, str) or not value.startswith(prefix):
            raise CanonicalFactMaterializationError(f"{name} must be a {prefix} identifier")

    @staticmethod
    def _validate_iso_timestamp(value: Any, *, field_name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise CanonicalFactMaterializationError(f"{field_name} must be ISO-8601")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CanonicalFactMaterializationError(f"{field_name} must be ISO-8601") from exc
