from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError(f"{path} is not a dev36 live-result artifact")
    return data


def _cases_by_id(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for case in data["cases"]:
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("every case must have case_id")
        if case_id in cases:
            raise ValueError(f"duplicate case_id: {case_id}")
        if not isinstance(case.get("released_text"), str):
            raise ValueError(f"case {case_id} has no released_text")
        cases[case_id] = case
    return cases


def build_packet(before: dict[str, Any], after: dict[str, Any], *, seed: int) -> tuple[dict[str, Any], dict[str, Any]]:
    before_cases = _cases_by_id(before)
    after_cases = _cases_by_id(after)
    if set(before_cases) != set(after_cases):
        missing_after = sorted(set(before_cases) - set(after_cases))
        missing_before = sorted(set(after_cases) - set(before_cases))
        raise ValueError(f"case sets differ: missing_after={missing_after} missing_before={missing_before}")

    rng = random.Random(seed)
    packet_cases: list[dict[str, Any]] = []
    reveal_cases: list[dict[str, str]] = []

    for case_id in sorted(before_cases):
        b = before_cases[case_id]
        a = after_cases[case_id]
        if b.get("user_text") != a.get("user_text"):
            raise ValueError(f"user_text changed for {case_id}")
        after_is_a = bool(rng.getrandbits(1))
        answer_a = a["released_text"] if after_is_a else b["released_text"]
        answer_b = b["released_text"] if after_is_a else a["released_text"]
        packet_cases.append({
            "case_id": case_id,
            "conversation_id": a.get("conversation_id"),
            "turn_index": a.get("turn_index"),
            "concept_area": a.get("concept_area"),
            "user_text": a.get("user_text"),
            "answer_a": answer_a,
            "answer_b": answer_b,
            "score_answer_a": {"safety": None, "correctness": None, "usefulness": None, "clarity": None, "deferral": None},
            "score_answer_b": {"safety": None, "correctness": None, "usefulness": None, "clarity": None, "deferral": None},
            "scorer_notes": "",
        })
        reveal_cases.append({
            "case_id": case_id,
            "answer_a": "AFTER" if after_is_a else "BEFORE",
            "answer_b": "BEFORE" if after_is_a else "AFTER",
        })

    packet = {
        "schema_version": "1.0",
        "benchmark_id": "health-customer-v0-dev36-blind-ab-v1",
        "case_count": len(packet_cases),
        "scoring_rubric": "benchmarks/health_customer_v0/SCORING_RUBRIC.md",
        "instructions": "Score A and B independently. Do not infer which answer is newer. Fill Safety, Correctness, Usefulness, Clarity and Deferral only from the rubric.",
        "cases": packet_cases,
    }
    reveal = {
        "schema_version": "1.0",
        "benchmark_id": packet["benchmark_id"],
        "seed": seed,
        "case_count": len(reveal_cases),
        "cases": reveal_cases,
    }
    return packet, reveal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--packet-output", required=True, type=Path)
    parser.add_argument("--reveal-output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=4352026)
    args = parser.parse_args()

    before = _load(args.before)
    after = _load(args.after)
    packet, reveal = build_packet(before, after, seed=args.seed)
    reveal["before_sha256"] = _sha256(args.before)
    reveal["after_sha256"] = _sha256(args.after)

    args.packet_output.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.reveal_output.write_text(json.dumps(reveal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"cases={packet['case_count']}")
    print(f"packet={args.packet_output}")
    print(f"reveal={args.reveal_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
