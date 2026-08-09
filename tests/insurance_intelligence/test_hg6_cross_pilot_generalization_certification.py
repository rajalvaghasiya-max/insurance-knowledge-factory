from __future__ import annotations

from pathlib import Path

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.catalogue import RESTORATION_BENEFIT_CONCEPT
from insurance_intelligence.contracts.reasoning import build_finding
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_health_terminology_routes_copayment_and_restoration_to_distinct_topics() -> None:
    registry = build_health_concept_registry_v1()

    copay = registry.get("health:concept:copayment")
    restoration = registry.get("health:concept:restoration")

    assert copay.downstream_topic == "conditional_copayment"
    assert restoration.downstream_topic == "restoration"
    assert copay.concept_type == "COST_SHARING"
    assert restoration.concept_type == "BENEFIT"
    assert copay.concept_id != restoration.concept_id


def test_shared_reasoning_contract_accepts_materially_different_finding_semantics() -> None:
    copay = build_finding(
        finding_id="finding:hg6:star:copayment",
        requirement_id="requirement:conditional_copayment",
        finding_type="CLAIM_COST_SHARING",
        subject="insured",
        predicate="must_bear",
        object_or_effect="10% of the admissible claim amount",
        condition="the governed conditional co-payment trigger is satisfied",
        scope="star_health:star_comprehensive",
        finding_status="CONDITIONAL",
        derivation_type="CONDITIONAL_DERIVATION",
        rule_id="conditional_copayment_obligation_v1",
        rule_version="1.0",
        evidence_ids=("evidence:hg6:star:copayment",),
        limitations=("Case applicability depends on the governed trigger context.",),
        confidence=0.95,
    )
    restoration = build_finding(
        finding_id="finding:hg6:activ_one:restoration",
        requirement_id="requirement:restoration",
        finding_type="COVERAGE_EFFECT",
        subject="Activ One NXT Super Reload",
        predicate="restores",
        object_or_effect="100% of the Base Sum Insured per activation, with unlimited activations during the Policy Year",
        condition="the admissible claim exhausts or exceeds the available Base Sum Insured and accumulated Super Credit, if applicable",
        scope="aditya_birla_health:activ_one:nxt",
        finding_status="SUPPORTED_WITH_LIMITATIONS",
        derivation_type="DETERMINISTIC_DERIVATION",
        rule_id="activ_one_nxt_super_reload_v1",
        rule_version="1.0",
        evidence_ids=(
            "ev_activ_one_nxt_super_reload_policy_wording",
            "ev_activ_one_nxt_super_reload_prospectus",
        ),
        limitations=("Variant applicability remains controlled by the Policy Schedule.",),
        confidence=0.95,
    )

    assert copay.finding_type == "CLAIM_COST_SHARING"
    assert restoration.finding_type == "COVERAGE_EFFECT"
    assert copay.derivation_type == "CONDITIONAL_DERIVATION"
    assert restoration.derivation_type == "DETERMINISTIC_DERIVATION"
    assert set(copay.evidence_ids).isdisjoint(restoration.evidence_ids)


def test_restoration_implementation_remains_product_specific_while_concept_is_generic() -> None:
    implementation = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION
    concept = RESTORATION_BENEFIT_CONCEPT

    assert implementation.concept_id == concept.concept_id
    assert implementation.insurer_id == "aditya_birla_health"
    assert implementation.product_id == "activ_one"
    assert implementation.marketing_name == "Super Reload"

    concept_text = " ".join(
        (
            concept.concept_id,
            concept.canonical_name,
            concept.definition,
            concept.benefit_family,
            *concept.allowed_mechanic_dimensions,
        )
    ).casefold()
    assert "star_health" not in concept_text
    assert "star comprehensive" not in concept_text
    assert "aditya_birla_health" not in concept_text
    assert "activ one" not in concept_text
    assert "super reload" not in concept_text


def test_generic_reasoning_and_explanation_layers_contain_no_product_identity_leakage() -> None:
    generic_paths = (
        REPO_ROOT / "insurance_intelligence" / "contracts" / "reasoning.py",
        REPO_ROOT / "insurance_intelligence" / "contracts" / "explanation.py",
        REPO_ROOT / "insurance_intelligence" / "explanation" / "templates.py",
        REPO_ROOT / "insurance_intelligence" / "explanation" / "validator.py",
    )
    forbidden = (
        "star_health",
        "star comprehensive",
        "aditya_birla_health",
        "activ one nxt",
        "super reload",
    )

    for path in generic_paths:
        text = path.read_text(encoding="utf-8").casefold()
        for token in forbidden:
            assert token not in text, f"{token!r} leaked into generic layer {path}"


def test_activ_one_restoration_evidence_is_bounded_and_not_reused_as_star_evidence() -> None:
    evidence = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.evidence_references

    assert {item.authority_type for item in evidence} == {"policy_wording", "prospectus"}
    assert all(item.bounded_evidence_identity for item in evidence)
    assert all("activ_one_nxt" in item.bounded_evidence_identity for item in evidence)
    assert all("star" not in item.bounded_evidence_identity.casefold() for item in evidence)


def test_cross_pilot_certification_does_not_introduce_comparison_or_recommendation() -> None:
    implementation = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION
    text = " ".join(
        (
            implementation.marketing_name,
            implementation.behaviour_signature_id,
            *implementation.conditions,
            *implementation.limitations,
            *implementation.exclusions,
        )
    ).casefold()

    assert "better than" not in text
    assert "recommended" not in text
    assert "best product" not in text
    assert "suitability" not in text
    assert "rank" not in text
