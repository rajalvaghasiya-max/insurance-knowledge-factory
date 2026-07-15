# P2.7-E — Star Comprehensive Publication-Eligibility Review

This overlay uses the existing P2.5-J `canonical_publication_decision_gate_v1` without code changes.

The gate has no global rule-type allow-list. Rule types are deliberately approved in the reviewed, product-scoped decision specification. This pilot therefore approves only `conditional_copayment_rule` for the single named canonical assertion.

The decision gate remains read-only:
- it does not change canonical assertion publication status;
- it does not publish an authoritative artifact;
- it requires exactly one policy-wording evidence span;
- it requires reusable-generic classifications for all source evidence;
- a separate authoritative publisher remains required.
