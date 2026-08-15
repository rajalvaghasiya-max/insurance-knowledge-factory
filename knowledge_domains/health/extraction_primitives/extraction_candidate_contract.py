"""Common evidence-candidate contract for deterministic Health extraction primitives.

This module defines only the shared extraction boundary.  It does not create
canonical facts, select among conflicting candidates, resolve applicability,
or determine publication/currentness.

A primitive may carry field-specific information in ``attributes`` while the
common envelope remains stable across value types such as duration, percentage,
and currency.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class ExtractionCandidateContractError(ValueError):
    """Raised when a candidate or candidate document violates the shared contract."""


@dataclass(frozen=True)
class ContractValidationResult:
    candidate_count: int
    primitive: str
    primitive_version: str


class ExtractionCandidateContract:
    """Validate and build the common non-fact extraction-candidate envelope.

    Contract v1 intentionally permits field-specific ``attributes``.  Every
    candidate must still contain deterministic identity, normalized value,
    evidence/page provenance, source provenance, review-bearing confidence, and
    an explicit non-fact guardrail.
    """

    SCHEMA_VERSION = "1.0"
    ENVELOPE_TYPE = "health_extraction_candidate_document_v1"
    CANDIDATE_GUARDRAIL = "evidence_candidate_only"
    GOVERNED_HASH_VERIFIED_PROVENANCE = "governed_source_registration_sha256_verified"
    _SHA256_RE = re.compile(r"[0-9a-f]{64}")

    @classmethod
    def deterministic_candidate_id(
        cls,
        *,
        primitive: str,
        source_sha256: str,
        page_number: int,
        normalized_character_start: int,
        normalized_character_end: int,
        candidate_type: str,
        normalized_value: Mapping[str, Any],
    ) -> str:
        """Return a stable ID derived from immutable source and evidence location."""
        cls._require_nonempty_string(primitive, "primitive")
        cls._require_sha256(source_sha256, "source_sha256")
        cls._require_positive_int(page_number, "page_number")
        cls._require_nonnegative_int(normalized_character_start, "normalized_character_start")
        cls._require_nonnegative_int(normalized_character_end, "normalized_character_end")
        if normalized_character_end < normalized_character_start:
            raise ExtractionCandidateContractError(
                "normalized_character_end must be >= normalized_character_start"
            )
        cls._require_nonempty_string(candidate_type, "candidate_type")
        cls.validate_normalized_value(normalized_value)
        material = {
            "primitive": primitive,
            "source_sha256": source_sha256,
            "page_number": page_number,
            "normalized_character_start": normalized_character_start,
            "normalized_character_end": normalized_character_end,
            "candidate_type": candidate_type,
            "normalized_value": dict(normalized_value),
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16]
        return f"excand_{digest}"

    @classmethod
    def build_candidate(
        cls,
        *,
        candidate_id: str,
        candidate_type: str,
        normalized_value: Mapping[str, Any],
        attributes: Mapping[str, Any],
        evidence: Mapping[str, Any],
        source: Mapping[str, Any],
        confidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Build a v1 common-envelope candidate after validating all shared fields."""
        candidate = {
            "candidate_id": candidate_id,
            "candidate_type": candidate_type,
            "normalized_value": dict(normalized_value),
            "attributes": dict(attributes),
            "evidence": dict(evidence),
            "source": dict(source),
            "confidence": dict(confidence),
            "non_fact_guardrail": cls.CANDIDATE_GUARDRAIL,
        }
        cls.validate_candidate(candidate)
        return candidate

    @classmethod
    def build_document(
        cls,
        *,
        primitive: str,
        primitive_version: str,
        source: Mapping[str, Any],
        candidates: Sequence[Mapping[str, Any]],
        status: str = "candidates_extracted",
        limitations: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Build a common candidate-document envelope without any fact semantics."""
        cls._require_nonempty_string(primitive, "primitive")
        cls._require_nonempty_string(primitive_version, "primitive_version")
        cls._require_nonempty_string(status, "status")
        cls.validate_source(source)
        result = {
            "schema_version": cls.SCHEMA_VERSION,
            "contract_type": cls.ENVELOPE_TYPE,
            "primitive": primitive,
            "primitive_version": primitive_version,
            "status": status,
            "source": dict(source),
            "candidate_count": len(candidates),
            "candidates": [dict(candidate) for candidate in candidates],
            "limitations": list(limitations),
        }
        cls.validate_document(result)
        return result

    @classmethod
    def validate_document(cls, document: Mapping[str, Any]) -> ContractValidationResult:
        if not isinstance(document, Mapping):
            raise ExtractionCandidateContractError("candidate_document must be an object")
        if document.get("schema_version") != cls.SCHEMA_VERSION:
            raise ExtractionCandidateContractError("candidate_document.schema_version must be 1.0")
        if document.get("contract_type") != cls.ENVELOPE_TYPE:
            raise ExtractionCandidateContractError(
                "candidate_document.contract_type must be health_extraction_candidate_document_v1"
            )
        primitive = document.get("primitive")
        primitive_version = document.get("primitive_version")
        cls._require_nonempty_string(primitive, "candidate_document.primitive")
        cls._require_nonempty_string(primitive_version, "candidate_document.primitive_version")
        cls._require_nonempty_string(document.get("status"), "candidate_document.status")
        cls.validate_source(cls._mapping(document.get("source"), "candidate_document.source"))
        candidates = document.get("candidates")
        if not isinstance(candidates, list):
            raise ExtractionCandidateContractError("candidate_document.candidates must be a list")
        if document.get("candidate_count") != len(candidates):
            raise ExtractionCandidateContractError(
                "candidate_document.candidate_count must equal the number of candidates"
            )
        for index, candidate in enumerate(candidates):
            try:
                cls.validate_candidate(cls._mapping(candidate, f"candidate_document.candidates[{index}]"))
            except ExtractionCandidateContractError as exc:
                raise ExtractionCandidateContractError(str(exc)) from exc
        limitations = document.get("limitations")
        if not isinstance(limitations, list) or not all(isinstance(item, str) for item in limitations):
            raise ExtractionCandidateContractError("candidate_document.limitations must be a list of strings")
        return ContractValidationResult(
            candidate_count=len(candidates), primitive=primitive, primitive_version=primitive_version
        )

    @classmethod
    def validate_candidate(cls, candidate: Mapping[str, Any]) -> None:
        cls._require_nonempty_string(candidate.get("candidate_id"), "candidate.candidate_id")
        cls._require_nonempty_string(candidate.get("candidate_type"), "candidate.candidate_type")
        cls.validate_normalized_value(cls._mapping(candidate.get("normalized_value"), "candidate.normalized_value"))
        attributes = candidate.get("attributes")
        if not isinstance(attributes, Mapping):
            raise ExtractionCandidateContractError("candidate.attributes must be an object")
        cls.validate_evidence(cls._mapping(candidate.get("evidence"), "candidate.evidence"))
        cls.validate_source(cls._mapping(candidate.get("source"), "candidate.source"))
        cls.validate_confidence(cls._mapping(candidate.get("confidence"), "candidate.confidence"))
        if candidate.get("non_fact_guardrail") != cls.CANDIDATE_GUARDRAIL:
            raise ExtractionCandidateContractError(
                "candidate.non_fact_guardrail must be evidence_candidate_only"
            )

    @classmethod
    def validate_normalized_value(cls, value: Mapping[str, Any]) -> None:
        cls._require_nonempty_string(value.get("kind"), "candidate.normalized_value.kind")
        raw_value = value.get("value")
        if not isinstance(raw_value, (int, float, str)) or isinstance(raw_value, bool):
            raise ExtractionCandidateContractError(
                "candidate.normalized_value.value must be a number or non-empty string"
            )
        if isinstance(raw_value, str) and not raw_value.strip():
            raise ExtractionCandidateContractError("candidate.normalized_value.value must not be blank")
        cls._require_nonempty_string(value.get("unit"), "candidate.normalized_value.unit")
        raw_text = value.get("raw_text")
        if raw_text is not None and (not isinstance(raw_text, str) or not raw_text.strip()):
            raise ExtractionCandidateContractError(
                "candidate.normalized_value.raw_text must be a non-empty string when present"
            )

    @classmethod
    def validate_evidence(cls, evidence: Mapping[str, Any]) -> None:
        cls._require_nonempty_string(evidence.get("text"), "candidate.evidence.text")
        cls._require_positive_int(evidence.get("page_number"), "candidate.evidence.page_number")
        cls._require_nonnegative_int(evidence.get("character_start"), "candidate.evidence.character_start")
        cls._require_nonnegative_int(evidence.get("character_end"), "candidate.evidence.character_end")
        if evidence["character_end"] < evidence["character_start"]:
            raise ExtractionCandidateContractError(
                "candidate.evidence.character_end must be >= candidate.evidence.character_start"
            )
        cls._require_nonnegative_int(
            evidence.get("normalized_character_start"),
            "candidate.evidence.normalized_character_start",
        )
        cls._require_nonnegative_int(
            evidence.get("normalized_character_end"),
            "candidate.evidence.normalized_character_end",
        )
        if evidence["normalized_character_end"] < evidence["normalized_character_start"]:
            raise ExtractionCandidateContractError(
                "candidate.evidence.normalized_character_end must be >= candidate.evidence.normalized_character_start"
            )
        cls._require_nonempty_string(evidence.get("evidence_type"), "candidate.evidence.evidence_type")

    @classmethod
    def validate_source(cls, source: Mapping[str, Any]) -> None:
        cls._require_sha256(source.get("sha256"), "candidate.source.sha256")
        cls._require_nonempty_string(source.get("source_document_id"), "candidate.source.source_document_id")
        if source["source_document_id"] != f"sha256:{source['sha256']}":
            raise ExtractionCandidateContractError(
                "candidate.source.source_document_id must equal sha256:<candidate.source.sha256>"
            )
        cls._require_nonempty_string(source.get("document_type"), "candidate.source.document_type")
        cls._require_nonempty_string(source.get("relative_archive_path"), "candidate.source.relative_archive_path")
        cls._require_nonempty_string(source.get("provenance_status"), "candidate.source.provenance_status")

        source_url = source.get("source_url")
        if source_url is None:
            if source.get("provenance_status") != cls.GOVERNED_HASH_VERIFIED_PROVENANCE:
                raise ExtractionCandidateContractError(
                    "candidate.source.source_url may be null only for governed SHA-256-verified registration provenance"
                )
        else:
            cls._require_nonempty_string(source_url, "candidate.source.source_url")

    @classmethod
    def validate_confidence(cls, confidence: Mapping[str, Any]) -> None:
        score = confidence.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= float(score) <= 1:
            raise ExtractionCandidateContractError("candidate.confidence.score must be between 0 and 1")
        if confidence.get("requires_review") is not True:
            raise ExtractionCandidateContractError(
                "candidate.confidence.requires_review must be true for evidence candidates"
            )
        cls._require_nonempty_string(confidence.get("method"), "candidate.confidence.method")
        cls._require_nonempty_string(confidence.get("reason"), "candidate.confidence.reason")

    @staticmethod
    def _mapping(value: Any, label: str) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise ExtractionCandidateContractError(f"{label} must be an object")
        return value

    @staticmethod
    def _require_nonempty_string(value: Any, label: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ExtractionCandidateContractError(f"{label} must be a non-empty string")

    @classmethod
    def _require_sha256(cls, value: Any, label: str) -> None:
        if not isinstance(value, str) or not cls._SHA256_RE.fullmatch(value):
            raise ExtractionCandidateContractError(f"{label} must be a 64-character lowercase SHA-256")

    @staticmethod
    def _require_positive_int(value: Any, label: str) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ExtractionCandidateContractError(f"{label} must be a positive integer")

    @staticmethod
    def _require_nonnegative_int(value: Any, label: str) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ExtractionCandidateContractError(f"{label} must be a non-negative integer")
