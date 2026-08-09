"""Deterministic waiting-period candidate isolation from a certified processed document.

MO-028B uses this adapter for products whose authoritative policy wording already exists
as a certified processed-document asset rather than as a Star-style generic source
registration.  The adapter deliberately performs candidate isolation only.  It does not
approve evidence, publish waiting-period facts, or promote coverage-registry readiness.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from insurance_intelligence.benefits.waiting_period_contracts import WaitingPeriodType


class ProcessedWaitingPeriodAuditError(ValueError):
    """Raised when a processed document cannot support deterministic evidence audit."""


class ProcessedEvidenceAuditStatus(str, Enum):
    NO_CANDIDATE = "NO_CANDIDATE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class ProcessedWaitingPeriodEvidenceCandidate:
    candidate_id: str
    source_page: int | None
    text_sha256: str
    excerpt: str
    json_path: str


@dataclass(frozen=True)
class ProcessedWaitingPeriodEvidenceAuditResult:
    waiting_period_type: WaitingPeriodType
    markers: tuple[str, ...]
    status: ProcessedEvidenceAuditStatus
    document_id: str
    processed_document_asset_id: str
    source_document_sha256: str
    candidates: tuple[ProcessedWaitingPeriodEvidenceCandidate, ...]


_MARKERS: Mapping[WaitingPeriodType, tuple[str, ...]] = {
    WaitingPeriodType.PRE_EXISTING_DISEASE: (
        "D.1.1",
        "Code-Excl01",
        "Code Excl 01",
    ),
    WaitingPeriodType.SPECIFIC_DISEASE_PROCEDURE: (
        "D.1.2",
        "Code-Excl02",
        "Code Excl 02",
    ),
    WaitingPeriodType.INITIAL: (
        "D.1.3",
        "Code-Excl03",
        "Code Excl 03",
        "30-day Waiting Period",
        "30-day waiting period",
    ),
}


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProcessedWaitingPeriodAuditError(f"{field_name} must be non-empty text")
    return value.strip()


def load_processed_document(path: str | Path) -> Mapping[str, Any]:
    source_path = Path(path)
    if not source_path.is_file():
        raise FileNotFoundError(f"processed document not found: {source_path}")
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProcessedWaitingPeriodAuditError(
            f"processed document is not valid UTF-8 JSON: {source_path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ProcessedWaitingPeriodAuditError("processed document root must be an object")
    return payload


def _iter_text_nodes(value: object, path: str = "$") -> Iterable[tuple[str, Mapping[str, Any]]]:
    """Yield mapping nodes containing non-empty ``text`` fields in stable JSON order."""
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str) and text.strip():
            yield path, value
        for key, child in value.items():
            yield from _iter_text_nodes(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_text_nodes(child, f"{path}[{index}]")


def _extract_page(node: Mapping[str, Any]) -> int | None:
    for field in ("source_page", "page_number", "page", "page_no"):
        value = node.get(field)
        if type(value) is int and value > 0:
            return value
    return None


def _candidate_id(document_id: str, json_path: str, text_sha256: str) -> str:
    digest = hashlib.sha256(
        f"{document_id}|{json_path}|{text_sha256}".encode("utf-8")
    ).hexdigest()[:20]
    return f"wp_candidate_{digest}"


def audit_processed_waiting_period_candidates(
    processed_document: Mapping[str, Any],
    waiting_period_type: WaitingPeriodType,
    *,
    document_id: str,
    processed_document_asset_id: str,
    source_document_sha256: str,
) -> ProcessedWaitingPeriodEvidenceAuditResult:
    if not isinstance(waiting_period_type, WaitingPeriodType):
        raise ProcessedWaitingPeriodAuditError(
            "waiting_period_type must be a WaitingPeriodType"
        )
    if not isinstance(processed_document, dict):
        raise ProcessedWaitingPeriodAuditError("processed_document must be an object")

    document_id = _required_text(document_id, "document_id")
    processed_document_asset_id = _required_text(
        processed_document_asset_id, "processed_document_asset_id"
    )
    source_document_sha256 = _required_text(
        source_document_sha256, "source_document_sha256"
    )

    markers = _MARKERS[waiting_period_type]
    candidates: list[ProcessedWaitingPeriodEvidenceCandidate] = []
    seen_text_hashes: set[str] = set()

    for json_path, node in _iter_text_nodes(processed_document):
        excerpt = _required_text(node.get("text"), f"{json_path}.text")
        if not any(marker in excerpt for marker in markers):
            continue
        text_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
        # The processed representation can repeat the same text in derived structures.
        # Keep one deterministic candidate per exact text body.
        if text_sha256 in seen_text_hashes:
            continue
        seen_text_hashes.add(text_sha256)
        candidates.append(
            ProcessedWaitingPeriodEvidenceCandidate(
                candidate_id=_candidate_id(document_id, json_path, text_sha256),
                source_page=_extract_page(node),
                text_sha256=text_sha256,
                excerpt=excerpt,
                json_path=json_path,
            )
        )

    candidates_tuple = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.source_page is None,
                item.source_page or 0,
                item.json_path,
                item.candidate_id,
            ),
        )
    )
    status = (
        ProcessedEvidenceAuditStatus.REVIEW_REQUIRED
        if candidates_tuple
        else ProcessedEvidenceAuditStatus.NO_CANDIDATE
    )
    return ProcessedWaitingPeriodEvidenceAuditResult(
        waiting_period_type=waiting_period_type,
        markers=markers,
        status=status,
        document_id=document_id,
        processed_document_asset_id=processed_document_asset_id,
        source_document_sha256=source_document_sha256,
        candidates=candidates_tuple,
    )


def audit_all_processed_waiting_period_candidates(
    processed_document: Mapping[str, Any],
    *,
    document_id: str,
    processed_document_asset_id: str,
    source_document_sha256: str,
) -> tuple[ProcessedWaitingPeriodEvidenceAuditResult, ...]:
    return tuple(
        audit_processed_waiting_period_candidates(
            processed_document,
            waiting_period_type,
            document_id=document_id,
            processed_document_asset_id=processed_document_asset_id,
            source_document_sha256=source_document_sha256,
        )
        for waiting_period_type in (
            WaitingPeriodType.INITIAL,
            WaitingPeriodType.SPECIFIC_DISEASE_PROCEDURE,
            WaitingPeriodType.PRE_EXISTING_DISEASE,
        )
    )


__all__ = [
    "ProcessedEvidenceAuditStatus",
    "ProcessedWaitingPeriodAuditError",
    "ProcessedWaitingPeriodEvidenceAuditResult",
    "ProcessedWaitingPeriodEvidenceCandidate",
    "audit_all_processed_waiting_period_candidates",
    "audit_processed_waiting_period_candidates",
    "load_processed_document",
]
