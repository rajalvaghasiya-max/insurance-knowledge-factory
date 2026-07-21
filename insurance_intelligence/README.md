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

---

# `planning` component (MO-015 v0.1)

The third executable stage: the **Reasoning Planner**.

## Responsibility

Transform validated Intent Analyzer + Context Builder output into an
explicit, validated execution plan: a governed plan type, an ordered
sequence of governed steps, the evidence categories and calculation
types those steps will need, required domain capabilities, inherited
assumptions/conflicts/limitations, governed stop conditions, and an
expected outcome type. **The planner declares what must be done; it
does not do it.**

## Input/output boundary

Input: validated `IntentAnalyzerOutput` + `ContextBuilderOutput` +
`domain` + `planning_mode`. Output: a `ReasoningPlan` -- see
[`contracts/reasoning_plan.py`](contracts/reasoning_plan.py). No
document, fact, or governed entity ID is ever retrieved or embedded;
`build_plan`'s own validation and the separate
[`planning/validator.py`](planning/validator.py) both fail closed on
governance violations (e.g. a plan step type not allowed for its
plan type, a recommendation plan missing its safety gate, a
`CLARIFICATION_REQUIRED` plan containing executable steps).

## Plan types

The 10 governed plan types (`planning/registry.py`:
`PLAN_TYPE_DEFINITIONS`) are centrally mapped from each governed
intent (`INTENT_TO_PLAN_TYPE`), each with a fixed execution mode
(`PLAN_TYPE_TO_EXECUTION_MODE`: `DIRECT_GROUNDED`, `INTERPRETIVE`, or
`DECISION_SUPPORT`) and a default expected outcome
(`PLAN_TYPE_TO_EXPECTED_OUTCOME`).

## Step registry

24 governed step types (`STEP_REGISTRY`), each with a stage owner
(`PLANNING`, `EVIDENCE_RESOLVER`, `REASONING_ENGINE`, `SAFETY_GATE`,
`EXPLANATION_GENERATOR`, `RESPONSE_ASSEMBLER`) and the set of plan
types it's allowed to appear in. A step being *declared* in a plan
(e.g. `FORM_CONDITIONAL_RECOMMENDATION`, `COMPARE_OPTIONS`) does not
mean that capability exists yet -- it means a later milestone's stage
is expected to perform it.

## Planning versus execution

This is the central distinction of the whole component. `plan()`
never calls the Knowledge Factory, never performs arithmetic, and
never produces a comparison/suitability/recommendation result --
`required_evidence` and `required_calculations` are declarations
(category + subject reference + which step would need it), not
resolved facts or computed values. Every test in
`tests/insurance_intelligence/test_reasoning_planner.py` that touches
a scenario capable of "looking answered" (claim scenario, calculation,
recommendation) explicitly asserts no calculated value or resolved
fact ever appears in the plan.

## Stop conditions

Governed stop-condition types (`MISSING_REQUIRED_CONTEXT`,
`UNRESOLVED_CONTEXT_CONFLICT`, `REQUIRED_DOCUMENT_FAILED`,
`OUT_OF_SCOPE_REQUEST`, etc.) are derived directly from the Context
Builder's own missing-context/conflict/answerability output --
the planner never re-decides sufficiency itself, it only translates
Context Builder's decision into the plan's `plan_status` and
`execution_mode`. Evidence-stage conditions (e.g.
`REQUIRED_EVIDENCE_MISSING`) are included as `PLANNED_FUTURE_CHECK`
entries -- named for completeness, not yet evaluated.

## Explicit non-goals

Does not retrieve any document or fact, resolve authoritative entity
IDs, interpret insurance clauses, calculate claim values, compare
actual products, assess suitability, make a recommendation, generate
user-facing explanations, or invoke an LLM provider. The presence of
a later-stage step type in a plan (e.g. `GENERATE_CONSUMER_EXPLANATION`)
does not mean the Explanation Generator (MO-018) exists yet.


---

# `evidence` component (MO-016 v0.1)

The Evidence Resolver is the first read-only bridge from a validated Reasoning Plan to governed Knowledge Factory records. It resolves candidate references through narrow registry-backed adapters, applies source-authority and version requirements, verifies byte-level lineage, packages only explicit supported claims, and reports requirement-level sufficiency and a structured trace. The initial real integration is deliberately bounded to the governed Star Health Star Comprehensive conditional co-payment lineage produced by MO-009/MO-010.

The resolver may decide which governed evidence applies. It does not calculate, derive insurance implications, compare products, assess suitability, recommend an action, or generate a final answer. In `STRICT` mode, missing or mismatched required lineage fails closed. Repository access is read-only and tests hash the pilot artifacts before and after resolution.

## Decision and Safety Gate (MO-018)

The Decision and Safety Gate consumes the validated reasoning plan, governed evidence-resolution output, and structured reasoning findings. It evaluates findings deterministically, preserves blocking evidence and clarification requirements, and emits an evidence-locked approved response packet only when communication is safe.

The first executable pilot covers Star Health Star Comprehensive conditional co-payment. General clause meaning may be approved with explicit conditions; case-specific applicability is withheld until the documented trigger context is supplied. Failed lineage, unresolved versions, material conflicts, unsupported reasoning, and recommendation operations fail closed.

The gate does not generate prose, explanations, recommendations, or final answers. Those remain downstream responsibilities.

## Explanation Generator (MO-019)

The Explanation Generator consumes only a Decision Gate-approved, evidence-locked response packet (or an approved clarification requirement). It selects a registered audience/style profile, renders deterministic sections, applies only meaning-preserving registered terminology, validates the draft against approved findings and evidence, and emits a structured explanation trace.

The initial executable pilot covers Star Health Star Comprehensive conditional co-payment. It preserves the documented 10% amount, triggering condition, evidence references, and limitations; a case-specific unresolved trigger produces only a clarification draft. Any fidelity failure withholds the generated sections.

The generator does not retrieve evidence, perform new reasoning, change the Decision Gate outcome, expose withheld findings, recommend products, calculate claim amounts, or assemble the final user response.
