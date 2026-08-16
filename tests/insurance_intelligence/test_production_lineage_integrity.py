"""Regression coverage for production certification lineage hash semantics."""

from __future__ import annotations

import hashlib
from pathlib import Path

from insurance_intelligence.rule_certification.aditya_birla_health import (
    ACTIV_ONE_POLICY_WORDING_SHA256,
    ACTIV_ONE_SPECIFIED_WAITING_PERIOD_TEXT_HASH,
    build_activ_one_specified_disease_waiting_period_case,
)
from insurance_intelligence.rule_certification.star_health import (
    STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE_HASH,
    STAR_COMPREHENSIVE_POLICY_WORDING_SHA256,
    build_star_comprehensive_conditional_copayment_case,
)
from insurance_intelligence.rule_certification.star_health_bariatric_surgery import (
    build_star_comprehensive_bariatric_surgery_case,
)
from insurance_intelligence.rule_certification.star_health_initial_waiting_period import (
    build_star_comprehensive_initial_waiting_period_case,
)
from insurance_intelligence.rule_certification.star_health_room_rent import (
    build_star_comprehensive_room_rent_case,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_case_lineage(case, expected_source_sha256: str) -> None:
    assert case.evidence_output.evidence_packages
    for package in case.evidence_output.evidence_packages:
        lineage = package.lineage
        assert lineage.source_artifact_sha256 == expected_source_sha256
        governed_record = REPOSITORY_ROOT / lineage.governed_record_path
        assert governed_record.is_file()
        assert lineage.governed_record_sha256 == _sha256(governed_record)


def test_star_copayment_uses_document_and_binding_hashes_not_candidate_text_hash() -> None:
    case = build_star_comprehensive_conditional_copayment_case()

    _assert_case_lineage(case, STAR_COMPREHENSIVE_POLICY_WORDING_SHA256)
    assert all(
        package.lineage.source_artifact_sha256 != STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE_HASH
        and package.lineage.governed_record_sha256 != STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE_HASH
        for package in case.evidence_output.evidence_packages
    )


def test_star_registration_backed_cases_use_document_and_registration_hashes() -> None:
    for case in (
        build_star_comprehensive_room_rent_case(),
        build_star_comprehensive_bariatric_surgery_case(),
        build_star_comprehensive_initial_waiting_period_case(),
    ):
        _assert_case_lineage(case, STAR_COMPREHENSIVE_POLICY_WORDING_SHA256)


def test_activ_one_uses_approved_document_and_governed_record_hashes() -> None:
    case = build_activ_one_specified_disease_waiting_period_case()

    _assert_case_lineage(case, ACTIV_ONE_POLICY_WORDING_SHA256)
    assert all(
        package.lineage.source_artifact_sha256 != ACTIV_ONE_SPECIFIED_WAITING_PERIOD_TEXT_HASH
        and package.lineage.governed_record_sha256 != ACTIV_ONE_SPECIFIED_WAITING_PERIOD_TEXT_HASH
        for package in case.evidence_output.evidence_packages
    )
