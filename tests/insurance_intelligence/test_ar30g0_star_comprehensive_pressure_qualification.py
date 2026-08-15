import json
import shutil
from pathlib import Path

from factory_core.governance.document_identity_resolution import (
    DocumentIdentityResolutionOverlay,
)
from factory_core.governance.product_identity_reference import ProductIdentityReference
from insurance_intelligence.benefits.contracts import PublicationStatus, ReviewStatus
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.orchestration.star_comprehensive_knowledge_build import (
    PRODUCT_REFERENCE,
    TOPIC,
    build_star_comprehensive_copay_snapshot,
)


REQUIRED_RESTORATION_DIMENSIONS = {
    "restoration_percentage",
    "restoration_count_per_policy_period",
    "trigger_requirement",
    "trigger_timing",
    "same_hospitalization_use",
    "subsequent_hospitalization_use",
    "same_illness_use",
    "covered_section_scope",
    "relapse_window_days",
    "policy_year_reset",
    "carry_over_between_policy_years",
    "floater_operation",
}

_STAR_IDENTITY_SPEC = (
    "docs/architecture/"
    "star_health_star_comprehensive_product_identity_reference_spec.json"
)
_STAR_OVERLAY_SPEC = (
    "docs/architecture/"
    "star_health_star_comprehensive_document_identity_resolution_spec.json"
)
_STAR_IDENTITY_OUTPUT = (
    "knowledge/factory/product_identity_references/"
    "star_health_star_comprehensive.product_identity_reference.json"
)
_STAR_OVERLAY_OUTPUT = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/governance/"
    "star_health_star_comprehensive_document_identity_resolution.json"
)

# These are retained governed inputs/outputs already present in a clean checkout.
# DOCUMENT_IDENTITY is intentionally absent: it is a generated migration output
# and is reproduced below through the real generic governance contracts.
_STAR_PRESSURE_WORKSPACE_FILES = (
    _STAR_IDENTITY_SPEC,
    _STAR_OVERLAY_SPEC,
    (
        "knowledge/factory/registry_backed/star_health_star_comprehensive/"
        "generic_source_registration/policy_wording_registration.json"
    ),
    (
        "knowledge/factory/registry_backed/star_health_star_comprehensive/"
        "generic_source_registration/"
        "star_health_star_comprehensive_generic_source_bundle.json"
    ),
    (
        "knowledge/factory/registry_backed/star_health_star_comprehensive/governance/"
        "star_health_star_comprehensive_document_classification.json"
    ),
    (
        "knowledge/factory/registry_backed/star_health_star_comprehensive/"
        "generic_legal_condition_binding/"
        "star_health_star_comprehensive_conditional_copayment.json"
    ),
    (
        "knowledge/factory/registry_backed/star_health_star_comprehensive/"
        "generic_legal_condition_canonical_projection/"
        "star_health_star_comprehensive_conditional_copayment.canonical.json"
    ),
    (
        "knowledge/factory/registry_backed/star_health_star_comprehensive/"
        "publication_decision/"
        "star_comprehensive_conditional_copayment.eligibility.json"
    ),
    (
        "knowledge/factory/registry_backed/star_health_star_comprehensive/"
        "authoritative/"
        "star_comprehensive_conditional_copayment.authoritative.json"
    ),
)


def _copy_repository_file(workspace: Path, relative: str) -> None:
    source = Path(relative)
    assert source.is_file(), f"required retained governed artifact missing: {relative}"
    destination = workspace / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _materialize_star_pressure_workspace(workspace: Path) -> Path:
    for relative in _STAR_PRESSURE_WORKSPACE_FILES:
        _copy_repository_file(workspace, relative)

    identity_runner = ProductIdentityReference()
    identity_result = identity_runner.build(
        spec=_load_json(workspace / _STAR_IDENTITY_SPEC),
        repository_root=workspace,
        reviewed_at="2026-08-15T00:00:00+00:00",
    )
    identity_runner.write_output(
        identity_result,
        repository_root=workspace,
        output_path=_STAR_IDENTITY_OUTPUT,
    )

    overlay_runner = DocumentIdentityResolutionOverlay()
    overlay_result = overlay_runner.build(
        spec=_load_json(workspace / _STAR_OVERLAY_SPEC),
        repository_root=workspace,
        resolved_at="2026-08-15T00:00:00+00:00",
    )
    overlay_runner.write_output(
        overlay_result,
        repository_root=workspace,
        output_path=_STAR_OVERLAY_OUTPUT,
    )

    return workspace


