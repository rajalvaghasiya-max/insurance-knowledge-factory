"""Prospective machine-side acquisition of product identity/currentness metadata.

This module sits after authorized blind metadata-path discovery and before neutral
product selection. It deliberately keeps raw locations machine-side. Callers supply
an acquisition callback that resolves an authorized URL into one metadata artifact.
The acquirer performs bounded deterministic traversal, hashes every acquired artifact,
normalizes identity/currentness evidence, and emits selector-safe projections only.

It does not authorize semantic target-clause inspection, decide publication, or infer
currentness from a source reference alone.
"""
from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit, urlunsplit

from agents.uin_candidate_extractor import UinCandidateExtractor
from factory_core.governance.preselection_metadata_projection import (
    BlindPreselectionMetadataProjectorV2,
    PreselectionMetadataProjectionError,
)


class ProductIdentityCurrentnessAcquisitionError(ValueError):
    """Raised when metadata traversal or normalization cannot proceed safely."""


AUTHORIZED_ARTIFACT_CLASSES = frozenset(
    {
        "metadata_page",
        "metadata_table",
        "metadata_pdf",
        "insurer_product_index",
        "regulator_product_index",
        "uin_register",
        "withdrawn_product_index",
    }
)

FORBIDDEN_PRESELECTION_ARTIFACT_CLASSES = frozenset(
    {
        "policy_wording",
        "prospectus",
        "customer_information_sheet",
        "cis",
        "claim_form",
        "proposal_form",
        "semantic_extract",
    }
)

CURRENTNESS_VALUES = frozenset(
    {
        "current",
        "active",
        "non_archived",
        "withdrawn",
        "discontinued",
        "archived",
    }
)


@dataclass(frozen=True)
class BlindIdentityCurrentnessEvidenceProjectionV1:
    """Selector-safe companion projection for explicit currentness evidence."""

    schema_version: str
    projection_type: str
    insurer_id: str
    source_ref: str
    source_content_hash: str
    authority_scope: str
    artifact_class: str
    product_names: tuple[str, ...]
    uins: tuple[str, ...]
    version_signals: tuple[str, ...]
    currentness_status: str
    binding_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "projection_type": self.projection_type,
            "insurer_id": self.insurer_id,
            "source_ref": self.source_ref,
            "source_content_hash": self.source_content_hash,
            "authority_scope": self.authority_scope,
            "artifact_class": self.artifact_class,
            "product_names": list(self.product_names),
            "uins": list(self.uins),
            "version_signals": list(self.version_signals),
            "currentness_status": self.currentness_status,
            "binding_status": self.binding_status,
        }


@dataclass(frozen=True)
class ProductIdentityCurrentnessAcquisitionResult:
    """Raw-location-free output intended for the selector boundary and audit."""

    selector_product_metadata: tuple[Mapping[str, Any], ...]
    selector_currentness_evidence: tuple[Mapping[str, Any], ...]
    acquisition_summary: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selector_product_metadata": [dict(item) for item in self.selector_product_metadata],
            "selector_currentness_evidence": [dict(item) for item in self.selector_currentness_evidence],
            "acquisition_summary": dict(self.acquisition_summary),
        }


ArtifactLoader = Callable[[str], Mapping[str, Any]]


