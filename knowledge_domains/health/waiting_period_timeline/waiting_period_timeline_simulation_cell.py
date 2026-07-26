from __future__ import annotations

import calendar
import json
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict

from .timeline_models import (
    TimelineAssessment,
    TimelineCertification,
    TimelineQualityReport,
    WaitingPeriodTimelineAsset,
    WaitingPeriodTimelineScenario,
    stable_id,
    utc_now,
)


class WaitingPeriodTimelineSimulationCell:
    """
    Evaluates only whether a stated waiting-period timeline appears complete.

    It does not determine final claim approval, claim settlement, or complete
    policy coverage. Those depend on policy wording, disclosures, exclusions,
    continuity benefits, condition details, and insurer claim assessment.
    """

    SUPPORTED_UNITS = {"days", "months", "years"}

    SUPPORTED_ACTIVATION_CONVENTIONS = {
        "ON_OR_AFTER_CALCULATED_DATE",
        "AFTER_COMPLETION_OF_PERIOD",
    }

    def __init__(
        self,
        output_dir: str | Path = "knowledge/factory/waiting_period_timelines",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        *,
        policy_start_date: str,
        claim_date: str,
        waiting_period_type: str,
        waiting_period_value: int,
        waiting_period_unit: str,
        activation_convention: str,
        source_assets: Dict[str, Any] | None = None,
    ) -> Dict[str, str]:
        scenario = self._build_scenario(
            policy_start_date=policy_start_date,
            claim_date=claim_date,
            waiting_period_type=waiting_period_type,
            waiting_period_value=waiting_period_value,
            waiting_period_unit=waiting_period_unit,
            activation_convention=activation_convention,
        )

        assessment = self._assess_timeline(scenario)
        quality = self._inspect_quality(scenario, assessment)
        certification = self._certify(scenario, quality)

        asset = self._build_asset(
            scenario=scenario,
            assessment=assessment,
            quality=quality,
            certification=certification,
            source_assets=source_assets or {},
        )

        certification = replace(certification, asset_id=asset.asset_id)

        asset = self._build_asset(
            scenario=scenario,
            assessment=assessment,
            quality=quality,
            certification=certification,
            source_assets=source_assets or {},
        )

        return self._write_outputs(asset, quality, certification)

    def _build_scenario(
        self,
        *,
        policy_start_date: str,
        claim_date: str,
        waiting_period_type: str,
        waiting_period_value: int,
        waiting_period_unit: str,
        activation_convention: str,
    ) -> WaitingPeriodTimelineScenario:
        start = self._parse_date(policy_start_date, "policy_start_date")
        claim = self._parse_date(claim_date, "claim_date")

        if claim < start:
            raise ValueError("claim_date cannot be earlier than policy_start_date.")

        normalized_unit = waiting_period_unit.strip().lower()
        if normalized_unit not in self.SUPPORTED_UNITS:
            supported = ", ".join(sorted(self.SUPPORTED_UNITS))
            raise ValueError(
                f"Unsupported waiting_period_unit: {waiting_period_unit!r}. "
                f"Supported values: {supported}."
            )

        normalized_convention = activation_convention.strip().upper()
        if normalized_convention not in self.SUPPORTED_ACTIVATION_CONVENTIONS:
            supported = ", ".join(
                sorted(self.SUPPORTED_ACTIVATION_CONVENTIONS)
            )
            raise ValueError(
                f"Unsupported activation_convention: {activation_convention!r}. "
                f"Supported values: {supported}."
            )

        if waiting_period_value <= 0:
            raise ValueError("waiting_period_value must be greater than zero.")

        if not waiting_period_type.strip():
            raise ValueError("waiting_period_type cannot be empty.")

        payload = {
            "concept_id": "waiting_period",
            "policy_start_date": start.isoformat(),
            "claim_date": claim.isoformat(),
            "waiting_period_type": waiting_period_type.strip(),
            "waiting_period_value": waiting_period_value,
            "waiting_period_unit": normalized_unit,
            "activation_convention": normalized_convention,
        }

        return WaitingPeriodTimelineScenario(
            scenario_id=stable_id("wpt", payload),
            concept_id="waiting_period",
            concept_name="Waiting Period",
            policy_start_date=start.isoformat(),
            claim_date=claim.isoformat(),
            waiting_period_type=waiting_period_type.strip(),
            waiting_period_value=waiting_period_value,
            waiting_period_unit=normalized_unit,
            activation_convention=normalized_convention,
            assumptions=[
                "This assessment evaluates only the stated waiting-period timeline.",
                "Coverage continuity, portability, policy wording, exclusions, disclosures, and claim facts may change final claim eligibility.",
                "A timeline marked ACTIVE does not mean a claim is approved or payable.",
            ],
        )

    def _assess_timeline(
        self,
        scenario: WaitingPeriodTimelineScenario,
    ) -> TimelineAssessment:
        start = date.fromisoformat(scenario.policy_start_date)
        claim = date.fromisoformat(scenario.claim_date)

        calculated_boundary_date = self._add_duration(
            start,
            scenario.waiting_period_value,
            scenario.waiting_period_unit,
        )

        if scenario.activation_convention == "ON_OR_AFTER_CALCULATED_DATE":
            first_active_date = calculated_boundary_date
            waiting_period_complete = claim >= first_active_date
            convention_text = "on or after the calculated boundary date"
        else:
            first_active_date = calculated_boundary_date + timedelta(days=1)
            waiting_period_complete = claim >= first_active_date
            convention_text = "after the calculated boundary date"

        timeline_status = "ACTIVE" if waiting_period_complete else "NOT_ACTIVE"

        if waiting_period_complete:
            explanation = (
                f"The {scenario.waiting_period_type} waiting period appears complete "
                f"on the claim date under the '{convention_text}' convention. "
                f"Calculated boundary date: {calculated_boundary_date.isoformat()}. "
                f"First active date: {first_active_date.isoformat()}."
            )
        else:
            explanation = (
                f"The {scenario.waiting_period_type} waiting period does not appear "
                f"complete on the claim date under the '{convention_text}' convention. "
                f"Calculated boundary date: {calculated_boundary_date.isoformat()}. "
                f"First active date: {first_active_date.isoformat()}."
            )

        limitation = (
            "This is a waiting-period timeline assessment only. Final claim "
            "eligibility depends on policy wording, condition details, disclosures, "
            "exclusions, continuity benefits, and insurer claim assessment."
        )

        return TimelineAssessment(
            calculated_boundary_date=calculated_boundary_date.isoformat(),
            first_active_date=first_active_date.isoformat(),
            timeline_status=timeline_status,
            waiting_period_complete=waiting_period_complete,
            explanation=explanation,
            limitation=limitation,
        )

    def _inspect_quality(
        self,
        scenario: WaitingPeriodTimelineScenario,
        assessment: TimelineAssessment,
    ) -> TimelineQualityReport:
        start = date.fromisoformat(scenario.policy_start_date)
        claim = date.fromisoformat(scenario.claim_date)
        boundary = date.fromisoformat(assessment.calculated_boundary_date)
        first_active = date.fromisoformat(assessment.first_active_date)

        expected_status = (
            "ACTIVE" if claim >= first_active else "NOT_ACTIVE"
        )

        checks = {
            "valid_timeline_dates": claim >= start,
            "valid_waiting_period_duration": scenario.waiting_period_value > 0,
            "calculated_boundary_after_policy_start": boundary > start,
            "first_active_date_not_before_boundary": first_active >= boundary,
            "activation_convention_present": (
                scenario.activation_convention
                in self.SUPPORTED_ACTIVATION_CONVENTIONS
            ),
            "timeline_status_matches_dates": (
                assessment.timeline_status == expected_status
            ),
            "limitation_present": bool(assessment.limitation),
            "explanation_present": bool(assessment.explanation),
        }

        return TimelineQualityReport(
            checks=checks,
            pass_=all(checks.values()),
        )

    def _certify(
        self,
        scenario: WaitingPeriodTimelineScenario,
        quality: TimelineQualityReport,
    ) -> TimelineCertification:
        payload = {
            "scenario_id": scenario.scenario_id,
            "concept_id": scenario.concept_id,
            "quality": quality.to_dict(),
        }

        return TimelineCertification(
            certification_id=stable_id("wptc", payload),
            asset_id="pending_until_asset_assembly",
            concept_id=scenario.concept_id,
            status="PASS" if quality.pass_ else "FAIL",
            checks=quality.checks,
            created_at=utc_now(),
        )

    def _build_asset(
        self,
        *,
        scenario: WaitingPeriodTimelineScenario,
        assessment: TimelineAssessment,
        quality: TimelineQualityReport,
        certification: TimelineCertification,
        source_assets: Dict[str, Any],
    ) -> WaitingPeriodTimelineAsset:
        payload = {
            "scenario_id": scenario.scenario_id,
            "timeline_status": assessment.timeline_status,
            "calculated_boundary_date": assessment.calculated_boundary_date,
            "first_active_date": assessment.first_active_date,
            "activation_convention": scenario.activation_convention,
            "source_assets": source_assets,
        }

        asset_id = stable_id("wpta", payload)
        is_active = assessment.timeline_status == "ACTIVE"

        return WaitingPeriodTimelineAsset(
            asset_id=asset_id,
            concept_id="waiting_period",
            concept_name="Waiting Period",
            version="1.1",
            certification_status=certification.status,
            source_assets=source_assets,
            scenario=scenario.to_dict(),
            timeline_assessment=assessment.to_dict(),
            explanation={
                "plain_language_summary": assessment.explanation,
                "what_this_means": (
                    "The stated waiting-period timeline appears complete."
                    if is_active
                    else "The stated waiting-period timeline does not appear complete yet."
                ),
                "what_this_does_not_mean": (
                    "This result does not confirm final claim approval, settlement, "
                    "or coverage under all policy terms."
                ),
                "limitation": assessment.limitation,
            },
            decision_readiness={
                "customer_can": [
                    "Identify the relevant policy start date.",
                    "Check the applicable waiting-period type.",
                    "Compare the claim date with the first active date.",
                ],
                "advisor_should_confirm": [
                    "Customer understands that waiting-period completion is not final claim approval.",
                    "Customer has checked the correct waiting-period type for the condition or benefit.",
                    "Customer has been shown the timeline using actual calendar dates.",
                ],
                "warning_flags": (
                    []
                    if is_active
                    else [
                        "Waiting-period timeline is not complete on the stated claim date."
                    ]
                ),
            },
            verification={
                "question": (
                    f"A policy starts on {scenario.policy_start_date} with a "
                    f"{scenario.waiting_period_value}-{scenario.waiting_period_unit} "
                    f"{scenario.waiting_period_type} waiting period. Is the timeline "
                    f"active on {scenario.claim_date}?"
                ),
                "correct_answer": assessment.timeline_status,
                "why": (
                    f"Calculated boundary date: "
                    f"{assessment.calculated_boundary_date}. "
                    f"First active date: {assessment.first_active_date}. "
                    f"Convention used: {scenario.activation_convention}. "
                    "This is only a waiting-period timeline result."
                ),
            },
            certification=certification.to_dict(),
            factory_signature={
                "factory": "PolicyScna Knowledge Factory",
                "production_cell": "WaitingPeriodTimelineSimulationCell",
                "version": "1.1",
                "deterministic": True,
                "created_at": utc_now(),
                "quality_pass": quality.pass_,
            },
        )

    def _write_outputs(
        self,
        asset: WaitingPeriodTimelineAsset,
        quality: TimelineQualityReport,
        certification: TimelineCertification,
    ) -> Dict[str, str]:
        asset_path = (
            self.output_dir
            / f"{asset.asset_id}_waiting_period_timeline_asset.json"
        )
        quality_path = self.output_dir / f"{asset.asset_id}_quality_report.json"
        certification_path = (
            self.output_dir / f"{asset.asset_id}_certification.json"
        )
        event_path = self.output_dir / f"{asset.asset_id}_event.json"
        summary_path = self.output_dir / "waiting_period_timeline_summary.json"

        asset_path.write_text(
            json.dumps(asset.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        quality_path.write_text(
            json.dumps(quality.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        certification_path.write_text(
            json.dumps(certification.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        event = {
            "event_type": "waiting_period_timeline_asset_manufactured",
            "asset_id": asset.asset_id,
            "concept_id": asset.concept_id,
            "status": certification.status,
            "created_at": utc_now(),
        }

        event_path.write_text(
            json.dumps(event, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        summary = {
            "production_cell": "Waiting Period Timeline Simulation Cell",
            "version": "1.1",
            "assets_manufactured": 1,
            "outputs": {
                "asset": str(asset_path),
                "quality": str(quality_path),
                "certification": str(certification_path),
                "event": str(event_path),
            },
            "timeline_status": asset.timeline_assessment["timeline_status"],
            "calculated_boundary_date": (
                asset.timeline_assessment["calculated_boundary_date"]
            ),
            "first_active_date": (
                asset.timeline_assessment["first_active_date"]
            ),
            "activation_convention": asset.scenario["activation_convention"],
        }

        summary_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return summary["outputs"]

    @staticmethod
    def _parse_date(value: str, field_name: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must be in YYYY-MM-DD format."
            ) from exc

    @staticmethod
    def _add_duration(start: date, value: int, unit: str) -> date:
        if unit == "days":
            return start + timedelta(days=value)

        months_to_add = value if unit == "months" else value * 12
        target_month_index = (start.month - 1) + months_to_add
        target_year = start.year + (target_month_index // 12)
        target_month = (target_month_index % 12) + 1
        target_day = min(
            start.day,
            calendar.monthrange(target_year, target_month)[1],
        )

        return date(target_year, target_month, target_day)