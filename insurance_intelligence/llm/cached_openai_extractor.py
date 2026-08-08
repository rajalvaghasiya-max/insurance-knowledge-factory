"""Cache-first adapter for governed OpenAI semantic extraction calls."""
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
class CachedOpenAIExtractorResult:
    trace: OpenAIStageTrace
    output: Mapping[str, object]
    cache_hit: bool
    cache_key: str


@dataclass(frozen=True)
class CachedOpenAIExtractor:
    provider: OpenAIComponentLockedProvider
    store: FilesystemGovernedArtifactStore
    prompt_version: str = "semantic-extractor-v4-cross-provider-openai"
    schema_version: str = "component-semantic-extraction-openai-schema-v1"

    def extract(
        self,
        *,
        prompt: str,
        schema_name: str,
        schema: Mapping[str, object],
        request_id: str,
        contract_payload: str,
        rendered_components: object,
        evidence_ids: tuple[str, ...],
        rule_family_id: str,
        rule_family_version: str,
        binding: Mapping[str, object],
        audience: str,
        reading_level: str,
        data_classification: str,
    ) -> CachedOpenAIExtractorResult:
        generation_config = {
            "reasoning_effort": "low",
            "max_output_tokens": 1800,
            "response_format": "json_schema_strict",
            "schema_name": schema_name,
        }
        identity = GovernedArtifactIdentity(
            stage="EXTRACTION_OPENAI",
            contract_hash=_hash(
                {
                    "contract_payload": contract_payload,
                    "rendered_components_hash": _hash(rendered_components),
                    "prompt_hash": _hash(prompt),
                }
            ),
            evidence_hash=_hash(sorted(evidence_ids)),
            rule_family_id=rule_family_id,
            rule_family_version=rule_family_version,
            binding_hash=_hash(binding),
            audience=audience,
            reading_level=reading_level,
            provider="openai",
            model=self.provider.extractor_model,
            prompt_version=self.prompt_version,
            schema_version=self.schema_version + ":" + _hash(schema),
            generation_config_hash=_hash(generation_config),
            data_classification=data_classification,
        )

        def _execute() -> GovernedArtifactRecord:
            trace, output = self.provider._call(
                model=self.provider.extractor_model,
                prompt=prompt,
                schema_name=schema_name,
                schema=schema,
                stage="EXTRACTION_OPENAI",
                prompt_version=self.prompt_version,
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
        return CachedOpenAIExtractorResult(
            trace=OpenAIStageTrace(**record.trace),
            output=record.parsed_output,
            cache_hit=cache_hit,
            cache_key=record.cache_key,
        )


__all__ = ["CachedOpenAIExtractor", "CachedOpenAIExtractorResult"]
