from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.education_publication.repository import EducationPublicationRepository
from insurance_intelligence.llm.provider import DeterministicFakeTextProvider
from policy_scna_app.health_customer_v0 import ask_health_question

ROOT = Path(__file__).resolve().parents[2]
PUBLICATION_ROOT = ROOT / "knowledge/factory/education_publications"
CATALOG_PATH = PUBLICATION_ROOT / "health_customer_v0_component_catalog_v1.json"


def _resolved_output(concept_id: str, component_id: str) -> str:
    return json.dumps(
        {
            "interpretation_status": "RESOLVED",
            "confidence": 0.99,
            "primary_intent": "understand_policy_effect",
            "requested_outcome": "CONTEXTUAL_POLICY_EXPLANATION",
            "governed_concept_candidates": [
                {"concept_id": concept_id, "confidence": 0.99}
            ],
            "selected_concept_id": concept_id,
            "requested_semantic_fact": component_id,
            "scenario_facts": [],
            "request_authority_class": "ASSERTIVE",
            "ambiguity_reasons": [],
            "competing_interpretations": [],
        },
        sort_keys=True,
    )


def _repository() -> EducationPublicationRepository:
    paths = tuple(sorted(PUBLICATION_ROOT.glob("*_education_publication.json")))
    return EducationPublicationRepository.from_json_files(paths)


def test_six_publications_expose_exact_frozen_component_ids() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["concepts"]
    repository = _repository()

    for topic, expected_ids in catalog.items():
        publication = repository.get_by_concept(topic)
        assert publication is not None
        assert [component.component_id for component in publication.components] == expected_ids


def test_valid_ped_component_releases_only_that_governed_component() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:pre_existing_disease",
            "ped.qualifying_history",
        )
    )

    result = ask_health_question(
        question="Could prior medical advice matter even without a formal diagnosis?",
        provider=provider,
        model_name="test-model",
        request_id="component-ped-valid",
        execution_id="component-ped-valid-execution",
        created_at="2026-10-18T06:00:00Z",
        education_repository=_repository(),
    )

    assert result.status == "ANSWER"
    assert result.render_outcome == "PASS"
    assert [section.section_type for section in result.response.sections] == [
        "DIRECT_ANSWER",
        "CUSTOMER_QUALIFICATION",
    ]
    lowered = result.released_text.casefold()
    assert "formal diagnosis is not the only history" in lowered
    assert "medical advice or treatment" in lowered


def test_cross_concept_component_fails_closed_to_clarification() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:pre_existing_disease",
            "copay.trigger_semantics",
        )
    )

    result = ask_health_question(
        question="Explain this PED point.",
        provider=provider,
        model_name="test-model",
        request_id="component-cross-concept",
        execution_id="component-cross-concept-execution",
        created_at="2026-10-18T06:00:00Z",
        education_repository=_repository(),
    )

    assert result.status == "CLARIFICATION"
    assert result.selected_concept_id == "health:concept:pre_existing_disease"
    assert result.selected_topic == "pre_existing_disease"
    assert result.render_outcome == "PASS"
    assert "ambiguous across insurance concepts" in result.released_text.casefold()
    assert "co-payment" not in result.released_text.casefold()
