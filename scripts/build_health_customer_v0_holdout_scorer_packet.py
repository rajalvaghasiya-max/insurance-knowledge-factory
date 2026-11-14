from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable


DEFAULT_INPUT = Path("health_customer_v0_independent_holdout_run_v1.json")
DEFAULT_OUTPUT = Path("health_customer_v0_independent_holdout_scorer_packet_v1.json")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_packet(run_path: Path) -> dict[str, object]:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    cases = run.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("run artifact must contain a non-empty cases list")

    scorer_cases: list[dict[str, object]] = []
    for raw_case in cases:
        if not isinstance(raw_case, dict):
            raise ValueError("case must be an object")
        scorer_cases.append(
            {
                "case_id": raw_case["case_id"],
                "conversation_id": raw_case["conversation_id"],
                "turn_index": raw_case["turn_index"],
                "prior_context_required": raw_case["prior_context_required"],
                "concept_area": raw_case["concept_area"],
                "user_text": raw_case["user_text"],
                "released_text": raw_case["released_text"],
                "reference": raw_case["reference"],
            }
        )

    return {
        "schema_version": "1.0",
        "benchmark_id": run["benchmark_id"],
        "benchmark_role": "HOLDOUT_SCORER_PACKET",
        "source_run_sha256": _sha256(run_path),
        "case_count": len(scorer_cases),
        "cases": scorer_cases,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(list(argv) if argv is not None else None)

    packet = build_packet(args.input)
    args.output.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "source_run_sha256": packet["source_run_sha256"],
                "output_path": str(args.output),
                "output_sha256": _sha256(args.output),
                "case_count": packet["case_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