def test_star_comprehensive_conditional_copay_chain_is_currently_certifiable(
    tmp_path: Path,
) -> None:
    workspace = _materialize_star_pressure_workspace(tmp_path)
    result = build_star_comprehensive_copay_snapshot(
        repository_root=workspace,
        build_request_id="ar30g0-pressure-qualification",
    )

    assert result.status == "CERTIFIED"
    assert result.product_reference == PRODUCT_REFERENCE == "star_health:star_comprehensive"
    assert result.topic == TOPIC == "conditional_copayment"
    assert len(result.receipts) == 7
    assert {receipt.stage for receipt in result.receipts} == {
        "SOURCE_REGISTRATION",
        "DOCUMENT_IDENTITY",
        "DOCUMENT_CLASSIFICATION",
        "LEGAL_BINDING",
        "CANONICAL_PROJECTION",
        "PUBLICATION_DECISION",
        "AUTHORITATIVE_PUBLICATION",
    }
    assert result.assertion_ids
    assert result.publication_ids
    assert result.limitations == (
        "Snapshot certifies the reviewed conditional co-payment artifact chain only.",
    )


def test_ar30g0_reproduces_generated_identity_overlay_in_isolated_workspace(
    tmp_path: Path,
) -> None:
    generated_overlay = tmp_path / _STAR_OVERLAY_OUTPUT
    assert not generated_overlay.exists()

    _materialize_star_pressure_workspace(tmp_path)

    assert generated_overlay.is_file()
    overlay = _load_json(generated_overlay)
    assert overlay["overlay_status"] == (
        "reviewed_document_identity_resolution_recorded_not_published"
    )
    assert overlay["documents"][0]["identity_resolution"]["resolution_status"] == "resolved"
    assert overlay["documents"][0]["identity_resolution"]["temporal_status"] == (
        "compatibility_unverified"
    )


def test_star_comprehensive_restoration_is_governed_and_preserves_dense_mechanics() -> None:
    implementation = STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION

    assert implementation.review_status is ReviewStatus.APPROVED
    assert implementation.publication_status is PublicationStatus.PUBLISHED
    assert implementation.is_governed_for_use is True

    mechanics = {item.dimension_id: item for item in implementation.mechanics}
    assert REQUIRED_RESTORATION_DIMENSIONS <= set(mechanics)
    assert mechanics["restoration_percentage"].value == 100
    assert mechanics["restoration_count_per_policy_period"].value == 1
    assert mechanics["same_hospitalization_use"].value is False
    assert mechanics["subsequent_hospitalization_use"].value is True
    assert mechanics["same_illness_use"].value is True
    assert mechanics["relapse_window_days"].value == 45
    assert mechanics["policy_year_reset"].value is True
    assert mechanics["carry_over_between_policy_years"].value is False


def test_ar30g0_quarantines_stale_transitional_coverage_audit() -> None:
    architecture = Path(
        "docs/architecture/AR_3_0_G0_STAR_COMPREHENSIVE_COMMERCIAL_PRESSURE_QUALIFICATION.md"
    ).read_text(encoding="utf-8")
    stale_audit = Path(
        "knowledge/health/coverage_audits/star_health_star_comprehensive_coverage_audit.json"
    ).read_text(encoding="utf-8")

    assert '"status": "INCOMPLETE"' in stale_audit
    assert "must not be used as a current governed coverage statement" in architecture
    assert "No AR-3.0 implementation may infer" in architecture
    assert "A new abstraction is permitted only if" in architecture
