from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from insurance_intelligence.concepts.waiting_periods.policy import (
    waiting_period_concept_policy,
    waiting_period_concept_policy_v2,
)
from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    EvidenceReference,
    NormativeUnit,
    NormativeUnitKind,
)
from insurance_intelligence.generic_knowledge.relevance_inventory import (
    SourceFragment,
    inventory_from_fragments,
)
from insurance_intelligence.generic_knowledge.waiting_period_mapping import (
    ReviewedMappingKind,
    ReviewedWaitingPeriodMapping,
    WaitingPeriodMappingError,
    WaitingPeriodSemanticType,
    map_reviewed_waiting_period_units,
)
from insurance_intelligence.generic_knowledge.waiting_period_migration import (
    migrate_waiting_period_record,
)


STAR_PATH = Path(
    "knowledge/factory/migrations/star_comprehensive_waiting_period_generic_migration_v1.json"
)
ACTIV_PATH = Path(
    "knowledge/factory/migrations/activ_one_nxt_waiting_period_generic_migration_v1.json"
)


def _fragment(fragment_id: str, text: str) -> SourceFragment:
    applicability = ApplicabilityKey(product_reference="product://adversarial")
    locator = f"page:{fragment_id}"
    return SourceFragment(
        fragment_id=fragment_id,
        text=text,
        locator=locator,
        source_class="POLICY_WORDING",
        applicability=applicability,
        evidence=EvidenceReference(
            evidence_id=f"evidence_{fragment_id}",
            source_document_id="doc-v2",
            source_document_version="v1",
            source_hash_sha256="a" * 64,
            locator=locator,
            authority_class="POLICY_WORDING",
        ),
    )


def _unit(unit_id: str) -> NormativeUnit:
    applicability = ApplicabilityKey(
        product_reference="product://adversarial",
        optional_cover_state="BASE",
        effective_from=date(2026, 1, 1),
    )
    evidence = EvidenceReference(
        evidence_id=f"evidence_{unit_id}",
        source_document_id="doc-v2",
        source_document_version="v1",
        source_hash_sha256="b" * 64,
        locator=f"page:{unit_id}",
        authority_class="POLICY_WORDING",
    )
    return NormativeUnit(
        normative_unit_id=unit_id,
        concept="waiting_periods",
        kind=NormativeUnitKind.CONDITION,
        text_sha256="c" * 64,
        excerpt="adversarial waiting-period clause",
        applicability=applicability,
        evidence=evidence,
        materially_affects=("DURATION", "APPLICABILITY"),
    )


def _effects(result, fragment_id: str) -> set[str]:
    selection = next(
        item
        for item in result.selections
        if item.normative_unit.evidence.locator == f"page:{fragment_id}"
    )
    return set(selection.normative_unit.materially_affects)


