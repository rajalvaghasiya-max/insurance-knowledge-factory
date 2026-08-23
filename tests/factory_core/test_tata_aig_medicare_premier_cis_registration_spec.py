from __future__ import annotations

import json
from pathlib import Path


def test_tata_policy_and_cis_registration_spec_is_governed_and_declarative() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "docs/architecture/tata_aig_medicare_premier_policy_and_cis_generic_sources_registration_spec.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["registration_type"] == "generic_source_registration_bundle_v1"
    assert data["product_context"]["insurer_id"] == "tata_aig_general"
    assert data["product_context"]["product_id"] == "medicare_premier"

    documents = {item["document_type"]: item for item in data["documents"]}
    assert set(documents) == {"policy_wording", "customer_information_sheet"}

    wording = documents["policy_wording"]
    cis = documents["customer_information_sheet"]

    assert wording["authority_role"] == "primary_legal"
    assert wording["source_document_id"] == "392feaeeb26cb9ec7f6addc3ed764291d9c9f16bf6c70f466d9f92f85db78960"

    assert cis["authority_role"] == "corroborating_product"
    assert cis["source_document_id"] == "673c37dbe7d93d2269019cb92b761b5deacd903c3fb7249251584876eb92768b"
    assert "Co-Payment" in cis["evidence_markers"]

    # Registration config identifies immutable sources and review markers only;
    # it must not smuggle a product-level copayment conclusion into configuration.
    serialized = json.dumps(data).lower()
    assert '"percentage"' not in serialized
    assert '"does_not_apply"' not in serialized
    assert '"0%"' not in serialized
