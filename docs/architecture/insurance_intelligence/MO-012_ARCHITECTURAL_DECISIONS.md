# MO-012 — Architectural Decisions

**Status:** Architectural documentation only. No implementation introduced.
**Related documents:** [Core Architecture](MO-012_INSURANCE_INTELLIGENCE_ARCHITECTURE.md) · [Stage Contracts](MO-012_STAGE_CONTRACTS.md) · [LLM and Deterministic Boundaries](MO-012_LLM_AND_DETERMINISTIC_BOUNDARIES.md) · [Failure and Safety Model](MO-012_FAILURE_AND_SAFETY_MODEL.md)

This document records the architectural decisions underlying the Insurance Intelligence Layer, in a consistent Decision / Context / Rationale / Consequences / Status format.

---

## AD-001 — Staged Intelligence Pipeline

**Decision:** PolicyScna will use bounded stages rather than one unrestricted agent.

**Context:** A single, unrestricted agent (one large prompt with tool access) can plausibly perform intent classification, evidence lookup, reasoning, and explanation in one undifferentiated pass.

**Rationale:** An undifferentiated agent has no clean point at which to enforce "evidence before conclusion" or "context before recommendation" — every principle in this architecture depends on there being a specific stage responsible for, and accountable for, each decision.

**Consequences:** More upfront design and more stages to implement (MO-013 through MO-018); in exchange, each stage is independently testable, independently governable, and independently able to fail safely without silently degrading the whole pipeline.

**Status:** Accepted.

## AD-002 — Governed Evidence Is Authoritative

**Decision:** LLM memory cannot override governed evidence.

**Context:** A capable LLM will often "know" something about insurance in general, or even about a specific well-known product, from training data.

**Rationale:** Training-data knowledge has no lineage, no version, no currentness guarantee, and no connection to the specific document a specific user's policy is governed by. Treating it as equivalent to a governed fact would silently reintroduce exactly the ungoverned-knowledge risk the Knowledge Factory was built to eliminate.

**Consequences:** The system will sometimes decline to answer a question a general-purpose chatbot would answer confidently. This is intentional.

**Status:** Accepted.

## AD-003 — Reasoning Plan Is Execution Authority

**Decision:** The validated structured plan, not an open-ended prompt, controls execution.

**Context:** The Reasoning Planner produces a `reasoning_plan` with an explicit plan type and explicit evidence requirements.

**Rationale:** If execution were instead driven by re-interpreting the original user prompt at each stage, later stages could silently drift from what was actually validated earlier, and the Evidence Resolver would have no fixed target to resolve against.

**Consequences:** Every downstream stage operates against the plan, not against the raw request; a stage that wants to change what's needed must produce a new or amended plan, not act outside it.

**Status:** Accepted.

## AD-004 — Facts and Conclusions Are Typed Separately

**Decision:** Source facts, calculations, implications, judgements, and recommendations remain separate.

**Context:** These five conclusion classes require progressively stronger evidence and context (see Stage Contracts, Conclusion Classes).

**Rationale:** If a response can't distinguish "the policy says X" from "based on X and your situation, we think Y," users and downstream systems cannot tell which parts of an answer are directly verifiable and which are interpretation.

**Consequences:** Every reasoning result and every response must carry its conclusion class explicitly; the Explanation Generator must preserve this distinction in the final wording, not just in internal structure.

**Status:** Accepted.

## AD-005 — Clarification and Abstention Are Valid Outcomes

**Decision:** The system is not required to answer every request immediately.

**Context:** `CLARIFICATION_REQUIRED`, `ABSTAINED`, `DOCUMENT_REQUIRED`, and similar outcomes are first-class outcomes, not failure states to be minimized at all costs.

**Rationale:** A forced answer under insufficient context or evidence is a worse outcome than a clarifying question or an honest "I can't verify this yet" — particularly in a domain where a wrong answer has real financial or health consequences.

**Consequences:** Product metrics that only reward "answered" outcomes would create pressure against this decision; that tension is called out explicitly here so it isn't rediscovered as a surprise later.

**Status:** Accepted.

## AD-006 — Recommendations Use a Higher Evidence Standard

**Decision:** Recommendations require stronger context, evidence, and safety review than explanations.

**Context:** See Recommendation Safeguards in the Failure and Safety Model.

**Rationale:** A `RECOMMENDATION` conclusion directs a user's action or decision; an `Explanation` merely informs. The former carries materially higher consequence if wrong.

**Consequences:** Many requests that could technically be answered with an on-the-nose recommendation will instead surface as a conditional or educational comparison, by design, whenever the higher bar isn't cleared.

**Status:** Accepted.

## AD-007 — Stable Calculations and Rules Are Deterministic

**Decision:** LLMs may explain deterministic outputs but may not replace them.

**Context:** Arithmetic, date calculations, and stable insurance rules (e.g. a governed co-payment threshold) have a single correct output for a given input.

