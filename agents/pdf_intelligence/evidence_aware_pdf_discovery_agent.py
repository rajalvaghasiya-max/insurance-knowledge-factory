from __future__ import annotations

from pathlib import Path

from agents.pdf_intelligence.pdf_discovery_agent import PDFDiscoveryAgent


class EvidenceAwarePDFDiscoveryAgent(PDFDiscoveryAgent):
    """Compatibility hardening for high-authority PDF document roles.

    The base discovery agent intentionally casts a wide net. This subclass makes
    one narrow correction before documents reach the stronger download path:
    `policy_wording` requires strong role evidence and cannot be inferred from
    the generic token ``wording`` alone.

    This remains a discovery/classification aid only. It does not establish
    product identity, document identity, currentness, or publication eligibility.
    """

    VERSION = "0.5.3"

    GOVERNANCE_REFERENCE_MARKERS = (
        "grievance redressal officer",
        "grievance-redressal-officer",
        "gro mapping",
        "gro-mapping",
        "gro_mapping",
        "final-gro-mapping",
    )

    STRONG_POLICY_WORDING_MARKERS = (
        "policy wording",
        "policy-wording",
        "policywording",
        "policy wordings",
        "policy-document",
        "policy document",
        "/health-pw/",
        "_pw.pdf",
        "-pw.pdf",
        "/policy-wordings/",
        "/policy-wording/",
    )

    def classify_document_type(self, url: str, text: str) -> str:
        combined = f"{url} {text}".lower()
        filename = Path(url.split("?", 1)[0]).name.lower()

        if any(marker in combined for marker in self.GOVERNANCE_REFERENCE_MARKERS):
            return "other_pdf"

        if any(marker in combined for marker in self.STRONG_POLICY_WORDING_MARKERS):
            return "policy_wording"

        # A standalone filename such as `wording.pdf` is still useful evidence,
        # but a generic prose occurrence of the word "wording" is not.
        if filename in {"wording.pdf", "wordings.pdf", "policywording.pdf"}:
            return "policy_wording"

        candidate = super().classify_document_type(url, text)

        # The parent v0.5.2 classifier includes the weak token `wording` in the
        # policy-wording rule. Demote only that unsupported promotion while
        # preserving every other existing document-type rule unchanged.
        if candidate == "policy_wording":
            return "other_pdf"

        return candidate
