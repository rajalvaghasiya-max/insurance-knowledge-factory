from __future__ import annotations

"""Safely enroll one declared product into the Health batch configuration."""

import argparse
import json
from pathlib import Path
from typing import Any

ENTITY_ID = "bajaj_allianz_general:health_guard"
CANDIDATE: dict[str, Any] = {
    "entity_id": ENTITY_ID,
    "insurer_id": "bajaj_allianz_general",
    "product_name": "Health Guard Policy",
    "source_urls": [
        "https://www.bajajgeneralinsurance.com/health-insurance-plans/health-guard-insurance-policy.html"
    ],
    "selection_reason": (
        "Second-product repeatability proof target; retained public policy wording, "
        "matching supporting documents, immutable raw-PDF hash, and governed official-source observation."
    ),
    "expected_document_types": [
        "policy_wording",
        "customer_information_sheet",
        "brochure",
    ],
}


class BatchCandidateEnrollmentError(ValueError):
    """Raised when the target batch configuration is unsafe to modify."""


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Health batch configuration not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BatchCandidateEnrollmentError(f"Invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise BatchCandidateEnrollmentError("Health batch configuration root must be an object")
    candidates = payload.get("candidate_products")
    if not isinstance(candidates, list):
        raise BatchCandidateEnrollmentError("candidate_products must be a JSON array")
    return payload


def _normalized(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "entity_id": candidate.get("entity_id"),
        "insurer_id": candidate.get("insurer_id"),
        "product_name": candidate.get("product_name"),
        "source_urls": candidate.get("source_urls"),
        "expected_document_types": candidate.get("expected_document_types"),
    }


def enroll(*, config_path: Path, write: bool) -> tuple[dict[str, Any], str]:
    payload = _load_json(config_path)
    candidates: list[Any] = payload["candidate_products"]
    matches = [
        item for item in candidates
        if isinstance(item, dict) and item.get("entity_id") == ENTITY_ID
    ]
    if len(matches) > 1:
        raise BatchCandidateEnrollmentError(
            f"Multiple {ENTITY_ID!r} declarations found; resolve manually before enrollment"
        )

    if matches:
        existing = matches[0]
        if _normalized(existing) != _normalized(CANDIDATE):
            raise BatchCandidateEnrollmentError(
                "Existing Health Guard declaration conflicts with the governed target contract. "
                f"Existing={_normalized(existing)!r}; expected={_normalized(CANDIDATE)!r}"
            )
        action = "verified_existing"
    else:
        candidates.append(CANDIDATE)
        candidates.sort(key=lambda item: str(item.get("entity_id", "")) if isinstance(item, dict) else "")
        action = "added"

    if write:
        config_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return payload, action


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely add or verify the Health Guard declared batch candidate."
    )
    parser.add_argument(
        "--config-path",
        default="registry/health_batch_pilot.json",
        help="Repository-relative or absolute batch configuration path.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate only; do not write the configuration.",
    )
    args = parser.parse_args()

    payload, action = enroll(config_path=Path(args.config_path), write=not args.check_only)
    print("=" * 70)
    print("HEALTH GUARD BATCH CANDIDATE ENROLLMENT")
    print("=" * 70)
    print(f"Action                 : {action}")
    print(f"Entity                 : {ENTITY_ID}")
    print(f"Candidate count        : {len(payload['candidate_products'])}")
    print(f"Configuration          : {Path(args.config_path)}")
    print("NOTE: configuration declaration only; no registry or evidence artifact changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
