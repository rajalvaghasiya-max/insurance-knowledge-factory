"""Deterministic Context Builder (MO-014 v0.1).

Boundary (MO-012, as extended by this order): may consume Intent
Analyzer output, user-provided context, approved conversation
context, session context, and document metadata; assembles typed,
provenance-tagged context and determines answerability. Must NOT
resolve authoritative product/policy identity, retrieve documents,
establish insurance facts, interpret clauses, calculate outcomes,
compare products, assess suitability, recommend, or generate final
answers.
"""
from __future__ import annotations

import re

from insurance_intelligence.contracts.context import (
    Assumption,
    ContextBuilderInput,
    ContextBuilderOutput,
    ContextConflict,
    MissingContextItem,
    ResolvedContextItem,
    build_assumption,
    build_context_conflict,
    build_missing_context_item,
    build_output,
    build_resolved_context_item,
)
from insurance_intelligence.context.requirements import requirements_for_intent

_CORRECTION_MARKERS = ("sorry", "actually", "i meant", "correction", "my mistake")

# Deterministic, bounded mapping from candidate-entity type to the context
# key it may provisionally populate for a given intent. Only entries
# listed here are ever auto-populated from candidate entities; anything
# else must come from explicit user_context.
_ENTITY_KEY_BY_INTENT: dict[str, dict[str, str]] = {
    "TERM_EXPLANATION": {"POLICY_FEATURE": "term_or_concept"},
    "PRODUCT_EXPLANATION": {"PRODUCT": "product_reference"},
    "ADVISOR_EXPLANATION": {"PRODUCT": "subject_reference"},
    "SUITABILITY_ASSESSMENT": {"PRODUCT": "subject_reference"},
    "CLAUSE_IMPLICATION": {"POLICY_FEATURE": "clause_or_feature", "PRODUCT": "policy_or_product_reference"},
    "COVERAGE_CHECK": {"CLAIM_CONCEPT": "coverage_subject", "PRODUCT": "policy_or_product_reference"},
    "EXCLUSION_CHECK": {"CLAIM_CONCEPT": "exclusion_subject", "PRODUCT": "policy_or_product_reference"},
    "CLAIM_SCENARIO": {"PRODUCT": "policy_or_product_reference", "FINANCIAL_VALUE": "claim_amount"},
    "DOCUMENT_INTERPRETATION": {"POLICY_FEATURE": "document_subject", "CLAIM_CONCEPT": "document_subject"},
}

_MULTI_VALUE_KEYS = {
    "PRODUCT_COMPARISON": ("comparison_subject_1", "comparison_subject_2"),
    "POLICY_COMPARISON": ("comparison_subject_1", "comparison_subject_2"),
    "QUOTE_COMPARISON": ("quote_reference_1", "quote_reference_2"),
}


