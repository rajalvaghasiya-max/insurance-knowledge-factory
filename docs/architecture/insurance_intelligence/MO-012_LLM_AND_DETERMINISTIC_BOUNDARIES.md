# MO-012 — LLM and Deterministic Boundaries

**Status:** Architectural documentation only. No prompts, models, or executable schemas are defined.
**Related documents:** [Core Architecture](MO-012_INSURANCE_INTELLIGENCE_ARCHITECTURE.md) · [Stage Contracts](MO-012_STAGE_CONTRACTS.md) · [Failure and Safety Model](MO-012_FAILURE_AND_SAFETY_MODEL.md)

PolicyScna intends to use LLMs **extensively** across the Intelligence Layer — but always in governed roles, never as an independent source of truth. This document draws the line precisely: what an LLM is permitted to do, what must remain deterministic or otherwise governed, and how LLM output is kept inside that boundary structurally, not just by instruction.

---

## LLM-permitted responsibilities

An LLM may be used for:

- semantic intent classification;
- implicit intent detection;
- natural-language entity extraction;
- ambiguity identification;
- candidate clarification generation;
- candidate reasoning-plan generation;
- complex clause synthesis;
- implication drafting;
- trade-off articulation;
- consumer-language explanation;
- advisor-language explanation;
- follow-up interpretation; and
- identification of potentially missing reasoning steps.

Every one of these is a *language and semantic* task: understanding what was said, drafting how something should be said, or noticing where reasoning might be incomplete. None of them is a task that establishes what is *true* about a product, a policy, or a rule.

## Deterministic or governed responsibilities

The following must remain deterministic, rule-based, or otherwise governed outside LLM judgment:

- input and output validation;
- allowed intent labels;
- entity identity;
- product and variant resolution;
- source authority;
- document version selection;
- evidence lineage;
- arithmetic;
- date calculations;
- stable insurance rules;
- threshold evaluation;
- safety thresholds;
- evidence citation assembly;
- recommendation permission; and
- final support validation.

The dividing line is not "hard vs. easy" — some of these (document version selection, source authority) are exactly the kind of judgment an LLM could plausibly attempt. They are excluded from LLM judgment specifically *because* getting them wrong corrupts the evidentiary basis for everything downstream, and because the Knowledge Factory already solves them deterministically (generic source registration, document identity resolution, product identity reference) — the Intelligence Layer consumes those governed decisions rather than re-deciding them.

## Evidence-locked reasoning

Not every LLM call in the system performs insurance-fact reasoning. The boundary below applies specifically to calls that interpret, derive, compare, or explain insurance facts — not to every LLM call anywhere in the pipeline:

> **Understanding-stage LLM calls** (Intent Analyzer, Context Builder) may receive normalized user input and approved conversation context under their own stage contract, in order to classify intent, detect implicit intent, interpret follow-ups, identify ambiguity, and extract entities from natural language. This is necessary and approved — these stages exist specifically to work with raw, normalized user language before any evidence has been resolved. They may not, in doing so, establish insurance facts, evidence, or entity identity — only the Deterministic or governed responsibilities listed above may do that.
>
> **Reasoning- and explanation-stage LLM calls** (Reasoning Engine, Explanation Generator) must operate only within an approved evidence-locked reasoning packet, as defined below. These are the calls that interpret what evidence means, derive implications, compare products, or generate an explanation — and are the calls this section's evidence-locking guarantee is about.

The mechanism that keeps *reasoning and explanation* LLM calls inside their boundary is the **approved reasoning packet**: such a call is never an open-ended prompt against raw documents or model memory. It is constructed by deterministic upstream stages and contains only what has already been governed:

```text
task
user_goal
approved_facts
approved_calculations
applicable_rules
known_context
declared_assumptions
unresolved_conflicts
prohibited_claims
required_output_schema
```

> **The LLM reasons within the approved evidence packet. It does not establish the factual universe independently.**

This is the single most important structural constraint in this document. Every other rule here is either an instance of this principle or a consequence of it.

## Structured output requirements

Every LLM-assisted stage must:

- return structured output;
- conform to a versioned contract;
- use controlled labels where defined (e.g. the governed intent taxonomy, evidence statuses, conclusion classes);
- record model and prompt versions;
- reject invalid output;
- preserve evidence references (an LLM must not paraphrase away a citation);
- and allow fallback, retry, or abstention.

Free-text LLM output that has not been validated against its stage's structured contract is not eligible to become part of a response.

## Prohibited LLM behaviour

Across every stage, an LLM must not:

- invent product facts;
- decide document authority;
- choose a policy version without governed resolution;
- override deterministic calculations;
- hide conflicting evidence;
- convert uncertainty into certainty;
- classify missing information as "not covered"; or
- present inference as explicit policy text.

The last two are worth calling out specifically because they are the failure modes most likely to look like a *helpful* answer while being an ungoverned one: "not covered" is a strong, specific claim that requires the same evidentiary standard as any other Source Fact, and a well-drafted implication can read exactly like quoted policy text unless the two are kept visibly distinct (per the Conclusion Classes in the Stage Contracts document).

## Model independence

The architecture must remain portable across model providers. No stage contract in this document or in [MO-012_STAGE_CONTRACTS.md](MO-012_STAGE_CONTRACTS.md) names or depends on a specific model vendor, model family, or hosting arrangement. "LLM-assisted responsibility" means *a task suitable for a capable language model*, not a commitment to any particular one. Implementation milestones (MO-013 onward) may choose a specific model for a specific stage, but the stage's contract — its inputs, outputs, and boundary — must not change if that choice changes later.