**Rationale:** An LLM computing "10% of ₹2,00,000 minus the deductible" is strictly worse — in both reliability and auditability — than a deterministic calculation the LLM is then handed to explain in plain language.

**Consequences:** The Reasoning Engine's deterministic component must be complete enough that the LLM's role in a `Deterministic Calculation` conclusion is limited to explaining a value it did not itself produce.

**Status:** Accepted.

## AD-008 — LLM Reasoning Is Evidence-Locked

**Decision:** LLMs receive approved facts, rules, context, and constraints for insurance-fact reasoning and explanation.

**Context:** See Evidence-Locked Reasoning in the LLM and Deterministic Boundaries document. Not every LLM call in the system performs insurance-fact reasoning: Understanding-layer stages (Intent Analyzer, Context Builder) necessarily operate on normalized user language and approved conversation context in order to classify intent, detect implicit intent, interpret follow-ups, identify ambiguity, and extract entities from natural language. That is a distinct responsibility from establishing or reasoning over insurance facts, and evidence-locking applies to the latter.

**Rationale:** Constraining what a *factual reasoning or explanation* LLM call can see is a structural guarantee, not a prompting convention — it remains true even if prompt wording changes, model provider changes, or a future engineer forgets to add an instruction. Applying that same absolute constraint to Understanding-layer calls would be incoherent with their approved stage contracts (see Stage Contracts: Intent Analyzer, Context Builder) and would make those stages impossible to implement, since their entire responsibility is to work with raw, normalized user language before any evidence has been resolved.

**Consequences:** Every factual reasoning or explanation call requires upstream stages to assemble a complete and bounded reasoning packet before the LLM is invoked; there is no reasoning or explanation LLM call that operates on raw, unfiltered inputs. Understanding-stage calls may operate on normalized user language and approved conversational context, but may not establish insurance facts or evidence, select or resolve entities against governed identity records, or otherwise reach a conclusion that requires evidence lineage — that boundary is enforced by the Understanding-layer stage contracts themselves (see Stage Contracts: Intent Analyzer, Context Builder), not by evidence-locking.

**Status:** Accepted, clarified. Originally recorded with an absolute "no LLM call operates on raw, unfiltered inputs" consequence; corrected following CTO review to distinguish Understanding-stage LLM calls from Reasoning/Explanation-stage LLM calls, consistent with the already-approved Intent Analyzer and Context Builder stage contracts.

## AD-009 — Confidence Is Stage-Specific

**Decision:** PolicyScna will not rely on one generic confidence score.

**Context:** Intent classification confidence, evidence sufficiency, and reasoning-result confidence are conceptually different quantities.

**Rationale:** Collapsing them into a single number hides exactly the information a safety gate needs — a request could have high intent-classification confidence and low evidence confidence, and treating that as "medium confidence overall" would obscure which part is actually uncertain.

**Consequences:** Each stage reports its own confidence/completeness signal in its own terms (see each stage's contract); the Decision and Safety Gate is responsible for synthesizing these into a pass/downgrade/exit decision, not for the individual stages to pre-average them away.

**Status:** Accepted.

## AD-010 — Shared Architecture, Separate Domain Capability Packs

**Decision:** Health, Motor, and Life use common contracts with domain-specific logic.

**Context:** See Domain Capability Model in the core architecture document.

**Rationale:** The four-layer pipeline, the stage contracts, and the LLM/deterministic boundary are domain-agnostic; what's domain-specific is the actual intents, evidence types, rules, and safety requirements.

**Consequences:** Extending to Motor or Life should not require rearchitecting the pipeline — only authoring a new capability pack. No Motor or Life work is authorized by this document.

**Status:** Accepted.

## AD-011 — Structured Trace Instead of Chain-of-Thought Exposure

**Decision:** The system records auditable decisions, evidence, rules, assumptions, and outcomes.

**Context:** See Audit Trace in the Failure and Safety Model.

**Rationale:** A structured, governed-label trace is reviewable, comparable across requests, and does not conflate the model's internal deliberation with the system's accountable decision record.

**Consequences:** Audit tooling and any future human-review package are built against structured trace fields, not against raw model output logs.

**Status:** Accepted.

## AD-012 — Architecture Before Implementation

**Decision:** MO-012 introduces documentation only.

**Context:** This Manufacturing Order.

**Rationale:** Given the scope of the Intelligence Layer and its dependency on the Knowledge Factory's governance discipline being carried forward faithfully, defining the target architecture and its constraints before writing any implementation reduces the risk of building a stage that later has to be re-architected to fit a boundary that should have been decided up front.

**Consequences:** MO-013 through MO-018 each implement one stage (or stage group) against the contracts defined here; none of them may weaken a boundary defined in this document without a new, explicit architectural decision recorded here.

**Status:** Accepted.
