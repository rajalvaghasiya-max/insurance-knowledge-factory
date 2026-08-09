"""Governed product identity reference adapter for ER-2.

The adapter converts already-reviewed ``product_identity_reference_v1`` specs
into the runtime entity registry. It does not verify source files itself or
weaken factory-side governance. Only human-reviewed records with an exact UIN
signal and a manual-review signal are admitted.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping, Any

from insurance_intelligence.entity_resolution.product_resolver import (
    GovernedProductEntity,
    GovernedProductEntityRegistry,
    ProductEntityRegistryError,
)


class ProductIdentityRegistryAdapterError(ValueError):
    """Raised when a governed identity reference cannot enter runtime use."""


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ProductIdentityRegistryAdapterError(f"{label} must be a JSON object")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProductIdentityRegistryAdapterError(f"{label} must be non-empty text")
    return value.strip()


def _strings(value: object, label: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ProductIdentityRegistryAdapterError(f"{label} must be a JSON array")
    return tuple(_text(item, f"{label}[]") for item in value)


def governed_entity_from_reference(spec: Mapping[str, Any]) -> GovernedProductEntity:
    spec = _mapping(spec, "product_identity_reference")
    if spec.get("schema_version") != "1.0":
        raise ProductIdentityRegistryAdapterError("schema_version must be 1.0")
    if spec.get("record_type") != "product_identity_reference_v1":
        raise ProductIdentityRegistryAdapterError(
            "record_type must be product_identity_reference_v1"
        )
    if spec.get("reviewed_by_human") is not True:
        raise ProductIdentityRegistryAdapterError(
            "product identity reference must be human reviewed"
        )

    product = _mapping(spec.get("product_identity"), "product_identity")
    evidence = spec.get("identity_evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ProductIdentityRegistryAdapterError("identity_evidence must not be empty")

    has_uin_exact = False
    has_manual_review = False
    for index, raw in enumerate(evidence):
        item = _mapping(raw, f"identity_evidence[{index}]")
        signal_type = _text(item.get("signal_type"), f"identity_evidence[{index}].signal_type")
        verification = _text(item.get("verification"), f"identity_evidence[{index}].verification")
        _text(item.get("evidence_reference"), f"identity_evidence[{index}].evidence_reference")
        has_uin_exact = has_uin_exact or signal_type == "uin_exact_match"
        has_manual_review = has_manual_review or (
            signal_type == "manual_product_review" and verification == "manual_reviewed"
        )

    if not has_uin_exact:
        raise ProductIdentityRegistryAdapterError(
            "runtime identity requires uin_exact_match evidence"
        )
    if not has_manual_review:
        raise ProductIdentityRegistryAdapterError(
            "runtime identity requires manual_product_review/manual_reviewed evidence"
        )

    try:
        return GovernedProductEntity(
            canonical_entity_id=_text(product.get("entity_id"), "product_identity.entity_id"),
            insurer_id=_text(product.get("insurer_id"), "product_identity.insurer_id"),
            product_id=_text(product.get("product_id"), "product_identity.product_id"),
            canonical_product_name=_text(
                product.get("canonical_product_name"),
                "product_identity.canonical_product_name",
            ),
            uin=_text(product.get("uin"), "product_identity.uin"),
            aliases=_strings(spec.get("aliases", []), "aliases"),
            product_variants=(),
        )
    except ProductEntityRegistryError as exc:
        raise ProductIdentityRegistryAdapterError(str(exc)) from exc


def build_runtime_registry_from_references(
    specs: Iterable[Mapping[str, Any]],
) -> GovernedProductEntityRegistry:
    entities = tuple(governed_entity_from_reference(spec) for spec in specs)
    try:
        return GovernedProductEntityRegistry(entities)
    except ProductEntityRegistryError as exc:
        raise ProductIdentityRegistryAdapterError(str(exc)) from exc


def load_runtime_registry_from_files(paths: Iterable[str | Path]) -> GovernedProductEntityRegistry:
    specs = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            raise FileNotFoundError(f"product identity reference not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProductIdentityRegistryAdapterError(
                f"invalid product identity reference JSON: {path}"
            ) from exc
        specs.append(_mapping(payload, str(path)))
    return build_runtime_registry_from_references(specs)
