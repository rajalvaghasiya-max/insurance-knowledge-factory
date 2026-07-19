# MO-012 — Insurance Intelligence Architecture

**Status:** Architectural documentation only. No implementation introduced.
**Related documents:** [Stage Contracts](MO-012_STAGE_CONTRACTS.md) · [LLM and Deterministic Boundaries](MO-012_LLM_AND_DETERMINISTIC_BOUNDARIES.md) · [Failure and Safety Model](MO-012_FAILURE_AND_SAFETY_MODEL.md) · [Architectural Decisions](MO-012_ARCHITECTURAL_DECISIONS.md)

---

## Purpose

The Knowledge Factory (the existing, implemented layer of PolicyScna — governed migration, generic source registration, document identity resolution, conditional-rule binding and canonical projection) answers one question:

> **What does the authoritative insurance material say?**

The Insurance Intelligence Layer, described in this document, answers a different question, downstream of the first:

> **What does that information mean for this user, this question, this product, this policy, or this decision?**

The Knowledge Factory manufactures governed knowledge assets. The Intelligence Layer *reasons over* those assets to produce an answer, an explanation, or a bounded recommendation for a specific person's situation — without ever becoming a second, competing source of truth. Every fact the Intelligence Layer relies on must trace back to something the Knowledge Factory already governed. The Intelligence Layer does not extract, classify, bind, or publish evidence; it consumes what has already been governed and reasons about what it means for a specific request.

## Product alignment

PolicyScna is building an **Insurance Intelligence Engine**. It is explicitly **not**:

- a CRM;
- a lead-management platform;
- a generic chatbot;
- a comparison website;
- or a frontend-first insurance application.

The Intelligence Layer is a reasoning capability that other surfaces (advisor tools, customer-facing products, internal review tools) can be built on top of — it is not itself a product surface, and this document does not define one.

## Architectural principles

1. **Trust before fluency.** A well-written answer that isn't grounded is worse than a plain, correctly-hedged one.
2. **Evidence before conclusion.** No conclusion is produced without an identifiable evidentiary basis.
3. **Context before recommendation.** Recommendations require sufficient user and situational context; absent that, the system explains rather than recommends.
4. **Clarification before unsupported assumptions.** When a material fact is missing, the system asks rather than assumes.
5. **Explicit distinction between fact and inference.** A quoted policy fact, a computed value, and a drawn implication are never presented identically.
6. **Traceability for material conclusions.** Every conclusion that could affect a real decision carries a trace back to its supporting evidence and rules.
7. **Domain-specific reasoning within a shared architecture.** Health, Motor, and Life share one pipeline; their domain knowledge differs, not their governance model.
8. **LLMs as constrained components, not sources of truth.** An LLM interprets, drafts, and explains within an evidence boundary it does not control.

These principles govern every layer, stage, and decision below; where a later section appears to create tension with one of them (for example, allowing an LLM to draft an explanation), the LLM/Deterministic Boundaries document resolves exactly how the tension is bounded.

## Four architectural layers

```text
Layer 1 — Understanding
  Request Intake
  Intent Analyzer
  Context Builder
  Context Sufficiency Gate

Layer 2 — Grounding
  Reasoning Planner
  Evidence Resolver
  Evidence Sufficiency Gate

Layer 3 — Intelligence
  Deterministic Rules
  Calculations
  LLM-Assisted Interpretation
  Domain Reasoning

Layer 4 — Communication and Governance
  Decision and Safety Gate
  Explanation Generator
  Response Assembler
  Audit Trace
```

**Layer 1 (Understanding)** turns a raw user interaction into a structured, classified request with sufficient context to proceed, or identifies what's missing.

**Layer 2 (Grounding)** turns a classified intent into a concrete plan for what evidence is required, then resolves that evidence against the Knowledge Factory's governed assets — never against model memory.

**Layer 3 (Intelligence)** is where reasoning happens: deterministic rule evaluation and calculation first, LLM-assisted interpretation second, always operating over the evidence Layer 2 resolved, never independently of it.

**Layer 4 (Communication and Governance)** decides whether and how the result may be surfaced, generates an explanation appropriate to the audience, assembles the final structured response, and records what happened for audit.

Full stage-level contracts (responsibilities, inputs, outputs, permitted/prohibited behaviour) are defined in [MO-012_STAGE_CONTRACTS.md](MO-012_STAGE_CONTRACTS.md), not here — this document defines the shape of the architecture, not the interface of each box.

## End-to-end pipeline

