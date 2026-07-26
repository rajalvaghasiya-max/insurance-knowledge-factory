from __future__ import annotations
import argparse, json
from factory_core.canonical.canonical_authoritative_publisher import CanonicalAuthoritativePublisher

def main()->int:
 p=argparse.ArgumentParser(); p.add_argument('--repository-root',required=True); p.add_argument('--spec-path',required=True); p.add_argument('--artifact-output-path',required=True); p.add_argument('--receipt-output-path',required=True); a=p.parse_args()
 r=CanonicalAuthoritativePublisher().publish_from_spec_file(spec_path=a.spec_path,repository_root=a.repository_root)
 artifact,receipt=CanonicalAuthoritativePublisher().write_outputs(r,repository_root=a.repository_root,artifact_output_path=a.artifact_output_path,receipt_output_path=a.receipt_output_path)
 print(json.dumps({'publication_status':'authoritative','published_assertion_count':len(r.artifact['assertions']),'artifact_output_path':str(artifact),'receipt_output_path':str(receipt)},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
