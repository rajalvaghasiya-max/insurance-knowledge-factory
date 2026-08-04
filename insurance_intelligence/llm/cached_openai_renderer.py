"""Cache-first adapter for governed OpenAI rendering calls."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Mapping

from insurance_intelligence.llm.governed_artifact_store import (
    FilesystemGovernedArtifactStore,
    GovernedArtifactIdentity,
    GovernedArtifactRecord,
)
from insurance_intelligence.llm.openai_component_locked import (
    OpenAIComponentLockedProvider,
    OpenAIStageTrace,
)


def _hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CachedOpenAIRendererResult:
    trace: OpenAIStageTrace
    output: Mapping[str, object]
    cache_hit: bool
    cache_key: str


@dataclass(frozen=True)
class CachedOpenAIRenderer:
    provider: OpenAIComponentLockedProvider
    store: FilesystemGovernedArtifactStore
    schema_version: str = "component-locked-renderer-schema-v1"

    def render(
        self,
        *,
        prompt: str,
        schema_name: str,
        schema: Mapping[str, object],
        request_id: str,
        contract_payload: str,
        evidence_ids: tuple[str, ...],
        rule_family_id: str,
        rule_family_version: str,
        binding: Mapping[str, object],
        audience: str,
        reading_level: str,
        data_classification: str,
    ) -> CachedOpenAIRendererResult:
        generation_config = {
            "reasoning_effort": "low",
            "max_output_tokens": 1800,
            "response_format": "json_schema_strict",
            "schema_name": schema_name,
            "prompt_hash": _hash(prompt),
        }
        identity = GovernedArtifactIdentity(
            stage="RENDERING",
            contract_hash=_hash(contract_payload),
            evidence_hash=_hash(sorted(evidence_ids)),
            rule_family_id=rule_family_id,
            rule_family_version=rule_family_version,
            binding_hash=_hash(binding),
            audience=audience,
            reading_level=reading_level,
            provider="openai",
            model=self.provider.renderer_model,
            prompt_version=self.provider.renderer_prompt_version,
            schema_version=self.schema_version + ":" + _hash(schema),
            generation_config_hash=_hash(generation_config),
            data_classification=data_classification,
        )

        def _execute() -> GovernedArtifactRecord:
            trace, output = self.provider._call(
                model=self.provider.renderer_model,
                prompt=prompt,
                schema_name=schema_name,
                schema=schema,
                stage="RENDERING",
                prompt_version=self.provider.renderer_prompt_version,
                request_id=request_id,
            )
            return GovernedArtifactRecord(
                schema_version="1.0",
                cache_key=identity.cache_key,
                identity=identity,
                raw_response={
                    "provider_response_id": trace.provider_response_id,
                    "canonical_output": trace.canonical_output,
                },
                parsed_output=dict(output),
                trace=asdict(trace),
                validation={"status": "STRUCTURED_OUTPUT_ACCEPTED"},
            )

        record, cache_hit = self.store.get_or_execute(identity, _execute)
        trace = OpenAIStageTrace(**record.trace)
        return CachedOpenAIRendererResult(
            trace=trace,
            output=record.parsed_output,
            cache_hit=cache_hit,
            cache_key=record.cache_key,
        )


__all__ = ["CachedOpenAIRenderer", "CachedOpenAIRendererResult"]
