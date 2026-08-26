"""Blind projection for machine-discovered metadata destinations.

The existing discovery stack may inspect raw HTML, anchor text and destination URLs
machine-side. This module is the information firewall that prevents those potentially
semantic-bearing values from crossing to the operator/selector. It is not a crawler
and it does not classify destinations itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping


class BlindDiscoveryLinkProjectionError(ValueError):
    """Raised when a discovery record cannot be projected safely."""


@dataclass(frozen=True)
class BlindDiscoveryLinkProjection:
    schema_version: str
    projection_type: str
    source_id: str
    destination_id: str
    discovery_record_hash: str
    page_type: str
    knowledge_value: str
    crawl: bool
    priority: int
    discovery_origin: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "projection_type": self.projection_type,
            "source_id": self.source_id,
            "destination_id": self.destination_id,
            "discovery_record_hash": self.discovery_record_hash,
            "page_type": self.page_type,
            "knowledge_value": self.knowledge_value,
            "crawl": self.crawl,
            "priority": self.priority,
            "discovery_origin": self.discovery_origin,
        }


class BlindDiscoveryLinkProjector:
    """Project an opaque selector-facing view of an existing discovery record."""

    SCHEMA_VERSION = "1.0"
    PROJECTION_TYPE = "blind_discovery_link_metadata_v1"
    AUTHORIZED_METADATA_PAGE_TYPES = frozenset(
        {
            "download_page",
            "public_disclosure",
            "regulatory",
            "uin_related",
            "withdrawn_products",
        }
    )

    @classmethod
    def project(cls, record: Mapping[str, Any]) -> BlindDiscoveryLinkProjection:
        if not isinstance(record, Mapping):
            raise BlindDiscoveryLinkProjectionError("record must be a mapping")

        source_id = cls._source_id(record)
        destination_url = cls._text(record.get("discovered_url"), "discovered_url")
        page_type = cls._text(record.get("page_type"), "page_type")
        knowledge_value = cls._text(record.get("knowledge_value"), "knowledge_value")
        discovery_origin = cls._text(
            record.get("discovery_origin", "captured_html"),
            "discovery_origin",
        )

        if page_type not in cls.AUTHORIZED_METADATA_PAGE_TYPES:
            raise BlindDiscoveryLinkProjectionError(
                f"page_type is not authorized for blind metadata traversal: {page_type}"
            )

        crawl = record.get("crawl")
        if crawl is not True:
            raise BlindDiscoveryLinkProjectionError("crawl must be exactly true")

        priority = record.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int) or priority < 1:
            raise BlindDiscoveryLinkProjectionError("priority must be a positive integer")

        return BlindDiscoveryLinkProjection(
            schema_version=cls.SCHEMA_VERSION,
            projection_type=cls.PROJECTION_TYPE,
            source_id=source_id,
            destination_id=cls._opaque_hash(destination_url),
            discovery_record_hash=cls._record_hash(record),
            page_type=page_type,
            knowledge_value=knowledge_value,
            crawl=True,
            priority=priority,
            discovery_origin=discovery_origin,
        )

    @classmethod
    def _source_id(cls, record: Mapping[str, Any]) -> str:
        raw = record.get("source_id") or record.get("insurer_id")
        return cls._text(raw, "source_id")

    @staticmethod
    def _text(value: object, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise BlindDiscoveryLinkProjectionError(f"{label} must be non-empty text")
        return value.strip()

    @staticmethod
    def _opaque_hash(value: str) -> str:
        return "sha256:" + sha256(value.encode("utf-8")).hexdigest()

    @classmethod
    def _record_hash(cls, record: Mapping[str, Any]) -> str:
        try:
            canonical = json.dumps(
                record,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                default=str,
            )
        except Exception as exc:  # pragma: no cover - defensive serialization guard
            raise BlindDiscoveryLinkProjectionError(
                "discovery record cannot be deterministically hashed"
            ) from exc
        return cls._opaque_hash(canonical)


__all__ = [
    "BlindDiscoveryLinkProjection",
    "BlindDiscoveryLinkProjectionError",
    "BlindDiscoveryLinkProjector",
]
