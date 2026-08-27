# Insurance Intelligence — Authority-Enforced Explanation V1

## Status

Implementation slice for the frozen Assertion / Advisory Boundary. This is a compatibility-preserving integration guard around the existing MO-019 Explanation Generator.

## Audit result

MO-019 is already evidence-locked and deterministic. It consumes only an eligible Decision Gate output, renders registered templates, preserves finding/evidence references, and runs fidelity checks including no-new-facts, no-new-reasoning, and no-recommendation checks.

The remaining integration seam was that MO-019 accepts a raw `DecisionGateOutput`. A new Insurance Intelligence caller could therefore bypass the newly introduced authority-enforcement wrapper and call the legacy explanation path directly.

## V1 invariant

New Insurance Intelligence orchestration may enter Explanation only through `AuthorityEnforcedExplanationGenerator`.

The wrapper requires an `AuthorityEnforcementResult` whose posture proves all of the following:

- `enforcement_outcome == DELEGATED_TO_DECISION_GATE`;
- the Decision Gate was actually called;
- the resulting `DecisionGateOutput` is preserved;
- no advisory safety obligation remains;
- the ordinary assertion path is explicitly permitted;
- recommendation authorization remains false.

If any condition is not met, explanation generation is refused before the legacy generator is called.

## Compatibility

The legacy MO-019 generator and contracts remain unchanged for historical pilot compatibility. This slice changes the authorized entry point for the new Intelligence path, not the renderer internals.

## Scope exclusions

This milestone does not:

- authorize advisory or recommendation output;
- change explanation templates;
- change terminology handling;
- change fidelity rules;
- modify Decision/Safety Gate behavior;
- add LLM rendering;
- create a recommendation engine.

## Architectural consequence

The complete current path is now:

`Authority + Intent -> Reconciliation -> Context -> Instance Sufficiency -> Planning -> Evidence (instance-enforced) -> Evidence Sufficiency -> Reasoning -> Authority-Enforced Decision -> Authority-Enforced Explanation`

This closes the ordinary-assertion publication bypass for the current phase.
