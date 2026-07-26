from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .evidence_profile_resolver import WaitingPeriodEvidenceProfileResolver
from .waiting_period_timeline_simulation_cell import (
    WaitingPeriodTimelineSimulationCell,
)


class EvidenceBackedWaitingPeriodTimelineRunner:
    """
    Runs a waiting-period timeline simulation only from an approved,
    fully specified evidence-profile example.

    Policy start date and claim date are runtime inputs. The waiting-period
    type, duration, unit, and activation convention come from approved
    evidence, not from hardcoded defaults.
    """

    def __init__(
        self,
        *,
        evidence_profile_path: str | Path,
        output_dir: str | Path,
    ) -> None:
        self.evidence_profile_path = Path(evidence_profile_path)
        self.output_dir = Path(output_dir)

    def run(
        self,
        *,
        policy_start_date: str,
        claim_date: str,
    ) -> Dict[str, str]:
        scenario = WaitingPeriodEvidenceProfileResolver(
            self.evidence_profile_path
        ).resolve_example(
            "activ_one_c10_1_reduced_specific_disease_1_year"
        )

        source_assets: Dict[str, Any] = {
            "evidence_profile_path": str(self.evidence_profile_path),
            "product_reference": scenario["product_reference"],
            "scope": scenario["scope"],
            "claim_eligibility_note": scenario["claim_eligibility_note"],
        }

        cell = WaitingPeriodTimelineSimulationCell(
            output_dir=self.output_dir
        )

        return cell.run(
            policy_start_date=policy_start_date,
            claim_date=claim_date,
            waiting_period_type=scenario["waiting_period_type"],
            waiting_period_value=scenario["waiting_period_value"],
            waiting_period_unit=scenario["waiting_period_unit"],
            activation_convention=scenario["activation_convention"],
            source_assets=source_assets,
        )