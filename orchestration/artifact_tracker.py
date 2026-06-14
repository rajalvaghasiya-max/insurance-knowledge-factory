from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


ARTIFACT_MANIFEST_PATH = BASE_DIR / "registry" / "artifact_manifest.json"
PIPELINE_MANIFEST_PATH = BASE_DIR / "registry" / "pipeline_manifest.json"


class ArtifactTracker:
    """
    Artifact Tracker v0.1

    Lightweight JSON-based tracker for:
    - artifact hashes
    - layer outputs
    - dependencies
    - selective rerun planning

    Later this can migrate to Postgres without changing agent business logic.
    """

    VERSION = "0.1"

    def __init__(self, artifact_manifest_path: Path | None = None, pipeline_manifest_path: Path | None = None):
        self.artifact_manifest_path = artifact_manifest_path or ARTIFACT_MANIFEST_PATH
        self.pipeline_manifest_path = pipeline_manifest_path or PIPELINE_MANIFEST_PATH
        self.artifact_manifest_path.parent.mkdir(parents=True, exist_ok=True)

        self.artifact_manifest = self.load_json(
            self.artifact_manifest_path,
            default={
                "schema_version": "0.1",
                "description": "Tracks generated artifacts, hashes, dependencies, and processing status for selective reruns.",
                "generated_at": self.utc_now(),
                "artifacts": [],
            },
        )

        self.pipeline_manifest = self.load_json(
            self.pipeline_manifest_path,
            default={"schema_version": "0.1", "layers": [], "rerun_rules": []},
        )

    def utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp_path.replace(path)

    def file_sha256(self, path: Path) -> str | None:
        if not path.exists() or not path.is_file():
            return None
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()

    def object_sha256(self, obj: Any) -> str:
        payload = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def register_artifact(
        self,
        *,
        artifact_id: str,
        entity_id: str,
        entity_type: str,
        layer: str,
        artifact_path: str | None = None,
        artifact_type: str = "json",
        input_hash: str | None = None,
        output_hash: str | None = None,
        depends_on: list[str] | None = None,
        agent_name: str | None = None,
        agent_version: str | None = None,
        status: str = "valid",
        metadata: dict | None = None,
    ) -> dict:
        if output_hash is None and artifact_path:
            output_hash = self.file_sha256(BASE_DIR / artifact_path)

        record = {
            "artifact_id": artifact_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "layer": layer,
            "artifact_type": artifact_type,
            "artifact_path": artifact_path,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "depends_on": depends_on or [],
            "agent_name": agent_name,
            "agent_version": agent_version,
            "status": status,
            "metadata": metadata or {},
            "updated_at": self.utc_now(),
        }

        artifacts = self.artifact_manifest.setdefault("artifacts", [])
        existing_index = None
        for idx, item in enumerate(artifacts):
            if item.get("artifact_id") == artifact_id:
                existing_index = idx
                break

        if existing_index is None:
            record["created_at"] = self.utc_now()
            artifacts.append(record)
        else:
            record["created_at"] = artifacts[existing_index].get("created_at", self.utc_now())
            artifacts[existing_index] = record

        self.save_json(self.artifact_manifest_path, self.artifact_manifest)
        return record

    def get_artifact(self, artifact_id: str) -> dict | None:
        for item in self.artifact_manifest.get("artifacts", []):
            if item.get("artifact_id") == artifact_id:
                return item
        return None

    def has_changed(self, *, artifact_id: str, new_output_hash: str | None = None, artifact_path: str | None = None) -> bool:
        existing = self.get_artifact(artifact_id)
        if existing is None:
            return True
        if new_output_hash is None and artifact_path:
            new_output_hash = self.file_sha256(BASE_DIR / artifact_path)
        return existing.get("output_hash") != new_output_hash

    def downstream_layers(self, changed_layer: str) -> list[str]:
        layers = self.pipeline_manifest.get("layers", [])
        ordered_layer_ids = [layer["layer_id"] for layer in layers]
        if changed_layer not in ordered_layer_ids:
            return [changed_layer]
        start = ordered_layer_ids.index(changed_layer)
        return ordered_layer_ids[start:]

    def plan_rerun(self, *, entity_id: str, changed_layer: str) -> dict:
        layers_to_rerun = self.downstream_layers(changed_layer)
        affected_artifacts = []
        for artifact in self.artifact_manifest.get("artifacts", []):
            if artifact.get("entity_id") == entity_id and artifact.get("layer") in layers_to_rerun:
                affected_artifacts.append(artifact.get("artifact_id"))

        return {
            "entity_id": entity_id,
            "changed_layer": changed_layer,
            "layers_to_rerun": layers_to_rerun,
            "affected_artifacts": affected_artifacts,
            "planned_at": self.utc_now(),
        }

    def mark_invalid_downstream(self, *, entity_id: str, changed_layer: str, reason: str) -> dict:
        plan = self.plan_rerun(entity_id=entity_id, changed_layer=changed_layer)
        layers_to_rerun = set(plan["layers_to_rerun"])

        for artifact in self.artifact_manifest.get("artifacts", []):
            if artifact.get("entity_id") == entity_id and artifact.get("layer") in layers_to_rerun:
                artifact["status"] = "stale"
                artifact["stale_reason"] = reason
                artifact["marked_stale_at"] = self.utc_now()

        self.save_json(self.artifact_manifest_path, self.artifact_manifest)
        return plan


def main():
    tracker = ArtifactTracker()
    print("=" * 70)
    print("ARTIFACT TRACKER SANITY CHECK")
    print("=" * 70)
    print(f"Artifact manifest : {tracker.artifact_manifest_path}")
    print(f"Pipeline manifest : {tracker.pipeline_manifest_path}")
    print(f"Artifacts tracked : {len(tracker.artifact_manifest.get('artifacts', []))}")
    print(f"Pipeline layers   : {len(tracker.pipeline_manifest.get('layers', []))}")
    print("=" * 70)


if __name__ == "__main__":
    main()
