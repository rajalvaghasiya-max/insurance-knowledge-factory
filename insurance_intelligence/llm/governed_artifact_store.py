"""Immutable, content-addressed storage for governed LLM stage artifacts."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Callable, Mapping


class GovernedArtifactStoreError(RuntimeError):
    """Raised when artifact identity or storage invariants are violated."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedArtifactStoreError(f"{field} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class GovernedArtifactIdentity:
    stage: str
    contract_hash: str
    evidence_hash: str
    rule_family_id: str
    rule_family_version: str
    binding_hash: str
    audience: str
    reading_level: str
    provider: str
    model: str
    prompt_version: str
    schema_version: str
    generation_config_hash: str
    data_classification: str

    def __post_init__(self) -> None:
        for field in self.__dataclass_fields__:
            object.__setattr__(self, field, _text(getattr(self, field), field))

    @property
    def cache_key(self) -> str:
        return _hash(asdict(self))


@dataclass(frozen=True)
class GovernedArtifactRecord:
    schema_version: str
    cache_key: str
    identity: GovernedArtifactIdentity
    raw_response: Mapping[str, object]
    parsed_output: Mapping[str, object]
    trace: Mapping[str, object]
    validation: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FilesystemGovernedArtifactStore:
    root: Path

    def _path(self, identity: GovernedArtifactIdentity) -> Path:
        return self.root / identity.stage.lower() / identity.cache_key[:2] / f"{identity.cache_key}.json"

    def load(self, identity: GovernedArtifactIdentity) -> GovernedArtifactRecord | None:
        path = self._path(identity)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        stored_identity = GovernedArtifactIdentity(**payload["identity"])
        if stored_identity != identity or payload.get("cache_key") != identity.cache_key:
            raise GovernedArtifactStoreError("stored artifact identity mismatch")
        return GovernedArtifactRecord(
            schema_version=payload["schema_version"],
            cache_key=payload["cache_key"],
            identity=stored_identity,
            raw_response=payload["raw_response"],
            parsed_output=payload["parsed_output"],
            trace=payload["trace"],
            validation=payload["validation"],
        )

    def save(self, record: GovernedArtifactRecord) -> Path:
        if record.cache_key != record.identity.cache_key:
            raise GovernedArtifactStoreError("record cache key does not match identity")
        path = self._path(record.identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(record.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        if path.exists():
            if path.read_text(encoding="utf-8") != encoded:
                raise GovernedArtifactStoreError("immutable artifact already exists with different content")
            return path
        path.write_text(encoded, encoding="utf-8")
        return path

    def get_or_execute(
        self,
        identity: GovernedArtifactIdentity,
        execute: Callable[[], GovernedArtifactRecord],
    ) -> tuple[GovernedArtifactRecord, bool]:
        cached = self.load(identity)
        if cached is not None:
            return cached, True
        record = execute()
        if record.identity != identity:
            raise GovernedArtifactStoreError("executor returned a different artifact identity")
        self.save(record)
        return record, False


__all__ = [
    "FilesystemGovernedArtifactStore",
    "GovernedArtifactIdentity",
    "GovernedArtifactRecord",
    "GovernedArtifactStoreError",
]
