# Independent Holdout Author Instructions — Health Customer v0

## Purpose

Create the independent holdout set for the Health Customer v0 milestone. The holdout is meant to test whether PolicyScna generalizes to ordinary customer language that was not used during the current development repair cycle.

Do not score the system and do not inspect any existing dev benchmark, implementation, repair notes, prompts, component text, prior live results, or earlier holdout wording.

## Independence requirement

Before authoring, confirm all of the following are true:

- You have not seen the existing 36-case development benchmark.
- You have not seen PolicyScna implementation code, GSI prompts, component text, repair logs, prior diagnoses, or previous scores.
- You have not seen any earlier held-back restoration wording.
- You will use only this instruction file plus your own ordinary health-insurance knowledge and language judgment.

If any statement is false, do not author the holdout.

## Required size and coverage

Create **15–20 questions total** covering all six current Health concept areas:

- pre-existing disease (PED)
- waiting periods
- restoration
- room-rent limits
- bariatric surgery
- co-payment

Use a mixture of:

- single-turn questions;
- short multi-turn conversations where later turns depend naturally on earlier context;
- ordinary customer language, including incomplete wording, pronouns, follow-ups, comparisons, uncertainty, and practical questions;
- conceptual questions and small customer-supplied arithmetic where it is natural;
- cases where the safe answer should explain the concept first and then identify what remains product- or customer-specific.

Do **not** attempt equal numbers per concept if that makes the set artificial, but every concept must appear at least twice across the holdout.

## Authoring rules

The questions must sound like real customers, not test prompts. Vary phrasing and sentence structure. Include some concise or ambiguous follow-ups that require conversation continuity.

Do not:

- copy or closely paraphrase any question you may have encountered elsewhere;
- encode implementation vocabulary such as component IDs, semantic facts, governed requests, routing, Rendering Exit, or GSI;
- write questions specifically designed around known bugs or repairs;
- include product-specific factual answers unless the question itself supplies the relevant fact;
- create trick questions whose only purpose is to make the system fail;
- reveal the finished holdout to the implementation team before the first milestone run.

## Reference criteria

For every question, author evaluation criteria at the same time as the question. Criteria must describe what a good answer needs without supplying a model answer.

Each case must contain:

- `must_include`: one or more material points a correct answer needs;
- `legitimate_dependency`: what genuinely requires a specific product, policy, date, customer fact, or claim fact;
- `must_not_imply`: unsafe or materially wrong conclusions the answer must avoid;
- `acceptable_clarification`: when a focused follow-up would be appropriate;
- `unnecessary_deferral`: what can be answered generically without forcing the customer to provide documents first.

Do not include exact policy values or universal rules unless they are part of the customer-supplied question and are only needed for arithmetic.

## Required artifact shape

Return one JSON object using this structure:

```json
{
  "schema_version": "1.0",
  "benchmark_id": "health-customer-v0-independent-holdout-v1",
  "benchmark_role": "HOLDOUT_UNSEEN",
  "author_declaration": {
    "independent": true,
    "author_or_model": "...",
    "fresh_session_or_equivalent": true,
    "date_authored": "YYYY-MM-DD"
  },
  "conversations": [
    {
      "conversation_id": "holdout-...",
      "cases": [
        {
          "case_id": "holdout-...",
          "turn_index": 1,
          "prior_context_required": false,
          "concept_area": "pre_existing_disease",
          "user_text": "...",
          "reference": {
            "must_include": ["..."],
            "legitimate_dependency": ["..."],
            "must_not_imply": ["..."],
            "acceptable_clarification": ["..."],
            "unnecessary_deferral": ["..."]
          }
        }
      ]
    }
  ]
}
```

Allowed `concept_area` values:

- `pre_existing_disease`
- `waiting_period`
- `restoration`
- `room_rent_limit`
- `bariatric_surgery`
- `copayment`

Use stable case IDs and conversation IDs. For follow-up turns, set `prior_context_required` to `true`.

## Freeze procedure

When the holdout is complete:

1. Save it as `health_customer_v0_independent_holdout_v1.json`.
2. Compute SHA-256 of the exact file bytes.
3. Record the SHA-256 separately with the author declaration.
4. Do not edit the holdout after hashing. If any change is necessary, create a new version and new hash.
5. Do not send the file contents to the implementation team before the first holdout run. A custodian may provide only the file path/reference, SHA-256, case count, concept counts, and author declaration until the run is complete.

## Acceptance checks before freeze

Before finalizing, verify:

- 15–20 total cases;
- all six concept areas represented at least twice;
- at least three multi-turn conversations;
- no duplicate question text;
- no implementation terminology;
- no direct product recommendation task;
- no question depends on unpublished implementation details;
- every case has all five reference-criteria fields;
- all follow-up turns that need prior context are marked correctly;
- the independence declaration is truthful.

## What to return

Return only:

- the frozen JSON artifact;
- SHA-256;
- author/model identity and date;
- confirmation that the independence declaration is true.

Do not include commentary about the implementation, guesses about expected system performance, or suggested repairs.
