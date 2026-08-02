"""Independent dual-extractor OpenAI path for MO-022G semantic fidelity.

The renderer runs once. Two extractor calls independently reconstruct canonical
semantics from the same rendered text. Agreement is computed deterministically;
models do not self-report agreement for certification gating.
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
from insurance_intelligence.llm.component_locked import build_component_locked_request
from insurance_intelligence.llm.openai_component_locked import (
    OpenAIComponentLockedError,
    OpenAIComponentLockedProvider,
    OpenAIStageTrace,
    _attribute_value_type,
    _extractor_schema,
    _renderer_schema,
)
from insurance_intelligence.llm.semantic_rendering_pipeline import (
    SemanticRenderingOutcome,
    evaluate_component_locked_rendering,
)


def _canonical_attributes(item: Mapping[str, object]) -> str:
    attributes = item.get("reconstructed_attributes")
    if not isinstance(attributes, list):
        raise OpenAIComponentLockedError("extractor reconstructed_attributes must be an array")
    normalized: list[dict[str, object]] = []
    for attribute in attributes:
        if not isinstance(attribute, Mapping):
            raise OpenAIComponentLockedError("extractor attribute must be an object")
        name = attribute.get("name")
        if not isinstance(name, str) or not name.strip():
            raise OpenAIComponentLockedError("extractor attribute name must be text")
        normalized.append({"name": name.strip(), "value": attribute.get("value")})
    normalized.sort(key=lambda value: value["name"])
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _preserve_disagreement_reason(
    outcome: SemanticRenderingOutcome,
    *,
    has_disagreement: bool,
) -> SemanticRenderingOutcome:
    """Expose the precise causes of an incomplete dual-extractor proof."""
    if not has_disagreement:
        return outcome
    reason_codes = tuple(
        sorted(
            set(outcome.routing_result.reason_codes)
            | {
                "LOW_EXTRACTOR_AGREEMENT",
                "SEMANTIC_EXTRACTION_UNRESOLVED",
            }
        )
    )
    routing_result = replace(outcome.routing_result, reason_codes=reason_codes)
    review_packet = outcome.human_review_packet
    if review_packet is not None:
        review_packet = replace(review_packet, reason_codes=reason_codes)
    return replace(
        outcome,
        routing_result=routing_result,
        human_review_packet=review_packet,
    )


@dataclass(frozen=True)
class DualExtractorAgreement:
    component_id: str
    agreed: bool
    extractor_a_attributes: str
    extractor_b_attributes: str


@dataclass(frozen=True)
class OpenAIDualExtractorResult:
    rendering_trace: OpenAIStageTrace
    extractor_a_trace: OpenAIStageTrace
    extractor_b_trace: OpenAIStageTrace
    agreements: tuple[DualExtractorAgreement, ...]
    outcome: SemanticRenderingOutcome


@dataclass(frozen=True)
class OpenAIDualExtractorProvider:
    provider: OpenAIComponentLockedProvider
    extractor_b_model: str | None = None
    extractor_b_prompt_version: str = "semantic-extractor-v3-independent-b"

    @classmethod
    def from_environment(cls) -> "OpenAIDualExtractorProvider":
        return cls(provider=OpenAIComponentLockedProvider.from_environment())

    def evaluate(
        self,
        contract: ExplanationSemanticContract,
        *,
        audience: str,
        reading_level: str,
        policy: FidelityRoutingPolicy,
        certification: RuleFamilyCertification | None,
    ) -> OpenAIDualExtractorResult:
        request = build_component_locked_request(
            contract,
            audience=audience,
            reading_level=reading_level,
        )
        render_prompt = (
            "Simplify wording only. Do not add, remove, infer, generalise, narrow, or change "
            "any fact or semantic relationship. Return each requested component exactly once. "
            "For an exception component, explicitly name the rule or effect that the exception "
            "negates; do not use an unqualified phrase such as 'does not apply'.\n"
            f"REQUEST={request.canonical_payload}"
        )
        rendering_trace, rendered = self.provider._call(
            model=self.provider.renderer_model,
            prompt=render_prompt,
            schema_name="component_locked_rendering",
            schema=_renderer_schema(request),
            stage="RENDERING",
            prompt_version=self.provider.renderer_prompt_version,
            request_id=request.request_id,
        )
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
            "Independently reconstruct only the literal semantics expressed in each rendered "
            "component. Do not use outside knowledge, expected values, another extractor output, "
            "or self-reported agreement. Return exactly the canonical attribute names and codec "
            "values permitted by attribute_contracts. Infer every value solely from the rendered "
            "text. If a value cannot be recovered literally, add an unresolved reason.\n"
            f"INPUT={json.dumps(extraction_input, sort_keys=True, separators=(',', ':'))}"
        )
        extractor_a_trace, extracted_a = self.provider._call(
            model=self.provider.extractor_model,
            prompt=extraction_prompt,
            schema_name="component_semantic_extraction_a",
            schema=_extractor_schema(request),
            stage="EXTRACTION_A",
            prompt_version=self.provider.extractor_prompt_version,
            request_id=request.request_id,
        )
        extractor_b_trace, extracted_b = self.provider._call(
            model=self.extractor_b_model or self.provider.extractor_model,
            prompt=extraction_prompt,
            schema_name="component_semantic_extraction_b",
            schema=_extractor_schema(request),
            stage="EXTRACTION_B",
            prompt_version=self.extractor_b_prompt_version,
            request_id=request.request_id,
        )
        components_a = extracted_a.get("components")
        components_b = extracted_b.get("components")
        if not isinstance(components_a, list) or not isinstance(components_b, list):
            raise OpenAIComponentLockedError("dual extractor output is missing components")

        by_id_a = {
            item.get("component_id"): item for item in components_a if isinstance(item, Mapping)
        }
        by_id_b = {
            item.get("component_id"): item for item in components_b if isinstance(item, Mapping)
        }
        rendered_by_id = {
            item.get("component_id"): item
            for item in rendered_components
            if isinstance(item, Mapping)
        }
        expected_ids = tuple(instruction.component_id for instruction in request.instructions)
        if set(by_id_a) != set(expected_ids) or set(by_id_b) != set(expected_ids):
            raise OpenAIComponentLockedError("dual extractors must return every component exactly once")

        agreements: list[DualExtractorAgreement] = []
        combined: list[dict[str, object]] = []
        for component_id in expected_ids:
            item_a = by_id_a[component_id]
            item_b = by_id_b[component_id]
            canonical_a = _canonical_attributes(item_a)
            canonical_b = _canonical_attributes(item_b)
            agreed = canonical_a == canonical_b
            agreements.append(
                DualExtractorAgreement(
                    component_id=component_id,
                    agreed=agreed,
                    extractor_a_attributes=canonical_a,
                    extractor_b_attributes=canonical_b,
                )
            )
            rendered_item = rendered_by_id.get(component_id)
            if not isinstance(rendered_item, Mapping):
                raise OpenAIComponentLockedError("renderer returned an unknown component")
            unresolved_a = item_a.get("unresolved_reasons")
            unresolved_b = item_b.get("unresolved_reasons")
            unresolved = []
            if isinstance(unresolved_a, list):
                unresolved.extend(str(value) for value in unresolved_a)
            if isinstance(unresolved_b, list):
                unresolved.extend(str(value) for value in unresolved_b)
            if not agreed:
                unresolved.append("Independent extractors produced different canonical semantics")
            confidence_values = [
                value
                for value in (item_a.get("confidence"), item_b.get("confidence"))
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            ]
            combined.append(
                {
                    "component_id": component_id,
                    "kind": item_a.get("kind"),
                    "text": rendered_item.get("text"),
                    "reconstructed_attributes": item_a.get("reconstructed_attributes"),
                    "confidence": min(confidence_values) if confidence_values else 0.0,
                    "extractor_ids": [
                        self.provider.extractor_prompt_version,
                        self.extractor_b_prompt_version,
                    ],
                    "extractor_agreement": 1.0 if agreed else 0.0,
                    "unresolved_reasons": sorted(set(unresolved)),
                }
            )

        outcome = evaluate_component_locked_rendering(
            contract,
            request,
            {"components": combined},
            policy,
            certification,
        )
        outcome = _preserve_disagreement_reason(
            outcome,
            has_disagreement=any(not item.agreed for item in agreements),
        )
        return OpenAIDualExtractorResult(
            rendering_trace=rendering_trace,
            extractor_a_trace=extractor_a_trace,
            extractor_b_trace=extractor_b_trace,
            agreements=tuple(agreements),
            outcome=outcome,
        )


__all__ = [
    "DualExtractorAgreement",
    "OpenAIDualExtractorProvider",
    "OpenAIDualExtractorResult",
]
