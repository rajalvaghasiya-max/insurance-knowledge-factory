"""Blind metadata projection for neutral cold-start product selection.

This module is an information firewall, not an extractor. It consumes the existing
ProductSignalExtractor output and exposes only product-identity metadata needed by
a deterministic preselection process. Raw text, evidence windows, benefit signals,
waiting-period signals and other semantic buckets never cross this boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class PreselectionMetadataProjectionError(ValueError):
    """Raised when a product-signal payload cannot be projected safely."""


@dataclass(frozen=True)
class PreselectionMetadataProjection:
    schema_version: str
    projection_type: str
    insurer_id: str
    source_url: str
    source_content_hash: str
    page_intent: str
    asset_scope: str
    classification_rules_version: str
    product_names: tuple[str, ...]
    uins: tuple[str, ...]
    uin_candidates: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "projection_type": self.projection_type,
            "insurer_id": self.insurer_id,
            "source_url": self.source_url,
            "source_content_hash": self.source_content_hash,
            "page_intent": self.page_intent,
            "asset_scope": self.asset_scope,
            "classification_rules_version": self.classification_rules_version,
            "product_names": list(self.product_names),
            "uins": list(self.uins),
            "uin_candidates": [dict(item) for item in self.uin_candidates],
        }


class BlindPreselectionMetadataProjector:
    """Project identity-only metadata from existing product-signal output."""

    SCHEMA_VERSION = "1.0"
    PROJECTION_TYPE = "blind_preselection_product_metadata_v1"
    _SAFE_CANDIDATE_SOURCE_KEYS = frozenset({
        "insurer_id",
        "url",
        "content_hash",
        "source_parsed_file",
    })

    @classmethod
    def project(cls, signals: Mapping[str, Any]) -> PreselectionMetadataProjection:
        if not isinstance(signals, Mapping):
            raise PreselectionMetadataProjectionError("signals must be a mapping")

        insurer_id = cls._text(signals.get("insurer_id"), "insurer_id")
        source_url = cls._text(signals.get("url"), "url")
        content_hash = cls._text(signals.get("content_hash"), "content_hash")
        page_intent = cls._text(signals.get("page_intent"), "page_intent")
        asset_scope = cls._text(signals.get("asset_scope"), "asset_scope")
        rules_version = cls._text(
            signals.get("classification_rules_version"),
            "classification_rules_version",
        )

        product_names = cls._product_names(signals.get("product_names", []))
        uins = cls._uins(signals.get("uins", []))
        candidates = cls._uin_candidates(signals.get("uin_candidates", []))

        candidate_uins = {item["uin"] for item in candidates}
        if candidate_uins and not candidate_uins.issubset(set(uins)):
            raise PreselectionMetadataProjectionError(
                "uin_candidates must be represented in the normalized uins list"
            )

        return PreselectionMetadataProjection(
            schema_version=cls.SCHEMA_VERSION,
            projection_type=cls.PROJECTION_TYPE,
            insurer_id=insurer_id,
            source_url=source_url,
            source_content_hash=content_hash,
            page_intent=page_intent,
            asset_scope=asset_scope,
            classification_rules_version=rules_version,
            product_names=product_names,
            uins=uins,
            uin_candidates=candidates,
        )

    @staticmethod
    def _text(value: object, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise PreselectionMetadataProjectionError(f"{label} must be non-empty text")
        return value.strip()

    @classmethod
    def _product_names(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            raise PreselectionMetadataProjectionError("product_names must be a list")
        names: set[str] = set()
        for item in value:
            if isinstance(item, str):
                name = item.strip()
            elif isinstance(item, Mapping):
                raw = item.get("name")
                name = raw.strip() if isinstance(raw, str) else ""
            else:
                name = ""
            if name:
                names.add(name)
        return tuple(sorted(names))

    @classmethod
    def _uins(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            raise PreselectionMetadataProjectionError("uins must be a list")
        normalized: set[str] = set()
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise PreselectionMetadataProjectionError("uins must contain non-empty text")
            normalized.add(item.strip().upper())
        return tuple(sorted(normalized))

    @classmethod
    def _uin_candidates(cls, value: object) -> tuple[Mapping[str, Any], ...]:
        if not isinstance(value, list):
            raise PreselectionMetadataProjectionError("uin_candidates must be a list")
        projected: list[dict[str, Any]] = []
        seen: set[tuple[str, str, tuple[tuple[str, str], ...]]] = set()
        for raw in value:
            if not isinstance(raw, Mapping):
                raise PreselectionMetadataProjectionError("uin_candidates entries must be mappings")
            uin = cls._text(raw.get("uin"), "uin_candidates[].uin").upper()
            status = cls._text(
                raw.get("candidate_status"),
                "uin_candidates[].candidate_status",
            )
            method = cls._text(
                raw.get("extraction_method"),
                "uin_candidates[].extraction_method",
            )
            source_raw = raw.get("source")
            if not isinstance(source_raw, Mapping):
                raise PreselectionMetadataProjectionError(
                    "uin_candidates[].source must be a mapping"
                )
            source = {
                key: source_raw[key]
                for key in sorted(cls._SAFE_CANDIDATE_SOURCE_KEYS)
                if isinstance(source_raw.get(key), str) and source_raw.get(key).strip()
            }
            source = {key: str(value).strip() for key, value in source.items()}
            marker = (uin, method, tuple(sorted(source.items())))
            if marker in seen:
                continue
            seen.add(marker)
            projected.append(
                {
                    "uin": uin,
                    "candidate_status": status,
                    "extraction_method": method,
                    "source": source,
                }
            )
        return tuple(sorted(projected, key=lambda item: (item["uin"], item["extraction_method"])))


__all__ = [
    "BlindPreselectionMetadataProjector",
    "PreselectionMetadataProjection",
    "PreselectionMetadataProjectionError",
]
