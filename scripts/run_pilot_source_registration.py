from __future__ import annotations

import argparse
import json
from pathlib import Path

from factory_core.canonical.pilot_source_registration import PilotSourceRegistration


def main() -> int:
    parser = argparse.ArgumentParser(description="P2.5-F2 controlled pilot source registration")
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--registration-output-path", required=True)
    parser.add_argument("--extracted-text-output-path", required=True)
    args = parser.parse_args()

    runner = PilotSourceRegistration()
    result = runner.register_from_spec_file(spec_path=args.spec_path, repository_root=args.repository_root)
    registration_path, text_path = runner.write_outputs(
        result,
        repository_root=args.repository_root,
        registration_output_path=args.registration_output_path,
        extracted_text_output_path=args.extracted_text_output_path,
    )
    print(json.dumps({
        "registration_status": result.registration["registration_status"],
        "candidate_count": result.registration["evidence_review"]["candidate_count"],
        "registration_output_path": str(registration_path),
        "extracted_text_output_path": str(text_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
