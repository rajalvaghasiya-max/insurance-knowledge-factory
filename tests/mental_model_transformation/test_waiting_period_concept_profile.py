from knowledge_domains.health.mental_model_transformation.concept_profiles import (
    get_concept_profile,
)


def test_waiting_period_profile_is_available():
    profile = get_concept_profile("waiting_period")

    assert profile is not None
    assert profile.concept_id == "waiting_period"
    assert "coverage_activation_timeline" in profile.missing_concepts
    assert "3 years" in profile.verification_scenario["applicable_waiting_period"]
    assert "waiting period" in profile.golden_rule.lower()


def test_unknown_concept_has_no_profile():
    assert get_concept_profile("unknown_concept") is None