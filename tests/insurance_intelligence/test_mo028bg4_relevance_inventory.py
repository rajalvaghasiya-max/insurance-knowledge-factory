from datetime import date

import pytest

from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    EvidenceReference,
    NormativeUnitKind,
)
from insurance_intelligence.generic_knowledge.normative_inventory import InventoryReviewStatus
from insurance_intelligence.generic_knowledge.relevance_inventory import (
    ConceptRelevanceEnvelope,
    InventoryRule,
    RelevanceInventoryError,
    SourceFragment,
    inventory_from_fragments,
)


def _app(*, optional_cover_state: str | None = None) -> ApplicabilityKey:
    return ApplicabilityKey(
        product_reference="pv_demo",
        policy_version="v1",
        optional_cover_state=optional_cover_state,
        effective_from=date(2026, 1, 1),
    )


def _evidence(evidence_id: str, locator: str, source_class: str = "POLICY_WORDING") -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        source_document_id="doc_demo",
        source_document_version="docv1",
        source_hash_sha256="abc123",
        locator=locator,
        authority_class=source_class,
    )


def _fragment(
    fragment_id: str,
    text: str,
    locator: str,
    *,
    source_class: str = "POLICY_WORDING",
    optional_cover_state: str | None = None,
) -> SourceFragment:
    return SourceFragment(
        fragment_id=fragment_id,
        text=text,
        locator=locator,
        source_class=source_class,
        applicability=_app(optional_cover_state=optional_cover_state),
        evidence=_evidence(fragment_id, locator, source_class),
    )


def _envelope() -> ConceptRelevanceEnvelope:
    return ConceptRelevanceEnvelope(
        concept="waiting_periods",
        policy_version="waiting_period_inventory_v1",
        required_source_classes=("POLICY_WORDING", "PRODUCT_BENEFIT_TABLE"),
        rules=(
            InventoryRule(
                rule_id="duration",
                anchors=("waiting period", "months", "years"),
                kind=NormativeUnitKind.CONDITION,
                materially_affects=("duration",),
            ),
            InventoryRule(
                rule_id="waiver",
                anchors=("shall not apply", "waived"),
                kind=NormativeUnitKind.RELATIONSHIP,
                materially_affects=("waiver", "cross_concept_relationship"),
            ),
            InventoryRule(
                rule_id="optional_reduction",
                anchors=("reduction in", "optional cover"),
                kind=NormativeUnitKind.MODIFICATION,
                materially_affects=("reduction", "optional_cover_state"),
            ),
        ),
    )


def test_inventory_is_product_agnostic_and_keeps_product_identity_as_data() -> None:
    result = inventory_from_fragments(
        _envelope(),
        [
            _fragment(
                "f1",
                "Expenses are excluded until expiry of 24 months waiting period.",
                "page:10",
            )
        ],
    )
    unit = result.inventory.units[0]
    assert unit.concept == "waiting_periods"
    assert unit.applicability.product_reference == "pv_demo"
    assert unit.evidence.source_document_id == "doc_demo"


def test_high_recall_rule_selects_clause_outside_named_concept_section() -> None:
    result = inventory_from_fragments(
        _envelope(),
        [
            _fragment(
                "renewal",
                "On renewal, all waiting periods shall apply afresh to the enhanced limit.",
                "section:E.2.5",
            )
        ],
    )
    assert len(result.inventory.units) == 1
    assert "waiting period" in result.inventory.units[0].excerpt.lower()


def test_multiple_rules_union_material_consequences_without_duplicate_unit() -> None:
    result = inventory_from_fragments(
        _envelope(),
        [
            _fragment(
                "optional",
                "Optional Cover: Reduction in waiting period; the base exclusion shall not apply after the reduced duration.",
                "section:C.10.1",
                optional_cover_state="ON",
            )
        ],
    )
    assert len(result.inventory.units) == 1
    unit = result.inventory.units[0]
    assert unit.kind is NormativeUnitKind.OTHER_NORMATIVE
    assert {"duration", "waiver", "cross_concept_relationship", "reduction", "optional_cover_state"} <= set(
        unit.materially_affects
    )
    assert len(result.selections[0].matched_rule_ids) == 3


def test_inventory_preserves_optional_cover_applicability() -> None:
    result = inventory_from_fragments(
        _envelope(),
        [
            _fragment(
                "optional",
                "Optional Cover: Reduction in Specific Disease Waiting Period to one year.",
                "section:C.10.1",
                optional_cover_state="ON",
            )
        ],
    )
    assert result.inventory.units[0].applicability.optional_cover_state == "ON"


def test_required_source_class_gap_is_visible_not_silent() -> None:
    result = inventory_from_fragments(
        _envelope(),
        [
            _fragment(
                "f1",
                "The waiting period is 24 months.",
                "page:10",
                source_class="POLICY_WORDING",
            )
        ],
    )
    assert not result.source_envelope_complete
    assert result.missing_required_source_classes == ("PRODUCT_BENEFIT_TABLE",)


def test_required_source_classes_complete_when_observed() -> None:
    result = inventory_from_fragments(
        _envelope(),
        [
            _fragment("f1", "The waiting period is 24 months.", "page:10"),
            _fragment(
                "f2",
                "Waiting Period - 3 Years",
                "benefit-table:waiting-period",
                source_class="PRODUCT_BENEFIT_TABLE",
            ),
        ],
        review_status=InventoryReviewStatus.REVIEWED,
    )
    assert result.source_envelope_complete
    assert result.inventory.review_status is InventoryReviewStatus.REVIEWED


def test_unmatched_source_fragment_is_not_forced_into_inventory() -> None:
    result = inventory_from_fragments(
        _envelope(),
        [
            _fragment("f1", "The waiting period is 24 months.", "page:10"),
            _fragment("f2", "Claims must be notified within 24 hours.", "page:20"),
        ],
    )
    assert len(result.inventory.units) == 1
    assert result.inventory.units[0].evidence.evidence_id == "f1"


def test_duplicate_fragment_ids_fail_closed() -> None:
    fragment = _fragment("f1", "The waiting period is 24 months.", "page:10")
    with pytest.raises(RelevanceInventoryError, match="duplicate fragment_id"):
        inventory_from_fragments(_envelope(), [fragment, fragment])


def test_fragment_and_evidence_locator_must_match() -> None:
    with pytest.raises(RelevanceInventoryError, match="locator"):
        SourceFragment(
            fragment_id="f1",
            text="waiting period",
            locator="page:10",
            source_class="POLICY_WORDING",
            applicability=_app(),
            evidence=_evidence("f1", "page:11"),
        )


def test_no_normative_units_fails_closed() -> None:
    with pytest.raises(RelevanceInventoryError, match="no normative units"):
        inventory_from_fragments(
            _envelope(),
            [_fragment("f1", "Customer support contact details.", "page:50")],
        )


def test_source_class_restriction_is_governed_by_rule_not_product() -> None:
    envelope = ConceptRelevanceEnvelope(
        concept="demo_concept",
        policy_version="v1",
        rules=(
            InventoryRule(
                rule_id="policy_only",
                anchors=("special condition",),
                kind=NormativeUnitKind.CONDITION,
                materially_affects=("scope",),
                allowed_source_classes=("POLICY_WORDING",),
            ),
        ),
    )
    with pytest.raises(RelevanceInventoryError, match="no normative units"):
        inventory_from_fragments(
            envelope,
            [
                _fragment(
                    "brochure",
                    "Special condition applies.",
                    "page:1",
                    source_class="BROCHURE",
                )
            ],
        )
