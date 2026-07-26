"""
Usage:
    python -m life_intelligence_lab.scripts.download_amfi_nav [--url URL] [--out-dir DIR]

Fetches the AMFI daily NAV flat file and writes it as an immutable raw
snapshot under --out-dir (default: life_intelligence_lab/data/snapshots).

This performs a live network request using the standard library only.
It does not parse NAV rows -- run parse_amfi_nav.py against the resulting
snapshot for that. See PROTOTYPE_REPORT.md for a note on network
reachability of the AMFI domain from restricted sandboxes.
"""

from __future__ import annotations

import argparse
import sys

from life_intelligence_lab.downloader import AMFI_NAV_URL, DownloadFailedError, download_amfi_nav

DEFAULT_OUT_DIR = "life_intelligence_lab/data/snapshots"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Download the AMFI daily NAV flat file.")
    parser.add_argument("--url", default=AMFI_NAV_URL, help="Source URL (default: official AMFI NAVAll.txt)")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Directory to write the raw snapshot under")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    args = parser.parse_args(argv)

    try:
        snapshot = download_amfi_nav(output_root=args.out_dir, url=args.url, timeout=args.timeout)
    except DownloadFailedError as exc:
        print(f"DOWNLOAD FAILED: {exc}", file=sys.stderr)
        print(f"  status: {exc.snapshot.status}", file=sys.stderr)
        print(f"  snapshot_id: {exc.snapshot.snapshot_id}", file=sys.stderr)
        print("  (failure manifest written for audit; no raw content persisted)", file=sys.stderr)
        return 1

    print("Download succeeded.")
    print(f"  snapshot_id: {snapshot.snapshot_id}")
    print(f"  raw_file_path: {snapshot.raw_file_path}")
    print(f"  raw_sha256: {snapshot.raw_sha256}")
    print(f"  retrieval_timestamp: {snapshot.retrieval_timestamp}")
    print(f"  Next: python -m life_intelligence_lab.scripts.parse_amfi_nav "
          f"--snapshot {args.out_dir}/{snapshot.snapshot_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
