"""Registry-backed field-selection policy for governed Health currency facts."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping


class HealthFieldSelectionPolicyError(ValueError):
    pass


class HealthFieldSelectionPolicy:
    REGISTRY_SCHEMA_VERSION = "0.2"

    @classmethod
    @lru_cache(maxsize=1)
    def _policies(cls) -> dict[str, dict[str, Any]]:
        path = Path(__file__).with_name("health_field_registry.json")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HealthFieldSelectionPolicyError("Health Field Registry is unavailable or invalid JSON") from exc
        if raw.get("schema_version") != cls.REGISTRY_SCHEMA_VERSION:
            raise HealthFieldSelectionPolicyError(
                f"Health Field Registry schema_version must be {cls.REGISTRY_SCHEMA_VERSION}"
            )
        fields = raw.get("fields")
        if not isinstance(fields, list):
            raise HealthFieldSelectionPolicyError("Health Field Registry fields must be a list")
        policies: dict[str, dict[str, Any]] = {}
        for field in fields:
            if not isinstance(field, Mapping):
                raise HealthFieldSelectionPolicyError("Health Field Registry field entries must be objects")
            field_id = field.get("field_id")
            policy = field.get("selection_policy")
            if policy is None:
                continue
            if not isinstance(field_id, str) or not field_id.strip() or not isinstance(policy, Mapping):
                raise HealthFieldSelectionPolicyError("selection-policy fields require non-empty field_id and policy")
            role = policy.get("reviewed_role")
            if not isinstance(role, str) or not role.strip() or role in policies:
                raise HealthFieldSelectionPolicyError("reviewed_role must be non-empty and unique")
            if policy.get("positive_inr_currency_only") is not True:
                raise HealthFieldSelectionPolicyError("selection_policy requires positive_inr_currency_only=true")
            if not isinstance(policy.get("requires_benefit_scope"), bool) or not isinstance(policy.get("requires_band_scope"), bool):
                raise HealthFieldSelectionPolicyError("selection_policy scope flags must be boolean")
            if not isinstance(policy.get("canonical_identity_includes_normalized_value"), bool):
                raise HealthFieldSelectionPolicyError(
                    "selection_policy canonical_identity_includes_normalized_value must be boolean"
                )
            policies[role] = {
                "field_id": field_id,
                "requires_benefit_scope": policy["requires_benefit_scope"],
                "requires_band_scope": policy["requires_band_scope"],
                "canonical_identity_includes_normalized_value": policy[
                    "canonical_identity_includes_normalized_value"
                ],
            }
        if not policies:
            raise HealthFieldSelectionPolicyError("Health Field Registry defines no selection policies")
        return policies

    @classmethod
    def field_for_role(cls, role: object) -> str | None:
        return cls._policies().get(role, {}).get("field_id") if isinstance(role, str) else None

    @classmethod
    def supported_field_keys(cls) -> set[str]:
        return {item["field_id"] for item in cls._policies().values()}

    @classmethod
    def canonical_identity_includes_normalized_value(cls, field_key: object) -> bool:
        policy = next((item for item in cls._policies().values() if item["field_id"] == field_key), None)
        if policy is None:
            raise HealthFieldSelectionPolicyError(
                "canonical field is not defined by the Health Field Registry selection policy"
            )
        return bool(policy["canonical_identity_includes_normalized_value"])

    @classmethod
    def validate_selection_scope(cls, *, field_key: object, benefit_scope: object, band_scope: object) -> str | None:
        policy = next((item for item in cls._policies().values() if item["field_id"] == field_key), None)
        if policy is None:
            return "canonical field is not defined by the Health Field Registry selection policy"
        if policy["requires_benefit_scope"] and not cls._non_empty(benefit_scope):
            return "accepted reviewed value requires selected_benefit_scope under the Health Field Registry policy"
        if policy["requires_band_scope"] and not cls._non_empty(band_scope):
            return "accepted reviewed value requires selected_band_scope under the Health Field Registry policy"
        return None

    @staticmethod
    def _non_empty(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())
