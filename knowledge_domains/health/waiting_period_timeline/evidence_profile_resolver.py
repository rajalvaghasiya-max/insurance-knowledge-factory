from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class WaitingPeriodEvidenceProfileResolver:
    """
    Reads an approved waiting-period evidence profile and returns only a
    specifically requested, fully defined, evidence-backed scenario.

    It never selects the first available example automatically and never
    creates a scenario for unresolved or Policy-Schedule-dependent items.
    """

    def __init__(self, profile_path: str | Path) -> None:
        self.profile_path = Path(profile_path)

    def resolve_example(self, example_id: str) -> Dict[str, Any]:
        profile = self._load_profile()

        examples = profile.get("evidence_backed_examples", [])
        if not isinstance(examples, list) or not examples:
            raise ValueError(
                "No evidence-backed waiting-period examples are available."
            )

        for example in examples:
            if example.get("example_id") != example_id:
                continue

            required_fields = [
                "waiting_period_type",
                "waiting_period_value",
                "waiting_period_unit",
                "activation_convention",
            ]

            missing = [
                field
                for field in required_fields
                if example.get(field) in (None, "")
            ]

            if missing:
                raise ValueError(
                    f"Evidence example '{example_id}' is not fully specified. "
                    f"Missing: {', '.join(missing)}."
                )

            return {
                "example_id": example_id,
                "concept_id": profile.get("concept_id"),
                "product_reference": profile.get("product_reference", {}),
                "waiting_period_type": example["waiting_period_type"],
                "waiting_period_value": example["waiting_period_value"],
                "waiting_period_unit": example["waiting_period_unit"],
                "activation_convention": example["activation_convention"],
                "scope": example.get("scope", ""),
                "claim_eligibility_note": example.get(
                    "claim_eligibility_note",
                    "",
                ),
            }

        raise ValueError(
            f"No evidence-backed example found for example_id={example_id!r}."
        )

    def _load_profile(self) -> Dict[str, Any]:
        if not self.profile_path.exists():
            raise FileNotFoundError(
                f"Evidence profile does not exist: {self.profile_path}"
            )

        data = json.loads(
            self.profile_path.read_text(encoding="utf-8")
        )

        if data.get("concept_id") != "waiting_period":
            raise ValueError(
                "Evidence profile concept_id must be 'waiting_period'."
            )

        return data