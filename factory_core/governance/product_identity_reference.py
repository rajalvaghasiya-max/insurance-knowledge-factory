"""P1.5a-1 — durable product identity reference records.

Creates reviewable, non-mutating product identity records used by document
identity overlays. A record is evidence-backed and human-reviewed, but it
does not publish insurance facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


class ProductIdentityReferenceError(ValueError):
    """Raised when a product identity reference is incomplete or unsafe."""


_ALLOWED_SIGNAL_TYPES = frozenset({
    "uin_exact_match", "canonical_title_match", "source_page_association",
    "issuer_label_match", "manual_product_review",
})
_ALLOWED_SIGNAL_VERIFICATION = frozenset({
    "product_identity_report", "document_embedded_text",
    "source_page_metadata", "manual_reviewed",
})


@dataclass(frozen=True)
class ProductIdentityReferenceResult:
    manifest: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ProductIdentityReferenceError(f"{label} must be a JSON object")
    return value


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProductIdentityReferenceError(f"{label} must be a JSON array")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProductIdentityReferenceError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise ProductIdentityReferenceError(f"{label} must be a safe repository-relative path")
    return path.as_posix()


def _validate_uin(value: object, label: str) -> str:
    uin = _nonempty(value, label).upper()
    if len(uin) < 8 or any(ch.isspace() for ch in uin):
        raise ProductIdentityReferenceError(f"{label} must be a compact UIN-like identifier")
    return uin


class ProductIdentityReference:
    """Builds a durable product identity reference record."""

    def build_from_spec_file(
        self, *, spec_path: str | Path, repository_root: str | Path
    ) -> ProductIdentityReferenceResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Product identity specification was not found: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProductIdentityReferenceError(
                f"Invalid product identity specification JSON: {path}"
            ) from exc
        return self.build(spec=_mapping(raw, "product_identity_spec"), repository_root=repository_root)

    def build(
        self, *, spec: Mapping[str, Any], repository_root: str | Path,
        reviewed_at: str | None = None
    ) -> ProductIdentityReferenceResult:
        # repository_root is deliberately accepted for a stable public API and
        # future evidence-path verification; this v1 does not mutate or load sources.
        Path(repository_root).resolve()
        spec = _mapping(spec, "product_identity_spec")
        if spec.get("schema_version") != "1.0":
            raise ProductIdentityReferenceError("product_identity_spec.schema_version must be 1.0")
        if spec.get("record_type") != "product_identity_reference_v1":
            raise ProductIdentityReferenceError(
                "product_identity_spec.record_type must be product_identity_reference_v1"
            )
        if spec.get("reviewed_by_human") is not True:
            raise ProductIdentityReferenceError("product_identity_spec.reviewed_by_human must be true")

        raw_product = _mapping(spec.get("product_identity"), "product_identity")
        product = {
            "entity_id": _nonempty(raw_product.get("entity_id"), "product_identity.entity_id"),
            "insurer_id": _nonempty(raw_product.get("insurer_id"), "product_identity.insurer_id"),
            "product_id": _nonempty(raw_product.get("product_id"), "product_identity.product_id"),
            "canonical_product_name": _nonempty(
                raw_product.get("canonical_product_name"), "product_identity.canonical_product_name"
            ),
            "uin": _validate_uin(raw_product.get("uin"), "product_identity.uin"),
        }
        expected_entity = f"{product['insurer_id']}:{product['product_id']}"
        if product["entity_id"] != expected_entity:
            raise ProductIdentityReferenceError(
                "product_identity.entity_id must equal insurer_id:product_id"
            )

        aliases_raw = spec.get("aliases", [])
        aliases: list[str] = []
        seen_aliases: set[str] = set()
        for index, value in enumerate(_list(aliases_raw, "aliases")):
            alias = _nonempty(value, f"aliases[{index}]")
            key = alias.casefold()
            if key in seen_aliases:
                raise ProductIdentityReferenceError("aliases must not contain duplicates")
            seen_aliases.add(key)
            aliases.append(alias)

        evidence_raw = _list(spec.get("identity_evidence"), "identity_evidence")
        if not evidence_raw:
            raise ProductIdentityReferenceError("identity_evidence must not be empty")
        evidence: list[dict[str, str]] = []
        seen_evidence: set[tuple[str, str]] = set()
        has_uin = False
        has_manual = False
        for index, value in enumerate(evidence_raw):
            item = _mapping(value, f"identity_evidence[{index}]")
            signal_type = _nonempty(item.get("signal_type"), f"identity_evidence[{index}].signal_type")
            verification = _nonempty(item.get("verification"), f"identity_evidence[{index}].verification")
            reference = _nonempty(item.get("evidence_reference"), f"identity_evidence[{index}].evidence_reference")
            if signal_type not in _ALLOWED_SIGNAL_TYPES:
                raise ProductIdentityReferenceError(f"unsupported signal_type {signal_type!r}")
            if verification not in _ALLOWED_SIGNAL_VERIFICATION:
                raise ProductIdentityReferenceError(f"unsupported signal verification {verification!r}")
            key = (signal_type, reference)
            if key in seen_evidence:
                raise ProductIdentityReferenceError(
                    "identity_evidence must not contain duplicate type/reference pairs"
                )
            seen_evidence.add(key)
            has_uin = has_uin or signal_type == "uin_exact_match"
            has_manual = has_manual or verification == "manual_reviewed"
            evidence.append({
                "signal_type": signal_type,
                "verification": verification,
                "evidence_reference": reference,
            })
        if not (has_uin and has_manual):
            raise ProductIdentityReferenceError(
                "identity_evidence requires a uin_exact_match and at least one manual_reviewed signal"
            )

        rationale = _nonempty(spec.get("review_rationale"), "review_rationale")
        manifest = {
            "schema_version": "1.0",
            "record_type": "product_identity_reference_v1",
            "record_status": "reviewed_product_identity_recorded_not_published",
            "product_identity": product,
            "aliases": aliases,
            "identity_resolution_status": "resolved",
            "identity_evidence": evidence,
            "review_rationale": rationale,
            "reviewed_by_human": True,
            "reviewed_at": reviewed_at or datetime.now(timezone.utc).isoformat(),
            "guardrails": [
                "This record establishes reviewed product identity only; it does not establish document-version compatibility.",
                "A UIN is a strong identity signal, but it does not establish a current product entitlement.",
                "This record is non-mutating and does not publish insurance facts or alter source-registration, classification, or authority artifacts.",
            ],
        }
        return ProductIdentityReferenceResult(manifest=manifest)

    def write_output(
        self, result: ProductIdentityReferenceResult, *, repository_root: str | Path,
        output_path: str | Path
    ) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative_path(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ProductIdentityReferenceError(
                "output_path must remain under repository_root"
            ) from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(result.manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
