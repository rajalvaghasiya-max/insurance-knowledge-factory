"""
Usage:
    python -m life_intelligence_lab.scripts.replay_amfi_nav --snapshot <snapshot_dir> \\
        [--compare-to <prior_canonical_dir>] [--out-dir DIR]

Re-parses a saved raw snapshot with no internet access, writes a fresh
canonical output, and (if --compare-to is given) proves that it produces
byte-identical observations.jsonl / rejected.jsonl content -- i.e. the
same SHA-256 hashes -- as a prior run over the same snapshot.

Exit code is 0 only if parsing succeeds AND (when --compare-to is given)
the hashes match.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from life_intelligence_lab.canonical import SUMMARY_FILENAME, write_canonical_outputs
from life_intelligence_lab.downloader import DownloadFailedError, load_snapshot
from life_intelligence_lab.parser import parse_amfi_nav

DEFAULT_OUT_ROOT = "life_intelligence_lab/data/canonical_replay"


def _load_prior_hashes(prior_dir: str) -> dict:
    with open(os.path.join(prior_dir, SUMMARY_FILENAME), "r", encoding="utf-8") as fh:
        summary = json.load(fh)
    return {
        "observations_sha256": summary["observations_sha256"],
        "rejected_sha256": summary["rejected_sha256"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Deterministically replay a raw AMFI NAV snapshot offline.")
    parser.add_argument("--snapshot", required=True, help="Path to the snapshot directory (contains manifest.json)")
    parser.add_argument("--compare-to", default=None, help="Path to a prior canonical output dir to compare hashes against")
    parser.add_argument("--out-dir", default=None, help="Output directory (default: data/canonical_replay/<snapshot_id>)")
    args = parser.parse_args(argv)

    try:
        snapshot, raw_text = load_snapshot(args.snapshot)
    except (DownloadFailedError, ValueError, FileNotFoundError) as exc:
        print(f"REPLAY FAILED (could not load snapshot, no network attempted): {exc}", file=sys.stderr)
        return 1

    result = parse_amfi_nav(raw_text, snapshot)
    out_dir = args.out_dir or os.path.join(DEFAULT_OUT_ROOT, snapshot.snapshot_id)
    hashes = write_canonical_outputs(result, out_dir, run_label="replay")

    print("Replay complete (offline, no network access used).")
    print(f"  snapshot_id: {snapshot.snapshot_id}")
    print(f"  observations_sha256: {hashes['observations_sha256']}")
    print(f"  rejected_sha256: {hashes['rejected_sha256']}")

    if args.compare_to:
        prior = _load_prior_hashes(args.compare_to)
        obs_match = prior["observations_sha256"] == hashes["observations_sha256"]
        rej_match = prior["rejected_sha256"] == hashes["rejected_sha256"]
        if obs_match and rej_match:
            print("  DETERMINISTIC REPLAY: MATCH (hashes identical to prior run)")
            return 0
        else:
            print("  DETERMINISTIC REPLAY: MISMATCH", file=sys.stderr)
            print(f"    observations match: {obs_match}", file=sys.stderr)
            print(f"    rejected match: {rej_match}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