class ContextBuilder:
    """Stateless deterministic context assembler. No I/O, no LLM call."""

    def build(self, request: ContextBuilderInput) -> ContextBuilderOutput:
        intent = request.intent_analysis.primary_intent

        if intent == "OUT_OF_SCOPE" or request.intent_analysis.analysis_status == "OUT_OF_SCOPE":
            return build_output(
                request_id=request.request_id,
                answerability="OUT_OF_SCOPE",
                context_completeness=0.0,
                classification_basis=["fallback_rule"],
            )

        resolved, basis_used = self._assemble_resolved_context(request)
        conflicts, resolved = self._detect_conflicts(request, resolved)
        assumptions: tuple[Assumption, ...] = ()

        # FOLLOW_UP-specific resolution.
        if intent == "FOLLOW_UP":
            follow_up = request.intent_analysis.follow_up
            if follow_up.is_follow_up and follow_up.reference_type == "prior_candidate_entity" and follow_up.referenced_text:
                resolved = resolved + (
                    build_resolved_context_item(
                        key="resolved_follow_up_reference",
                        value=follow_up.referenced_text,
                        category="CONVERSATION",
                        provenance="SYSTEM_DERIVED",
                        source_reference="intent_analysis.follow_up",
                        confidence=follow_up.confidence,
                        materiality="high",
                    ),
                )
                basis_used.add("conversation_reference")

        # Document processing failure gate (DOCUMENT_INTERPRETATION only, v0.1).
        if intent == "DOCUMENT_INTERPRETATION":
            for doc in request.document_context:
                if doc.processing_status == "FAILED":
                    return build_output(
                        request_id=request.request_id,
                        answerability="NOT_ANSWERABLE",
                        context_completeness=0.0,
                        resolved_context=resolved,
                        conflicts=conflicts,
                        classification_basis=["document_metadata"],
                    )

        required = requirements_for_intent(intent)
        resolved_keys = {item.key for item in resolved if item.status == "ACTIVE"}

        missing_required = tuple(
            build_missing_context_item(
                key=req.context_key,
                category=req.category,
                required=True,
                materiality=req.materiality,
                reason=f"{req.context_key} is required for {intent} and was not provided or resolved.",
                clarification_question=req.clarification_question,
            )
            for req in required
            if req.required and req.context_key not in resolved_keys
        )
        missing_optional = tuple(
            build_missing_context_item(
                key=req.context_key,
                category=req.category,
                required=False,
                materiality=req.materiality,
                reason=f"{req.context_key} is optional for {intent} and was not provided or resolved.",
                clarification_question=req.clarification_question,
            )
            for req in required
            if not req.required and req.context_key not in resolved_keys
        )

        blocking_conflicts = tuple(c for c in conflicts if c.resolution_status == "UNRESOLVED" and c.materiality == "high")

        completeness = _completeness_score(required, resolved_keys, blocking_conflicts, assumptions)

        answerability, clarification_questions = _determine_answerability(
            intent=intent,
            required=required,
            missing_required=missing_required,
            missing_optional=missing_optional,
            blocking_conflicts=blocking_conflicts,
            assumptions=assumptions,
        )

        classification_basis = tuple(sorted(basis_used)) if basis_used else ("fallback_rule",)

        return build_output(
            request_id=request.request_id,
            answerability=answerability,
            context_completeness=completeness,
            resolved_context=resolved,
            missing_required_context=missing_required,
            missing_optional_context=missing_optional,
            conflicts=conflicts,
            assumptions=assumptions,
            clarification_questions=clarification_questions,
            classification_basis=classification_basis,
        )

    # -- assembly ---------------------------------------------------------

    def _assemble_resolved_context(self, request: ContextBuilderInput) -> tuple[tuple[ResolvedContextItem, ...], set[str]]:
        items: list[ResolvedContextItem] = []
        basis_used: set[str] = set()

        # Priority 1: explicit user-provided context (highest).
        for user_item in request.user_context:
            items.append(
                build_resolved_context_item(
                    key=user_item.key,
                    value=user_item.value,
                    category=_category_for_key(user_item.key),
                    provenance="USER_PROVIDED",
                    source_reference=user_item.source_reference,
                    confidence=1.0,
                    materiality="high",
                )
            )
            basis_used.add("user_provided")

        already_resolved_keys = {item.key for item in items}

        # Priority 2: session context (previously accepted, carried forward).
        for session_item in request.session_context:
            if session_item.key in already_resolved_keys:
                continue
            items.append(session_item)
            already_resolved_keys.add(session_item.key)
            basis_used.add("session_context")

        # Priority 3: document metadata.
        for doc in request.document_context:
            key = "document_reference"
            if key not in already_resolved_keys and doc.processing_status in ("PROCESSED", "PENDING"):
                items.append(
                    build_resolved_context_item(
                        key=key,
                        value=doc.document_reference,
                        category="DOCUMENT",
                        provenance="DOCUMENT_RESOLVED",
                        source_reference=f"document_context:{doc.document_reference}",
                        confidence=0.95,
                        materiality="high",
                    )
                )
                already_resolved_keys.add(key)
                basis_used.add("document_metadata")

        # Priority 4: system-derived from candidate entities (intent-specific mapping).
        intent = request.intent_analysis.primary_intent
        mapping = _ENTITY_KEY_BY_INTENT.get(intent, {})
        multi_keys = _MULTI_VALUE_KEYS.get(intent)

        if multi_keys:
            product_entities = [e for e in request.intent_analysis.candidate_entities if e.entity_type == "PRODUCT"]
            for key, entity in zip(multi_keys, product_entities):
                if key in already_resolved_keys:
                    continue
                items.append(
                    build_resolved_context_item(
                        key=key,
                        value=entity.normalized_text,
                        category="PRODUCT",
                        provenance="SYSTEM_DERIVED",
                        source_reference="intent_analysis.candidate_entities",
                        confidence=entity.confidence,
                        materiality="high",
                    )
                )
                already_resolved_keys.add(key)
                basis_used.add("candidate_entity")
        else:
            for entity in request.intent_analysis.candidate_entities:
                key = mapping.get(entity.entity_type)
                if key is None or key in already_resolved_keys:
                    continue
                items.append(
                    build_resolved_context_item(
                        key=key,
                        value=entity.normalized_text,
                        category=_category_for_key(key),
                        provenance="SYSTEM_DERIVED",
                        source_reference="intent_analysis.candidate_entities",
                        confidence=entity.confidence,
                        materiality="high",
                    )
                )
                already_resolved_keys.add(key)
                basis_used.add("candidate_entity")

        # Fallback: current message may have no candidate entity of its own
        # (e.g. "What is its biggest weakness?"), but a resolved follow-up
        # reference to a prior candidate entity can populate the same
        # intent-specific key the mapping above targets.
        follow_up = request.intent_analysis.follow_up
        if follow_up.is_follow_up and follow_up.reference_type == "prior_candidate_entity" and follow_up.referenced_text:
            for key in mapping.values():
                if key not in already_resolved_keys:
                    items.append(
                        build_resolved_context_item(
                            key=key,
                            value=follow_up.referenced_text,
                            category=_category_for_key(key),
                            provenance="SYSTEM_DERIVED",
                            source_reference="intent_analysis.follow_up",
                            confidence=follow_up.confidence,
                            materiality="high",
                        )
                    )
                    already_resolved_keys.add(key)
                    basis_used.add("conversation_reference")
                    break  # populate only the first still-missing mapped key

        # CLAIM_SCENARIO's own narrative is always derivable from the request text.
        if intent == "CLAIM_SCENARIO" and "claim_scenario" not in already_resolved_keys:
            items.append(
                build_resolved_context_item(
                    key="claim_scenario",
                    value=request.intent_analysis.requested_outcome,
                    category="SCENARIO",
                    provenance="SYSTEM_DERIVED",
                    source_reference="intent_analysis.requested_outcome",
                    confidence=0.75,
                    materiality="high",
                )
            )
            already_resolved_keys.add("claim_scenario")
            basis_used.add("candidate_entity")

        return tuple(items), basis_used

    # -- conflicts ----------------------------------------------------------

    def _detect_conflicts(
        self, request: ContextBuilderInput, resolved: tuple[ResolvedContextItem, ...]
    ) -> tuple[tuple[ContextConflict, ...], tuple[ResolvedContextItem, ...]]:
        by_key: dict[str, list[ResolvedContextItem]] = {}
        for item in resolved:
            by_key.setdefault(item.key, []).append(item)

        # Also fold in raw user_context (may contain multiple sequenced
        # values for the same key even though only the first became
        # "resolved" above under simple last-wins precedence).
        user_values_by_key: dict[str, list] = {}
        for user_item in request.user_context:
            user_values_by_key.setdefault(user_item.key, []).append(user_item)

        has_correction_marker = any(
            any(marker in item.text.lower() for marker in _CORRECTION_MARKERS)
            for item in request.conversation_context
            if item.role == "user"
        )

        conflicts: list[ContextConflict] = []
        final_items = list(resolved)

        for key, user_items in user_values_by_key.items():
            distinct_values = {item.value for item in user_items}
            if len(distinct_values) < 2:
                continue
            ordered = sorted(user_items, key=lambda i: i.sequence)
            if has_correction_marker:
                winner = ordered[-1]
                conflicts.append(
                    build_context_conflict(
                        key=key,
                        values=tuple(i.value for i in ordered),
                        source_references=tuple(i.source_reference for i in ordered),
                        materiality="medium",
                        resolution_status="RESOLVED_BY_EXPLICIT_USER_CORRECTION",
                    )
                )
                final_items = [
                    (
                        build_resolved_context_item(
                            key=item.key,
                            value=item.value,
                            category=item.category,
                            provenance=item.provenance,
                            source_reference=item.source_reference,
                            confidence=item.confidence,
                            status="SUPERSEDED",
                            materiality=item.materiality,
                        )
                        if item.key == key and item.value != winner.value and item.status == "ACTIVE"
                        else item
                    )
                    for item in final_items
                ]
            else:
                conflicts.append(
                    build_context_conflict(
                        key=key,
                        values=tuple(i.value for i in ordered),
                        source_references=tuple(i.source_reference for i in ordered),
                        materiality="high",
                        resolution_status="UNRESOLVED",
                    )
                )

        return tuple(conflicts), tuple(final_items)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_KEY_CATEGORY_HINTS = {
    "age": "USER",
    "family_composition": "USER",
    "budget": "FINANCIAL",
    "claim_amount": "FINANCIAL",
    "admissible_amount": "FINANCIAL",
    "deductible": "FINANCIAL",
    "copay": "FINANCIAL",
    "current_sum_insured": "FINANCIAL",
    "hospitalization_date": "TEMPORAL",
    "document_reference": "DOCUMENT",
    "document_subject": "SCENARIO",
    "product_reference": "PRODUCT",
    "subject_reference": "PRODUCT",
    "comparison_subject_1": "PRODUCT",
    "comparison_subject_2": "PRODUCT",
    "quote_reference_1": "PRODUCT",
    "quote_reference_2": "PRODUCT",
    "policy_or_product_reference": "POLICY",
    "policy_or_document_reference": "POLICY",
    "existing_coverage": "POLICY",
}