def _record(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _facts_by_type(result):
    return {
        fact.value["waiting_period_type"]: fact
        for fact in result.mapping.semantic_facts
    }


def test_v1_policy_remains_frozen_and_v2_is_additive() -> None:
    v1 = waiting_period_concept_policy()
    v2 = waiting_period_concept_policy_v2()
    assert v1.policy_version == "waiting_period_policy_v1"
    assert v2.policy_version == "waiting_period_policy_v2"
    assert len(v2.envelope.rules) > len(v1.envelope.rules)
    v1_ids = {rule.rule_id for rule in v1.envelope.rules}
    v2_ids = {rule.rule_id for rule in v2.envelope.rules}
    assert v1_ids < v2_ids


def test_v2_high_recall_detects_maternity_and_baby_care_waits() -> None:
    result = inventory_from_fragments(
        waiting_period_concept_policy_v2().envelope,
        [
            _fragment(
                "maternity",
                "Maternity Expenses waiting period 36 months and Baby Care waiting period 36 months; each will decrease by 1 year if long term policy premium is paid upfront.",
            )
        ],
    )
    effects = _effects(result, "maternity")
    assert "DURATION" in effects
    assert "REDUCTION" in effects
    assert "APPLICABILITY" in effects


def test_v2_high_recall_detects_schedule_selected_duration_options() -> None:
    result = inventory_from_fragments(
        waiting_period_concept_policy_v2().envelope,
        [
            _fragment(
                "selection",
                "Options Available for Change in PED waiting Period: 1 year, 2 years, 3 years.",
            )
        ],
    )
    effects = _effects(result, "selection")
    assert "DURATION" in effects
    assert "APPLICABILITY" in effects
    assert "EFFECTIVE_DATE_OR_VERSION" in effects


def test_v2_high_recall_detects_new_insured_member_reset() -> None:
    result = inventory_from_fragments(
        waiting_period_concept_policy_v2().envelope,
        [
            _fragment(
                "new_member",
                "Where an Insured Beneficiary is added to the Policy, the pre-existing disease clause, exclusions and Waiting Periods will apply considering that Policy Year as the first year for the newly added Insured Beneficiary.",
            )
        ],
    )
    effects = _effects(result, "new_member")
    assert "START_BASIS" in effects
    assert "RENEWAL_OR_REINSTATEMENT_EFFECT" in effects
    assert "APPLICABILITY" in effects


def test_v2_mapper_supports_maternity_base_mechanic() -> None:
    unit = _unit("maternity")
    result = map_reviewed_waiting_period_units(
        (unit,),
        (
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit.normative_unit_id,
                kind=ReviewedMappingKind.SEMANTIC_FACT,
                reason="reviewed maternity wait",
                semantic_type=WaitingPeriodSemanticType.BASE_MECHANIC,
                semantic_value={
                    "waiting_period_type": "MATERNITY",
                    "duration_value": 36,
                    "duration_unit": "MONTHS",
                    "start_basis": "POLICY_INCEPTION",
                    "applies_to": ["maternity expenses"],
                },
            ),
        ),
        ontology_version="waiting_periods_v2",
    )
    fact = result.semantic_facts[0]
    assert fact.value["waiting_period_type"] == "MATERNITY"
    assert fact.value["duration_value"] == 36
    assert fact.ontology_version == "waiting_periods_v2"


def test_v2_mapper_supports_baby_care_base_mechanic() -> None:
    unit = _unit("baby")
    result = map_reviewed_waiting_period_units(
        (unit,),
        (
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit.normative_unit_id,
                kind=ReviewedMappingKind.SEMANTIC_FACT,
                reason="reviewed baby-care wait",
                semantic_type=WaitingPeriodSemanticType.BASE_MECHANIC,
                semantic_value={
                    "waiting_period_type": "BABY_CARE",
                    "duration_value": 36,
                    "duration_unit": "MONTHS",
                    "start_basis": "POLICY_INCEPTION",
                    "applies_to": ["baby care benefit"],
                },
            ),
        ),
        ontology_version="waiting_periods_v2",
    )
    assert result.semantic_facts[0].value["waiting_period_type"] == "BABY_CARE"


def test_v2_mapper_supports_schedule_duration_selection() -> None:
    unit = _unit("duration_selection")
    result = map_reviewed_waiting_period_units(
        (unit,),
        (
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit.normative_unit_id,
                kind=ReviewedMappingKind.SEMANTIC_FACT,
                reason="policy schedule selects one governed duration",
                semantic_type=WaitingPeriodSemanticType.DURATION_SELECTION,
                semantic_value={
                    "waiting_period_type": "PRE_EXISTING_DISEASE",
                    "duration_options": [
                        {"duration_value": 1, "duration_unit": "YEARS"},
                        {"duration_value": 2, "duration_unit": "YEARS"},
                        {"duration_value": 3, "duration_unit": "YEARS"},
                    ],
                    "selection_basis": "Policy Schedule",
                },
            ),
        ),
        ontology_version="waiting_periods_v2",
    )
    fact = result.semantic_facts[0]
    assert fact.semantic_type == "DURATION_SELECTION"
    assert tuple(item["duration_value"] for item in fact.value["duration_options"]) == (1, 2, 3)
    assert fact.value["selection_basis"] == "Policy Schedule"


