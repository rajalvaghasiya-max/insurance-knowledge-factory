# Health Customer v0 deterministic arithmetic repair

Issue: #433

This repair adds application-layer arithmetic over customer-supplied values only.

- Supports percentage-of-amount and simple difference calculations.
- Requires explicit monetary notation (`₹` or an Indian money unit) and a single unambiguous amount/rate basis.
- Runs only for resolved co-payment or room-rent Health customer answers.
- Does not infer policy percentages, admissible amounts, room entitlement, linked deductions, insurer liability, claim admissibility, or final out-of-pocket cost.
- Enriches the already-governed customer response and then reruns Rendering Exit Safety before release.
- Leaves the governed Health v0 answer function unchanged.
- Uses arbitrary-number tests; no benchmark-specific arithmetic constants or branches are present.
