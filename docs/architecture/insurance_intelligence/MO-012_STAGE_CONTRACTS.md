# MO-012 — Stage Contracts

**Status:** Conceptual contracts only. No executable schema is defined or implied.
**Related documents:** [Core Architecture](MO-012_INSURANCE_INTELLIGENCE_ARCHITECTURE.md) · [LLM and Deterministic Boundaries](MO-012_LLM_AND_DETERMINISTIC_BOUNDARIES.md) · [Failure and Safety Model](MO-012_FAILURE_AND_SAFETY_MODEL.md)

This document defines what each pipeline stage is responsible for, what it may and may not do, and how it fails. It does not define classes, function signatures, or a production JSON Schema — those belong to the implementation milestones (MO-013 through MO-018) once each stage is actually built.

---

## Shared request envelope (illustrative only)

The example below shows the conceptual shape a request-and-response record accumulates as it passes through the pipeline. **This is an architectural example, not a final production schema** — field names, nesting, and types are all subject to change during implementation.

```json
{
  "contract_version": "0.1-architectural-draft",
  "request_id": "string",
  "session_id": "string",
  "created_at": "ISO-8601 timestamp",
  "domain": "health | motor | life",
  "user_input": "string",
  "conversation_context": {
    "prior_turns": "array, provenance-tagged, re-validated not silently reused"
  },
  "intent": {
    "label": "one of the governed intent taxonomy labels",
    "confidence": "stage-specific, see AD-009"
  },
  "context": {
    "items": "array of context items, each with a provenance status"
  },
  "reasoning_plan": {
    "plan_type": "one of the governed reasoning plan types",
    "required_evidence": "array"
  },
  "evidence_resolution": {
    "status": "one of the governed evidence statuses",
    "resolved_facts": "array, each with lineage back to a governed Knowledge Factory artifact"
  },
  "reasoning_result": {
    "conclusion_class": "Source Fact | Deterministic Calculation | Derived Insurance Implication | Contextual Judgement | Recommendation"
  },
  "response": {
    "outcome": "one of the governed response outcomes",
    "answer": "string or structured payload",
    "citations": "array"
  },
  "audit_trace": {
    "decisions": "structured record of gates passed/failed and why"
  }
}
```

---

## Stage: Request Intake

- **Responsibility:** accept and normalize the raw user interaction into the envelope shape; attach session/conversation identifiers.
- **Inputs:** raw user input, session identifier, prior conversation reference (if any).
- **Outputs:** a normalized request record with `user_input`, `session_id`, `created_at` populated.
- **Permitted behaviour:** text normalization, language/locale detection, basic input validation.
- **Prohibited behaviour:** intent classification, entity resolution, or any evidence access.
- **Confidence/completeness:** not applicable at this stage.
- **Failure behaviour:** malformed or empty input is rejected before entering the pipeline; this is a request-level failure, not a pipeline outcome.
- **Deterministic responsibilities:** all of them — this stage is fully deterministic.
- **LLM-assisted responsibilities:** none.

## Stage: Intent Analyzer

- **Responsibility:** classify the normalized request into one governed intent label.
- **Inputs:** normalized request, conversation context.
- **Outputs:** `intent.label` (from the governed taxonomy only), `intent.confidence`.
- **Permitted behaviour:** semantic classification, implicit-intent detection, follow-up interpretation against conversation context.
- **Prohibited behaviour:** inventing a new intent label; resolving entities; accessing evidence.
- **Confidence/completeness:** must report a stage-specific confidence; low-confidence classification is a valid trigger for `CLARIFICATION_REQUIRED` downstream, not a reason to guess.
- **Failure behaviour:** if no governed label fits, the request is classified `OUT_OF_SCOPE` rather than force-fit.
- **Deterministic responsibilities:** validating the classified label is a member of the governed taxonomy; rejecting invalid labels.
- **LLM-assisted responsibilities:** semantic and implicit intent classification (see LLM-Permitted Responsibilities).

## Stage: Context Builder

