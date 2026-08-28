# Rendering Exit Safety v1

## Status

Bounded Insurance Intelligence safety slice. This milestone deliberately excludes a production LLM provider and does not modify the existing Response Assembler.

## Problem

A constrained prompt does not make model output trustworthy. Post-hoc semantic verification of arbitrary free prose is not a structurally reliable safety boundary: rule/pattern verification is enumerable and incomplete, while an LLM judge recreates the same trust problem one stage later.

The safe v1 approach is therefore to constrain rendering into a representation whose pass/fail properties can be checked deterministically.

## Frozen invariants

1. **The model remains outside the trusted boundary.**
2. **Rendering is optional enhancement over a deterministic safe floor.** The validated `ResponseAssemblerOutput` is always preserved as the fallback.
3. **No free prose is authorized outside canonical render units.**
4. **Conformance is bidirectional.** The gate rejects both commission (unexpected units) and omission (missing required units).
5. **Pass/fail is deterministic for the same envelope and candidate.**
6. **v1 does not claim semantic safety for arbitrary paraphrase.** Every unit uses `PRESERVE_EXACT`.
7. **Safety-critical content cannot be smoothed away.** Limitations and clarifications are required units and must survive exactly.

## Boundary

```text
ResponseAssemblerOutput
        |
        +------------------------------> deterministic safe fallback
        |
        v
Canonical Render Envelope
        |
        v
optional external renderer candidate
        |
        v
Deterministic Bidirectional Conformance
        |
        +-- PASS --> candidate text may be used
        |
        +-- FAIL --> original ResponseAssemblerOutput fallback
```

## Canonical render unit

Each included response section is projected into a canonical unit with:

- `render_unit_id`
- `source_section_id`
- `unit_type`
- `source_text`
- `approved_finding_ids`
- `evidence_reference_ids`
- `limitation_ids`
- `clarification_ids`
- `required`
- `render_policy`
- `sequence`

The existing Response Assembler already preserves finding/evidence/limitation/clarification lineage at section granularity. v1 reuses that lineage and adds an explicit rendering boundary rather than rewriting MO-020.

## Why v1 is exact-preserve only

A renderer could return a valid claim ID beside text that does not actually express that claim. IDs alone prove declaration, not semantic fidelity. Because v1 has no trusted deterministic semantic-equivalence prover, it does not authorize free paraphrase. `PRESERVE_EXACT` is the only render policy.

This is intentionally conservative. Future transformation policies may be added only when their safety properties are independently demonstrated; adding a production model does not by itself justify relaxing this rule.

## Commission checks

The gate fails if the candidate introduces a render unit that is not present in the envelope, changes request/response identity, or otherwise changes the authorized unit set.

## Omission checks

Every v1 unit is `required=True`. The gate fails if any unit is missing, including limitations and clarifications. This prevents a candidate from returning only supported factual content while silently dropping the refusal/limitation that makes the answer safe.

## Ordering and exactness

Candidate unit IDs must match the envelope in the same sequence. Every candidate text must equal the unit `source_text` exactly under `PRESERVE_EXACT`.

## Fallback

On any failure the gate exposes no rendered candidate text and preserves the original validated `ResponseAssemblerOutput` as the deterministic fallback. Rendering is therefore never a correctness dependency.

## Explicit non-goals

v1 does not:

- call an LLM;
- provide a production `LLMRendererProvider`;
- perform semantic entailment;
- use an LLM judge;
- add regex/pattern-based semantic approval;
- authorize recommendation execution;
- change MO-020 response assembly;
- claim sentence/span-level semantic decomposition of findings.

## Acceptance seams

The regression suite proves at minimum:

- exact authorized candidate passes;
- unexpected unit fails;
- missing required limitation fails even when emitted fact text is valid;
- missing required clarification fails;
- rewritten safety text fails;
- rewritten factual/numeric text fails in v1;
- reordered units fail;
- identity mismatch fails;
- failure preserves the original assembler fallback;
- repeated evaluation of the same input produces the same result.

## Next milestone boundary

Do not attach a production model until this exit representation is stable. A future renderer must emit this structured candidate shape. Any future non-exact transformation policy requires its own proof and must not weaken required safety-unit preservation or deterministic fallback.