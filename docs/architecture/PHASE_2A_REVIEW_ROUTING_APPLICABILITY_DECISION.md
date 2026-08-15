# PHASE-2A — Review Routing Applicability Decision

**Status:** ACTIVE DECISION  
**Date:** 2026-08-15

## Decision

MO-029 review-risk routing is not a universal product-onboarding artifact.

Review routing becomes applicable only when a product/document has entered a reviewer-ready evidence-group stage that produces legitimate review groups for routing.

The explicit applicability states for the Phase-2A batch audit are:

- `required_when_review_input_exists`
- `not_applicable_no_review_input`

`not_applicable_no_review_input` is not a successful review decision and is not a bypass. It means only that no reviewer-ready input exists yet, so manufacturing a routing artifact would create fake workload metadata.

## Guardrails

1. A product with reviewer-ready input must not use `not_applicable_no_review_input` to avoid review routing.
2. A product marked `not_applicable_no_review_input` must not declare a review-risk routing artifact.
3. Risk routing remains workload orchestration only; it does not accept evidence, create facts, decide applicability/currentness, or publish knowledge.
4. When reviewer-ready groups are later generated, the batch spec must transition the product to `required_when_review_input_exists` and route the real groups through the generic MO-029 contract.
5. Product identity must never be added to production routing logic.

## Current first-batch finding

The first Phase-2A batch contains Star Comprehensive, Bajaj My Health Care, and Aditya Birla Health Activ One. The repository contains generic review contracts and MO-029 routing logic, but no committed reviewer-ready currency review documents for these three audited product versions.

Therefore their current routing applicability is `not_applicable_no_review_input`.

This decision prevents the onboarding audit from treating an unentered downstream review stage as a missing product-governance artifact while preserving fail-closed behavior once review input exists.