- **Responsibility:** assemble the context items needed to attempt the classified intent — user-provided facts, resolved entities, conversation-derived context, system-derived defaults.
- **Inputs:** intent, conversation context, user-provided facts, prior-turn context (if `FOLLOW_UP`).
- **Outputs:** an array of context items, **each individually tagged with a provenance status** (see Context Provenance below).
- **Permitted behaviour:** natural-language entity extraction; requesting values already provided earlier in conversation; flagging assumed values explicitly as `ASSUMED`.
- **Prohibited behaviour:** silently reusing prior-turn context without re-validating it still applies (see Scenario 10 in the core architecture document); treating an assumption as `USER_PROVIDED`.
- **Confidence/completeness:** every item's provenance status is itself the completeness signal; there is no separate aggregate score at this stage.
- **Failure behaviour:** context items that cannot be resolved are omitted, not fabricated; their absence is what the Context Sufficiency Gate evaluates.
- **Deterministic responsibilities:** provenance tagging and retention; entity identity resolution against governed identity records.
- **LLM-assisted responsibilities:** natural-language entity extraction, ambiguity identification.

## Stage: Context Sufficiency Gate

- **Responsibility:** decide whether enough context exists to proceed to reasoning planning, or whether the request must exit for clarification.
- **Inputs:** the context item array with provenance.
- **Outputs:** one of the answerability outcomes (see below) plus, if `CLARIFICATION_REQUIRED`, one or more targeted clarification questions.
- **Permitted behaviour:** identifying which specific missing item(s) would change the answer.
- **Prohibited behaviour:** proceeding on `ASSUMED` context for anything material without disclosing the assumption downstream.
- **Confidence/completeness:** produces the request's answerability classification.
- **Failure behaviour:** this stage *is* an exit point — `CLARIFICATION_REQUIRED`, `PARTIALLY_ANSWERABLE`, or `NOT_ANSWERABLE` all legitimately end the pipeline here.
- **Deterministic responsibilities:** the sufficiency rule itself (what counts as "enough" per intent type) is a governed, deterministic rule, not an LLM judgment call.
- **LLM-assisted responsibilities:** candidate clarification-question generation (the *decision* to ask is deterministic; the *wording* may be LLM-drafted).

## Stage: Reasoning Planner

- **Responsibility:** turn a sufficiently-contextualized intent into a concrete reasoning plan naming what evidence and what reasoning steps are required.
- **Inputs:** intent, sufficient context.
- **Outputs:** `reasoning_plan.plan_type` (from the governed plan-type list), an explicit list of required evidence.
- **Permitted behaviour:** selecting among governed plan types; composing multi-step plans for `COMPARISON_PLAN`/`SCENARIO_PLAN`/`RECOMMENDATION_PLAN`.
- **Prohibited behaviour:** inventing a plan type; specifying evidence requirements that bypass the Evidence Resolver.
- **Confidence/completeness:** plans may be marked provisional pending evidence resolution.
- **Failure behaviour:** if no governed plan type fits the intent, the request degrades to `NOT_ANSWERABLE`.
- **Deterministic responsibilities:** validating the plan against the governed plan-type list.
- **LLM-assisted responsibilities:** candidate reasoning-plan generation for complex/composite intents.

## Stage: Evidence Resolver

