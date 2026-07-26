# GMVS-001 — Waiting Period

This is the second Golden Concept after Copay.

Purpose: validate whether Department V can manufacture understanding for a time-based insurance concept without architecture changes.

Run:

```powershell
python -m scripts.run_gmvs_waiting_period_validation
```

Expected learning: the current generic Learning Primitive line may produce fewer primitive types than Copay. If that happens, treat it as a validation discovery, not a failure.
