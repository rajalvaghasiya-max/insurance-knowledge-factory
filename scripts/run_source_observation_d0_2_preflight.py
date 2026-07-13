"""P1.5d-0 D0.2 preflight for governed source-observation pilot records.

This runner is deliberately non-mutating. It reports whether the retained repository
artifacts are sufficient to build each D0.1 source-observation record truthfully.
"""
from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any


ASSESSMENT_PATH = "knowledge/factory/source_observation_pilots/p1_5d_0_d0_2_pilot_assessment.json"


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(root: Path, relative_path: str) -> dict[str, Any]:
    return json.loads((root / relative_path).read_text(encoding="utf-8"))


def evaluate(repository_root: str | Path) -> list[dict[str, Any]]:
    root = Path(repository_root)
    assessment = _load(root, ASSESSMENT_PATH)
    results: list[dict[str, Any]] = []

    for pilot in assessment["pilots"]:
        result = {
            "entity_id": pilot["entity_id"],
            "declared_status": pilot["status"],
            "record_buildable": False,
            "detail": None,
        }
        if pilot["status"] != "record_buildable_from_existing_governed_artifacts":
            result["detail"] = pilot["reason"]
            results.append(result)
            continue

        spec = _load(root, pilot["record_spec_path"])
        artifact = root / spec["observation"]["observed_pdf_path"]
        if not artifact.is_file():
            result["detail"] = (
                "Required immutable observed PDF is not present at "
                f"{spec['observation']['observed_pdf_path']}. "
                "The record must not be built until that retained artifact is restored."
            )
            results.append(result)
            continue

        actual_sha = _sha256(artifact)
        if actual_sha != spec["observation"]["observed_pdf_sha256"]:
            result["detail"] = "Observed PDF hash does not match the D0.2 record spec."
            results.append(result)
            continue

        result["record_buildable"] = True
        result["detail"] = "All D0.1 record inputs are present and hash-consistent."
        results.append(result)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight P1.5d-0 D0.2 pilot evidence.")
    parser.add_argument("--repository-root", required=True)
    args = parser.parse_args()

    results = evaluate(args.repository_root)
    print("=" * 70)
    print("P1.5d-0 D0.2 SOURCE OBSERVATION PREFLIGHT")
    print("=" * 70)
    for result in results:
        print(f"{result['entity_id']}")
        print(f"  declared status : {result['declared_status']}")
        print(f"  record buildable: {result['record_buildable']}")
        print(f"  detail          : {result['detail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
