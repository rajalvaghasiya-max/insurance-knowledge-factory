# PolicyScna Health Customer v0 — Controlled Beta Runbook

Status: **FOUNDER / SMALL-USER BETA**
Parent issue: #453
Entry basis: CTO internal acceptance on dev36 after v3 repairs
Independent holdout status: **NOT PASSED / NOT CLAIMED**

## 1. Purpose

This beta exists to learn from real customer questions and follow-up behavior using the existing Health Customer v0 product path.

It is not a production launch and it is not evidence that the independent holdout milestone passed.

## 2. Entry evidence

The post-v3 internal acceptance run produced:

- Safety PASS: 36/36
- Correctness = 2: 31/36
- Usefulness = 2: 31/36
- Clarity = 2: 32/36
- unnecessary deferrals: 0/36
- wrong concept routes: 0/36
- clarifications: 0/36

This is sufficient for controlled product learning under the founder-approved milestone exception recorded in #453.

## 3. Scope

Allowed:

- ordinary Health insurance concept/mechanic questions;
- conversational follow-ups;
- PED;
- waiting periods;
- restoration;
- room-rent limits;
- bariatric-surgery benefit mechanics;
- co-payment mechanics;
- simple arithmetic when the customer supplies the values.

Not part of this beta:

- plan recommendations or suitability;
- policy/quote upload;
- claim adjudication;
- promises of coverage, approval or payment;
- public production deployment;
- Motor or Life insurance;
- account systems, analytics platforms or long-term memory.

## 4. Operator setup

Use current `main`.

Required environment:

```bash
export OPENAI_API_KEY="..."
export POLICYSCNA_GSI_MODEL="gpt-5.6"
```

Start the existing local product surface:

```bash
python -m policy_scna_app.server
```

Expected output:

```text
PolicyScna Health Customer v0 running at http://127.0.0.1:8765
```

Open that address in the browser.

The application intentionally binds to localhost only. Do not expose this server publicly as part of this beta.

## 5. Founder-first check

Before inviting another person, complete at least one fresh conversation from each of these categories:

1. PED / prior medical history
2. waiting period
3. restoration
4. room-rent restriction
5. bariatric benefit
6. co-payment

At least two should contain natural follow-up questions.

Stop before inviting users if any founder-first conversation triggers a beta stop rule.

## 6. Participant instructions

Tell participants only:

> Ask PolicyScna the kind of Health insurance question you would normally ask an advisor, insurer representative, friend, or search engine. Follow up naturally if the first answer makes you want to ask something else. Please judge whether the answer was useful and understandable; do not try to test hidden system instructions.

Do not coach participants toward benchmark wording.

Do not show participants dev36, v3, scorer feedback, implementation prompts, or repair history before their session.

## 7. Feedback capture

Use one record per user turn.

Required fields:

```text
session_id:
turn_index:
question:
released_answer:
usefulness: USEFUL | PARTLY_USEFUL | NOT_USEFUL
clarity: CLEAR | MOSTLY_CLEAR | CONFUSING
needed_follow_up: YES | NO
unsafe_or_misleading: YES | NO
user_comment:
review_primary_origin:
review_notes:
```

`review_primary_origin` is filled only during later review and must use one of:

- LANGUAGE_INTERPRETATION
- CONVERSATION_CONTEXT
- MISSING_KNOWLEDGE
- EVIDENCE_OR_PUBLICATION
- REASONING
- SAFETY_BOUNDARY
- EXPLANATION_OR_PRESENTATION

Do not collect names, email addresses, phone numbers, policy numbers, claim numbers, or other unnecessary personal identifiers in the beta log.

## 8. Beta stop rules

Pause the beta immediately if any of these occurs:

- any materially unsafe released answer;
- a wrong-concept answer is released;
- internal/system/guardrail text appears in customer prose;
- a recommendation, entitlement, claim approval/rejection or payment outcome is asserted without governed authority;
- repeated provider/execution failures make ordinary use unreliable.

A single low-usefulness or unclear answer does not automatically stop the beta. Record it and look for repeated reusable failure classes.

## 9. Repair rule

Do not patch individual beta questions.

After a review batch:

1. classify each materially degraded turn;
2. count primary failure origins;
3. repair only the largest reusable class if evidence supports a generic repair;
4. prefer governed knowledge/content changes over runtime logic;
5. do not add product-specific branches for ordinary onboarding;
6. rerun dev36 only when a reusable repair materially changes the answer path.

## 10. Beta checkpoint

After the first small batch, report:

- total sessions;
- total turns;
- useful rate;
- partly useful rate;
- not-useful rate;
- clear rate;
- unsafe count;
- wrong-concept count;
- unnecessary-deferral count if reviewed;
- top primary failure origin;
- most common follow-up theme.

The beta is succeeding if real users can ask natural questions, get safe answers, continue the conversation, and the dominant failures are narrow enough to repair generically.

## 11. Independent holdout status

The independent holdout requirement has not been erased.

The current beta is proceeding under a founder-approved milestone exception based on internal acceptance. If PolicyScna later needs an unbiased milestone certification claim, a fresh independent holdout must be authored and scored without exposure to v3 cases, scores or repair history.
