from __future__ import annotations

import json
from pathlib import Path


AUTH_PATH = Path(
    "docs/architecture/health_product12_gate_a_execution_authorization_v1.json"
)


def test_product12_authorization_is_gate_a_only() -> None:
    record = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    assert record["record_status"] == "EFFECTIVE_ONLY_AFTER_PREREGISTRATION_MERGE"
    assert record["product_number"] == 12
    assert record["authorized_gate"] == "A"
    assert record["gate_b_authorized"] is False
    assert record["gate_c_authorized"] is False
    assert record["product_screening_authorized"] is False
    assert record["target_clause_reads_authorized"] is False


def test_product12_gate_a_requires_fresh_frozen_transport_run() -> None:
    record = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    scope = record["gate_a_scope"]
    assert scope["historical_product11_gate_a_result_may_substitute"] is False
    assert scope["search_engine_fallback_allowed"] is False
    assert scope["ad_hoc_transport_allowed"] is False
    assert scope["semantic_inspection_allowed"] is False
    assert "Freeze Gate A outcome" in record["next_step"]
