from datetime import date

from insurance_intelligence.generic_knowledge.authority_resolution import (
    AuthorityClass,
    AuthorityResolution,
    ResolutionStatus,
)
from insurance_intelligence.generic_knowledge.contracts import (
    AccountingState,
    ApplicabilityKey,
    PublicationBlocker,
    PublicationBlockerCode,
    ResidueRecord,
)
from insurance_intelligence.generic_knowledge.normative_inventory import (
    InventoryAccountingResult,
    ResidueTelemetry,
)
from insurance_intelligence.generic_knowledge.publication_eligibility import (
    GovernedReviewStatus,
    PublicationDependencyBinding,
    PublicationEligibilityInput,
    PublicationEligibilityStatus,
    SourceFreshnessStatus,
    dependency_binding_matches,
    evaluate_publication_eligibility,
)


def _app() -> ApplicabilityKey:
    return ApplicabilityKey(
        product_reference="pv_example",
        policy_version="v1",
        effective_from=date(2026, 1, 1),
    )


def _authority(
    *,
    status: ResolutionStatus = ResolutionStatus.RESOLVED,
    authority: AuthorityClass = AuthorityClass.POLICY_WORDING,
) -> AuthorityResolution:
    return AuthorityResolution(
        status=status,
        concept="waiting_periods",
        semantic_key="PRE_EXISTING_DISEASE.duration",
        as_of_date=date(2026, 8, 9),
        selected_candidate_ids=("cand_1",) if status is ResolutionStatus.RESOLVED else (),
        selected_authority_class=authority if status is not ResolutionStatus.NO_APPLICABLE_CANDIDATE else None,
        semantic_value={"value": 36, "unit": "MONTHS"} if status is ResolutionStatus.RESOLVED else None,
        rejected_candidate_ids=(),
        conflict_candidate_ids=("cand_1", "cand_2") if status is ResolutionStatus.CONFLICTED else (),
        regulatory_overlay_applied=authority is AuthorityClass.REGULATORY_OVERLAY,
    )


def _accounting(*, blocker: PublicationBlocker | None = None) -> InventoryAccountingResult:
    blockers = (blocker,) if blocker else ()
    return InventoryAccountingResult(
        concept="waiting_periods",
        inventory_method="high_recall",
        inventory_version="wp-envelope-v1",
        residues=(),
        blockers=blockers,
        telemetry=ResidueTelemetry(
            concept="waiting_periods",
            normative_unit_count=3,
            accounted_unit_count=3,
            residue_count=1 if blocker else 0,
            blocking_residue_count=1 if blocker else 0,
            state_counts={state: 0 for state in AccountingState},
        ),
    )


def _binding(**overrides) -> PublicationDependencyBinding:
    values = dict(
        ontology_version="waiting-period-ontology-v1",
        source_document_id="doc_1",
        source_document_version="docver_1",
        source_hash_sha256="abc123",
        review_decision_version="review_v1",
        regulatory_overlay_version="reg_v1",
    )
    values.update(overrides)
    return PublicationDependencyBinding(**values)


def _input(**overrides) -> PublicationEligibilityInput:
    values = dict(
        concept="waiting_periods",
        applicability=_app(),
        authority_resolution=_authority(),
        inventory_accounting=_accounting(),
        review_status=GovernedReviewStatus.APPROVED,
        source_freshness=SourceFreshnessStatus.CURRENT,
        dependency_binding=_binding(),
    )
    values.update(overrides)
    return PublicationEligibilityInput(**values)


def test_clean_governed_unit_is_publication_eligible():
    decision = evaluate_publication_eligibility(_input())
    assert decision.status is PublicationEligibilityStatus.ELIGIBLE
    assert decision.publishable is True
    assert decision.blockers == ()


