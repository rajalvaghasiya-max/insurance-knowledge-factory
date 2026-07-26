from __future__ import annotations

from .financial_outcome_models import Scenario, stable_id


class ScenarioBuilder:
    def build(
        self,
        hospital_bill: float = 500000,
        non_medical_expenses: float = 50000,
        copay_percent: float = 0.10,
        concept_id: str = "copay",
        concept_name: str = "Copay",
        medical_event: str = "Hospitalization",
        claim_mode: str = "cashless",
        hospital_type: str = "network_hospital",
        city_zone: str = "standard",
    ) -> Scenario:
        if hospital_bill <= 0:
            raise ValueError("hospital_bill must be positive")
        if non_medical_expenses < 0:
            raise ValueError("non_medical_expenses cannot be negative")
        if non_medical_expenses > hospital_bill:
            raise ValueError("non_medical_expenses cannot exceed hospital_bill")
        if not 0 <= copay_percent <= 1:
            raise ValueError("copay_percent must be between 0 and 1")

        payload = f"{concept_id}|{hospital_bill}|{non_medical_expenses}|{copay_percent}|{medical_event}|{claim_mode}"
        return Scenario(
            scenario_id=stable_id("fos", payload),
            concept_id=concept_id,
            concept_name=concept_name,
            hospital_bill=float(hospital_bill),
            non_medical_expenses=float(non_medical_expenses),
            copay_percent=float(copay_percent),
            medical_event=medical_event,
            claim_mode=claim_mode,
            hospital_type=hospital_type,
            city_zone=city_zone,
            assumptions=[
                "FOSC-001A supports standard copay path only.",
                "Non-medical expenses are deducted before copay is applied.",
                "Copay is applied on admissible claim amount.",
            ],
        )
