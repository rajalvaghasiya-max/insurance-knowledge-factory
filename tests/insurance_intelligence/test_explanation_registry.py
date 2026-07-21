from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.explanation.registry import (
    ExplanationRegistryError,
    ExplanationStyleRegistry,
    TerminologyRegistry,
    build_style_definition,
    build_terminology_definition,
)


def style(**overrides):
    values = dict(
        style_id="customer-simple",
        style_version="1.0",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_modes=("PLAIN_LANGUAGE", "CLAUSE_MEANING"),
        priority=10,
    )
    values.update(overrides)
    return build_style_definition(**values)


def term(**overrides):
    values = dict(
        terminology_id="admissible-claim",
        terminology_version="1.0",
        source_term="admissible claim amount",
        rendered_term="eligible claim amount",
        action="SIMPLIFY",
        audience="CUSTOMER",
        reading_levels=("SIMPLE", "STANDARD"),
        explanation_modes=("PLAIN_LANGUAGE", "CLAUSE_MEANING"),
        scope="HEALTH",
        priority=10,
    )
    values.update(overrides)
    return build_terminology_definition(**values)


def test_style_is_immutable():
    item = style()
    with pytest.raises(FrozenInstanceError):
        item.tone = "TECHNICAL"  # type: ignore[misc]


def test_style_rejects_invalid_audience():
    with pytest.raises(ExplanationRegistryError, match="audience"):
        style(audience="PUBLIC")


def test_style_rejects_invalid_mode():
    with pytest.raises(ExplanationRegistryError, match="explanation_modes"):
        style(explanation_modes=("UNKNOWN",))


def test_style_requires_modes():
    with pytest.raises(ExplanationRegistryError, match="must not be empty"):
        style(explanation_modes=())


def test_style_requires_positive_word_limit():
    with pytest.raises(ExplanationRegistryError, match="positive integer"):
        style(max_section_words=0)


def test_style_cannot_drop_conditions():
    with pytest.raises(ExplanationRegistryError, match="preserve conditions"):
        style(preserve_conditions=False)


def test_style_cannot_drop_limitations():
    with pytest.raises(ExplanationRegistryError, match="preserve conditions"):
        style(preserve_limitations=False)


def test_style_registry_orders_deterministically():
    registry = ExplanationStyleRegistry((style(style_id="b", priority=20), style(style_id="a", priority=10)))
    assert tuple(item.style_id for item in registry.all_styles()) == ("a", "b")


def test_style_registry_rejects_duplicate_key():
    item = style()
    with pytest.raises(ExplanationRegistryError, match="duplicate style"):
        ExplanationStyleRegistry((item, item))


def test_style_registry_rejects_ambiguous_id():
    with pytest.raises(ExplanationRegistryError, match="ambiguous duplicate style_id"):
        ExplanationStyleRegistry((style(), style(style_version="2.0")))


def test_style_eligibility_matches_all_dimensions():
    registry = ExplanationStyleRegistry((style(), style(style_id="advisor", audience="ADVISOR")))
    matches = registry.eligible_styles(audience="CUSTOMER", reading_level="SIMPLE", explanation_mode="CLAUSE_MEANING")
    assert tuple(item.style_id for item in matches) == ("customer-simple",)


def test_style_eligibility_fails_closed_on_level():
    registry = ExplanationStyleRegistry((style(),))
    assert registry.eligible_styles(audience="CUSTOMER", reading_level="TECHNICAL", explanation_mode="CLAUSE_MEANING") == ()


def test_terminology_is_immutable():
    item = term()
    with pytest.raises(FrozenInstanceError):
        item.rendered_term = "changed"  # type: ignore[misc]


def test_terminology_rejects_meaning_change():
    with pytest.raises(ExplanationRegistryError, match="preserve meaning"):
        term(meaning_preserved=False)


def test_terminology_define_requires_definition():
    with pytest.raises(ExplanationRegistryError, match="definition_text"):
        term(action="DEFINE", definition_text="")


def test_terminology_expand_accepts_definition():
    item = term(action="EXPAND", definition_text="The amount accepted as payable under the policy terms.")
    assert item.action == "EXPAND"


def test_terminology_rejects_invalid_scope():
    with pytest.raises(ExplanationRegistryError, match="scope"):
        term(scope="PROPERTY")


def test_terminology_rejects_duplicate_levels():
    with pytest.raises(ExplanationRegistryError, match="unique"):
        term(reading_levels=("SIMPLE", "SIMPLE"))


def test_terminology_registry_orders_deterministically():
    registry = TerminologyRegistry((term(terminology_id="b", priority=20), term(terminology_id="a", priority=10)))
    assert tuple(item.terminology_id for item in registry.all_terms()) == ("a", "b")


def test_terminology_registry_rejects_duplicate_key():
    item = term()
    with pytest.raises(ExplanationRegistryError, match="duplicate terminology"):
        TerminologyRegistry((item, item))


def test_terminology_registry_rejects_ambiguous_id():
    with pytest.raises(ExplanationRegistryError, match="ambiguous duplicate terminology_id"):
        TerminologyRegistry((term(), term(terminology_version="2.0")))


def test_terminology_eligibility_matches_term_and_dimensions():
    registry = TerminologyRegistry((term(),))
    matches = registry.eligible_terms(
        source_terms=("admissible claim amount",),
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="CLAUSE_MEANING",
        scope="HEALTH",
    )
    assert len(matches) == 1


def test_terminology_global_scope_matches_domain_scope():
    registry = TerminologyRegistry((term(scope="GLOBAL"),))
    assert len(registry.eligible_terms(
        source_terms=("admissible claim amount",), audience="CUSTOMER", reading_level="SIMPLE",
        explanation_mode="PLAIN_LANGUAGE", scope="HEALTH"
    )) == 1


def test_terminology_eligibility_fails_closed_on_unknown_term():
    registry = TerminologyRegistry((term(),))
    assert registry.eligible_terms(
        source_terms=("different term",), audience="CUSTOMER", reading_level="SIMPLE",
        explanation_mode="PLAIN_LANGUAGE", scope="HEALTH"
    ) == ()


def test_terminology_eligibility_rejects_duplicate_source_terms():
    registry = TerminologyRegistry((term(),))
    with pytest.raises(ExplanationRegistryError, match="unique"):
        registry.eligible_terms(
            source_terms=("admissible claim amount", "admissible claim amount"),
            audience="CUSTOMER", reading_level="SIMPLE", explanation_mode="PLAIN_LANGUAGE", scope="HEALTH"
        )
