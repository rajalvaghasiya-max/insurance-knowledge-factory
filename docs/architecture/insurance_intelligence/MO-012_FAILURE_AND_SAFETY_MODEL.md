# MO-012 — Failure and Safety Model

**Status:** Architectural documentation only. No implementation introduced.
**Related documents:** [Core Architecture](MO-012_INSURANCE_INTELLIGENCE_ARCHITECTURE.md) · [Stage Contracts](MO-012_STAGE_CONTRACTS.md) · [LLM and Deterministic Boundaries](MO-012_LLM_AND_DETERMINISTIC_BOUNDARIES.md)

Failure in the Intelligence Layer is a **governed system outcome**, not an exception to be caught and hidden. A request that cannot be safely and fully answered should produce one of the outcomes below — visibly, with a reason — rather than a plausible-sounding answer that overstates what the system actually knows.

---

## Supported response outcomes

```text
ANSWERED
ANSWERED_WITH_LIMITATIONS
PARTIAL_ANSWER
CLARIFICATION_REQUIRED
DOCUMENT_REQUIRED
EVIDENCE_CONFLICT
ABSTAINED
OUT_OF_SCOPE
PROCESSING_FAILED
HUMAN_REVIEW_REQUIRED
```

Every one of these is a first-class, expected outcome of the pipeline — not an error state layered on top of it. The [Stage Contracts](MO-012_STAGE_CONTRACTS.md) document identifies exactly which stage can produce which of these.

## Ambiguous intent

When the Intent Analyzer cannot classify a request with sufficient confidence into a single governed label, the system:

- identifies the ambiguity explicitly, rather than silently picking the most likely label;
- presents bounded interpretations when doing so is genuinely helpful (e.g. "Are you asking about your current policy's waiting period, or waiting periods in general?");
- asks one or more targeted clarification questions; and
- avoids silently choosing a high-risk interpretation (a claim-related or recommendation-adjacent interpretation is never the silent default among several plausible readings).

## Missing context

Clarification questions, when needed, must be:

- material — the answer would actually change based on the response;
- specific — not a generic "can you tell me more?";
- easy to answer — phrased so the user can respond without needing to consult documents themselves where avoidable;
- ordered by importance — the question most likely to change the answer comes first; and
- limited to information that could change the answer — no speculative or merely-interesting questions.

## Missing evidence

When required evidence is not governed (not yet extracted, bound, or published in the Knowledge Factory), the system may:

- provide general education about the topic, clearly distinguished from a product-specific answer;
- answer the portions of the request that *are* supported;
- request the relevant document from the user, if that would unblock resolution;
- explain plainly what could not be verified; or
- abstain entirely, if none of the above is appropriate.

It must **not** fill product-specific gaps from model memory. General insurance education (e.g. "waiting periods are common in health policies and typically range from X to Y") is permitted as general education; asserting a *specific* product's waiting period without governed evidence is not, even if the LLM's training data happens to contain a plausible-looking number.

## Conflicting evidence

When more than one governed fact could answer the same requirement and they disagree, the system attempts resolution through governed statuses, in this order of preference:

```text
RESOLVED_BY_AUTHORITY
RESOLVED_BY_VERSION
RESOLVED_BY_SCOPE
UNRESOLVED
REQUIRES_POLICY_SCHEDULE
REQUIRES_HUMAN_REVIEW
```

If no resolution status applies, the conflict is `UNRESOLVED` and the response outcome is `EVIDENCE_CONFLICT`. Conflicts must remain visible in the audit trace regardless of how (or whether) they were resolved — a conflict that gets silently resolved by an LLM picking whichever fact it saw first is exactly the failure mode this status list exists to prevent.

## Claim safeguards

The system must not claim that a future or unresolved claim:

- will definitely be approved;
- will definitely be rejected;
- will definitely be paid in full; or
- is guaranteed in any other respect.

Claims outcomes depend on adjudication facts the system does not and cannot have at the time of the question (medical records review, documentation completeness, insurer discretion within policy terms). Instead, for claim-scenario questions, the system explains:

- applicable wording — the governed clause(s) that would apply;
- material conditions — what would need to be true for the clause to apply as described;
- missing facts — what the system doesn't know that would matter;
- claim-process dependencies — that the actual outcome depends on the claims process itself; and
- uncertainty — stated plainly, not hedged into vagueness.

## Recommendation safeguards

A `RECOMMENDATION`-class conclusion must be downgraded to an educational comparison (a `Contextual Judgement`, per the Stage Contracts' conclusion classes) when any of the following hold:

- the user's objective is unclear;
- personal context is insufficient;
- the products being considered are not genuinely comparable;
- evidence is partial;
- a material conflict remains unresolved;
- affordability is unknown where it's material to the decision; or
- recommendation confidence is below the governed threshold.

Recommendations are **conditional by default** (AD-006): even a fully-supported recommendation is framed against its stated conditions ("given what you've told me about X, Y is likely to suit you better — this could change if Z"), not as an unconditional directive.

## Human review

The architecture anticipates a future human-review package, without implementing one in this milestone. The package should contain:

```text
request
intent
context
reasoning_plan
evidence
conflicts
calculations
assumptions
reasoning_result
safety_decisions
proposed_answer
```

Potential review triggers include:

- unresolved policy conflicts;
- complex claim interpretation;
- material financial recommendations;
- tax reasoning;
- endorsement interactions;
- lineage failure (evidence that should have resolved cleanly but didn't, suggesting a Knowledge Factory data problem rather than a genuine gap); and
- low-confidence, high-impact decisions.

`HUMAN_REVIEW_REQUIRED` is a legitimate terminal outcome for a request, not merely an internal flag — the user-facing response can and should say plainly that the question needs review before a confident answer can be given.

## Audit trace

PolicyScna should retain **structured decision records** — governed labels, statuses, resolved evidence references, and structured rationale for each gate decision — not private free-form LLM chain-of-thought. This distinction matters for two reasons: a structured trace is auditable and comparable across requests in a way free-form reasoning text is not, and retaining raw chain-of-thought as if it were the system's accountable record would blur exactly the fact/inference boundary this entire architecture exists to preserve. The audit trace records *what was decided and on what governed basis*, not *a transcript of how the model arrived at its draft language*.