```text
User Interaction
        ↓
Request Intake
        ↓
Intent Analyzer
        ↓
Context Builder
        ↓
Context Sufficiency Gate
        ↓
Reasoning Planner
        ↓
Evidence Resolver
        ↓
Evidence Sufficiency Gate
        ↓
Reasoning Engine
        ↓
Decision and Safety Gate
        ↓
Explanation Generator
        ↓
Response Assembler
        ↓
Final Answer and Evidence Trace
```

Both sufficiency gates (Context, Evidence) and the Decision and Safety Gate are **exit points**, not merely checkpoints: a request may leave the pipeline at any of these points with a governed non-answer outcome (clarification required, evidence conflict, abstained, etc. — see the [Failure and Safety Model](MO-012_FAILURE_AND_SAFETY_MODEL.md)) rather than being forced through to a low-confidence answer.

## Execution modes

Not every request needs the full pipeline at full depth. Three execution modes describe how far a request travels and how much reasoning it requires.

### Direct Grounded Answer

For simple factual questions ("What is my waiting period for cataract surgery?").

```text
Intent → Entity Resolution → Evidence Resolution → Answer → Citation
```

Minimal reasoning; the answer is close to a direct, cited lookup against governed evidence.

### Interpretive Answer

For questions asking what a clause or term means in practice ("What does my co-payment clause actually mean for a ₹2,00,000 claim at age 63?").

```text
Intent → Context → Evidence → Calculation or Rule → Implication → Explanation
```

Requires binding evidence to the user's specific situation and applying deterministic calculation or rule evaluation before an LLM drafts the implication in plain language.

### Decision Support

For comparisons, suitability assessments, and recommendations ("Should I keep my base policy or add a super top-up?").

```text
Intent → Context Sufficiency → Clarification → Reasoning Plan
       → Multi-source Evidence → Scenario Reasoning → Trade-off Assessment
       → Safety Gate → Conditional Recommendation
```

The deepest mode: multiple evidence sources, explicit scenario reasoning, and a safety gate that may downgrade an intended recommendation to an educational comparison (see AD-006 and the Recommendation Safeguards in the Failure and Safety Model).

## Domain capability model

Health, Motor, and Life Insurance share the same four-layer pipeline and the same stage contracts. What differs between them is captured in a **domain capability pack**, not in the pipeline itself. Each capability pack may define:

- domain intents (a domain-scoped subset/extension of the shared intent taxonomy);
- required context per intent;
- evidence requirements (which governed knowledge types are needed);
- reasoning rules (domain-specific deterministic rules, e.g. Health waiting-period logic vs. Motor IDV depreciation schedules);
- deterministic calculations;
- comparison dimensions (what "comparable" means within the domain);
- safety requirements (domain-specific claim/recommendation safeguards); and
- evaluation scenarios (domain-specific test scenarios analogous to the ten challenge scenarios below).

This is the architectural expression of AD-010: one governance model, many domain packs. Only Health has any governed knowledge today (via the Knowledge Factory); Motor and Life capability packs are named here for extensibility but are out of scope for MO-012 and every subsequent milestone until explicitly authorized.

## Milestone roadmap

```text
MO-013 — Intent Analyzer
MO-014 — Context Builder
MO-015 — Reasoning Planner
MO-016 — Evidence Resolver
MO-017 — Reasoning Engine
MO-018 — Explanation Generator
```

This document defines the target architecture those milestones will implement, stage by stage, against the contracts in [MO-012_STAGE_CONTRACTS.md](MO-012_STAGE_CONTRACTS.md). No implementation order is authorized by this document; each of MO-013 through MO-018 requires its own Manufacturing Order.

---

## Appendix — Architecture Challenge Scenarios

The architecture above must be able to route each of the following ten representative scenarios to a safe, governed outcome without bypassing evidence governance. None of these are simulated end-to-end; each shows only the routing the architecture implies.

### 1. Direct policy fact question
*"What is my sum insured?"*
- **Execution mode:** Direct Grounded Answer
- **Likely intent:** `POLICY_FACT_LOOKUP`
- **Required context:** resolved policy/product identity
- **Evidence needs:** a single governed fact with lineage
- **Reasoning:** none beyond lookup
- **Safe outcome:** `ANSWERED`, with citation

### 2. Clause implication question
*"What does my co-payment clause mean for a ₹2,00,000 claim if I'm 63?"*
- **Execution mode:** Interpretive Answer
- **Likely intent:** `CLAUSE_IMPLICATION`
- **Required context:** age at entry, claim amount, applicable section
- **Evidence needs:** the governed conditional-rule assertion (e.g. the Star Comprehensive copay rule) plus its scope
- **Reasoning:** deterministic rule evaluation (age ≥ 61, section applicability), then LLM-drafted implication
- **Safe outcome:** `ANSWERED` if all inputs resolve; `CLARIFICATION_REQUIRED` if age-at-entry is unknown

