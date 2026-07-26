"""
Usage:
    python -m life_intelligence_lab.scripts.parse_amfi_nav --snapshot <snapshot_dir> [--out-dir DIR]

Parses a previously-downloaded raw snapshot into canonical
FundNAVObservation records. Performs NO network access -- it only reads
the local snapshot directory produced by download_amfi_nav.py (or a hand
-constructed one, e.g. for offline test fixtures).
"""

from __future__ import annotations

import argparse
import os
import sys

from life_intelligence_lab.canonical import write_canonical_outputs
from life_intelligence_lab.downloader import DownloadFailedError, load_snapshot
from life_intelligence_lab.parser import parse_amfi_nav

DEFAULT_OUT_ROOT = "life_intelligence_lab/data/canonical"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Parse a raw AMFI NAV snapshot into canonical output.")
    parser.add_argument("--snapshot", required=True, help="Path to the snapshot directory (contains manifest.json)")
    parser.add_argument("--out-dir", default=None, help="Output directory (default: data/canonical/<snapshot_id>)")
    args = parser.parse_args(argv)

    try:
        snapshot, raw_text = load_snapshot(args.snapshot)
    except (DownloadFailedError, ValueError, FileNotFoundError) as exc:
        print(f"PARSE FAILED (could not load snapshot): {exc}", file=sys.stderr)
        return 1

    result = parse_amfi_nav(raw_text, snapshot)
    out_dir = args.out_dir or os.path.join(DEFAULT_OUT_ROOT, snapshot.snapshot_id)
    hashes = write_canonical_outputs(result, out_dir, run_label="parse")

    print("Parse complete.")
    print(f"  snapshot_id: {snapshot.snapshot_id}")
    print(f"  accepted: {result.summary['accepted_count']}")
    print(f"  rejected: {result.summary['rejected_count']}")
    if result.summary["rejected_by_reason"]:
        print("  rejected_by_reason:")
        for reason, count in result.summary["rejected_by_reason"].items():
            print(f"    {reason}: {count}")
    print(f"  observations_sha256: {hashes['observations_sha256']}")
    print(f"  rejected_sha256: {hashes['rejected_sha256']}")
    print(f"  output_dir: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