def test_material_residue_blocks_only_supplied_applicability_unit():
    residue = ResidueRecord(
        residue_id="r1",
        normative_unit_id="n1",
        concept="waiting_periods",
        applicability=_app(),
        accounting_state=AccountingState.NOT_YET_REPRESENTABLE,
        reason="novel waiting-period suspension mechanic",
        material=True,
    )
    blocker = PublicationBlocker(
        blocker_id="blocker_r1",
        code=PublicationBlockerCode.NOT_YET_REPRESENTABLE,
        concept="waiting_periods",
        applicability=_app(),
        reason=residue.reason,
        normative_unit_ids=("n1",),
    )
    decision = evaluate_publication_eligibility(
        _input(inventory_accounting=_accounting(blocker=blocker))
    )
    assert decision.status is PublicationEligibilityStatus.BLOCKED
    assert decision.blockers[0].applicability == _app()
    assert decision.blockers[0].code is PublicationBlockerCode.NOT_YET_REPRESENTABLE


def test_equal_authority_conflict_blocks_publication():
    decision = evaluate_publication_eligibility(
        _input(authority_resolution=_authority(status=ResolutionStatus.CONFLICTED))
    )
    assert decision.status is PublicationEligibilityStatus.BLOCKED
    assert any(b.code is PublicationBlockerCode.AUTHORITY_CONFLICT for b in decision.blockers)


def test_regulatory_conflict_is_distinct_blocker():
    decision = evaluate_publication_eligibility(
        _input(
            authority_resolution=_authority(
                status=ResolutionStatus.CONFLICTED,
                authority=AuthorityClass.REGULATORY_OVERLAY,
            )
        )
    )
    assert any(b.code is PublicationBlockerCode.REGULATORY_CONFLICT for b in decision.blockers)


def test_no_applicable_authority_requires_review():
    decision = evaluate_publication_eligibility(
        _input(
            authority_resolution=_authority(
                status=ResolutionStatus.NO_APPLICABLE_CANDIDATE
            )
        )
    )
    assert any(b.code is PublicationBlockerCode.REVIEW_REQUIRED for b in decision.blockers)


def test_unreviewed_governed_semantics_block_publication():
    decision = evaluate_publication_eligibility(
        _input(review_status=GovernedReviewStatus.UNREVIEWED)
    )
    assert any(b.code is PublicationBlockerCode.REVIEW_REQUIRED for b in decision.blockers)


def test_rejected_review_blocks_publication():
    decision = evaluate_publication_eligibility(
        _input(review_status=GovernedReviewStatus.REJECTED)
    )
    assert decision.status is PublicationEligibilityStatus.BLOCKED
    assert any("rejected" in b.reason for b in decision.blockers)


def test_superseded_source_blocks_publication():
    decision = evaluate_publication_eligibility(
        _input(source_freshness=SourceFreshnessStatus.SUPERSEDED)
    )
    assert any(b.code is PublicationBlockerCode.SOURCE_STALE for b in decision.blockers)
    assert any("superseded" in b.reason for b in decision.blockers)


def test_unknown_source_freshness_fails_closed():
    decision = evaluate_publication_eligibility(
        _input(source_freshness=SourceFreshnessStatus.UNKNOWN)
    )
    assert any(b.code is PublicationBlockerCode.SOURCE_STALE for b in decision.blockers)


def test_dependency_binding_requires_exact_match():
    published = _binding()
    assert dependency_binding_matches(published, _binding()) is True
    assert dependency_binding_matches(
        published,
        _binding(source_hash_sha256="different"),
    ) is False
    assert dependency_binding_matches(
        published,
        _binding(ontology_version="waiting-period-ontology-v2"),
    ) is False


def test_product_identity_is_data_not_branching_logic():
    first = evaluate_publication_eligibility(_input())
    other_app = ApplicabilityKey(
        product_reference="pv_completely_different_product",
        policy_version="v9",
        effective_from=date(2026, 1, 1),
    )
    second = evaluate_publication_eligibility(
        _input(applicability=other_app)
    )
    assert first.status is second.status is PublicationEligibilityStatus.ELIGIBLE
    assert second.applicability.product_reference == "pv_completely_different_product"
