from __future__ import annotations

import json

from insurance_intelligence.orchestration import guarded_star_comprehensive_pilot as guarded


def test_temporal_status_loader_accepts_governed_overlay_manifest_shape(tmp_path) -> None:
    overlay = tmp_path / "identity_overlay.json"
    overlay.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "identity_resolution": {
                            "temporal_status": "current_observed_reviewed"
                        }
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert guarded._load_temporal_status(overlay) == "current_observed_reviewed"


def test_reviewed_current_status_does_not_add_stale_currentness_limitation() -> None:
    sentinel = object()

    assert (
        guarded._apply_currentness_limitation(
            sentinel,
            temporal_status="current_observed_reviewed",
        )
        is sentinel
    )
