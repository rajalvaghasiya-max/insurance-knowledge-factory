"""Cross-provider semantic fidelity using OpenAI and Google Gemini.

OpenAI renders once and performs extractor A. Gemini independently performs
extractor B over the same rendered text. Exact canonical agreement is computed
locally and the existing semantic fidelity gate remains authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Mapping

from insurance_intelligence.contracts.semantic_fidelity import (
    ExplanationSemanticContract,
    FidelityRoutingPolicy,
    RuleFamilyCertification,
)
from insurance_intelligence.llm.cached_openai_extractor import CachedOpenAIExtractor
from insurance_intelligence.llm.cached_openai_renderer import CachedOpenAIRenderer
from insurance_intelligence.llm.component_locked import build_component_locked_request
from insurance_intelligence.llm.gemini_semantic_extractor import (
    GeminiExtractionTrace,
    GeminiSemanticExtractor,
)
from insurance_intelligence.llm.governed_artifact_store import (
    FilesystemGovernedArtifactStore,
)
from insurance_intelligence.llm.openai_component_locked import (
    OpenAIComponentLockedError,
    OpenAIComponentLockedProvider,
    OpenAIStageTrace,
    _attribute_value_type,
    _canonical_values,
    _extractor_schema,
    _renderer_schema,
)
from insurance_intelligence.llm.openai_dual_extractor import (
    DualExtractorAgreement,
    _canonical_attributes,
)
from insurance_intelligence.llm.semantic_rendering_pipeline import (
    SemanticRenderingOutcome,
    evaluate_component_locked_rendering,
)


def _with_disagreement_reasons(
    outcome: SemanticRenderingOutcome,
    *,
    has_disagreement: bool,
) -> SemanticRenderingOutcome:
    if not has_disagreement:
        return outcome
    additions = {
        "LOW_EXTRACTOR_AGREEMENT",
        "SEMANTIC_EXTRACTION_UNRESOLVED",
        "SEMANTIC_PROOF_INCOMPLETE",
    }
    reasons = tuple(sorted(set(outcome.routing_result.reason_codes) | additions))
    routing = replace(outcome.routing_result, reason_codes=reasons)
    packet = outcome.human_review_packet
    if packet is not None:
        packet = replace(packet, reason_codes=reasons)
    return replace(outcome, routing_result=routing, human_review_packet=packet)


def _evidence_ids(contract: ExplanationSemanticContract) -> tuple[str, ...]:
    values = set(contract.approved_finding_ids)
    for component in contract.components:
        values.update(component.evidence_ids)
    return tuple(sorted(values))


def _fallback_binding(contract: ExplanationSemanticContract) -> dict[str, object]:
    return {
        "contract_id": contract.contract_id,
        "components": [
            {
                "component_id": component.component_id,
                "kind": component.kind.value,
            }
            for component in contract.components
        ],
    }


@dataclass(frozen=True)
class OpenAIGeminiCrossProviderResult:
    rendering_trace: OpenAIStageTrace
    openai_extractor_trace: OpenAIStageTrace
    gemini_extractor_trace: GeminiExtractionTrace
    agreements: tuple[DualExtractorAgreement, ...]
    outcome: SemanticRenderingOutcome
    renderer_cache_hit: bool = False
    renderer_cache_key: str | None = None
    openai_extractor_cache_hit: bool = False
    openai_extractor_cache_key: str | None = None
    artifact_store_root: str | None = None


@dataclass(frozen=True)
class OpenAIGeminiCrossProvider:
    openai: OpenAIComponentLockedProvider
    gemini: GeminiSemanticExtractor
    renderer_store: FilesystemGovernedArtifactStore | None = None
    extractor_store: FilesystemGovernedArtifactStore | None = None

    @classmethod
    def from_environment(
        cls,
        *,
        renderer_store: FilesystemGovernedArtifactStore | None = None,
        extractor_store: FilesystemGovernedArtifactStore | None = None,
    ) -> "OpenAIGeminiCrossProvider":
        return cls(
            openai=OpenAIComponentLockedProvider.from_environment(),
            gemini=GeminiSemanticExtractor.from_environment(),
            renderer_store=renderer_store,
            extractor_store=extractor_store,
        )

    def evaluate(
        self,
        contract: ExplanationSemanticContract,
        *,
        audience: str,
        reading_level: str,
        policy: FidelityRoutingPolicy,
        certification: RuleFamilyCertification | None,
        data_classification: str,
        cache_rule_family_version: str = "UNVERSIONED",
        cache_binding: Mapping[str, object] | None = None,
    ) -> OpenAIGeminiCrossProviderResult:
        request = build_component_locked_request(
            contract,
            audience=audience,
            reading_level=reading_level,
        )
        binding = cache_binding or _fallback_binding(contract)
        evidence_ids = _evidence_ids(contract)
        render_prompt = (
            "Simplify wording only. Do not add, remove, infer, generalise, narrow, or change "
            "any fact or semantic relationship. Return each requested component exactly once. "
            "For an exception component, explicitly name the rule or effect that the exception "
            "negates; do not use an unqualified phrase such as 'does not apply'.\n"
            f"REQUEST={request.canonical_payload}"
        )
        renderer_cache_hit = False
        renderer_cache_key: str | None = None
        openai_extractor_cache_hit = False
        openai_extractor_cache_key: str | None = None
        artifact_store_root: str | None = None
        renderer_schema = _renderer_schema(request)
        if self.renderer_store is None:
            rendering_trace, rendered = self.openai._call(
                model=self.openai.renderer_model,
                prompt=render_prompt,
                schema_name="component_locked_rendering",
                schema=renderer_schema,
                stage="RENDERING",
                prompt_version=self.openai.renderer_prompt_version,
                request_id=request.request_id,
            )
        else:
            cached = CachedOpenAIRenderer(
                provider=self.openai,
                store=self.renderer_store,
            ).render(
                prompt=render_prompt,
                schema_name="component_locked_rendering",
                schema=renderer_schema,
                request_id=request.request_id,
                contract_payload=request.canonical_payload,
                evidence_ids=evidence_ids,
                rule_family_id=contract.rule_family,
                rule_family_version=cache_rule_family_version,
                binding=binding,
                audience=audience,
                reading_level=reading_level,
                data_classification=data_classification,
            )
            rendering_trace = cached.trace
            rendered = cached.output
            renderer_cache_hit = cached.cache_hit
            renderer_cache_key = cached.cache_key
            artifact_store_root = str(self.renderer_store.root)
        rendered_components = rendered.get("components")
        if not isinstance(rendered_components, list):
            raise OpenAIComponentLockedError("renderer output is missing components")

        attribute_contracts = [
            {
                "component_id": instruction.component_id,
                "kind": instruction.kind.value,
                "attributes": [
                    {
                        "name": attribute.name,
                        "value_type": _attribute_value_type(attribute),
                        "allowed_values": list(_canonical_values(attribute.name)),
                    }
                    for attribute in instruction.attributes
                ],
            }
            for instruction in request.instructions
        ]
        extraction_input = {
            "contract_id": request.contract_id,
            "components": rendered_components,
            "attribute_contracts": attribute_contracts,
        }
        extraction_prompt = (
            "Independently reconstruct only literal semantics expressed in each rendered component. "
            "Return exactly the canonical attribute names. When allowed_values is non-empty, use "
            "one of those exact tokens and never a prose synonym. Infer solely from rendered text. "
            "If a value cannot be recovered literally, add an unresolved reason. Ignore and set "
            "extractor_agreement to 0 because agreement is computed externally.\n"
            f"INPUT={json.dumps(extraction_input, sort_keys=True, separators=(',', ':'))}"
        )
        schema = _extractor_schema(request)
        effective_extractor_store = self.extractor_store or self.renderer_store
        if effective_extractor_store is None:
            openai_trace, extracted_a = self.openai._call(
                model=self.openai.extractor_model,
                prompt=extraction_prompt,
                schema_name="component_semantic_extraction_openai",
                schema=schema,
                stage="EXTRACTION_OPENAI",
                prompt_version="semantic-extractor-v4-cross-provider-openai",
                request_id=request.request_id,
            )
        else:
            cached_extractor = CachedOpenAIExtractor(
                provider=self.openai,
                store=effective_extractor_store,
            ).extract(
                prompt=extraction_prompt,
                schema_name="component_semantic_extraction_openai",
                schema=schema,
                request_id=request.request_id,
                contract_payload=request.canonical_payload,
                rendered_components=rendered_components,
                evidence_ids=evidence_ids,
                rule_family_id=contract.rule_family,
                rule_family_version=cache_rule_family_version,
                binding=binding,
                audience=audience,
                reading_level=reading_level,
                data_classification=data_classification,
            )
            openai_trace = cached_extractor.trace
            extracted_a = cached_extractor.output
            openai_extractor_cache_hit = cached_extractor.cache_hit
            openai_extractor_cache_key = cached_extractor.cache_key
            if artifact_store_root is None:
                artifact_store_root = str(effective_extractor_store.root)

        gemini_trace, extracted_b = self.gemini.extract(
            prompt=extraction_prompt,
            schema=schema,
            request_id=request.request_id,
            data_classification=data_classification,
        )

        components_a = extracted_a.get("components")
        components_b = extracted_b.get("components")
        if not isinstance(components_a, list) or not isinstance(components_b, list):
            raise OpenAIComponentLockedError("cross-provider extractor output is missing components")
        by_id_a = {item.get("component_id"): item for item in components_a if isinstance(item, Mapping)}
        by_id_b = {item.get("component_id"): item for item in components_b if isinstance(item, Mapping)}
        rendered_by_id = {item.get("component_id"): item for item in rendered_components if isinstance(item, Mapping)}
        expected_ids = tuple(item.component_id for item in request.instructions)
        if set(by_id_a) != set(expected_ids) or set(by_id_b) != set(expected_ids):
            raise OpenAIComponentLockedError("both providers must return every component exactly once")

        agreements: list[DualExtractorAgreement] = []
        combined: list[dict[str, object]] = []
        for component_id in expected_ids:
            item_a = by_id_a[component_id]
            item_b = by_id_b[component_id]
            canonical_a = _canonical_attributes(item_a)
            canonical_b = _canonical_attributes(item_b)
            agreed = canonical_a == canonical_b
            agreements.append(DualExtractorAgreement(
                component_id=component_id,
                agreed=agreed,
                extractor_a_attributes=canonical_a,
                extractor_b_attributes=canonical_b,
            ))
            unresolved: list[str] = []
            for item in (item_a, item_b):
                values = item.get("unresolved_reasons")
                if isinstance(values, list):
                    unresolved.extend(str(value) for value in values)
            if not agreed:
                unresolved.append("OpenAI and Gemini produced different canonical semantics")
            confidence_values = [
                value for value in (item_a.get("confidence"), item_b.get("confidence"))
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            ]
            rendered_item = rendered_by_id[component_id]
            combined.append({
                "component_id": component_id,
                "kind": item_a.get("kind"),
                "text": rendered_item.get("text"),
                "reconstructed_attributes": item_a.get("reconstructed_attributes"),
                "confidence": min(confidence_values) if confidence_values else 0.0,
                "extractor_ids": [
                    "openai:semantic-extractor-v4-cross-provider-openai",
                    f"google:{self.gemini.prompt_version}",
                ],
                "extractor_agreement": 1.0 if agreed else 0.0,
                "unresolved_reasons": sorted(set(unresolved)),
            })

        outcome = evaluate_component_locked_rendering(
            contract,
            request,
            {"components": combined},
            policy,
            certification,
        )
        outcome = _with_disagreement_reasons(
            outcome,
            has_disagreement=any(not item.agreed for item in agreements),
        )
        return OpenAIGeminiCrossProviderResult(
            rendering_trace=rendering_trace,
            openai_extractor_trace=openai_trace,
            gemini_extractor_trace=gemini_trace,
            agreements=tuple(agreements),
            outcome=outcome,
            renderer_cache_hit=renderer_cache_hit,
            renderer_cache_key=renderer_cache_key,
            openai_extractor_cache_hit=openai_extractor_cache_hit,
            openai_extractor_cache_key=openai_extractor_cache_key,
            artifact_store_root=artifact_store_root,
        )


__all__ = ["OpenAIGeminiCrossProvider", "OpenAIGeminiCrossProviderResult"]
