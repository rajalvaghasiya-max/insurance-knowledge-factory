# Insurance Intelligence Layer — `intent` component (MO-013 v0.1)

This package implements the first executable stage of the PolicyScna
Insurance Intelligence Layer defined in
[docs/architecture/insurance_intelligence/](../docs/architecture/insurance_intelligence/):
the **Intent Analyzer**.

## Responsibility

Classify a normalized user request into exactly one governed primary
intent label (plus zero or more governed secondary labels), extract
candidate entity mentions, detect ambiguity and conversational
follow-up, and report a deterministic confidence and classification
basis — or fail safely into a governed non-classification outcome
(`CLARIFICATION_REQUIRED`, `OUT_OF_SCOPE`, `INVALID_REQUEST`).

## Boundary

Per MO-012 (AD-008, as clarified) and the [Stage Contracts](../docs/architecture/insurance_intelligence/MO-012_STAGE_CONTRACTS.md):

> The Intent Analyzer may interpret normalized user language and
> approved conversation context, but it must not establish governed
> insurance facts, resolve authoritative entity identity, retrieve
> evidence, or perform insurance reasoning.

Concretely, in this implementation:

- Candidate entities (`candidate_entities`) are **mentions only** —
  `entity_type` / `surface_text` / `normalized_text`. There is no
  `entity_id`, no product/insurer resolution, and no lookup against
  `factory_core/` or `knowledge_domains/`.
- `known_entity_mentions` supplied in the input (for follow-up
  continuity) are treated as prior candidate mentions, never as
  authoritative identity.
- Conversation context is used to interpret follow-ups; it is never
  treated as governed insurance truth.

## Taxonomy

The governed intent labels are centrally defined in
[`intent/taxonomy.py`](intent/taxonomy.py) as an immutable `frozenset`.
No component may introduce a new label at runtime; extending the
taxonomy requires a code change and review.

## Deterministic nature of v0.1

Classification in this version is **purely deterministic rule-based
pattern matching** over normalized text — a registry of explicit
`IntentRule` objects (pattern, priority, confidence, classification
basis), evaluated independently, with an explicit, documented
precedence resolution when multiple rules match (see
`RULE_REGISTRY` and `_select_primary` in
[`intent/analyzer.py`](intent/analyzer.py)). There is no LLM call, no
network call, and no statistical model — confidence values are
deterministic classification confidence, not calibrated probability.

## Candidate entity limitation

Entity mention extraction uses bounded alias lists and regex patterns
(financial values, ages, time periods, a small set of policy-feature
and claim-concept terms). It is intentionally shallow: it will miss
mentions outside its known lists, and it must never be relied on for
authoritative identity resolution — that responsibility belongs to
the Knowledge Factory's generic contracts (e.g.
`factory_core/governance/product_identity_reference.py`), consumed by
a later stage (Context Builder, MO-014), not by this one.

## Future LLM assistance

The contract (`insurance_intelligence/contracts/intent.py`) is
designed so a future LLM-assisted implementation of `IntentAnalyzer`
(per MO-012's LLM-permitted responsibilities: semantic classification,
implicit-intent detection, natural-language entity extraction,
ambiguity identification) can be introduced **behind this same
input/output contract**, without changing anything downstream. The
deterministic v0.1 baseline exists so behaviour is fully testable and
explainable before that integration, and can continue to serve as a
fallback/validation path afterward.

---

# `context` component (MO-014 v0.1)

The second executable stage: the **Context Builder**.

## Responsibility

Given Intent Analyzer output plus user-provided, conversational,
session, and document-metadata context, assemble typed,
provenance-tagged context items; detect missing required context,
conflicts, and assumptions; compute a deterministic completeness
score; and decide the request's answerability -- or produce targeted
clarification questions (at most three, ordered by materiality).

## Inputs and outputs

Input: the validated `IntentAnalyzerOutput` plus `user_context`,
`conversation_context`, `document_context`, and `session_context`.
Output: `resolved_context`, `missing_required_context`,
`missing_optional_context`, `conflicts`, `assumptions`,
`context_completeness`, `answerability`, `clarification_questions`.
See [`contracts/context.py`](contracts/context.py) for the full
executable contract.

## Provenance model

Every resolved context item carries one of the seven governed MO-012
provenance statuses (`USER_PROVIDED`, `DOCUMENT_RESOLVED`,
`SYSTEM_DERIVED`, `ASSUMED`, `UNVERIFIED`, `STALE`, `SUPERSEDED`).
Resolution follows a fixed deterministic precedence: explicit current
user value > session (prior user) value > document metadata >
system-derived (from Intent Analyzer candidate entities or a resolved
follow-up reference) > assumption. A required-context registry
(`context/requirements.py`) centrally maps each governed intent to
its required and optional context keys -- it is not scattered through
conditional logic in the builder.

## Answerability model

One of the six governed MO-012 outcomes
(`ANSWERABLE`, `ANSWERABLE_WITH_ASSUMPTIONS`, `PARTIALLY_ANSWERABLE`,
`CLARIFICATION_REQUIRED`, `NOT_ANSWERABLE`, `OUT_OF_SCOPE`) is
determined by explicit gates -- required context and blocking
conflicts, never the numeric completeness score alone. A blocking
(high-materiality, unresolved) conflict or any missing required
context forces `CLARIFICATION_REQUIRED`; a failed required document
forces `NOT_ANSWERABLE`; an intent whose only gap is an optional
product/policy reference (e.g. `CLAUSE_IMPLICATION`) is
`PARTIALLY_ANSWERABLE` rather than fully blocked.

## Conflict and assumption boundaries

Repeated context keys with distinct values are detected as conflicts.
An explicit user correction (detected via a bounded marker-phrase
heuristic, e.g. "sorry", "actually") resolves in favour of the later
value, marking the earlier one `SUPERSEDED`; otherwise the conflict
remains `UNRESOLVED` and blocks answerability. System-derived values
never override explicit user-provided values. High-materiality
assumptions must be visible, not silently created.

## Explicit non-goals

Same boundary discipline as the Intent Analyzer, extended: the
Context Builder does not resolve authoritative product/policy
identity, retrieve documents, establish insurance facts, interpret
clauses, calculate insurance outcomes, compare products, determine
suitability, or generate recommendations or final answers. It decides
*whether* context is sufficient -- it never answers the insurance
question itself.
