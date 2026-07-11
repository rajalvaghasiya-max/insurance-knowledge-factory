"""Non-publishing validation and publication-eligibility assessment for canonical facts.

This contract is downstream of immutable canonical-fact materialization.  It
never writes a publication artifact, changes currentness, or makes an
entitlement decision.  Its only purpose is to make validation and temporal
blocking reasons explicit before a separate publication-review workflow.
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Mapping

from knowledge_domains.health.field_registry.selection_policy import HealthFieldSelectionPolicy

from knowledge_domains.health.extraction_primitives.canonical_fact_materialization import (
    CanonicalFactMaterializationContract,
    CanonicalFactMaterializationError,
)


class FactPublicationEligibilityError(ValueError):
    """Raised when materialized facts or identity overlay are unsafe to assess."""


class FactPublicationEligibilityContract:
    VERSION = "1.0"
    DOCUMENT_TYPE = "health_fact_publication_eligibility_document_v1"
    STATUS = "publication_eligibility_assessed_not_published"
    GUARDRAIL = "publication_eligibility_assessment_only_not_published"

    ELIGIBLE = "eligible_for_publication_review"
    BLOCKED = "blocked"
    DEFERRED = "deferred"

    @classmethod
    def build_eligibility_document(
        cls,
        materialization_document: Mapping[str, Any],
        identity_overlay: Mapping[str, Any],
        *,
        validated_by: str,
        validated_at: str,
    ) -> dict[str, Any]:
        try:
            CanonicalFactMaterializationContract.validate_materialization_document(materialization_document)
        except CanonicalFactMaterializationError as exc:
            raise FactPublicationEligibilityError(str(exc)) from exc

        cls._require_non_empty("validated_by", validated_by)
        cls._validate_iso_timestamp(validated_at, field_name="validated_at")
        source = dict(materialization_document["source"])
        overlay = cls._resolve_matching_overlay(identity_overlay, source)
        overlay_summary = cls._overlay_summary(identity_overlay, overlay, source)
        global_currentness_reason = cls._currentness_block_reason(overlay["identity_resolution"])

        records: list[dict[str, Any]] = []
        for fact in materialization_document["canonical_facts"]:
            records.append(cls._fact_record(fact, source, overlay_summary, global_currentness_reason))
        for non_materialized in materialization_document["non_materialized_selection_records"]:
            records.append(cls._deferred_record(non_materialized, source, overlay_summary))

        cls._assert_unique_materialized_fact_keys(records)
        counts = {
            cls.ELIGIBLE: sum(1 for r in records if r["eligibility_status"] == cls.ELIGIBLE),
            cls.BLOCKED: sum(1 for r in records if r["eligibility_status"] == cls.BLOCKED),
            cls.DEFERRED: sum(1 for r in records if r["eligibility_status"] == cls.DEFERRED),
        }

        output = {
            "schema_version": "1.0",
            "eligibility_document_type": cls.DOCUMENT_TYPE,
            "eligibility_contract_version": cls.VERSION,
            "status": cls.STATUS,
            "source": source,
            "input": {
                "materialization_document_type": materialization_document["materialization_document_type"],
                "materialization_contract_version": materialization_document["materialization_contract_version"],
                "materialization_id": materialization_document["materialization_id"],
                "source_submission_id": materialization_document["input"]["source_submission_id"],
                "canonical_fact_count": materialization_document["canonical_fact_count"],
                "non_materialized_selection_record_count": materialization_document["non_materialized_selection_record_count"],
            },
            "identity_overlay": overlay_summary,
            "validated_by": validated_by,
            "validated_at": validated_at,
            "eligibility_assessment_id": cls._assessment_id(
                source_sha256=source["sha256"],
                materialization_id=materialization_document["materialization_id"],
                validated_by=validated_by,
                validated_at=validated_at,
                record_ids=[record["eligibility_record_id"] for record in records],
            ),
            "eligibility_record_count": len(records),
            "eligibility_records": records,
            "eligible_for_publication_review_count": counts[cls.ELIGIBLE],
            "blocked_count": counts[cls.BLOCKED],
            "deferred_count": counts[cls.DEFERRED],
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "non_publication_guardrail": cls.GUARDRAIL,
            "limitations": [
                "This artifact assesses validation and publication-review eligibility only; it does not publish facts or write an operational fact store.",
                "Eligibility for publication review is not customer-facing publication, a current-entitlement conclusion, or legal interpretation.",
                "Temporal identity status is consumed conservatively: compatibility-unverified, historical, replaced, failed, unknown, or missing temporal evidence blocks publication-review eligibility.",
                "Cross-document conflict resolution, policy applicability beyond reviewed scope, and entitlement calculation remain outside this gate.",
            ],
        }
        cls.validate_eligibility_document(output)
        return output

    @classmethod
    def validate_eligibility_document(cls, document: Mapping[str, Any]) -> None:
        if not isinstance(document, Mapping):
            raise FactPublicationEligibilityError("eligibility document must be an object")
        if document.get("eligibility_document_type") != cls.DOCUMENT_TYPE:
            raise FactPublicationEligibilityError("unsupported eligibility_document_type")
        if document.get("eligibility_contract_version") != cls.VERSION:
            raise FactPublicationEligibilityError("unsupported eligibility_contract_version")
        if document.get("status") != cls.STATUS:
            raise FactPublicationEligibilityError("eligibility status must be publication_eligibility_assessed_not_published")
        if document.get("publication_state") != "not_published":
            raise FactPublicationEligibilityError("eligibility document must remain not_published")
        if document.get("entitlement_state") != "not_evaluated":
            raise FactPublicationEligibilityError("eligibility document must remain not_evaluated")
        if document.get("non_publication_guardrail") != cls.GUARDRAIL:
            raise FactPublicationEligibilityError("eligibility document must carry non-publication guardrail")

        source = document.get("source")
        if not isinstance(source, Mapping):
            raise FactPublicationEligibilityError("source must be an object")
        cls._validate_source(source)
        inp = document.get("input")
        if not isinstance(inp, Mapping):
            raise FactPublicationEligibilityError("input must be an object")
        if inp.get("materialization_document_type") != CanonicalFactMaterializationContract.DOCUMENT_TYPE:
            raise FactPublicationEligibilityError("input must reference canonical fact materialization v1")
        if inp.get("materialization_contract_version") != CanonicalFactMaterializationContract.VERSION:
            raise FactPublicationEligibilityError("input materialization contract version mismatch")
        cls._require_prefixed_id("input.materialization_id", inp.get("materialization_id"), "fmat_")
        cls._require_prefixed_id("input.source_submission_id", inp.get("source_submission_id"), "rsub_")

        overlay = document.get("identity_overlay")
        if not isinstance(overlay, Mapping):
            raise FactPublicationEligibilityError("identity_overlay must be an object")
        cls._validate_overlay_summary(overlay, source)
        cls._require_non_empty("validated_by", document.get("validated_by"))
        cls._validate_iso_timestamp(document.get("validated_at"), field_name="validated_at")
        cls._require_prefixed_id("eligibility_assessment_id", document.get("eligibility_assessment_id"), "felig_")

        records = document.get("eligibility_records")
        if not isinstance(records, list) or not records:
            raise FactPublicationEligibilityError("eligibility_records must be a non-empty list")
        if document.get("eligibility_record_count") != len(records):
            raise FactPublicationEligibilityError("eligibility_record_count must equal eligibility_records length")
        cls._assert_unique_materialized_fact_keys(records)
        seen: set[str] = set()
        for record in records:
            cls._validate_record(record, source=source, inp=inp, overlay=overlay)
            record_id = record["eligibility_record_id"]
            if record_id in seen:
                raise FactPublicationEligibilityError("duplicate eligibility_record_id")
            seen.add(record_id)

        actual = {
            cls.ELIGIBLE: sum(1 for r in records if r["eligibility_status"] == cls.ELIGIBLE),
            cls.BLOCKED: sum(1 for r in records if r["eligibility_status"] == cls.BLOCKED),
            cls.DEFERRED: sum(1 for r in records if r["eligibility_status"] == cls.DEFERRED),
        }
        if document.get("eligible_for_publication_review_count") != actual[cls.ELIGIBLE]:
            raise FactPublicationEligibilityError("eligible_for_publication_review_count mismatch")
        if document.get("blocked_count") != actual[cls.BLOCKED]:
            raise FactPublicationEligibilityError("blocked_count mismatch")
        if document.get("deferred_count") != actual[cls.DEFERRED]:
            raise FactPublicationEligibilityError("deferred_count mismatch")

    @classmethod
    def _resolve_matching_overlay(cls, overlay_document: Mapping[str, Any], source: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(overlay_document, Mapping):
            raise FactPublicationEligibilityError("identity overlay must be an object")
        if overlay_document.get("overlay_type") != "document_identity_resolution_overlay_v1":
            raise FactPublicationEligibilityError("unsupported identity overlay type")
        product = overlay_document.get("product_identity_reference")
        if not isinstance(product, Mapping) or product.get("entity_id") != source.get("entity_id"):
            raise FactPublicationEligibilityError("identity overlay entity_id must match materialized source")
        matches = []
        for item in overlay_document.get("documents", []):
            if not isinstance(item, Mapping):
                continue
            link = item.get("document_version_link")
            if isinstance(link, Mapping) and link.get("content_sha256") == source.get("sha256") and link.get("document_type") == source.get("document_type"):
                matches.append(item)
        if len(matches) != 1:
            raise FactPublicationEligibilityError("identity overlay must contain exactly one matching document hash and type")
        identity = matches[0].get("identity_resolution")
        if not isinstance(identity, Mapping):
            raise FactPublicationEligibilityError("matching identity overlay document lacks identity_resolution")
        return matches[0]

    @classmethod
    def _overlay_summary(cls, overlay_document: Mapping[str, Any], match: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
        link = match["document_version_link"]
        identity = match["identity_resolution"]
        return {
            "overlay_type": overlay_document["overlay_type"],
            "overlay_status": overlay_document.get("overlay_status"),
            "document_version_id": link.get("document_version_id"),
            "document_id": link.get("document_id"),
            "content_sha256": link.get("content_sha256"),
            "resolution_status": identity.get("resolution_status"),
            "evidence_review_eligibility": identity.get("evidence_review_eligibility"),
            "temporal_status": identity.get("temporal_status"),
            "current_entitlement_publication_eligibility": identity.get("current_entitlement_publication_eligibility"),
            "source_entity_id": source["entity_id"],
        }

    @classmethod
    def _currentness_block_reason(cls, identity: Mapping[str, Any]) -> str | None:
        if identity.get("resolution_status") != "resolved":
            return "identity_not_resolved"
        if identity.get("evidence_review_eligibility") != "eligible_for_evidence_review":
            return "evidence_review_not_eligible"
        # V0.1 uses the existing overlay's explicit current-entitlement signal as
        # a conservative publication-review prerequisite. It does not upgrade it.
        if identity.get("current_entitlement_publication_eligibility") != "eligible":
            temporal = identity.get("temporal_status") or "unknown"
            return f"currentness_not_eligible:{temporal}"
        if identity.get("temporal_status") != "current_observed_reviewed":
            return f"temporal_status_not_current_observed_reviewed:{identity.get('temporal_status') or 'unknown'}"
        return None

    @classmethod
    def _fact_record(cls, fact: Mapping[str, Any], source: Mapping[str, Any], overlay: Mapping[str, Any], reason: str | None) -> dict[str, Any]:
        if not isinstance(fact, Mapping):
            raise FactPublicationEligibilityError("canonical fact must be an object")
        record = {
            "eligibility_record_id": cls._record_id("fact", fact.get("canonical_fact_id")),
            "record_kind": "canonical_fact",
            "canonical_fact_id": fact.get("canonical_fact_id"),
            "canonical_field_key": fact.get("canonical_field_key"),
            "normalized_value": dict(fact.get("normalized_value", {})),
            "benefit_scope": fact.get("benefit_scope"),
            "applicability": dict(fact.get("applicability", {})),
            "source_document": dict(fact.get("source_document", {})),
            "review_lineage": dict(fact.get("review_lineage", {})),
            "input_materialization_status": fact.get("materialization_status"),
            "eligibility_status": cls.ELIGIBLE if reason is None else cls.BLOCKED,
            "validation_checks": {
                "canonical_fact_contract": "passed",
                "source_lineage": "passed",
                "duplicate_applicability_key": "passed",
                "identity_resolution": overlay.get("resolution_status"),
                "evidence_review_eligibility": overlay.get("evidence_review_eligibility"),
                "temporal_currentness": overlay.get("temporal_status"),
                "current_entitlement_publication_eligibility": overlay.get("current_entitlement_publication_eligibility"),
            },
            "eligibility_reason": "all_v0_1_validation_prerequisites_satisfied" if reason is None else reason,
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
        }
        return record

    @classmethod
    def _deferred_record(cls, record: Mapping[str, Any], source: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(record, Mapping):
            raise FactPublicationEligibilityError("non-materialized selection record must be an object")
        return {
            "eligibility_record_id": cls._record_id("deferred", record.get("selection_record_id")),
            "record_kind": "non_materialized_selection_record",
            "selection_record_id": record.get("selection_record_id"),
            "selection_status": record.get("selection_status"),
            "normalized_value": dict(record.get("normalized_value", {})),
            "selected_role": record.get("selected_role"),
            "selected_benefit_scope": record.get("selected_benefit_scope"),
            "selected_band_scope": record.get("selected_band_scope"),
            "source_sha256": record.get("source_sha256"),
            "eligibility_status": cls.DEFERRED,
            "validation_checks": {
                "input_non_materialized": "passed",
                "source_lineage": "passed" if record.get("source_sha256") == source.get("sha256") else "failed",
                "identity_resolution": overlay.get("resolution_status"),
                "temporal_currentness": overlay.get("temporal_status"),
            },
            "eligibility_reason": record.get("non_materialization_reason") or "non_materialized_input",
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
        }

    @classmethod
    def _validate_record(cls, record: Mapping[str, Any], *, source: Mapping[str, Any], inp: Mapping[str, Any], overlay: Mapping[str, Any]) -> None:
        if not isinstance(record, Mapping):
            raise FactPublicationEligibilityError("eligibility record must be an object")
        cls._require_prefixed_id("eligibility_record_id", record.get("eligibility_record_id"), "feligrec_")
        if record.get("eligibility_status") not in {cls.ELIGIBLE, cls.BLOCKED, cls.DEFERRED}:
            raise FactPublicationEligibilityError("invalid eligibility_status")
        if record.get("publication_state") != "not_published" or record.get("entitlement_state") != "not_evaluated":
            raise FactPublicationEligibilityError("eligibility records must remain not_published and not_evaluated")
        checks = record.get("validation_checks")
        if not isinstance(checks, Mapping):
            raise FactPublicationEligibilityError("eligibility record requires validation_checks")
        cls._require_non_empty("eligibility_reason", record.get("eligibility_reason"))
        if record.get("record_kind") == "canonical_fact":
            cls._require_prefixed_id("canonical_fact_id", record.get("canonical_fact_id"), "cfact_")
            if record.get("input_materialization_status") != CanonicalFactMaterializationContract.FACT_STATUS:
                raise FactPublicationEligibilityError("canonical fact eligibility record has invalid materialization status")
            src_doc = record.get("source_document")
            if not isinstance(src_doc, Mapping) or src_doc.get("sha256") != source.get("sha256"):
                raise FactPublicationEligibilityError("canonical fact eligibility source lineage mismatch")
            lineage = record.get("review_lineage")
            if not isinstance(lineage, Mapping) or lineage.get("source_submission_id") != inp.get("source_submission_id"):
                raise FactPublicationEligibilityError("canonical fact eligibility review lineage mismatch")
            if record.get("eligibility_status") == cls.ELIGIBLE:
                if overlay.get("current_entitlement_publication_eligibility") != "eligible" or overlay.get("temporal_status") != "current_observed_reviewed":
                    raise FactPublicationEligibilityError("eligible fact requires reviewed current temporal eligibility")
        elif record.get("record_kind") == "non_materialized_selection_record":
            cls._require_prefixed_id("selection_record_id", record.get("selection_record_id"), "fsel_")
            if record.get("eligibility_status") != cls.DEFERRED:
                raise FactPublicationEligibilityError("non-materialized input must remain deferred")
            if record.get("source_sha256") != source.get("sha256"):
                raise FactPublicationEligibilityError("non-materialized eligibility source lineage mismatch")
        else:
            raise FactPublicationEligibilityError("unsupported eligibility record_kind")

    @classmethod
    def _validate_overlay_summary(cls, overlay: Mapping[str, Any], source: Mapping[str, Any]) -> None:
        if overlay.get("overlay_type") != "document_identity_resolution_overlay_v1":
            raise FactPublicationEligibilityError("identity overlay summary type mismatch")
        if overlay.get("source_entity_id") != source.get("entity_id"):
            raise FactPublicationEligibilityError("identity overlay summary entity mismatch")
        if overlay.get("content_sha256") != source.get("sha256"):
            raise FactPublicationEligibilityError("identity overlay summary source SHA mismatch")
        for key in ("resolution_status", "evidence_review_eligibility", "temporal_status", "current_entitlement_publication_eligibility"):
            cls._require_non_empty(f"identity_overlay.{key}", overlay.get(key))

    @classmethod
    def _assert_unique_materialized_fact_keys(cls, records: list[Mapping[str, Any]]) -> None:
        """Validate canonical identities using the approved registry cardinality policy.

        This must remain aligned with materialization. A registry-declared option
        set may contain distinct INR values for one field/scope/band identity;
        ordinary fields remain single-valued for that identity.
        """
        seen: set[tuple[Any, ...]] = set()
        for record in records:
            if record.get("record_kind") != "canonical_fact":
                continue
            field_key = record.get("canonical_field_key")
            try:
                include_value = HealthFieldSelectionPolicy.canonical_identity_includes_normalized_value(field_key)
            except Exception as exc:
                raise FactPublicationEligibilityError(
                    "canonical fact has unsupported canonical_field_key"
                ) from exc
            app = record.get("applicability")
            band = app.get("sum_insured_band_scope") if isinstance(app, Mapping) else None
            key = (
                field_key,
                record.get("benefit_scope"),
                band,
                cls._normalized_currency_value_for_key(record) if include_value else None,
            )
            if key in seen:
                raise FactPublicationEligibilityError(
                    "duplicate canonical fact applicability key with required value identity"
                )
            seen.add(key)

    @staticmethod
    def _normalized_currency_value_for_key(record: Mapping[str, Any]) -> tuple[Any, Any, Any]:
        value = record.get("normalized_value")
        if not isinstance(value, Mapping):
            return (None, None, None)
        return (value.get("kind"), value.get("unit"), value.get("value"))

    @staticmethod
    def _record_id(kind: str, source_id: Any) -> str:
        raw = f"fact-eligibility|{kind}|{source_id}"
        return "feligrec_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _assessment_id(*, source_sha256: str, materialization_id: str, validated_by: str, validated_at: str, record_ids: list[str]) -> str:
        payload = "|".join([source_sha256, materialization_id, validated_by, validated_at, *sorted(record_ids)])
        return "felig_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _validate_source(source: Mapping[str, Any]) -> None:
        if not FactPublicationEligibilityContract._valid_sha(source.get("sha256")):
            raise FactPublicationEligibilityError("source.sha256 must be a valid SHA-256")
        for key in ("entity_id", "insurer_id", "document_type", "source_document_id"):
            FactPublicationEligibilityContract._require_non_empty(f"source.{key}", source.get(key))

    @staticmethod
    def _valid_sha(value: Any) -> bool:
        return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())

    @staticmethod
    def _require_non_empty(name: str, value: Any) -> None:
        if not isinstance(value, str) or not value.strip():
            raise FactPublicationEligibilityError(f"{name} must be a non-empty string")

    @staticmethod
    def _require_prefixed_id(name: str, value: Any, prefix: str) -> None:
        if not isinstance(value, str) or not value.startswith(prefix):
            raise FactPublicationEligibilityError(f"{name} must be a {prefix} identifier")

    @staticmethod
    def _validate_iso_timestamp(value: Any, *, field_name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise FactPublicationEligibilityError(f"{field_name} must be ISO-8601")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise FactPublicationEligibilityError(f"{field_name} must be ISO-8601") from exc