def _category_for_key(key: str) -> str:
    return _KEY_CATEGORY_HINTS.get(key, "SCENARIO")


def _completeness_score(required, resolved_keys, blocking_conflicts, assumptions) -> float:
    if not required:
        return 1.0 if not blocking_conflicts else 0.5
    required_items = [r for r in required if r.required]
    optional_items = [r for r in required if not r.required]
    total_weight = len(required_items) * 1.0 + len(optional_items) * 0.25
    if total_weight == 0:
        score = 1.0
    else:
        earned = sum(1.0 for r in required_items if r.context_key in resolved_keys)
        earned += sum(0.25 for r in optional_items if r.context_key in resolved_keys)
        score = earned / total_weight
    score -= 0.2 * len(blocking_conflicts)
    score -= 0.1 * sum(1 for a in assumptions if a.materiality == "high")
    return max(0.0, min(1.0, score))


def _determine_answerability(*, intent, required, missing_required, missing_optional, blocking_conflicts, assumptions):
    if blocking_conflicts:
        questions = [f"Could you confirm the correct value for {c.key.replace('_', ' ')}?" for c in blocking_conflicts[:3]]
        return "CLARIFICATION_REQUIRED", tuple(questions)

    if missing_required:
        ordered = sorted(missing_required, key=lambda m: {"high": 0, "medium": 1, "low": 2}[m.materiality])
        questions = tuple(m.clarification_question for m in ordered[:3])
        return "CLARIFICATION_REQUIRED", questions

    # A general explanation is possible without a product/policy reference,
    # but the product-specific implication is not -- PARTIALLY_ANSWERABLE
    # rather than a full ANSWERABLE, per MO-014 s12.
    if intent == "CLAUSE_IMPLICATION" and any(m.key == "policy_or_product_reference" for m in missing_optional):
        return "PARTIALLY_ANSWERABLE", ()

    if any(a.resolution_required for a in assumptions):
        return "CLARIFICATION_REQUIRED", tuple(a.reason for a in assumptions if a.resolution_required)[:3]

    if assumptions:
        return "ANSWERABLE_WITH_ASSUMPTIONS", ()

    return "ANSWERABLE", ()