### 3. Product explanation
*"Explain what Star Comprehensive covers."*
- **Execution mode:** Interpretive Answer
- **Likely intent:** `PRODUCT_EXPLANATION`
- **Required context:** product identity
- **Evidence needs:** governed product-knowledge records (once published, per the Knowledge Factory's D0.2/D0.3 layers)
- **Reasoning:** synthesis/summarization of multiple governed facts by the LLM, evidence-locked
- **Safe outcome:** `ANSWERED_WITH_LIMITATIONS` if some benefit categories are not yet governed

### 4. Product comparison
*"Compare Star Comprehensive and [another governed product]."*
- **Execution mode:** Decision Support (comparison sub-case)
- **Likely intent:** `PRODUCT_COMPARISON`
- **Required context:** both product identities resolved
- **Evidence needs:** comparable governed facts on both sides, on the same comparison dimensions
- **Reasoning:** deterministic dimension-by-dimension comparison, LLM-drafted trade-off narrative
- **Safe outcome:** `ANSWERED_WITH_LIMITATIONS` or `PARTIAL_ANSWER` if one product lacks governed data on a dimension

### 5. Claim scenario
*"If I claim for a knee surgery at age 65, will it be covered?"*
- **Execution mode:** Interpretive Answer
- **Likely intent:** `CLAIM_SCENARIO`
- **Required context:** age, procedure, policy tenure/continuity
- **Evidence needs:** waiting-period and exclusion rules, co-payment rules
- **Reasoning:** deterministic rule evaluation against declared scenario facts
- **Safe outcome:** `ANSWERED_WITH_LIMITATIONS` — explains applicable wording and conditions; never a claims-approval guarantee (Claim Safeguards)

### 6. Base policy versus super top-up decision support
*"Should I add a super top-up or increase my base sum insured?"*
- **Execution mode:** Decision Support
- **Likely intent:** `SUITABILITY_ASSESSMENT` or `RECOMMENDATION`
- **Required context:** current sum insured, claim history/appetite, affordability signal, deductible tolerance
- **Evidence needs:** both product structures, governed rules for top-up trigger mechanics
- **Reasoning:** scenario reasoning across claim-size bands, trade-off assessment, safety gate
- **Safe outcome:** `ANSWERED_WITH_LIMITATIONS` as a conditional/educational comparison if personal context (affordability, risk appetite) is insufficient — downgraded per Recommendation Safeguards

### 7. Advisor-facing explanation
*"Explain the co-payment clause to me the way I'd explain it to a client."*
- **Execution mode:** Interpretive Answer
- **Likely intent:** `ADVISOR_EXPLANATION`
- **Required context:** advisor audience flag (changes explanation register, not evidence)
- **Evidence needs:** same governed evidence as the consumer-facing case
- **Reasoning:** identical deterministic reasoning; only the Explanation Generator's register changes
- **Safe outcome:** `ANSWERED`, using advisor-register language

### 8. Insufficient evidence
*"What's my room-rent limit?"* (no governed room-rent fact exists yet)
- **Execution mode:** Direct Grounded Answer (attempted)
- **Likely intent:** `POLICY_FACT_LOOKUP`
- **Required context:** policy identity (resolvable)
- **Evidence needs:** a governed room-rent fact — absent
- **Reasoning:** none reachable
- **Safe outcome:** `DOCUMENT_REQUIRED` or `ABSTAINED` — never filled from model memory

### 9. Conflicting evidence
*Two governed sources disagree on a waiting period.*
- **Execution mode:** any
- **Likely intent:** depends on the underlying question
- **Required context:** as needed for the underlying intent
- **Evidence needs:** resolves to more than one candidate fact
- **Reasoning:** conflict resolution attempted (`RESOLVED_BY_AUTHORITY`, `RESOLVED_BY_VERSION`, `RESOLVED_BY_SCOPE`); if none apply, conflict remains
- **Safe outcome:** `EVIDENCE_CONFLICT`, visible in trace, never silently resolved by the LLM picking one

### 10. Follow-up question requiring conversation context
*"And what about my spouse's policy?" (after a prior question about the user's own policy)*
- **Execution mode:** inherits the mode of the underlying re-derived intent
- **Likely intent:** `FOLLOW_UP`, re-resolved against conversation context into the appropriate underlying intent
- **Required context:** prior turn's resolved entities, explicitly re-validated (not silently reused) via Context Builder
- **Evidence needs:** re-resolved for the new entity (spouse's policy), not inherited from the prior turn's evidence
- **Reasoning:** as for the re-derived intent
- **Safe outcome:** `ANSWERED` if the new entity resolves; `CLARIFICATION_REQUIRED` if "my spouse's policy" doesn't resolve to a specific governed policy identity
