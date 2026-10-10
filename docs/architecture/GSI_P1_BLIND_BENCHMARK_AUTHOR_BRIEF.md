# GSI P1 Blind Held-Back Benchmark Author Brief

## Purpose

Create the external held-back evaluation pack for `health:concept:restoration` without seeing or adapting to the Governed Semantic Interpreter implementation.

This artifact is evaluation data only. It must not be copied into interpreter prompts, runtime branches, aliases, cue tables, regexes, or post-processing logic.

## Author eligibility

Use an insurance-literate cold reader who has not reviewed the interpreter source, prompt builder, provider adapter, or existing restoration benchmark wording.

## What to write

Write at least **three** natural customer questions about the health-insurance restoration benefit.

The questions should:

- sound like ordinary customer language rather than policy drafting;
- be meaningfully different from one another in sentence structure and vocabulary;
- include at least one indirect question that avoids obvious lexical cues such as `restore`, `restoration`, `replenish`, `refill`, or `fill back up`;
- remain understandable to an insurance-literate reviewer as asking about restoration;
- avoid insurer names, product names, or implementation vocabulary.

The author should receive only this concept-level explanation:

> Restoration is the policy feature under which available health cover may become available again after some or all of the original sum insured has been used, subject to the policy's actual terms and conditions.

Do not provide examples from the current benchmark runner or interpreter implementation.

## File format

Submit UTF-8 JSON with this exact top-level shape:

```json
{
  "schema_version": "1.0",
  "concept_id": "health:concept:restoration",
  "cases": [
    {
      "case_id": "blind-restoration-1",
      "user_text": "<author-written customer question>"
    }
  ]
}
```

`case_id` values must be unique. At least three cases are required.

## Freeze procedure

1. The independent author completes the JSON file.
2. Before any live provider run, compute its SHA-256.
3. Record the exact SHA-256 as the frozen benchmark identifier.
4. Run the live benchmark only with both the file path and that expected SHA-256.
5. Missing file, malformed file, or hash mismatch makes the run **INVALID**. There is no fallback held-back pack.
6. Do not edit the file after its SHA-256 is frozen. Any change creates a new benchmark artifact and requires an explicit new freeze decision before another run.

## Verdict rule

Held-back genericity passes only if the frozen restoration cases resolve through the same generic interpreter path with no restoration-specific runtime code or repair.

If restoration fails, do not add restoration-specific handling. A repair is acceptable only when a failing customer case demonstrates a reusable class-level problem across concepts.
