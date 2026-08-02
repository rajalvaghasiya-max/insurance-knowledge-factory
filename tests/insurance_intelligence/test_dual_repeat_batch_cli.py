"""Regression coverage for the governed dual-extractor repeat-batch command."""
from __future__ import annotations


def test_dual_repeat_batch_imports_serializer() -> None:
    from scripts.run_mo_022g_star_copay_dual_extractor import result_payload
    from scripts.run_mo_022g_star_copay_dual_repeat_batch import main

    assert callable(result_payload)
    assert callable(main)