class GovernedProductIdentityCurrentnessEvidenceAcquirer:
    """Traverse authorized metadata surfaces without leaking raw locations.

    The loader is machine-side and may use raw URLs. Its return mapping must contain:
    - artifact_class: one authorized metadata class
    - text: identity/currentness-bearing text only
    - links: optional list of second-hop metadata URLs
    - authority_scope: insurer | regulator

    Optional `content_bytes` may be supplied. If omitted, UTF-8 text bytes are hashed.
    The loader must not return target-clause semantic extractions for this stage.
    """

    VERSION = "1.0"
    CURRENTNESS_PROJECTION_TYPE = "blind_product_identity_currentness_evidence_v1"
    CLASSIFICATION_RULES_VERSION = "identity_currentness_acquisition_v1"
    DEFAULT_MAX_DEPTH = 2
    DEFAULT_MAX_ARTIFACTS = 24

    _PRODUCT_NAME_RE = re.compile(
        r"(?im)^\s*(?:product|plan|policy)\s+name\s*[:\-]\s*(?P<name>[^\n\r|]{3,120})\s*$"
    )
    _VERSION_RE = re.compile(
        r"(?im)^\s*(?:version|product\s+version)\s*[:\-]\s*(?P<version>[^\n\r|]{1,80})\s*$"
    )
    _STATUS_RE = re.compile(
        r"(?im)^\s*(?:status|currentness|product\s+status)\s*[:\-]\s*"
        r"(?P<status>current|active|non[- ]?archived|withdrawn|discontinued|archived)\s*$"
    )

    def __init__(
        self,
        *,
        max_depth: int = DEFAULT_MAX_DEPTH,
        max_artifacts: int = DEFAULT_MAX_ARTIFACTS,
        uin_extractor: UinCandidateExtractor | None = None,
    ) -> None:
        if not isinstance(max_depth, int) or max_depth < 0 or max_depth > 4:
            raise ProductIdentityCurrentnessAcquisitionError("max_depth must be between 0 and 4")
        if not isinstance(max_artifacts, int) or max_artifacts < 1 or max_artifacts > 100:
            raise ProductIdentityCurrentnessAcquisitionError("max_artifacts must be between 1 and 100")
        self.max_depth = max_depth
        self.max_artifacts = max_artifacts
        self.uin_extractor = uin_extractor or UinCandidateExtractor()

    def acquire(
        self,
        *,
        insurer_id: str,
        authorized_start_urls: list[str] | tuple[str, ...],
        loader: ArtifactLoader,
    ) -> ProductIdentityCurrentnessAcquisitionResult:
        insurer = self._nonempty(insurer_id, "insurer_id")
        if not callable(loader):
            raise ProductIdentityCurrentnessAcquisitionError("loader must be callable")
        if not isinstance(authorized_start_urls, (list, tuple)) or not authorized_start_urls:
            raise ProductIdentityCurrentnessAcquisitionError(
                "authorized_start_urls must be a non-empty list or tuple"
            )

        roots = sorted({self._normalize_url(url) for url in authorized_start_urls})
        queue: deque[tuple[str, int]] = deque((url, 0) for url in roots)
        seen_urls: set[str] = set()
        product_projections: list[Mapping[str, Any]] = []
        currentness_projections: list[Mapping[str, Any]] = []
        rejection_counts: dict[str, int] = {}
        acquired_count = 0
        max_depth_observed = 0

        while queue and acquired_count < self.max_artifacts:
            raw_url, depth = queue.popleft()
            normalized_url = self._normalize_url(raw_url)
            if normalized_url in seen_urls:
                continue
            seen_urls.add(normalized_url)
            max_depth_observed = max(max_depth_observed, depth)

            payload = loader(normalized_url)
            if not isinstance(payload, Mapping):
                raise ProductIdentityCurrentnessAcquisitionError(
                    "loader results must be mappings"
                )

            artifact_class = self._nonempty(
                payload.get("artifact_class"), "loader_result.artifact_class"
            ).lower()
            if artifact_class in FORBIDDEN_PRESELECTION_ARTIFACT_CLASSES:
                self._increment(rejection_counts, f"forbidden_artifact_class:{artifact_class}")
                continue
            if artifact_class not in AUTHORIZED_ARTIFACT_CLASSES:
                self._increment(rejection_counts, f"unauthorized_artifact_class:{artifact_class}")
                continue

            authority_scope = self._nonempty(
                payload.get("authority_scope"), "loader_result.authority_scope"
            ).lower()
            if authority_scope not in {"insurer", "regulator"}:
                raise ProductIdentityCurrentnessAcquisitionError(
                    "authority_scope must be insurer or regulator"
                )

            text = payload.get("text", "")
            if not isinstance(text, str):
                raise ProductIdentityCurrentnessAcquisitionError("loader_result.text must be text")
            content_bytes = payload.get("content_bytes")
            if content_bytes is None:
                byte_content = text.encode("utf-8")
            elif isinstance(content_bytes, bytes):
                byte_content = content_bytes
            else:
                raise ProductIdentityCurrentnessAcquisitionError(
                    "loader_result.content_bytes must be bytes when supplied"
                )
            content_hash = sha256(byte_content).hexdigest()
            acquired_count += 1

            product_names = self._extract_product_names(text)
            uin_candidates = self.uin_extractor.extract(
                text,
                source={
                    "insurer_id": insurer,
                    "url": normalized_url,
                    "content_hash": content_hash,
                },
            )
            uins = sorted({item["uin"] for item in uin_candidates})
            version_signals = self._extract_version_signals(text)
            currentness_status = self._extract_currentness_status(text)
            binding_status = self._binding_status(product_names, uins)

            signals = {
                "insurer_id": insurer,
                "url": normalized_url,
                "content_hash": content_hash,
                "page_intent": "identity_currentness_metadata",
                "asset_scope": artifact_class,
                "classification_rules_version": self.CLASSIFICATION_RULES_VERSION,
                "product_names": product_names,
                "uins": uins,
                "uin_candidates": uin_candidates,
            }
            try:
                v2 = BlindPreselectionMetadataProjectorV2.project(signals).to_dict()
            except PreselectionMetadataProjectionError as exc:
                raise ProductIdentityCurrentnessAcquisitionError(str(exc)) from exc

            currentness = BlindIdentityCurrentnessEvidenceProjectionV1(
                schema_version="1.0",
                projection_type=self.CURRENTNESS_PROJECTION_TYPE,
                insurer_id=insurer,
                source_ref=v2["source_ref"],
                source_content_hash=content_hash,
                authority_scope=authority_scope,
                artifact_class=artifact_class,
                product_names=tuple(product_names),
                uins=tuple(uins),
                version_signals=tuple(version_signals),
                currentness_status=currentness_status,
                binding_status=binding_status,
            ).to_dict()

            product_projections.append(v2)
            currentness_projections.append(currentness)

            if depth < self.max_depth:
                links = payload.get("links", [])
                if links is None:
                    links = []
                if not isinstance(links, list):
                    raise ProductIdentityCurrentnessAcquisitionError(
                        "loader_result.links must be a list"
                    )
                normalized_links = sorted(
                    {
                        self._normalize_url(link)
                        for link in links
                        if isinstance(link, str) and link.strip()
                    }
                )
                for link in normalized_links:
                    if link not in seen_urls:
                        queue.append((link, depth + 1))

        product_projections = sorted(
            product_projections,
            key=lambda item: (item["source_ref"], item["source_content_hash"]),
        )
        currentness_projections = sorted(
            currentness_projections,
            key=lambda item: (item["source_ref"], item["source_content_hash"]),
        )

        summary = {
            "schema_version": "1.0",
            "acquisition_type": "governed_product_identity_currentness_evidence_acquisition_v1",
            "insurer_id": insurer,
            "authorized_root_count": len(roots),
            "acquired_artifact_count": acquired_count,
            "selector_product_projection_count": len(product_projections),
            "selector_currentness_projection_count": len(currentness_projections),
            "max_depth_configured": self.max_depth,
            "max_depth_observed": max_depth_observed,
            "max_artifacts_configured": self.max_artifacts,
            "rejection_counts": dict(sorted(rejection_counts.items())),
            "raw_url_fields_emitted": 0,
            "raw_anchor_fields_emitted": 0,
            "raw_parsed_path_fields_emitted": 0,
            "page_body_fields_emitted": 0,
            "screenshot_fields_emitted": 0,
            "semantic_bucket_fields_emitted": 0,
            "target_clause_reads": 0,
        }
        return ProductIdentityCurrentnessAcquisitionResult(
            selector_product_metadata=tuple(product_projections),
            selector_currentness_evidence=tuple(currentness_projections),
            acquisition_summary=summary,
        )

    @classmethod
    def _extract_product_names(cls, text: str) -> list[str]:
        names = {
            re.sub(r"\s+", " ", match.group("name")).strip(" -|:")
            for match in cls._PRODUCT_NAME_RE.finditer(text)
        }
        return sorted(name for name in names if name)

    @classmethod
    def _extract_version_signals(cls, text: str) -> list[str]:
        versions = {
            re.sub(r"\s+", " ", match.group("version")).strip(" -|:")
            for match in cls._VERSION_RE.finditer(text)
        }
        return sorted(version for version in versions if version)

    @classmethod
    def _extract_currentness_status(cls, text: str) -> str:
        observed = {
            match.group("status").lower().replace("-", " ").replace(" ", "_")
            for match in cls._STATUS_RE.finditer(text)
        }
        normalized = {"non_archived" if value == "non_archived" else value for value in observed}
        if not normalized:
            return "not_observed"
        if len(normalized) != 1:
            return "ambiguous"
        status = next(iter(normalized))
        return status if status in CURRENTNESS_VALUES else "ambiguous"

    @staticmethod
    def _binding_status(product_names: list[str], uins: list[str]) -> str:
        if len(product_names) == 1 and len(uins) == 1:
            return "exact_single_product_single_uin"
        if not product_names or not uins:
            return "insufficient_identity_evidence"
        return "ambiguous_identity_binding"

    @staticmethod
    def _increment(counts: dict[str, int], key: str) -> None:
        counts[key] = counts.get(key, 0) + 1

    @staticmethod
    def _nonempty(value: object, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ProductIdentityCurrentnessAcquisitionError(f"{label} must be non-empty text")
        return value.strip()

    @classmethod
    def _normalize_url(cls, value: object) -> str:
        raw = cls._nonempty(value, "url")
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise ProductIdentityCurrentnessAcquisitionError("url must be absolute http(s)")
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        return urlunsplit((scheme, netloc, path, parsed.query, ""))


__all__ = [
    "AUTHORIZED_ARTIFACT_CLASSES",
    "FORBIDDEN_PRESELECTION_ARTIFACT_CLASSES",
    "BlindIdentityCurrentnessEvidenceProjectionV1",
    "GovernedProductIdentityCurrentnessEvidenceAcquirer",
    "ProductIdentityCurrentnessAcquisitionError",
    "ProductIdentityCurrentnessAcquisitionResult",
]
