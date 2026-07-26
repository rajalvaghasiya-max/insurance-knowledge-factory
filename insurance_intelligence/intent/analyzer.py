"""Deterministic baseline Intent Analyzer (MO-013 v0.1).

Boundary (MO-012 AD-008, as clarified): this module may interpret
normalized user language and approved conversation context. It must
NOT establish governed insurance facts, resolve authoritative entity
identity, retrieve evidence, or perform insurance reasoning. It makes
no network call and no LLM call -- classification is purely
rule-based pattern matching over normalized text, chosen deliberately
for v0.1 so behaviour is fully deterministic, explainable, and
testable before any model integration is introduced behind this same
contract.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from insurance_intelligence.contracts.intent import (
    Ambiguity,
    CandidateEntity,
    FollowUp,
    IntentAnalyzerInput,
    IntentAnalyzerOutput,
    build_ambiguity,
    build_candidate_entity,
    build_follow_up,
    build_output,
)

# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntentRule:
    rule_id: str
    intent: str
    patterns: tuple[re.Pattern[str], ...]
    priority: int
    confidence: float
    basis: str
    exclude_patterns: tuple[re.Pattern[str], ...] = ()

    def matches(self, normalized_text: str) -> bool:
        if any(pattern.search(normalized_text) for pattern in self.exclude_patterns):
            return False
        return any(pattern.search(normalized_text) for pattern in self.patterns)


def _p(*expressions: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(expr, re.IGNORECASE) for expr in expressions)


# Rules are evaluated independently; precedence among matches is resolved
# by (priority desc, confidence desc, rule_id asc) -- see _select_primary.
# Priority tiers group related precedence decisions documented in MO-013 s4.
RULE_REGISTRY: tuple[IntentRule, ...] = (
    # Tier 100 -- advisor framing overrides product/clause explanation.
    IntentRule(
        rule_id="advisor_explanation_customer",
        intent="ADVISOR_EXPLANATION",
        patterns=_p(r"\bmy (customer|client)s?\b", r"\bexplain (it |this )?to (my|a) (customer|client)\b"),
        priority=100,
        confidence=0.92,
        basis="matched_phrase",
    ),
    # Tier 95 -- explicit recommendation requests.
    IntentRule(
        rule_id="recommendation_should_i",
        intent="RECOMMENDATION",
        patterns=_p(
            r"\bshould i (buy|choose|select|pick|increase|add|get|go with)\b",
            r"\bwhich (one )?should i (buy|choose|select|pick|get)\b",
            r"\bwhat should i buy\b",
        ),
        priority=95,
        confidence=0.9,
        basis="matched_phrase",
    ),
    # Tier 90 -- claim scenario (financial/claim narrative), before generic calculation.
    IntentRule(
        rule_id="claim_scenario_bill",
        intent="CLAIM_SCENARIO",
        patterns=_p(
            r"\b(hospital )?bill is\b.*\bco-?pay\b",
            r"\bco-?pay\b.*\bwhat happens\b",
            r"\bif i claim\b",
            r"\bmy claim\b.*\bwhat happens\b",
            r"\bwill (it|this|that) be covered\b",
        ),
        priority=90,
        confidence=0.85,
        basis="matched_phrase",
    ),
    # Tier 85 -- clause implication (asks how a clause affects/impacts something).
    IntentRule(
        rule_id="clause_implication_affect",
        intent="CLAUSE_IMPLICATION",
        patterns=_p(
            r"\bhow (will|does|would) .* (affect|impact)\b",
            r"\bwhat does .* mean for (my|me)\b",
        ),
        priority=85,
        confidence=0.85,
        basis="matched_phrase",
    ),
    # Tier 85 -- pure calculation (arithmetic phrasing, no claim narrative).
    IntentRule(
        rule_id="calculation_percentage_of",
        intent="CALCULATION",
        patterns=_p(
            r"\bwhat is \d+(\.\d+)?%? of\b",
            r"\bcalculate\b",
            r"\bhow much is \d+(\.\d+)?%? of\b",
        ),
        priority=85,
        confidence=0.88,
        basis="matched_phrase",
    ),
    # Tier 80 -- exclusion vs coverage checks.
    IntentRule(
        rule_id="exclusion_check",
        intent="EXCLUSION_CHECK",
        patterns=_p(r"\bexclu(ded|sion|des)\b", r"\bnot covered\b"),
        priority=80,
        confidence=0.85,
        basis="matched_term",
    ),
    IntentRule(
        rule_id="coverage_check",
        intent="COVERAGE_CHECK",
        patterns=_p(r"\bdoes .* cover\b", r"\bis .* covered\b", r"\bcoverage for\b"),
        priority=80,
        confidence=0.85,
        basis="matched_phrase",
        exclude_patterns=_p(r"\bexclu(ded|sion|des)\b"),
    ),
    # Tier 75 -- comparisons: quote comparison before generic product comparison.
    IntentRule(
        rule_id="quote_comparison",
        intent="QUOTE_COMPARISON",
        patterns=_p(r"\bcompare\b.*\bquotes?\b"),
        priority=75,
        confidence=0.87,
        basis="matched_phrase",
    ),
    IntentRule(
        rule_id="policy_comparison",
        intent="POLICY_COMPARISON",
        patterns=_p(r"\bcompare\b.*\bmy (two |2 )?polic(y|ies)\b"),
        priority=75,
        confidence=0.85,
        basis="matched_phrase",
    ),
    IntentRule(
        rule_id="product_comparison",
        intent="PRODUCT_COMPARISON",
        patterns=_p(r"\bcompare\b.*\band\b", r"\bcompare\b.*\bwith\b", r"\bversus\b", r"\bvs\.?\b"),
        priority=70,
        confidence=0.8,
        basis="matched_phrase",
        exclude_patterns=_p(r"\bquotes?\b", r"\bmy (two |2 )?polic(y|ies)\b"),
    ),
    # Lowest-priority fallback: a bare "compare X" with no second subject
    # named in the sentence. Deliberately low priority so any of the more
    # specific comparison rules above always take precedence when they
    # apply; this exists so the Context Builder (not the Intent Analyzer)
    # is the stage that identifies and asks for the missing second subject.
    IntentRule(
        rule_id="product_comparison_bare",
        intent="PRODUCT_COMPARISON",
        patterns=_p(r"\bcompare\b"),
        priority=40,
        confidence=0.6,
        basis="matched_term",
    ),
    # Tier 70 -- document interpretation (specific passage / clause from a document).
    IntentRule(
        rule_id="document_interpretation",
        intent="DOCUMENT_INTERPRETATION",
        patterns=_p(
            r"\bexplain this clause\b",
            r"\bexplain .* from my policy\b",
            r"\bwhat does this (clause|paragraph|section) (say|mean)\b",
        ),
        priority=70,
        confidence=0.82,
        basis="matched_phrase",
    ),
    # Tier 65 -- policy fact lookup (a fact anchored to "this/my policy").
    IntentRule(
        rule_id="policy_fact_lookup",
        intent="POLICY_FACT_LOOKUP",
        patterns=_p(
            r"\bwhat is the .* (in|on|for) (this|my) policy\b",
            r"\bpercentage in (this|my) policy\b",
            r"\bmy (sum insured|premium|policy number|co-?pay)\b",
        ),
        priority=65,
        confidence=0.83,
        basis="matched_phrase",
    ),
    # Tier 60 -- product explanation.
    IntentRule(
        rule_id="product_explanation_weakness",
        intent="PRODUCT_EXPLANATION",
        patterns=_p(r"\b(biggest )?(weakness|downside|drawback|con|disadvantage)\b"),
        priority=61,
        confidence=0.72,
        basis="conversation_reference",
    ),
    IntentRule(
        rule_id="product_explanation",
        intent="PRODUCT_EXPLANATION",
        patterns=_p(
            r"\bhelp me understand\b",
            r"\bexplain [a-z0-9 ]*(plan|policy|product)?\b.*\bto me\b",
            r"\btell me about\b",
            r"\bwhat is\b.*\b(plan|policy|product)\b",
        ),
        priority=60,
        confidence=0.75,
        basis="matched_phrase",
    ),
    # Tier 55 -- generic term explanation (lowest-priority "what is X").
    IntentRule(
        rule_id="term_explanation",
        intent="TERM_EXPLANATION",
        patterns=_p(r"\bwhat is (a |an |the )?[a-z\- ]+\??$", r"\bdefine\b"),
        priority=55,
        confidence=0.75,
        basis="matched_term",
        exclude_patterns=_p(r"\bmy policy\b", r"\bthis policy\b", r"\baffect\b", r"\bimpact\b"),
    ),
    # Suitability as an explicit standalone ask (kept lower priority than RECOMMENDATION).
    IntentRule(
        rule_id="suitability_assessment",
        intent="SUITABILITY_ASSESSMENT",
        patterns=_p(r"\bwould (it|this|that) suit\b", r"\bis (it|this|that) suitable for\b", r"\bright for me\b"),
        priority=58,
        confidence=0.78,
        basis="matched_phrase",
    ),
    IntentRule(
        rule_id="policy_summary",
        intent="POLICY_SUMMARY",
        patterns=_p(r"\bsummar(ise|ize) my policy\b", r"\boverview of my policy\b"),
        priority=62,
        confidence=0.8,
        basis="matched_phrase",
    ),
)

_OUT_OF_SCOPE_PATTERNS = _p(
    r"\bweather\b",
    r"\bfootball score\b",
    r"\brecipe\b",
    r"\bstock price\b",
    r"\bcapital of\b",
)

_PRONOUN_PATTERN = re.compile(r"\b(it|this|that|they|its)\b", re.IGNORECASE)
# 'it'/'its'/'they' are always pronoun usage in English and are treated as
# potentially bare/unresolved. 'this'/'that' are only bare when NOT used
# as a determiner immediately before one of these common, self-contained
# nouns (e.g. "this plan", "that policy") -- a bounded, testable v0.1
# heuristic, not full part-of-speech tagging.
_SELF_CONTAINED_DETERMINER_NOUNS = (
    "plan",
    "policy",
    "product",
    "clause",
    "claim",
    "cover",
    "coverage",
    "quote",
)
_BARE_PRONOUN_PATTERN = re.compile(
    r"\b(it|its|they)\b|\b(this|that)\b(?!\s+(?:" + "|".join(_SELF_CONTAINED_DETERMINER_NOUNS) + r")\b)",
    re.IGNORECASE,
)
_CONTINUATION_PATTERN = re.compile(r"^\s*(what about|and|also|how about)\b", re.IGNORECASE)
_COMPARISON_TARGET_PATTERN = re.compile(r"\bthis with the other one\b|\bthese two\b(?!\s+\w)", re.IGNORECASE)

# Bounded alias lists for MENTION detection only -- never resolved to a
# governed identity. Extending this list does not grant authoritative
# resolution; see MO-013 s5.
_KNOWN_INSURER_ALIASES = (
    "aditya birla health",
    "star health",
    "bajaj allianz",
    "hdfc life",
    "star comprehensive",
)
_KNOWN_PRODUCT_ALIASES = (
    "activ one max",
    "activ one",
    "star comprehensive",
    "my health care",
)
_FINANCIAL_VALUE_PATTERN = re.compile(r"(?:₹|rs\.?|inr)\s?[\d,]+(?:\.\d+)?\s?(?:lakh|crore|k)?", re.IGNORECASE)
_PERCENTAGE_PATTERN = re.compile(r"\b\d{1,3}(?:\.\d+)?\s?%")
_AGE_PATTERN = re.compile(r"\b(\d{1,3})\s*-?\s*year-?\s*old\b", re.IGNORECASE)
_TIME_PERIOD_PATTERN = re.compile(r"\b\d{1,3}\s*(day|days|month|months|year|years)\b", re.IGNORECASE)
_POLICY_FEATURE_TERMS = (
    "deductible",
    "co-pay",
    "copay",
    "premium",
    "waiting period",
    "sum insured",
    "no claim bonus",
    "room rent capping",
    "room-rent capping",
    "sub-limit",
    "floater",
)
_CLAIM_CONCEPT_TERMS = ("claim", "hospitalisation", "hospitalization", "admissible", "reimbursement")
_DOCUMENT_TYPE_TERMS = ("policy wording", "prospectus", "certificate of insurance", "clause", "schedule")

# CLARIFICATION_REQUIRED still requires a governed primary_intent value
# per the output contract; FOLLOW_UP is the most semantically accurate
# governed label to carry when the system cannot yet proceed but the
# request is clearly conversational/insurance-adjacent rather than out
# of scope.
_CLARIFICATION_PLACEHOLDER_INTENT = "FOLLOW_UP"


class IntentAnalyzer:
    """Stateless deterministic classifier. Safe to reuse across calls;
    holds no mutable state and performs no I/O."""

    def analyze(self, request: IntentAnalyzerInput) -> IntentAnalyzerOutput:
        text = request.text.strip()

        if not text:
            return build_output(
                request_id=request.request_id,
                primary_intent="OUT_OF_SCOPE",
                domain=request.domain_hint,
                requested_outcome="",
                confidence=0.0,
                analysis_status="INVALID_REQUEST",
                classification_basis=["fallback_rule"],
            )

        normalized = _normalize(text)

        if any(pattern.search(normalized) for pattern in _OUT_OF_SCOPE_PATTERNS):
            return build_output(
                request_id=request.request_id,
                primary_intent="OUT_OF_SCOPE",
                domain=request.domain_hint,
                requested_outcome=text,
                confidence=0.9,
                analysis_status="OUT_OF_SCOPE",
                classification_basis=["domain_keyword"],
            )

        follow_up = _detect_follow_up(normalized, request)
        candidate_entities = _extract_candidate_entities(text, request)
        ambiguities = _detect_ambiguities(normalized, follow_up, candidate_entities)

        matched_rules = [rule for rule in RULE_REGISTRY if rule.matches(normalized)]

        if not matched_rules:
            if follow_up.is_follow_up:
                return _build_clarification(
                    request,
                    text,
                    ambiguity=build_ambiguity(
                        ambiguity_type="INSUFFICIENT_FOLLOW_UP_CONTEXT",
                        description="The follow-up reference could not be safely interpreted without more context.",
                        materiality="high",
                    ),
                    question="Could you clarify what you're referring to?",
                    candidate_entities=candidate_entities,
                    follow_up=follow_up,
                )
            return _build_clarification(
                request,
                text,
                ambiguity=build_ambiguity(
                    ambiguity_type="UNCLEAR_REQUESTED_OUTCOME",
                    description="No governed intent pattern matched this request.",
                    materiality="high",
                ),
                question="Could you tell me more specifically what you'd like to know?",
                candidate_entities=candidate_entities,
                follow_up=follow_up,
            )

        # A material, unresolved ambiguity blocks confident classification
        # even when a rule matched (e.g. an unresolved pronoun with no
        # usable follow-up context).
        blocking = [a for a in ambiguities if a.materiality == "high"]
        if blocking and follow_up.reference_type != "prior_candidate_entity":
            return _build_clarification(
                request,
                text,
                ambiguity=blocking[0],
                question=_question_for_ambiguity(blocking[0]),
                candidate_entities=candidate_entities,
                follow_up=follow_up,
            )

        primary_rule = _select_primary(matched_rules)
        secondary_labels = _select_secondary(matched_rules, primary_rule)

        status = "CLASSIFIED_WITH_AMBIGUITY" if ambiguities else "CLASSIFIED"

        return build_output(
            request_id=request.request_id,
            primary_intent=primary_rule.intent,
            secondary_intents=secondary_labels,
            domain=request.domain_hint,
            requested_outcome=text,
            confidence=primary_rule.confidence,
            analysis_status=status,
            candidate_entities=candidate_entities,
            ambiguities=ambiguities,
            follow_up=follow_up,
            classification_basis=[primary_rule.basis],
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _select_primary(matched_rules: list[IntentRule]) -> IntentRule:
    return sorted(matched_rules, key=lambda r: (-r.priority, -r.confidence, r.rule_id))[0]


def _select_secondary(matched_rules: list[IntentRule], primary_rule: IntentRule) -> tuple[str, ...]:
    seen: list[str] = []
    for rule in sorted(matched_rules, key=lambda r: (-r.priority, -r.confidence, r.rule_id)):
        if rule.intent == primary_rule.intent:
            continue
        if rule.intent not in seen:
            seen.append(rule.intent)
    return tuple(seen)


def _detect_follow_up(normalized: str, request: IntentAnalyzerInput) -> FollowUp:
    has_pronoun = bool(_PRONOUN_PATTERN.search(normalized))
    has_continuation = bool(_CONTINUATION_PATTERN.search(normalized))
    has_prior_context = bool(request.conversation_context) or bool(request.known_entity_mentions)

    if not (has_pronoun or has_continuation):
        return build_follow_up(is_follow_up=False)

    if has_prior_context:
        referenced = ""
        if request.known_entity_mentions:
            referenced = request.known_entity_mentions[-1].surface_text
        elif request.conversation_context:
            referenced = request.conversation_context[-1].text
        return build_follow_up(
            is_follow_up=True,
            reference_type="prior_candidate_entity" if request.known_entity_mentions else "prior_topic",
            referenced_text=referenced,
            confidence=0.75,
        )

    # Pronoun/continuation present but nothing to resolve against.
    return build_follow_up(is_follow_up=True, reference_type="none", referenced_text="", confidence=0.2)


def _extract_candidate_entities(text: str, request: IntentAnalyzerInput) -> tuple[CandidateEntity, ...]:
    lowered = text.lower()
    entities: list[CandidateEntity] = []

    matched_product_aliases = _longest_non_overlapping_aliases(lowered, _KNOWN_PRODUCT_ALIASES)
    for alias in matched_product_aliases:
        entities.append(
            build_candidate_entity(
                entity_type="PRODUCT",
                surface_text=_surface_for_alias(text, alias),
                normalized_text=alias,
                source="alias_list",
                confidence=0.7,
            )
        )
    matched_insurer_aliases = _longest_non_overlapping_aliases(lowered, _KNOWN_INSURER_ALIASES)
    for alias in matched_insurer_aliases:
        if alias in matched_product_aliases:
            continue
        entities.append(
            build_candidate_entity(
                entity_type="INSURER",
                surface_text=_surface_for_alias(text, alias),
                normalized_text=alias,
                source="alias_list",
                confidence=0.65,
            )
        )
    for term in _POLICY_FEATURE_TERMS:
        if term in lowered:
            entities.append(
                build_candidate_entity(
                    entity_type="POLICY_FEATURE",
                    surface_text=term,
                    normalized_text=term,
                    source="term_list",
                    confidence=0.6,
                )
            )
    for term in _CLAIM_CONCEPT_TERMS:
        if term in lowered:
            entities.append(
                build_candidate_entity(
                    entity_type="CLAIM_CONCEPT",
                    surface_text=term,
                    normalized_text=term,
                    source="term_list",
                    confidence=0.55,
                )
            )
    for term in _DOCUMENT_TYPE_TERMS:
        if term in lowered:
            entities.append(
                build_candidate_entity(
                    entity_type="DOCUMENT_TYPE",
                    surface_text=term,
                    normalized_text=term,
                    source="term_list",
                    confidence=0.55,
                )
            )
    for match in _FINANCIAL_VALUE_PATTERN.finditer(text):
        entities.append(
            build_candidate_entity(
                entity_type="FINANCIAL_VALUE",
                surface_text=match.group(0),
                normalized_text=match.group(0).lower().replace(" ", ""),
                source="pattern",
                confidence=0.8,
            )
        )
    for match in _PERCENTAGE_PATTERN.finditer(text):
        entities.append(
            build_candidate_entity(
                entity_type="FINANCIAL_VALUE",
                surface_text=match.group(0),
                normalized_text=match.group(0).replace(" ", ""),
                source="pattern",
                confidence=0.75,
            )
        )
    for match in _AGE_PATTERN.finditer(text):
        entities.append(
            build_candidate_entity(
                entity_type="AGE",
                surface_text=match.group(0),
                normalized_text=match.group(1),
                source="pattern",
                confidence=0.8,
            )
        )
    for match in _TIME_PERIOD_PATTERN.finditer(text):
        entities.append(
            build_candidate_entity(
                entity_type="TIME_PERIOD",
                surface_text=match.group(0),
                normalized_text=match.group(0).lower(),
                source="pattern",
                confidence=0.75,
            )
        )

    return tuple(entities)


def _surface_for_alias(text: str, alias: str) -> str:
    match = re.search(re.escape(alias), text, re.IGNORECASE)
    return match.group(0) if match else alias


def _longest_non_overlapping_aliases(lowered_text: str, aliases: tuple[str, ...]) -> list[str]:
    """Return matched aliases, preferring the longest match at each
    position so a shorter alias fully contained within a longer matched
    alias (e.g. 'activ one' inside 'activ one max') is not also reported
    as a separate, redundant mention."""
    matched = [alias for alias in aliases if alias in lowered_text]
    result: list[str] = []
    for alias in sorted(matched, key=len, reverse=True):
        if any(alias != longer and alias in longer for longer in result):
            continue
        result.append(alias)
    return result


def _detect_ambiguities(
    normalized: str, follow_up: FollowUp, candidate_entities: tuple[CandidateEntity, ...]
) -> tuple[Ambiguity, ...]:
    ambiguities: list[Ambiguity] = []

    unresolved_pronoun = (
        _BARE_PRONOUN_PATTERN.search(normalized)
        and not candidate_entities
        and not (follow_up.is_follow_up and follow_up.reference_type == "prior_candidate_entity")
    )
    if unresolved_pronoun:
        ambiguities.append(
            build_ambiguity(
                ambiguity_type="UNRESOLVED_PRONOUN",
                description="The request uses a pronoun with no resolvable prior subject.",
                materiality="high",
            )
        )

    if _COMPARISON_TARGET_PATTERN.search(normalized) and len(candidate_entities) < 2:
        ambiguities.append(
            build_ambiguity(
                ambiguity_type="MISSING_COMPARISON_TARGET",
                description="A comparison was requested without two identifiable subjects.",
                materiality="high",
            )
        )

    return tuple(ambiguities)


def _question_for_ambiguity(ambiguity: Ambiguity) -> str:
    return {
        "UNRESOLVED_PRONOUN": "Could you tell me specifically what you're asking about?",
        "MISSING_COMPARISON_TARGET": "Which two plans would you like me to compare?",
        "MISSING_SUBJECT": "Could you tell me which product or policy you mean?",
        "MULTIPLE_POSSIBLE_SUBJECTS": "Which one did you mean?",
        "UNCLEAR_REQUESTED_OUTCOME": "Could you tell me more specifically what you'd like to know?",
        "DOMAIN_AMBIGUITY": "Is this about your health, motor, or life insurance?",
        "INSUFFICIENT_FOLLOW_UP_CONTEXT": "Could you clarify what you're referring to?",
    }[ambiguity.ambiguity_type]


def _build_clarification(
    request: IntentAnalyzerInput,
    text: str,
    *,
    ambiguity: Ambiguity,
    question: str,
    candidate_entities: tuple[CandidateEntity, ...],
    follow_up: FollowUp,
) -> IntentAnalyzerOutput:
    return build_output(
        request_id=request.request_id,
        primary_intent=_CLARIFICATION_PLACEHOLDER_INTENT,
        domain=request.domain_hint,
        requested_outcome=text,
        confidence=0.3,
        analysis_status="CLARIFICATION_REQUIRED",
        candidate_entities=candidate_entities,
        ambiguities=[ambiguity],
        follow_up=follow_up,
        classification_basis=["fallback_rule"],
        clarification_question=question,
    )
