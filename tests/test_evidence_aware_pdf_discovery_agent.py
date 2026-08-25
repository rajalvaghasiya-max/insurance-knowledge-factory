from agents.pdf_intelligence.evidence_aware_pdf_discovery_agent import (
    EvidenceAwarePDFDiscoveryAgent,
)


def _agent() -> EvidenceAwarePDFDiscoveryAgent:
    return object.__new__(EvidenceAwarePDFDiscoveryAgent)


def test_strong_policy_wording_markers_are_preserved() -> None:
    agent = _agent()

    assert agent.classify_document_type(
        "https://example.test/docs/arogya-sanjeevani-policy-wording.pdf",
        "Download",
    ) == "policy_wording"
    assert agent.classify_document_type(
        "https://example.test/docs/arogya_sanjeevani_pw.pdf",
        "Arogya Sanjeevani",
    ) == "policy_wording"


def test_generic_wording_token_does_not_promote_unrelated_pdf_to_policy_wording() -> None:
    agent = _agent()

    assert agent.classify_document_type(
        "https://example.test/docs/final-gro-mapping.pdf",
        "Reference wording for grievance contacts",
    ) == "other_pdf"


def test_gro_mapping_is_explicitly_non_policy_even_when_anchor_mentions_policy_wording() -> None:
    agent = _agent()

    assert agent.classify_document_type(
        "https://example.test/downloads/final-gro-mapping.pdf",
        "Policy wording and GRO mapping downloads",
    ) == "other_pdf"


def test_other_existing_document_roles_still_delegate_to_base_classifier() -> None:
    agent = _agent()

    assert agent.classify_document_type(
        "https://example.test/docs/arogya-brochure.pdf",
        "Product brochure",
    ) == "brochure"
    assert agent.classify_document_type(
        "https://example.test/docs/arogya-cis.pdf",
        "Customer Information Sheet",
    ) == "customer_information_sheet"
    assert agent.classify_document_type(
        "https://example.test/docs/claim-form.pdf",
        "Claim form",
    ) == "claim_form"


def test_standalone_wording_filename_remains_policy_wording_candidate() -> None:
    agent = _agent()

    assert agent.classify_document_type(
        "https://example.test/downloads/wording.pdf",
        "Arogya Sanjeevani",
    ) == "policy_wording"
