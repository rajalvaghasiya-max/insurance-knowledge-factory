"""Generic governed product-instance binding for canonical response orchestration.

This module does not infer product identity from text.  It binds active product-compatible
context values to the already-declared orchestration ProductScope only when the existing
governed ProductEntityResolver independently resolves the value to that exact product.
The resulting attestations can be consumed by Instance Sufficiency and the same canonical
identity substitutions can be passed to publication-backed evidence resolution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from insurance_intelligence.context.requirements import requirements_for_intent
from insurance_intelligence.contracts.authority_intent_reconciliation import (
    AuthorityIntentReconciliationOutput,
)
from insurance_intelligence.contracts.context import ContextBuilderOutput
from insurance_intelligence.contracts.full_cycle import ProductScope
from insurance_intelligence.contracts.instance_sufficiency import (
    InstanceResolutionAttestation,
    build_attestation,
)
from insurance_intelligence.entity_resolution.product_resolver import (
    GovernedProductEntityRegistry,
    ProductEntityResolution,
    ProductEntityResolver,
)


class ProductInstanceBindingError(ValueError):
    """Raised when governed product scope cannot be bound safely to runtime context."""


@dataclass(frozen=True)
class ProductIdentityRecordEvidence:
    canonical_entity_id: str
    identity_record_ref: str
    identity_record_hash: str

    def __post_init__(self) -> None:
        for label, value in (
            ("canonical_entity_id", self.canonical_entity_id),
            ("identity_record_ref", self.identity_record_ref),
            ("identity_record_hash", self.identity_record_hash),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ProductInstanceBindingError(f"{label} must be non-empty text")


IdentityRecordLookup = Callable[[str], ProductIdentityRecordEvidence | None]


@dataclass(frozen=True)
class ProductInstanceBinding:
    resolution: ProductEntityResolution
    identity_record: ProductIdentityRecordEvidence
    attestations: tuple[InstanceResolutionAttestation, ...]
    candidate_reference_pairs: tuple[tuple[str, str], ...]

    @property
    def resolved_candidate_references(self) -> dict[str, str]:
        return dict(self.candidate_reference_pairs)


def _scope_entity_id(scope: ProductScope) -> str:
    return f"{scope.insurer_id}:{scope.product_id}"


def _product_compatible_context_keys(primary_intent: str) -> frozenset[str]:
    requirements = requirements_for_intent(primary_intent)
    keys = {
        item.context_key
        for item in requirements
        if item.category == "PRODUCT"
    }
    # This governed key is intentionally dual-use: its contract explicitly permits
    # either a policy or a product reference, while its broad context category is POLICY.
    if any(item.context_key == "policy_or_product_reference" for item in requirements):
        keys.add("policy_or_product_reference")
    return frozenset(keys)


def bind_product_scope_to_context(
    *,
    product_scope: ProductScope,
    reconciliation: AuthorityIntentReconciliationOutput,
    context: ContextBuilderOutput,
    registry: GovernedProductEntityRegistry,
    identity_record_lookup: IdentityRecordLookup,
) -> ProductInstanceBinding:
    """Bind active context references to one governed product scope, fail-closed.

    The orchestration scope is first resolved by canonical entity ID through the existing
    governed registry.  Active context values are then independently resolved and receive
    attestations only when they resolve to that exact scoped product.  Text that does not
    resolve, resolves ambiguously, resolves to another product, or belongs to a policy-only
    context key remains unattested for Instance Sufficiency to reject later.
    """
    if not isinstance(product_scope, ProductScope):
        raise ProductInstanceBindingError("product_scope must be a validated ProductScope")
    if not isinstance(reconciliation, AuthorityIntentReconciliationOutput):
        raise ProductInstanceBindingError(
            "reconciliation must be a validated AuthorityIntentReconciliationOutput"
        )
    if not isinstance(context, ContextBuilderOutput):
        raise ProductInstanceBindingError("context must be a validated ContextBuilderOutput")
    if reconciliation.request_id != context.request_id:
        raise ProductInstanceBindingError("reconciliation and context request_id must match")
    if not isinstance(registry, GovernedProductEntityRegistry):
        raise ProductInstanceBindingError("registry must be a GovernedProductEntityRegistry")
    if not callable(identity_record_lookup):
        raise ProductInstanceBindingError("identity_record_lookup must be callable")

    resolver = ProductEntityResolver(registry)
    canonical_entity_id = _scope_entity_id(product_scope)
    scope_resolution = resolver.resolve(
        canonical_entity_id,
        insurer_id=product_scope.insurer_id,
    )
    selected = scope_resolution.selected_entity
    if (
        scope_resolution.status != "RESOLVED"
        or selected is None
        or selected.canonical_entity_id != canonical_entity_id
        or selected.insurer_id != product_scope.insurer_id
        or selected.product_id != product_scope.product_id
    ):
        raise ProductInstanceBindingError(
            "orchestration product_scope did not resolve to one exact governed product identity"
        )

    identity_record = identity_record_lookup(canonical_entity_id)
    if not isinstance(identity_record, ProductIdentityRecordEvidence):
        raise ProductInstanceBindingError(
            "governed product identity record evidence is required for scoped product"
        )
    if identity_record.canonical_entity_id != canonical_entity_id:
        raise ProductInstanceBindingError(
            "identity record evidence canonical_entity_id does not match resolved product scope"
        )

    compatible_keys = _product_compatible_context_keys(reconciliation.primary_intent)
    attestations: list[InstanceResolutionAttestation] = []
    substitutions: list[tuple[str, str]] = []

    active_items = tuple(
        item
        for item in context.resolved_context
        if item.status == "ACTIVE" and item.key in compatible_keys
    )
    for item in sorted(active_items, key=lambda value: value.key):
        if not isinstance(item.value, str) or not item.value.strip():
            continue
        candidate_resolution = resolver.resolve(
            item.value,
            insurer_id=product_scope.insurer_id,
        )
        candidate = candidate_resolution.selected_entity
        if (
            candidate_resolution.status != "RESOLVED"
            or candidate is None
            or candidate.canonical_entity_id != canonical_entity_id
        ):
            continue
        attestations.append(
            build_attestation(
                instance_kind="PRODUCT",
                context_key=item.key,
                resolution_status="RESOLVED",
                canonical_identity=canonical_entity_id,
                identity_record_ref=identity_record.identity_record_ref,
                identity_record_hash=identity_record.identity_record_hash,
                resolution_basis=(
                    "active context reference independently resolved through the governed "
                    "product registry and matched the canonical orchestration product scope"
                ),
            )
        )
        substitutions.append((item.key, canonical_entity_id))

    return ProductInstanceBinding(
        resolution=scope_resolution,
        identity_record=identity_record,
        attestations=tuple(attestations),
        candidate_reference_pairs=tuple(substitutions),
    )


__all__ = [
    "IdentityRecordLookup",
    "ProductIdentityRecordEvidence",
    "ProductInstanceBinding",
    "ProductInstanceBindingError",
    "bind_product_scope_to_context",
]
