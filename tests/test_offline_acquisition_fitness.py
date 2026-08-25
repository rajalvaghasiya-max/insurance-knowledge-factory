from __future__ import annotations

import json
from pathlib import Path

import agents.html_section_agent as html_section_module
import agents.preservation_agent as preservation_module
from agents.html_section_agent import HtmlSectionAgent
from agents.pdf_intelligence.evidence_aware_pdf_discovery_agent import (
    EvidenceAwarePDFDiscoveryAgent,
)
from agents.preservation_agent import PreservationAgent
from agents.product_signal_extractor import ProductSignalExtractor


PRODUCT_URL = "https://www.icicilombard.com/health-insurance/arogya-sanjeevani"
CURRENT_UIN = "ICIHLIP25041V022425"
POLICY_WORDING_URL = (
    "https://www.icicilombard.com/docs/arogya-sanjeevani-policy-wording.pdf"
)
GRO_MAPPING_URL = "https://www.icicilombard.com/docs/final-gro-mapping.pdf"


class _FakeCaptureEngine:
    def capture(self, url: str) -> dict:
        assert url == PRODUCT_URL
        html = f"""
        <html>
          <head>
            <title>Arogya Sanjeevani Health Insurance</title>
            <link rel="canonical" href="{PRODUCT_URL}" />
          </head>
          <body>
            <h1>Arogya Sanjeevani Health Insurance</h1>
            <p>UIN: {CURRENT_UIN}</p>
            <a href="{POLICY_WORDING_URL}">Arogya Sanjeevani Policy Wording</a>
            <a href="{GRO_MAPPING_URL}">GRO Mapping</a>
          </body>
        </html>
        """
        text = f"""
        Arogya Sanjeevani Health Insurance
        Overview
        Arogya Sanjeevani is a health insurance policy. UIN: {CURRENT_UIN}. This page describes the current product and its coverage.
        Benefits
        Hospitalisation and day care coverage are available subject to the policy terms and conditions.
        Waiting Period
        A specific waiting period may apply according to the policy wording and the insured member's coverage history.
        Documents
        Policy wording and customer information documents are available for download from this product page.
        """
        return {
            "status": "captured",
            "url": url,
            "html": html,
            "text": text,
            "page_title": "Arogya Sanjeevani Health Insurance",
            "capture_strategy": "fitness_fixture",
            "screenshot_bytes": b"fixture-screenshot",
            "error": None,
            "capture_strategy_attempted": ["fitness_fixture"],
        }


class _TempSignalExtractor(ProductSignalExtractor):
    def __init__(self, output_dir: Path):
        super().__init__()
        self._output_dir = output_dir

    def save_signals(self, signals: dict) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._output_dir / f"{signals['content_hash']}.json"
        output_path.write_text(json.dumps(signals, indent=2), encoding="utf-8")
        return output_path


def test_offline_acquisition_chain_preserves_identity_signals_and_document_roles(
    monkeypatch,
    tmp_path,
) -> None:
    raw_html_dir = tmp_path / "archive" / "raw_html"
    text_dir = tmp_path / "archive" / "text"
    metadata_dir = tmp_path / "archive" / "metadata"
    screenshot_dir = tmp_path / "archive" / "screenshots"

    monkeypatch.setattr(preservation_module, "RAW_HTML_DIR", raw_html_dir)
    monkeypatch.setattr(preservation_module, "TEXT_DIR", text_dir)
    monkeypatch.setattr(preservation_module, "METADATA_DIR", metadata_dir)
    monkeypatch.setattr(preservation_module, "SCREENSHOT_DIR", screenshot_dir)
    monkeypatch.setattr(html_section_module, "BASE_DIR", tmp_path)

    preservation = PreservationAgent()
    preservation.capture_engine = _FakeCaptureEngine()

    metadata = preservation.preserve_page("icici_lombard", PRODUCT_URL)

    assert metadata["status"] == "captured"
    assert metadata["has_screenshot"] is True
    assert metadata["content_hash"]
    assert Path(metadata["html_path"]).is_file()
    assert Path(metadata["text_path"]).is_file()
    assert Path(metadata["screenshot_path"]).read_bytes() == b"fixture-screenshot"

    metadata_files = list((metadata_dir / "icici_lombard").glob("*.json"))
    assert len(metadata_files) == 1

    parsed = HtmlSectionAgent().parse_metadata_file(metadata_files[0])
    assert parsed["status"] == "parsed"
    assert parsed["section_count"] >= 3

    signal_extractor = _TempSignalExtractor(tmp_path / "signals")
    signal_result = signal_extractor.extract_from_parsed_file(Path(parsed["output_path"]))

    assert signal_result["status"] == "extracted"
    assert signal_result["page_intent"] == "individual_product"
    assert signal_result["asset_scope"] == "product_specific"
    assert signal_result["product_names"] == 1
    assert signal_result["uins"] == 1

    signal_record = json.loads(Path(signal_result["output_path"]).read_text(encoding="utf-8"))
    assert signal_record["uins"] == [CURRENT_UIN]
    assert signal_record["uin_candidates"][0]["candidate_status"] == "format_valid_candidate"
    assert signal_record["uin_candidates"][0]["source"]["url"] == PRODUCT_URL

    discovery = EvidenceAwarePDFDiscoveryAgent()
    discovery.PDF_QUEUE_DIR = tmp_path / "discovery" / "pdf_queue"
    discovery_result = discovery.discover_for_insurer(
        "icici_lombard",
        raw_html_dir / "icici_lombard",
    )

    assert discovery_result["pdf_urls_found"] == 1
    assert discovery_result["pdf_urls_skipped"] >= 1
    assert discovery_result["document_type_counts"] == {"policy_wording": 1}

    queue = json.loads(Path(discovery_result["output_file"]).read_text(encoding="utf-8"))
    assert len(queue["items"]) == 1
    assert queue["items"][0]["url"] == POLICY_WORDING_URL
    assert queue["items"][0]["document_type"] == "policy_wording"
    assert queue["items"][0]["source_page_url"] == PRODUCT_URL

    skipped_urls = {item["url"] for item in queue["skipped_items_sample"]}
    assert GRO_MAPPING_URL in skipped_urls