def test_v2_duration_selection_rejects_duplicate_options() -> None:
    unit = _unit("bad_selection")
    with pytest.raises(WaitingPeriodMappingError):
        map_reviewed_waiting_period_units(
            (unit,),
            (
                ReviewedWaitingPeriodMapping(
                    normative_unit_id=unit.normative_unit_id,
                    kind=ReviewedMappingKind.SEMANTIC_FACT,
                    reason="bad duplicate schedule options",
                    semantic_type=WaitingPeriodSemanticType.DURATION_SELECTION,
                    semantic_value={
                        "waiting_period_type": "PRE_EXISTING_DISEASE",
                        "duration_options": [
                            {"duration_value": 1, "duration_unit": "YEARS"},
                            {"duration_value": 1, "duration_unit": "YEARS"},
                        ],
                        "selection_basis": "Policy Schedule",
                    },
                ),
            ),
            ontology_version="waiting_periods_v2",
        )


def test_v2_mapper_supports_new_member_reset_semantic() -> None:
    unit = _unit("new_member")
    result = map_reviewed_waiting_period_units(
        (unit,),
        (
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit.normative_unit_id,
                kind=ReviewedMappingKind.SEMANTIC_FACT,
                reason="new member starts waits afresh",
                semantic_type=WaitingPeriodSemanticType.NEW_MEMBER_EFFECT,
                semantic_value={
                    "waiting_period_type": "PRE_EXISTING_DISEASE",
                    "start_basis": "INSURED_PERSON_ADDITION_DATE",
                    "detail": "waiting periods apply afresh for the newly added insured beneficiary",
                },
            ),
        ),
        ontology_version="waiting_periods_v2",
    )
    fact = result.semantic_facts[0]
    assert fact.semantic_type == "NEW_MEMBER_EFFECT"
    assert fact.value["start_basis"] == "INSURED_PERSON_ADDITION_DATE"


def test_star_recertifies_under_v2_without_semantic_drift_or_residue() -> None:
    v1 = migrate_waiting_period_record(_record(STAR_PATH))
    v2 = migrate_waiting_period_record(
        _record(STAR_PATH), ontology_version_override="waiting_periods_v2"
    )
    assert v1.accounting.publishable and v2.accounting.publishable
    assert v2.accounting.telemetry.residue_count == 0
    assert {k: v.value for k, v in _facts_by_type(v1).items()} == {
        k: v.value for k, v in _facts_by_type(v2).items()
    }
    assert all(fact.ontology_version == "waiting_periods_v2" for fact in v2.mapping.semantic_facts)


def test_activ_recertifies_under_v2_without_semantic_drift_or_residue() -> None:
    v1 = migrate_waiting_period_record(_record(ACTIV_PATH))
    v2 = migrate_waiting_period_record(
        _record(ACTIV_PATH), ontology_version_override="waiting_periods_v2"
    )
    assert v1.accounting.publishable and v2.accounting.publishable
    assert v2.accounting.telemetry.residue_count == 0
    assert {k: v.value for k, v in _facts_by_type(v1).items()} == {
        k: v.value for k, v in _facts_by_type(v2).items()
    }
    assert all(fact.ontology_version == "waiting_periods_v2" for fact in v2.mapping.semantic_facts)


def test_v2_extension_contains_no_product_identity_logic() -> None:
    paths = (
        Path("insurance_intelligence/benefits/waiting_period_contracts.py"),
        Path("insurance_intelligence/generic_knowledge/waiting_period_mapping.py"),
        Path("insurance_intelligence/concepts/waiting_periods/policy.py"),
    )
    source = "\n".join(path.read_text(encoding="utf-8").casefold() for path in paths)
    for forbidden in (
        "bajaj_allianz",
        "my_health_care",
        "star_health",
        "activ_one",
        "aditya_birla",
        "if insurer",
        "if product ==",
    ):
        assert forbidden not in source
