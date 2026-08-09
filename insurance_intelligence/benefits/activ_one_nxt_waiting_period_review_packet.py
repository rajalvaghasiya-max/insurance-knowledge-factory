"""Deterministic review-packet rendering for Activ One NXT waiting-period evidence.

This module is review-only. It renders deterministic candidates isolated from the
certified processed policy wording. It does not approve evidence, construct governed
waiting-period mechanics, publish facts, or promote coverage-registry readiness.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from insurance_intelligence.benefits.processed_waiting_period_evidence_audit import (
    ProcessedWaitingPeriodEvidenceAuditResult,
    audit_all_processed_waiting_period_candidates,
    load_processed_document,
)


DEFAULT_BINDING_PATH = Path(
    "docs/architecture/ACTIV_ONE_NXT_POLICY_WORDING_SOURCE_BINDING.json"
)
DEFAULT_PROCESSED_DOCUMENT_PATH = Path(
    "knowledge/factory/processed_documents/"
    "doc_d20a8488ecb3243f6de2_pdoc_72d03e57d4b49c68d69a11fc_processed_document_v2.json"
)
DEFAULT_OUTPUT_PATH = Path(
    "docs/architecture/ACTIV_ONE_NXT_WAITING_PERIOD_REVIEW_PACKET.md"
)


class ActivOneNxtWaitingPeriodReviewPacketError(ValueError):
    """Raised when review-packet inputs are incomplete or inconsistent."""


def _load_json_object(path: str | Path) -> Mapping[str, Any]:
    source_path = Path(path)
    if not source_path.is_file():
        raise FileNotFoundError(f"review-packet input not found: {source_path}")
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ActivOneNxtWaitingPeriodReviewPacketError(
            f"review-packet input is not valid UTF-8 JSON: {source_path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ActivOneNxtWaitingPeriodReviewPacketError(
            f"review-packet input root must be an object: {source_path}"
        )
    return payload


def _binding_value(binding: Mapping[str, Any], *names: str) -> str:
    for name in names:
        value = binding.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for container_name in (
        "source_registration",
        "certified_processed_asset",
        "source",
        "document",
        "processed_document",
        "binding",
    ):
        container = binding.get(container_name)
        if isinstance(container, dict):
            for name in names:
                value = container.get(name)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    raise ActivOneNxtWaitingPeriodReviewPacketError(
        f"binding is missing required field; accepted names={names}"
    )


def _render_candidate(candidate) -> list[str]:
    page = str(candidate.source_page) if candidate.source_page is not None else "unknown"
    return [
        f"### {candidate.candidate_id}",
        "",
        f"- Source page: `{page}`",
        f"- JSON path: `{candidate.json_path}`",
        f"- Text SHA256: `{candidate.text_sha256}`",
        "",
        "```text",
        candidate.excerpt,
        "```",
        "",
    ]


def render_activ_one_nxt_waiting_period_review_packet(
    *,
    binding: Mapping[str, Any],
    audit_results: tuple[ProcessedWaitingPeriodEvidenceAuditResult, ...],
) -> str:
    uin = _binding_value(binding, "uin", "product_uin", "approved_uin")
    product_reference = _binding_value(
        binding, "product_reference", "product_variant_id", "variant_id"
    )
    document_id = _binding_value(binding, "document_id")
    asset_id = _binding_value(
        binding, "processed_document_asset_id", "asset_id", "processed_asset_id"
    )
    source_hash = _binding_value(
        binding,
        "source_document_sha256",
        "document_hash_sha256",
        "document_sha256",
        "content_sha256",
        "sha256",
    )

    lines = [
        "# Activ One NXT Waiting-Period Evidence Review Packet",
        "",
        "> REVIEW MATERIAL ONLY — this packet does not approve evidence, publish waiting-period facts, or promote the Coverage Registry.",
        "",
        "## Bound product and source",
        "",
        f"- Product reference: `{product_reference}`",
        f"- Product UIN: `{uin}`",
        f"- Document ID: `{document_id}`",
        f"- Processed-document asset ID: `{asset_id}`",
        f"- Source document SHA256: `{source_hash}`",
        "",
        "## Review instructions",
        "",
        "For each waiting-period type, identify the base policy clause, supporting cross-references, and any optional-cover modification candidates. Optional reductions must not be treated as base waiting-period terms merely because they occur in the same source document.",
        "",
    ]

    for result in audit_results:
        lines.extend(
            [
                f"## {result.waiting_period_type.value}",
                "",
                f"Audit status: `{result.status.value}`",
                "",
                "Markers used: " + ", ".join(f"`{marker}`" for marker in result.markers),
                "",
                f"Candidate count: **{len(result.candidates)}**",
                "",
            ]
        )
        if not result.candidates:
            lines.extend(["No candidates isolated.", ""])
            continue
        for candidate in result.candidates:
            lines.extend(_render_candidate(candidate))

    lines.extend(
        [
            "## Publication boundary",
            "",
            "- Human base-clause review decision recorded: **NO**",
            "- Governed waiting-period publication created: **NO**",
            "- Coverage Registry promoted: **NO**",
            "",
        ]
    )
    return "\n".join(lines)


def build_activ_one_nxt_waiting_period_review_packet(
    *,
    binding_path: str | Path = DEFAULT_BINDING_PATH,
    processed_document_path: str | Path = DEFAULT_PROCESSED_DOCUMENT_PATH,
) -> str:
    binding = _load_json_object(binding_path)
    processed_document = load_processed_document(processed_document_path)
    document_id = _binding_value(binding, "document_id")
    asset_id = _binding_value(
        binding, "processed_document_asset_id", "asset_id", "processed_asset_id"
    )
    source_hash = _binding_value(
        binding,
        "source_document_sha256",
        "document_hash_sha256",
        "document_sha256",
        "content_sha256",
        "sha256",
    )
    results = audit_all_processed_waiting_period_candidates(
        processed_document,
        document_id=document_id,
        processed_document_asset_id=asset_id,
        source_document_sha256=source_hash,
    )
    return render_activ_one_nxt_waiting_period_review_packet(
        binding=binding,
        audit_results=results,
    )


def write_activ_one_nxt_waiting_period_review_packet(
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    binding_path: str | Path = DEFAULT_BINDING_PATH,
    processed_document_path: str | Path = DEFAULT_PROCESSED_DOCUMENT_PATH,
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        build_activ_one_nxt_waiting_period_review_packet(
            binding_path=binding_path,
            processed_document_path=processed_document_path,
        ),
        encoding="utf-8",
        newline="\n",
    )
    return target


__all__ = [
    "ActivOneNxtWaitingPeriodReviewPacketError",
    "DEFAULT_BINDING_PATH",
    "DEFAULT_OUTPUT_PATH",
    "DEFAULT_PROCESSED_DOCUMENT_PATH",
    "build_activ_one_nxt_waiting_period_review_packet",
    "render_activ_one_nxt_waiting_period_review_packet",
    "write_activ_one_nxt_waiting_period_review_packet",
]
