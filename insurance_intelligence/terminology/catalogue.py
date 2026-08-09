"""Controlled canonical concept-family catalogue for MO-024D.1.

This module defines only insurer-neutral canonical concept families. It does not
publish insurer marketing terms, product implementations, aliases, or resolver
matches. Those remain separate governed records.
"""
from __future__ import annotations

from insurance_intelligence.contracts.terminology import CanonicalConceptFamily
from insurance_intelligence.terminology.registry import TerminologyRegistrySnapshot


COPAYMENT_CONCEPT = CanonicalConceptFamily(
    concept_family_id="health:cost_sharing:copayment",
    canonical_name="Copayment",
    definition=(
        "A cost-sharing arrangement under which the insured person bears a "
        "specified proportion of an otherwise admissible claim or covered expense, "
        "subject to the policy terms."
    ),
    domain="health",
    concept_subtype="cost_sharing",
)


DEDUCTIBLE_CONCEPT = CanonicalConceptFamily(
    concept_family_id="health:cost_sharing:deductible",
    canonical_name="Deductible",
    definition=(
        "A cost-sharing threshold that must be borne or satisfied before the "
        "insurer becomes liable for covered expenses, with the applicable basis "
        "and period determined by the policy terms."
    ),
    domain="health",
    concept_subtype="cost_sharing",
)


RESTORATION_BENEFIT_CONCEPT = CanonicalConceptFamily(
    concept_family_id="health:coverage_capacity:restoration_benefit",
    canonical_name="Restoration Benefit",
    definition=(
        "A benefit that replenishes or makes additional coverage capacity available "
        "after a policy-defined trigger, subject to product-specific conditions, "
        "scope, frequency, and utilisation rules."
    ),
    domain="health",
    concept_subtype="coverage_capacity",
)


INITIAL_CANONICAL_CONCEPTS = (
    COPAYMENT_CONCEPT,
    DEDUCTIBLE_CONCEPT,
    RESTORATION_BENEFIT_CONCEPT,
)


def build_initial_canonical_catalogue_snapshot() -> TerminologyRegistrySnapshot:
    """Return the controlled concept-only registry snapshot for MO-024D.1."""
    return TerminologyRegistrySnapshot(
        marketing_terms=(),
        implementations=(),
        concepts=INITIAL_CANONICAL_CONCEPTS,
        alias_candidates=(),
    )


__all__ = [
    "COPAYMENT_CONCEPT",
    "DEDUCTIBLE_CONCEPT",
    "RESTORATION_BENEFIT_CONCEPT",
    "INITIAL_CANONICAL_CONCEPTS",
    "build_initial_canonical_catalogue_snapshot",
]
