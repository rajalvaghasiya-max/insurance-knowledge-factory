"""Reusable insurance rule-family definitions and contract validation.

A rule family describes the semantic shape shared by many product-specific
contracts. Product contracts provide evidence-bound values; the family registry
provides reusable component, attribute, type, and vocabulary requirements.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from insurance_intelligence.contracts.semantic_fidelity import (
    ExplanationSemanticContract,
    SemanticAttribute,
    SemanticKind,
    SemanticRiskTier,
)


class RuleFamilyRegistryError(ValueError):
    """Raised when a rule-family definition or contract binding is invalid."""


class SemanticValueType(str, Enum):
    STRING = "STRING"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    STRING_SET = "STRING_SET"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuleFamilyRegistryError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise RuleFamilyRegistryError(f"{field_name} must be a sequence")
    result = tuple(_text(value, field_name) for value in values)
    if len(result) != len(set(result)):
        raise RuleFamilyRegistryError(f"{field_name} must not contain duplicates")
    return result


@dataclass(frozen=True)
class RuleFamilyAttributeDefinition:
    name: str
    value_type: SemanticValueType
    required: bool = True
    canonical_values: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "name"))
        if not isinstance(self.value_type, SemanticValueType):
            raise RuleFamilyRegistryError("value_type must be a SemanticValueType")
        if not isinstance(self.required, bool):
            raise RuleFamilyRegistryError("required must be boolean")
        object.__setattr__(
            self,
            "canonical_values",
            _text_tuple(self.canonical_values, "canonical_values"),
        )
        if self.canonical_values and self.value_type is not SemanticValueType.STRING:
            raise RuleFamilyRegistryError(
                "canonical_values are supported only for STRING attributes"
            )


@dataclass(frozen=True)
class RuleFamilyComponentDefinition:
    role: str
    kind: SemanticKind
    risk_tier: SemanticRiskTier
    attributes: tuple[RuleFamilyAttributeDefinition, ...]
    required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _text(self.role, "role"))
        if not isinstance(self.kind, SemanticKind):
            raise RuleFamilyRegistryError("kind must be a SemanticKind")
        if not isinstance(self.risk_tier, SemanticRiskTier):
            raise RuleFamilyRegistryError("risk_tier must be a SemanticRiskTier")
        if not isinstance(self.required, bool):
            raise RuleFamilyRegistryError("required must be boolean")
        if not isinstance(self.attributes, tuple) or not self.attributes:
            raise RuleFamilyRegistryError("attributes must be a non-empty tuple")
        if not all(isinstance(item, RuleFamilyAttributeDefinition) for item in self.attributes):
            raise RuleFamilyRegistryError(
                "attributes must contain RuleFamilyAttributeDefinition values"
            )
        names = tuple(item.name for item in self.attributes)
        if len(names) != len(set(names)):
            raise RuleFamilyRegistryError("attribute names must be unique within a role")


@dataclass(frozen=True)
class RuleFamilyDefinition:
    family_id: str
    version: str
    components: tuple[RuleFamilyComponentDefinition, ...]
    supported_domains: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "family_id", _text(self.family_id, "family_id"))
        object.__setattr__(self, "version", _text(self.version, "version"))
        object.__setattr__(
            self,
            "supported_domains",
            _text_tuple(self.supported_domains, "supported_domains"),
        )
        if not self.supported_domains:
            raise RuleFamilyRegistryError("supported_domains must not be empty")
        if not isinstance(self.components, tuple) or not self.components:
            raise RuleFamilyRegistryError("components must be a non-empty tuple")
        if not all(isinstance(item, RuleFamilyComponentDefinition) for item in self.components):
            raise RuleFamilyRegistryError(
                "components must contain RuleFamilyComponentDefinition values"
            )
        roles = tuple(item.role for item in self.components)
        if len(roles) != len(set(roles)):
            raise RuleFamilyRegistryError("component roles must be unique")


@dataclass(frozen=True)
class RuleFamilyBinding:
    family_id: str
    family_version: str
    contract_id: str
    component_roles: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        for field_name in ("family_id", "family_version", "contract_id"):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if not isinstance(self.component_roles, tuple) or not self.component_roles:
            raise RuleFamilyRegistryError("component_roles must be a non-empty tuple")
        roles: list[str] = []
        component_ids: list[str] = []
        normalized: list[tuple[str, str]] = []
        for item in self.component_roles:
            if not isinstance(item, tuple) or len(item) != 2:
                raise RuleFamilyRegistryError("component_roles must contain (role, component_id)")
            role, component_id = item
            normalized.append((_text(role, "role"), _text(component_id, "component_id")))
            roles.append(normalized[-1][0])
            component_ids.append(normalized[-1][1])
        if len(roles) != len(set(roles)):
            raise RuleFamilyRegistryError("binding roles must be unique")
        if len(component_ids) != len(set(component_ids)):
            raise RuleFamilyRegistryError("bound component IDs must be unique")
        object.__setattr__(self, "component_roles", tuple(sorted(normalized)))

    def component_id_for(self, role: str) -> str | None:
        normalized_role = _text(role, "role")
        return dict(self.component_roles).get(normalized_role)


@dataclass(frozen=True)
class RuleFamilyValidationResult:
    valid: bool
    error_codes: tuple[str, ...]


def _attribute_type(attribute: SemanticAttribute) -> SemanticValueType:
    value = attribute.value
    if isinstance(value, bool):
        return SemanticValueType.BOOLEAN
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return SemanticValueType.NUMBER
    if isinstance(value, tuple):
        return SemanticValueType.STRING_SET
    return SemanticValueType.STRING


def validate_contract_against_family(
    contract: ExplanationSemanticContract,
    family: RuleFamilyDefinition,
    binding: RuleFamilyBinding,
) -> RuleFamilyValidationResult:
    errors: set[str] = set()
    if contract.rule_family != family.family_id:
        errors.add("RULE_FAMILY_ID_MISMATCH")
    if binding.family_id != family.family_id:
        errors.add("BINDING_FAMILY_ID_MISMATCH")
    if binding.family_version != family.version:
        errors.add("BINDING_FAMILY_VERSION_MISMATCH")
    if binding.contract_id != contract.contract_id:
        errors.add("BINDING_CONTRACT_ID_MISMATCH")

    contract_components = {item.component_id: item for item in contract.components}
    bound_roles = dict(binding.component_roles)
    family_roles = {item.role: item for item in family.components}

    if set(bound_roles) - set(family_roles):
        errors.add("UNKNOWN_BOUND_COMPONENT_ROLE")

    for role, definition in family_roles.items():
        component_id = bound_roles.get(role)
        if component_id is None:
            if definition.required:
                errors.add("MISSING_REQUIRED_COMPONENT_ROLE")
            continue
        component = contract_components.get(component_id)
        if component is None:
            errors.add("BOUND_COMPONENT_NOT_FOUND")
            continue
        if component.kind is not definition.kind:
            errors.add("COMPONENT_KIND_MISMATCH")
        if component.risk_tier is not definition.risk_tier:
            errors.add("COMPONENT_RISK_TIER_MISMATCH")

        observed = {attribute.name: attribute for attribute in component.attributes}
        expected = {attribute.name: attribute for attribute in definition.attributes}
        if set(observed) - set(expected):
            errors.add("SURPLUS_COMPONENT_ATTRIBUTE")
        for name, attribute_definition in expected.items():
            attribute = observed.get(name)
            if attribute is None:
                if attribute_definition.required:
                    errors.add("MISSING_REQUIRED_COMPONENT_ATTRIBUTE")
                continue
            if _attribute_type(attribute) is not attribute_definition.value_type:
                errors.add("COMPONENT_ATTRIBUTE_TYPE_MISMATCH")
            if attribute_definition.canonical_values:
                if not isinstance(attribute.value, str) or attribute.value not in attribute_definition.canonical_values:
                    errors.add("COMPONENT_ATTRIBUTE_VOCABULARY_MISMATCH")

    bound_component_ids = set(bound_roles.values())
    if set(contract_components) - bound_component_ids:
        errors.add("UNBOUND_CONTRACT_COMPONENT")

    return RuleFamilyValidationResult(valid=not errors, error_codes=tuple(sorted(errors)))


def build_conditional_copayment_family() -> RuleFamilyDefinition:
    """Return the first reusable rule family proven by the Star copayment case."""
    return RuleFamilyDefinition(
        family_id="CONDITIONAL_COPAYMENT",
        version="1.0",
        supported_domains=("HEALTH",),
        components=(
            RuleFamilyComponentDefinition(
                role="trigger",
                kind=SemanticKind.TRIGGER,
                risk_tier=SemanticRiskTier.RULE_LOGIC,
                attributes=(
                    RuleFamilyAttributeDefinition("subject", SemanticValueType.STRING, canonical_values=("insured_person", "policyholder", "claimant")),
                    RuleFamilyAttributeDefinition("attribute", SemanticValueType.STRING, canonical_values=("age_at_entry", "current_age")),
                    RuleFamilyAttributeDefinition("operator", SemanticValueType.STRING, canonical_values=("<", "<=", "=", ">=", ">")),
                    RuleFamilyAttributeDefinition("value", SemanticValueType.NUMBER),
                ),
            ),
            RuleFamilyComponentDefinition(
                role="effect",
                kind=SemanticKind.EFFECT,
                risk_tier=SemanticRiskTier.EXACT_VALUE,
                attributes=(
                    RuleFamilyAttributeDefinition("effect_type", SemanticValueType.STRING, canonical_values=("copayment",)),
                    RuleFamilyAttributeDefinition("percentage", SemanticValueType.NUMBER),
                    RuleFamilyAttributeDefinition("claim_scope", SemanticValueType.STRING, canonical_values=("each_and_every_claim", "aggregate_claims", "specified_claims")),
                ),
            ),
            RuleFamilyComponentDefinition(
                role="exception",
                kind=SemanticKind.EXCEPTION,
                risk_tier=SemanticRiskTier.RULE_LOGIC,
                attributes=(
                    RuleFamilyAttributeDefinition("age_operator", SemanticValueType.STRING, canonical_values=("<", "<=", "=", ">=", ">")),
                    RuleFamilyAttributeDefinition("age_value", SemanticValueType.NUMBER),
                    RuleFamilyAttributeDefinition("continuous_renewal", SemanticValueType.BOOLEAN),
                    RuleFamilyAttributeDefinition("logical_operator", SemanticValueType.STRING, canonical_values=("AND", "OR")),
                    RuleFamilyAttributeDefinition("policy_break", SemanticValueType.BOOLEAN),
                ),
                required=False,
            ),
            RuleFamilyComponentDefinition(
                role="scope",
                kind=SemanticKind.APPLICABILITY_SCOPE,
                risk_tier=SemanticRiskTier.EXACT_VALUE,
                attributes=(
                    RuleFamilyAttributeDefinition("mode", SemanticValueType.STRING, canonical_values=("exact_set", "range", "all")),
                    RuleFamilyAttributeDefinition("sections", SemanticValueType.STRING_SET),
                ),
            ),
        ),
    )


__all__ = [
    "RuleFamilyAttributeDefinition",
    "RuleFamilyBinding",
    "RuleFamilyComponentDefinition",
    "RuleFamilyDefinition",
    "RuleFamilyRegistryError",
    "RuleFamilyValidationResult",
    "SemanticValueType",
    "build_conditional_copayment_family",
    "validate_contract_against_family",
]
