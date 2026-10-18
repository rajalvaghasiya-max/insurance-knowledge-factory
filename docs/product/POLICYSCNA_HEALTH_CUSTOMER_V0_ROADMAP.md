# PolicyScna Health Customer Intelligence v0 — Product Roadmap

Status: FROZEN FOR EXECUTION
Date: 2026-10-18
Parent: #412

## North Star

A normal person can ask PolicyScna a Health insurance question, continue the conversation naturally, and receive a safe, correct, useful, easy-to-understand answer grounded in governed insurance knowledge.

This phase is not an architecture-completion program. Product failures determine the next work.

## Operating rule

Architecture is frozen by default. Do not add a new subsystem, agent, framework, database design, ontology layer, governance abstraction, or cross-domain expansion unless the customer journey cannot safely progress without it.

Fix reusable failure classes, never individual benchmark questions.

## Phase plan

### Phase 0 — Freeze and baseline

Current evidence is accepted but bounded:
- GSI Genericity: PASS.
- Authority & Customer Safety: PASS.
- Combined frozen gate: `advance_allowed=true`.
- Customer Quality: NOT_SCORED.
- Health repeatability remains PENDING unless separately proven.

The P1E safety result proves the tested authority-pressure path did not release unsupported payment/claim conclusions. It does not prove cross-concept routing/relevance correctness.

### Phase 1 — First runnable answer path (#420)

Build one founder-usable local product path:

`customer question -> GSI interpretation -> concept/product routing -> governed knowledge -> customer answer projection -> relevance invariant -> Rendering Exit Safety -> released customer text`

Required behavior:
- validated GSI interpretation drives semantic routing on this slice;
- topic/concept is selected from the interpretation, not hard-wired to co-payment;
- governed knowledge is loaded through repository-backed reusable registries/adapters, not hand-built test fixtures;
- concept-only questions are supported without requiring a named product;
- product-specific conclusions require resolved product evidence;
- wrong-concept ordinary answers are never released;
- literal customer text is visible through one tiny local browser page;
- diagnostics are separate from customer prose.

Acceptance:
- all six frozen dev-seed questions reach customer-visible released text or a justified governed clarification;
- zero wrong-concept releases;
- no fake adapters or test-fixture-only product execution;
- existing Rendering Exit Safety remains authoritative;
- no question-specific repair code;
- full CI remains green.

### Phase 2 — Customer education content (#421, parallel with Phase 1)

Author governed general education for:
- waiting period;
- restoration;
- room-rent limit;
- bariatric surgery;
- co-payment.

PED remains the quality reference.

Each concept answer should clearly cover:
1. what it is;
2. why it matters in practice;
3. what genuinely depends on the specific policy/customer facts.

Do not infer claim payment, coverage, admissibility, recommendation, or personal outcome.

### Phase 3 — Dev benchmark and minimum conversation continuity (#419 resumes)

After the six seed questions run through the real product path:
- expand to 36 preregistered dev questions;
- include at least 8 multi-turn conversations;
- implement only the minimum typed context required for natural follow-ups.

Allowed carried context is limited to material items such as:
- current concept;
- resolved product, if any;
- relevant scenario facts;
- previous clarification;
- customer facts required by the next turn.

This is not authorization for long-term memory, an agent framework, or autonomous planning.

### Phase 4 — Product improvement loop

Score every dev item independently on:
- Safety — hard gate;
- Correctness;
- Usefulness;
- Clarity;
- Deferral — necessary vs unnecessary.

Every failed item receives exactly one primary failure origin and optional secondary tags.

Primary failure origins:
- LANGUAGE_INTERPRETATION
- CONVERSATION_CONTEXT
- MISSING_KNOWLEDGE
- EVIDENCE_OR_PUBLICATION
- REASONING
- SAFETY_BOUNDARY
- EXPLANATION_OR_PRESENTATION

Only primary origins drive the repair priority. Fix the largest reusable failure class.

Dev target:
- 0 unsafe released answers;
- >=80% useful;
- correctness and clarity reported separately;
- unnecessary deferral rate explicitly reported;
- no question-specific runtime code.

Also track unsupported-question handling quality: when PolicyScna cannot answer safely, it should ask for the most useful next information rather than merely refuse.

### Phase 5 — Independent holdout

Use 15–20 frozen questions from an independent author who has not seen the dev set, prompts, templates, failure logs, prior blind wording, or repair history.

Freeze exact bytes/hash before the checkpoint. Run only at milestone checkpoints.

Success requires:
- 0 unsafe released answers;
- holdout usefulness reasonably close to dev usefulness;
- no material overfit;
- unnecessary deferral remains controlled.

### Phase 6 — Small Health beta

Only after the holdout gate, expose the Health conversation product to a small controlled user group. Learn what real users ask, where they abandon, which follow-ups occur naturally, and which policy-specific requests dominate.

### Phase 7 — Scope expansion

Only after the Health conversation product is credible should we evaluate policy/quote upload, comparison, recommendation, broader Health coverage, Motor, or Life. Their detailed order is intentionally not fixed now.

## Architecture tripwires

Do not replace the existing answer architecture unless either condition becomes true:

1. adding one governed concept requires runtime changes in more than one pipeline stage; or
2. after two product-repair weeks, dev usefulness remains below 50% primarily because of pipeline mechanics rather than missing knowledge/content.

Only then reopen the deterministic-projector vs constrained-LLM-written-answer decision.

## Explicitly out of scope now

- Motor or Life;
- recommendation/suitability expansion;
- quote/policy upload;
- database redesign;
- public deployment infrastructure;
- repository cleanup or script retirement;
- ontology redesign;
- new agents/frameworks;
- broad governance redesign;
- product-specific special cases to pass benchmark questions.

## Governance rule

Govern insurance authority and truth proportionately to risk. Existing safety, publication, evidence and authority controls remain intact. Product application code, benchmark data and local UI should not cause new architecture merely because they are new files.

If fingerprint/capability tooling materially blocks product work, repair the tooling itself rather than using temporary diagnostic commits as routine workflow.

## Weekly CTO checkpoint

Track only these core numbers:
- Questions runnable
- Useful answers
- Unsafe released answers
- Unnecessary deferrals
- Runtime changes required per new concept
- Top primary failure class

These numbers determine the next week's work.

## Milestone success definition

PolicyScna Health Customer Intelligence v0 can answer a diverse set of ordinary Health insurance questions in a real conversation, using governed knowledge, with zero unsafe releases, at least 80% useful answers on the development set, comparable performance on an independent holdout, controlled unnecessary deferral, and no question-specific runtime changes.

## Immediate execution order

1. Freeze this roadmap.
2. Execute #420 and #421 in parallel.
3. Run the six frozen dev-seed questions through the real product path and inspect literal answers.
4. Resume #419 and add minimum conversation continuity.
5. Run the 36-question dev benchmark.
6. Repair only the dominant reusable failure class.
7. Run the independent holdout checkpoint.
8. Move to a small Health beta only if the checkpoint passes.
