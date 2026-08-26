"""Blind metadata projections for neutral cold-start product selection.

These projectors are information firewalls, not extractors. They consume existing
ProductSignalExtractor output and expose only product-identity metadata needed by
a deterministic preselection process.

V1 is retained unchanged for historical reproducibility. V2 prospectively removes
raw source locations from the selector boundary and replaces them with opaque,
deterministic source references.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
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


@dataclass(frozen=True)
class PreselectionMetadataProjectionV2:
    schema_version: str
    projection_type: str
    insurer_id: str
    source_ref: str
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
            "source_ref": self.source_ref,
            "source_content_hash": self.source_content_hash,
            "page_intent": self.page_intent,
            "asset_scope": self.asset_scope,
            "classification_rules_version": self.classification_rules_version,
            "product_names": list(self.product_names),
            "uins": list(self.uins),
            "uin_candidates": [dict(item) for item in self.uin_candidates],
        }


class BlindPreselectionMetadataProjector:
    """Historical v1 projection retained for immutable experiment replay."""

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


class BlindPreselectionMetadataProjectorV2:
    """Prospective selector projection with no raw source locations."""

    SCHEMA_VERSION = "2.0"
    PROJECTION_TYPE = "blind_preselection_product_metadata_v2"

    @classmethod
    def project(cls, signals: Mapping[str, Any]) -> PreselectionMetadataProjectionV2:
        if not isinstance(signals, Mapping):
            raise PreselectionMetadataProjectionError("signals must be a mapping")

        insurer_id = BlindPreselectionMetadataProjector._text(signals.get("insurer_id"), "insurer_id")
        source_url = BlindPreselectionMetadataProjector._text(signals.get("url"), "url")
        content_hash = BlindPreselectionMetadataProjector._text(signals.get("content_hash"), "content_hash")
        page_intent = BlindPreselectionMetadataProjector._text(signals.get("page_intent"), "page_intent")
        asset_scope = BlindPreselectionMetadataProjector._text(signals.get("asset_scope"), "asset_scope")
        rules_version = BlindPreselectionMetadataProjector._text(
            signals.get("classification_rules_version"),
            "classification_rules_version",
        )

        product_names = BlindPreselectionMetadataProjector._product_names(
            signals.get("product_names", [])
        )
        uins = BlindPreselectionMetadataProjector._uins(signals.get("uins", []))
        source_ref = cls._source_ref(insurer_id, source_url, content_hash)
        candidates = cls._uin_candidates(
            signals.get("uin_candidates", []),
            default_insurer_id=insurer_id,
            default_source_url=source_url,
            default_content_hash=content_hash,
        )

        candidate_uins = {item["uin"] for item in candidates}
        if candidate_uins and not candidate_uins.issubset(set(uins)):
            raise PreselectionMetadataProjectionError(
                "uin_candidates must be represented in the normalized uins list"
            )

        return PreselectionMetadataProjectionV2(
            schema_version=cls.SCHEMA_VERSION,
            projection_type=cls.PROJECTION_TYPE,
            insurer_id=insurer_id,
            source_ref=source_ref,
            source_content_hash=content_hash,
            page_intent=page_intent,
            asset_scope=asset_scope,
            classification_rules_version=rules_version,
            product_names=product_names,
            uins=uins,
            uin_candidates=candidates,
        )

    @staticmethod
    def _source_ref(insurer_id: str, source_url: str, content_hash: str) -> str:
        material = "\x1f".join((insurer_id, source_url, content_hash)).encode("utf-8")
        return f"src_sha256:{sha256(material).hexdigest()}"

    @classmethod
    def _uin_candidates(
        cls,
        value: object,
        *,
        default_insurer_id: str,
        default_source_url: str,
        default_content_hash: str,
    ) -> tuple[Mapping[str, Any], ...]:
        if not isinstance(value, list):
            raise PreselectionMetadataProjectionError("uin_candidates must be a list")

        projected: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for raw in value:
            if not isinstance(raw, Mapping):
                raise PreselectionMetadataProjectionError("uin_candidates entries must be mappings")

            uin = BlindPreselectionMetadataProjector._text(
                raw.get("uin"), "uin_candidates[].uin"
            ).upper()
            status = BlindPreselectionMetadataProjector._text(
                raw.get("candidate_status"),
                "uin_candidates[].candidate_status",
            )
            method = BlindPreselectionMetadataProjector._text(
                raw.get("extraction_method"),
                "uin_candidates[].extraction_method",
            )
            source_raw = raw.get("source")
            if not isinstance(source_raw, Mapping):
                raise PreselectionMetadataProjectionError(
                    "uin_candidates[].source must be a mapping"
                )

            insurer_id = cls._optional_text(source_raw.get("insurer_id")) or default_insurer_id
            source_url = cls._optional_text(source_raw.get("url")) or default_source_url
            content_hash = cls._optional_text(source_raw.get("content_hash")) or default_content_hash
            source_ref = cls._source_ref(insurer_id, source_url, content_hash)
            marker = (uin, method, source_ref)
            if marker in seen:
                continue
            seen.add(marker)
            projected.append(
                {
                    "uin": uin,
                    "candidate_status": status,
                    "extraction_method": method,
                    "source": {
                        "insurer_id": insurer_id,
                        "source_ref": source_ref,
                        "content_hash": content_hash,
                    },
                }
            )

        return tuple(
            sorted(
                projected,
                key=lambda item: (
                    item["uin"],
                    item["extraction_method"],
                    item["source"]["source_ref"],
                ),
            )
        )

    @staticmethod
    def _optional_text(value: object) -> str:
        return value.strip() if isinstance(value, str) and value.strip() else ""


__all__ = [
    "BlindPreselectionMetadataProjector",
    "BlindPreselectionMetadataProjectorV2",
    "PreselectionMetadataProjection",
    "PreselectionMetadataProjectionV2",
    "PreselectionMetadataProjectionError",
]