- **Responsibility:** resolve the reasoning plan's declared evidence requirements against governed Knowledge Factory artifacts.
- **Inputs:** reasoning plan, resolved entity/product/document identities.
- **Outputs:** resolved facts, each retaining lineage to its governed source (entity, document, version, hash — the same lineage discipline already enforced in the Knowledge Factory's generic contracts).
- **Permitted behaviour:** querying governed knowledge assets; identifying multiple candidate facts when more than one exists.
- **Prohibited behaviour:** answering from model memory when governed evidence is absent; silently picking one candidate fact when several conflict.
- **Confidence/completeness:** reports one of the governed evidence statuses per requirement.
- **Failure behaviour:** unresolved or conflicting requirements are reported as such, not silently dropped.
- **Deterministic responsibilities:** all resolution logic — this stage does not use LLM judgment to decide what counts as evidence.
- **LLM-assisted responsibilities:** none directly; downstream stages interpret what this stage resolves.

## Stage: Evidence Sufficiency Gate

- **Responsibility:** decide whether the resolved evidence is sufficient to proceed to reasoning, or whether the request must exit.
- **Inputs:** evidence resolution results.
- **Outputs:** a pass/exit decision; if exiting, one of `DOCUMENT_REQUIRED`, `EVIDENCE_CONFLICT`, `ABSTAINED`, `PARTIAL_ANSWER`.
- **Permitted behaviour:** allowing a `PARTIAL_ANSWER` to proceed when part of the request is supportable.
- **Prohibited behaviour:** proceeding on `MISSING` or unresolved-conflict evidence for the affected portion of the answer.
- **Confidence/completeness:** mirrors the evidence statuses it receives; does not invent a new confidence measure.
- **Failure behaviour:** this stage *is* an exit point, symmetrically with the Context Sufficiency Gate.
- **Deterministic responsibilities:** the sufficiency threshold itself.
- **LLM-assisted responsibilities:** none.

## Stage: Reasoning Engine

- **Responsibility:** produce a reasoning result from sufficient context and sufficient evidence, using deterministic rules and calculations first, LLM-assisted interpretation second.
- **Inputs:** context, resolved evidence, reasoning plan.
- **Outputs:** `reasoning_result` with an explicit `conclusion_class` (Source Fact, Deterministic Calculation, Derived Insurance Implication, Contextual Judgement, or Recommendation).
- **Permitted behaviour:** deterministic rule evaluation and arithmetic; LLM-drafted implication/synthesis strictly within the evidence-locked reasoning packet (see LLM and Deterministic Boundaries).
- **Prohibited behaviour:** LLM output overriding a deterministic calculation; presenting a Contextual Judgement as a Source Fact.
- **Confidence/completeness:** confidence is reported per conclusion, and typically decreases moving down the conclusion-class list.
- **Failure behaviour:** an unreachable conclusion (e.g. a rule requires a fact that didn't resolve) degrades the outcome rather than being silently skipped.
- **Deterministic responsibilities:** all stable insurance rules, thresholds, arithmetic, and date calculations.
- **LLM-assisted responsibilities:** complex clause synthesis, implication drafting, trade-off articulation, identification of potentially missing reasoning steps.

## Stage: Decision and Safety Gate

- **Responsibility:** decide whether, and in what form, the reasoning result may be surfaced.
- **Inputs:** reasoning result, conclusion class, evidence sufficiency, context sufficiency.
- **Outputs:** final response outcome (see the Failure and Safety Model's supported outcomes); may downgrade a Recommendation to a Contextual Judgement / educational comparison.
- **Permitted behaviour:** applying governed safety thresholds; requiring human review for flagged categories.
- **Prohibited behaviour:** allowing a claim-outcome guarantee or an unconditional recommendation through (see Claim and Recommendation Safeguards).
- **Confidence/completeness:** the final arbiter of whether stage-specific confidence, taken together, clears the governed bar for the conclusion class being surfaced.
- **Failure behaviour:** this is the last governance exit point before communication; `HUMAN_REVIEW_REQUIRED` and `PROCESSING_FAILED` both originate here.
- **Deterministic responsibilities:** all safety thresholds and downgrade rules.
- **LLM-assisted responsibilities:** none — this gate does not use the LLM to decide whether to trust the LLM's own output.

## Stage: Explanation Generator

- **Responsibility:** draft the natural-language explanation appropriate to the audience (consumer vs. advisor) for the outcome the Decision and Safety Gate approved.
- **Inputs:** approved reasoning result, audience register, evidence citations.
- **Outputs:** drafted explanation text, structured per the required output schema.
- **Permitted behaviour:** consumer-language and advisor-language explanation, chosen by audience flag, not by re-deciding what was approved.
- **Prohibited behaviour:** introducing a new fact or softening/hardening a conclusion beyond what the Decision and Safety Gate approved.
- **Confidence/completeness:** inherits the approved outcome's status; does not independently assert confidence.
- **Failure behaviour:** if explanation generation fails validation (see Structured Output Requirements), the stage retries or the response falls back to a template-based explanation rather than an unvalidated draft.
- **Deterministic responsibilities:** citation assembly, output-schema validation.
- **LLM-assisted responsibilities:** consumer-language explanation, advisor-language explanation, follow-up interpretation for explanation phrasing.

## Stage: Response Assembler

- **Responsibility:** assemble the final structured response envelope from the approved outcome, explanation, and citations.
- **Inputs:** approved outcome, explanation, citations, audit trace so far.
- **Outputs:** the final `response` object.
- **Permitted behaviour:** formatting only.
- **Prohibited behaviour:** any content decision — this stage does not reason.
- **Confidence/completeness:** passthrough.
- **Failure behaviour:** assembly failure is a `PROCESSING_FAILED` outcome.
- **Deterministic responsibilities:** all of them.
- **LLM-assisted responsibilities:** none.

## Stage: Audit Trace

- **Responsibility:** record the structured decision trail — which gates were passed or failed and why, what evidence and rules were used, what assumptions were declared.
- **Inputs:** the full request record as it passed through every stage.
- **Outputs:** `audit_trace`, a structured (not free-form chain-of-thought) decision record.
- **Permitted behaviour:** recording governed labels, statuses, and structured rationale.
- **Prohibited behaviour:** recording private LLM chain-of-thought as the audit record (see Failure and Safety Model, Audit Trace section).
- **Confidence/completeness:** captures every stage's reported confidence for later review.
- **Failure behaviour:** an audit-trace write failure should not silently discard the trace; it is itself a `PROCESSING_FAILED`-class event.
- **Deterministic responsibilities:** all of them.
- **LLM-assisted responsibilities:** none.

---

## Intent taxonomy

Runtime components (the Intent Analyzer above all) may select **only** from this governed list:

```text
TERM_EXPLANATION
POLICY_FACT_LOOKUP
POLICY_SUMMARY
COVERAGE_CHECK
EXCLUSION_CHECK
CLAIM_SCENARIO
CLAUSE_IMPLICATION
PRODUCT_EXPLANATION
PRODUCT_COMPARISON
POLICY_COMPARISON
QUOTE_COMPARISON
SUITABILITY_ASSESSMENT
RECOMMENDATION
CALCULATION
DOCUMENT_INTERPRETATION
ADVISOR_EXPLANATION
CLARIFICATION_RESPONSE
FOLLOW_UP
OUT_OF_SCOPE
```

## Context provenance

Every context item retains one of these statuses; an item without a provenance status is not a valid context item.

```text
USER_PROVIDED
DOCUMENT_RESOLVED
SYSTEM_DERIVED
ASSUMED
UNVERIFIED
STALE
SUPERSEDED
```

## Answerability outcomes

Produced by the Context Sufficiency Gate:

```text
ANSWERABLE
ANSWERABLE_WITH_ASSUMPTIONS
PARTIALLY_ANSWERABLE
CLARIFICATION_REQUIRED
NOT_ANSWERABLE
OUT_OF_SCOPE
```

## Reasoning plan types

```text
DIRECT_FACT_PLAN
EXPLANATION_PLAN
CLAUSE_IMPACT_PLAN
DOCUMENT_INTERPRETATION_PLAN
COMPARISON_PLAN
SCENARIO_PLAN
CALCULATION_PLAN
SUITABILITY_PLAN
RECOMMENDATION_PLAN
ADVISOR_COMMUNICATION_PLAN
```

## Evidence statuses

Produced by the Evidence Resolver, consumed by the Evidence Sufficiency Gate:

```text
COMPLETE
SUFFICIENT
PARTIAL
CONFLICTING
MISSING
STALE
ENTITY_UNRESOLVED
VERSION_UNRESOLVED
```

## Conclusion classes

The reasoning result must distinguish between these, in increasing order of the evidence and context strength required to produce them:

1. **Source Fact** — a governed fact, quoted or closely paraphrased, with direct lineage. Requires only that the fact resolve.
2. **Deterministic Calculation** — a computed value from governed facts and stable rules (e.g. applying a co-payment percentage to a claim amount). Requires the calculation's inputs to all resolve.
3. **Derived Insurance Implication** — what a rule or calculation means for the user's situation. Requires sufficient user context in addition to the evidence.
4. **Contextual Judgement** — an assessment that weighs multiple factors without a single deterministic rule (e.g. "this benefit is unlikely to be material given your stated claim history"). Requires broader context and is inherently softer.
5. **Recommendation** — a directive suggestion. Requires the highest evidence and context bar, and is subject to the Recommendation Safeguards in the Failure and Safety Model; is conditional by default (AD-006).

Each class is tagged explicitly in the reasoning result and carried through to the final response — the user-facing answer must never blur a Source Fact and a Contextual Judgement into indistinguishable prose.
