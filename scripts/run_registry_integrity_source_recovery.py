from __future__ import annotations
import argparse
from factory_core.canonical.registry_integrity_source_recovery import RegistryIntegrityAndPilotSourceRecovery

def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only registry integrity and canonical pilot-source recovery.")
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--report-path", required=True)
    args = parser.parse_args()
    runner = RegistryIntegrityAndPilotSourceRecovery()
    result = runner.analyze(repository_root=args.repository_root, document_id=args.document_id)
    output = runner.write_report(result, args.report_path)
    print("=" * 70)
    print("REGISTRY INTEGRITY & PILOT SOURCE RECOVERY")
    print("=" * 70)
    print(f"Document ID              : {result.report['document_id']}")
    print(f"Registry blockers        : {len(result.report['registry_blockers'])}")
    print(f"Reference candidates     : {len(result.report['explicit_document_reference_candidates'])}")
    print(f"Source asset candidates  : {len(result.report['explicit_source_asset_candidates'])}")
    print(f"Recovery status          : {result.report['source_recovery_status']}")
    print(f"Report                   : {output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
