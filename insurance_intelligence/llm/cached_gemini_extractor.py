"""Cache-first adapter for governed Gemini semantic extraction calls."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Mapping

from insurance_intelligence.llm.gemini_semantic_extractor import (
    GeminiExtractionTrace,
    GeminiSemanticExtractor,
    build_gemini_extraction_prompt,
    compile_gemini_schema,
)
from insurance_intelligence.llm.governed_artifact_store import (
    FilesystemGovernedArtifactStore,
    GovernedArtifactIdentity,
    GovernedArtifactRecord,
)


def _hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CachedGeminiExtractorResult:
    trace: GeminiExtractionTrace
    output: Mapping[str, object]
    cache_hit: bool
    cache_key: str


@dataclass(frozen=True)
class CachedGeminiExtractor:
    provider: GeminiSemanticExtractor
    store: FilesystemGovernedArtifactStore
    schema_version: str = "component-semantic-extraction-gemini-schema-v1"

    def extract(
        self,
        *,
        prompt: str,
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
    ) -> CachedGeminiExtractorResult:
        governed_prompt = build_gemini_extraction_prompt(prompt)
        compiled_schema = compile_gemini_schema(schema)
        generation_config = {
            "responseMimeType": "application/json",
            "responseSchemaHash": _hash(compiled_schema),
        }
        identity = GovernedArtifactIdentity(
            stage="EXTRACTION_GEMINI",
            contract_hash=_hash(
                {
                    "contract_payload": contract_payload,
                    "rendered_components_hash": _hash(rendered_components),
                    "governed_prompt_hash": _hash(governed_prompt),
                }
            ),
            evidence_hash=_hash(sorted(evidence_ids)),
            rule_family_id=rule_family_id,
            rule_family_version=rule_family_version,
            binding_hash=_hash(binding),
            audience=audience,
            reading_level=reading_level,
            provider="google",
            model=self.provider.model,
            prompt_version=self.provider.prompt_version,
            schema_version=self.schema_version + ":" + _hash(compiled_schema),
            generation_config_hash=_hash(generation_config),
            data_classification=data_classification,
        )

        def _execute() -> GovernedArtifactRecord:
            trace, output = self.provider.extract(
                prompt=prompt,
                schema=schema,
                request_id=request_id,
                data_classification=data_classification,
            )
            return GovernedArtifactRecord(
                schema_version="1.0",
                cache_key=identity.cache_key,
                identity=identity,
                raw_response={"canonical_output": trace.canonical_output},
                parsed_output=dict(output),
                trace=asdict(trace),
                validation={"status": "STRUCTURED_OUTPUT_ACCEPTED"},
            )

        record, cache_hit = self.store.get_or_execute(identity, _execute)
        return CachedGeminiExtractorResult(
            trace=GeminiExtractionTrace(**record.trace),
            output=record.parsed_output,
            cache_hit=cache_hit,
            cache_key=record.cache_key,
        )


__all__ = ["CachedGeminiExtractor", "CachedGeminiExtractorResult"]
