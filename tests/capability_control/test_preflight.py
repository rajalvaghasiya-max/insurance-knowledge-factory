from capability_control.catalog import validate_catalog
from capability_control.preflight import preflight_capability


def _catalog():
    return validate_catalog(
        {
            "catalog_version": "1.0",
            "enforcement_mode": "RECONCILIATION",
            "governed_roots": ["insurance_intelligence"],
            "capabilities": [
                {
                    "capability_id": "LLM.EVALUATION.DISAGREEMENT_ANALYSIS",
                    "name": "LLM disagreement analysis",
                    "responsibility": "Compare model and provider outputs, analyze disagreement and support adjudication without making model agreement authoritative.",
                    "plane": "LLM_EVALUATION",
                    "lifecycle_status": "ACTIVE",
                    "authority_role": "Evaluation evidence only.",
                    "safety_invariants": ["Model agreement is not insurance truth."],
                    "reuse_policy": "REUSE",
                    "ownership_paths": ["insurance_intelligence/evaluation"],
                    "introduced_by": "MO-022F",
                    "supersedes": [],
                    "superseded_by": None,
                    "notes": "Supports controlled multi-provider comparison and adjudication.",
                },
                {
                    "capability_id": "II.REQUEST.AUTHORITY_BOUNDARY",
                    "name": "Assertion and Advisory Request Authority Boundary",
                    "responsibility": "Classify requested authority independently of intent as assertive advisory mixed or unresolved.",
                    "plane": "REQUEST_GOVERNANCE",
                    "lifecycle_status": "ACTIVE",
                    "authority_role": "Raises advisory safety obligations.",
                    "safety_invariants": ["Unresolved authority fails strict."],
                    "reuse_policy": "REUSE",
                    "ownership_paths": ["insurance_intelligence/request_authority.py"],
                    "introduced_by": "PR-193",
                    "supersedes": [],
                    "superseded_by": None,
                    "notes": None,
                },
            ],
        }
    )


def test_preflight_surfaces_existing_multi_model_comparison_capability():
    result = preflight_capability(
        catalog=_catalog(), query="compare outputs from multiple LLM providers"
    )
    assert result.classification == "EXISTING_CAPABILITY_CANDIDATES_FOUND"
    assert result.new_authorized is False
    assert result.candidates[0].capability_id == "LLM.EVALUATION.DISAGREEMENT_ANALYSIS"


def test_preflight_surfaces_authority_boundary_under_different_wording():
    result = preflight_capability(
        catalog=_catalog(), query="decide whether a request is advisory or assertive"
    )
    ids = [candidate.capability_id for candidate in result.candidates]
    assert "II.REQUEST.AUTHORITY_BOUNDARY" in ids


def test_no_match_never_authorizes_new():
    result = preflight_capability(
        catalog=_catalog(), query="quantum orbital telemetry ingestion"
    )
    assert result.candidates == ()
    assert result.classification == "NO_LEXICAL_CANDIDATE_FOUND_REQUIRES_MANUAL_REPOSITORY_REVIEW"
    assert result.new_authorized is False


def test_preflight_is_deterministic():
    first = preflight_capability(catalog=_catalog(), query="provider disagreement comparison")
    second = preflight_capability(catalog=_catalog(), query="provider disagreement comparison")
    assert first == second


def test_preflight_rejects_empty_query_and_invalid_limit():
    catalog = _catalog()
    try:
        preflight_capability(catalog=catalog, query="")
    except ValueError as exc:
        assert "query" in str(exc)
    else:
        raise AssertionError("empty query must fail")

    try:
        preflight_capability(catalog=catalog, query="comparison", limit=0)
    except ValueError as exc:
        assert "limit" in str(exc)
    else:
        raise AssertionError("invalid limit must fail")
