from __future__ import annotations

import argparse
import json
from pathlib import Path

from factory_core.governance.acquisition_source_observation import (
    AcquisitionSourceObservationBridge,
)
from factory_core.governance.source_observation import SourceObservationRecord


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path, label: str) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"{label} was not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return payload


def select_download_observation(download_run: dict, observation_id: str) -> dict:
    items = download_run.get("items")
    if not isinstance(items, list):
        raise ValueError("download run must contain an items array")
    matches = [item for item in items if isinstance(item, dict) and item.get("observation_id") == observation_id]
    if len(matches) != 1:
        raise ValueError(
            f"observation_id {observation_id!r} must match exactly one download-run item; found {len(matches)}"
        )
    return matches[0]


def build_source_observation_from_acquisition(
    *,
    download_run_path: str | Path,
    observation_id: str,
    registration_path: str,
    output_path: str,
    repository_root: str | Path = REPOSITORY_ROOT,
    source_issued_label: str | None = None,
    effective_date_signal: str | None = None,
    version_signal: str | None = None,
) -> Path:
    root = Path(repository_root).resolve()
    run_path = Path(download_run_path)
    if not run_path.is_absolute():
        run_path = root / run_path
    run = _load_json(run_path, "download run")
    item = select_download_observation(run, observation_id)

    result = AcquisitionSourceObservationBridge().build(
        acquisition_result=item,
        registration_path=registration_path,
        repository_root=root,
        source_signals={
            "source_issued_label": source_issued_label,
            "effective_date_signal": effective_date_signal,
            "version_signal": version_signal,
        },
    )
    return SourceObservationRecord().write_output(
        result,
        repository_root=root,
        output_path=output_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bind one persisted PDF acquisition observation to an existing registered document version."
    )
    parser.add_argument("--download-run-path", required=True)
    parser.add_argument("--observation-id", required=True)
    parser.add_argument("--registration-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--source-issued-label")
    parser.add_argument("--effective-date-signal")
    parser.add_argument("--version-signal")
    args = parser.parse_args()

    output = build_source_observation_from_acquisition(
        download_run_path=args.download_run_path,
        observation_id=args.observation_id,
        registration_path=args.registration_path,
        output_path=args.output_path,
        source_issued_label=args.source_issued_label,
        effective_date_signal=args.effective_date_signal,
        version_signal=args.version_signal,
    )
    print(output)


if __name__ == "__main__":
    main()
