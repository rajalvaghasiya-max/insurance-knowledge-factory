"""Bounded publication decision for one certified Bajaj conditional co-payment assertion.

This module is product-specific orchestration over generic certification and publication-
decision machinery. It does not add reasoning rules, broaden product-level co-payment
authority, or authorize policy-specific option selection.
"""
from __future__ import annotations

from pathlib import Path

from insurance_intelligence.contracts.publication_decision import (
    PublicationDecisionResult,
    build_publication_boundary_authorization,
    build_publication_decision_input,
)
from insurance_intelligence.publication_decision.evaluator import evaluate_publication_decision
from insurance_intelligence.rule_certification.conditional_copayment import (
    build_conditional_copayment_certification_cases,
    run_conditional_copayment_certification_cases,
)


BAJAJ_V2_COPAY_BINDING_PATH = (
    "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/v2/"
    "generic_legal_condition_binding/bajaj_my_health_care_v2_copayment_binding.json"
)
BAJAJ_LAB_ASSERTION_ID = (
    "ga_bajaj_my_health_care_lab_radiology_unapproved_reimbursement_copay_v1"
)
DECISION_AUTHORITY = "governed publication decision authority"
BOUNDARY_AUTHORITY = "reviewed publication-boundary authorization"


def build_bajaj_lab_copay_publication_context(*, repository_root: str | Path):
    bundle = build_conditional_copayment_certification_cases(
        binding_manifest_path=BAJAJ_V2_COPAY_BINDING_PATH,
        repository_root=repository_root,
        assertion_ids=(BAJAJ_LAB_ASSERTION_ID,),
    )
    case = bundle.cases[0]
    certification = run_conditional_copayment_certification_cases(bundle)[0]
    return case, certification


def build_bajaj_lab_copay_publication_decision(
    *, repository_root: str | Path
) -> PublicationDecisionResult:
    case, certification = build_bajaj_lab_copay_publication_context(
        repository_root=repository_root
    )
    authorization = build_publication_boundary_authorization(
        authorization_id="publication-boundary:bajaj-my-health-care-v2:lab-radiology-copay",
        governed_subject_reference=certification.governed_subject_reference,
        certification_id=certification.certification_id,
        resolved_boundary_tokens=("bound_not_published",),
        authorization_authority=BOUNDARY_AUTHORITY,
        trace_references=(
            BAJAJ_V2_COPAY_BINDING_PATH,
            "docs/architecture/bajaj_my_health_care_v2_copayment_certification_spec.json",
        ),
    )
    retained_limitations = tuple(
        item
        for item in certification.limitations
        if "bound_not_published" not in item.casefold()
    )
    evidence_refs = tuple(
        package.evidence_id for package in case.evidence_output.evidence_packages
    )
    return evaluate_publication_decision(
        build_publication_decision_input(
            decision_id="publication-decision:bajaj-my-health-care-v2:lab-radiology-copay",
            governed_subject_reference=certification.governed_subject_reference,
            certification_result=certification,
            requested_status="PUBLISH",
            decision_reasons=(
                "The exact bounded assertion certified PASS/COMPLETE from current reviewed primary-legal evidence.",
                "Only the historical bound_not_published publication-state boundary is explicitly resolved.",
                "Publication remains scoped to the lab/radiology reimbursement-not-pre-approved condition and does not establish a product-level co-payment.",
            ),
            limitations=retained_limitations,
            evidence_trace_references=evidence_refs,
            decision_authority=DECISION_AUTHORITY,
            boundary_authorization=authorization,
        )
    )


__all__ = [
    "BAJAJ_LAB_ASSERTION_ID",
    "BAJAJ_V2_COPAY_BINDING_PATH",
    "build_bajaj_lab_copay_publication_context",
    "build_bajaj_lab_copay_publication_decision",
]
