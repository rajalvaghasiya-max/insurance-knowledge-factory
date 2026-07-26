"""Product Identity Resolution capability."""

from knowledge_domains.product.identity.product_identity_models import (
    IdentityResolutionStatus,
    ProductIdentityDecision,
)
from knowledge_domains.product.identity.product_identity_resolver import (
    ProductIdentityRegistryBuilder,
    ProductIdentityResolver,
)

__all__ = [
    "IdentityResolutionStatus",
    "ProductIdentityDecision",
    "ProductIdentityRegistryBuilder",
    "ProductIdentityResolver",
]
