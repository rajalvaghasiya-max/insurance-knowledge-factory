"""Single governed end-to-end runner for the deductible answer pilot."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from knowledge_domains.health.extraction_primitives.currency_sum_insured_parser import (
    CurrencySumInsuredParser,
)

from .answer_route_decision import AnswerRouteDecisionEngine
from .approved_content_bundle import ApprovedContentBundleAssembler
from .concept_understanding_matcher import ConceptUnderstandingMatcher
from .constrained_llm_verbalizer import ConstrainedLLMVerbalizer
from .deductible_customer_fact_selector import DeductibleCustomerFactSelector
from .draft_validation import DraftValidationEngine
from .interpretation_packet import InterpretationPacketAssembler
from .verbalizer_request import VerbalizerRequestAssembler


class EndToEndAnswerPipelineError(ValueError):
    """Raised when the governed pipeline cannot complete safely."""


class GovernedDeductibleAnswerPipeline:
    VERSION = "1.0"
    SCHEMA_VERSION = "1.0"
    DELIVERY_RECORD_TYPE = "health_customer_answer_delivery_artifact_v1"
    RUN_RECORD_TYPE = "health_governed_answer_pipeline_run_v1"

    def run(
        self,
        *,
        parsed_document: Mapping[str, Any],
        understanding_asset: Mapping[str, Any],
        llm_callable: Callable[[Mapping[str, Any]], str],
        provider_metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        candidate_document = CurrencySumInsuredParser().extract_from_parsed_document(
            parsed_document
        )
        customer_fact = DeductibleCustomerFactSelector().select(candidate_document)
        understanding_match = ConceptUnderstandingMatcher().match(
            customer_fact=customer_fact,
            understanding_asset=understanding_asset,
        )
        interpretation_packet = InterpretationPacketAssembler().assemble(
            customer_fact=customer_fact,
            understanding_match=understanding_match,
        )
        route_decision = AnswerRouteDecisionEngine().decide(
            interpretation_packet
        )
        content_bundle = ApprovedContentBundleAssembler().assemble(
            packet=interpretation_packet,
            route_decision=route_decision,
        )
        verbalizer_request = VerbalizerRequestAssembler().assemble(content_bundle)
        verbalized_draft = ConstrainedLLMVerbalizer().verbalize(
            request=verbalizer_request,
            llm_callable=llm_callable,
            provider_metadata=provider_metadata,
        )
        validation_result = DraftValidationEngine().validate_draft(
            bundle=content_bundle,
            request=verbalizer_request,
            draft=verbalized_draft,
        )
        delivery_artifact = self._delivery_artifact(
            customer_fact=customer_fact,
            understanding_match=understanding_match,
            interpretation_packet=interpretation_packet,
            route_decision=route_decision,
            content_bundle=content_bundle,
            verbalizer_request=verbalizer_request,
            verbalized_draft=verbalized_draft,
            validation_result=validation_result,
        )

        run = {
            "schema_version": self.SCHEMA_VERSION,
            "record_type": self.RUN_RECORD_TYPE,
            "pipeline_version": self.VERSION,
            "run_id": self._run_id(
                source_sha256=str(customer_fact["source"]["sha256"]),
                delivery_artifact_id=str(delivery_artifact["delivery_artifact_id"]),
            ),
            "status": (
                "completed_approved"
                if validation_result["validation_state"] == "approved"
                else "completed_not_deliverable"
            ),
            "source_document_id": customer_fact["source"]["source_document_id"],
            "source_sha256": customer_fact["source"]["sha256"],
            "artifacts": {
                "candidate_document": candidate_document,
                "customer_fact": customer_fact,
                "understanding_match": understanding_match,
                "interpretation_packet": interpretation_packet,
                "route_decision": route_decision,
                "approved_content_bundle": content_bundle,
                "verbalizer_request": verbalizer_request,
                "verbalized_draft": verbalized_draft,
                "validation_result": validation_result,
                "delivery_artifact": delivery_artifact,
            },
        }
        self.validate_run(run)
        return run

    def run_from_files(
        self,
        *,
        parsed_document_path: str | Path,
        understanding_asset_path: str | Path,
        llm_response_path: str | Path,
        provider_metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        parsed_document = json.loads(
            Path(parsed_document_path).read_text(encoding="utf-8")
        )
        understanding_asset = json.loads(
            Path(understanding_asset_path).read_text(encoding="utf-8")
        )
        response_path = Path(llm_response_path)

        def llm_callable(_: Mapping[str, Any]) -> str:
            return response_path.read_text(encoding="utf-8")

        return self.run(
            parsed_document=parsed_document,
            understanding_asset=understanding_asset,
            llm_callable=llm_callable,
            provider_metadata=provider_metadata,
        )

    @classmethod
    def _delivery_artifact(
        cls,
        *,
        customer_fact: Mapping[str, Any],
        understanding_match: Mapping[str, Any],
        interpretation_packet: Mapping[str, Any],
        route_decision: Mapping[str, Any],
        content_bundle: Mapping[str, Any],
        verbalizer_request: Mapping[str, Any],
        verbalized_draft: Mapping[str, Any],
        validation_result: Mapping[str, Any],
    ) -> dict[str, Any]:
        approved = validation_result["validation_state"] == "approved"
        artifact = {
            "schema_version": cls.SCHEMA_VERSION,
            "record_type": cls.DELIVERY_RECORD_TYPE,
            "delivery_artifact_id": cls._delivery_id(
                validation_id=str(validation_result["validation_id"]),
                validation_state=str(validation_result["validation_state"]),
            ),
            "concept_id": "deductible",
            "delivery_state": (
                "approved_for_delivery" if approved else "not_deliverable"
            ),
            "answer_text": (
                validation_result["validated_draft_text"] if approved else None
            ),
            "lineage": {
                "customer_fact_id": customer_fact["fact_id"],
                "customer_source_document_id": customer_fact["source"][
                    "source_document_id"
                ],
                "customer_source_sha256": customer_fact["source"]["sha256"],
                "understanding_match_id": understanding_match["match_id"],
                "understanding_asset_id": understanding_match[
                    "understanding_asset"
                ]["asset_id"],
                "interpretation_packet_id": interpretation_packet["packet_id"],
                "route_decision_id": route_decision["decision_id"],
                "approved_content_bundle_id": content_bundle["bundle_id"],
                "verbalizer_request_id": verbalizer_request["request_id"],
                "verbalized_draft_id": verbalized_draft["draft_id"],
                "validation_id": validation_result["validation_id"],
            },
            "validation_state": validation_result["validation_state"],
            "validation_findings": list(validation_result["findings"]),
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
            "guardrails": [
                "delivery_artifact_requires_approved_validation",
                "delivery_artifact_not_published",
                "delivery_artifact_not_entitlement_decision",
                "delivery_artifact_not_recommendation",
            ],
        }
        cls.validate_delivery_artifact(artifact)
        return artifact

    @classmethod
    def validate_delivery_artifact(cls, artifact: Mapping[str, Any]) -> None:
        if not isinstance(artifact, Mapping):
            raise EndToEndAnswerPipelineError(
                "delivery artifact must be an object"
            )
        if artifact.get("record_type") != cls.DELIVERY_RECORD_TYPE:
            raise EndToEndAnswerPipelineError(
                "unsupported delivery artifact record_type"
            )
        cls._require_prefixed(
            artifact.get("delivery_artifact_id"),
            "delivery_",
            "delivery_artifact_id",
        )
        if artifact.get("concept_id") != "deductible":
            raise EndToEndAnswerPipelineError(
                "delivery artifact concept_id must be deductible"
            )
        state = artifact.get("delivery_state")
        if state not in {"approved_for_delivery", "not_deliverable"}:
            raise EndToEndAnswerPipelineError("unsupported delivery_state")
        if state == "approved_for_delivery":
            if artifact.get("validation_state") != "approved":
                raise EndToEndAnswerPipelineError(
                    "deliverable artifact requires approved validation"
                )
            if not isinstance(artifact.get("answer_text"), str) or not artifact[
                "answer_text"
            ].strip():
                raise EndToEndAnswerPipelineError(
                    "deliverable artifact requires answer_text"
                )
        elif artifact.get("answer_text") is not None:
            raise EndToEndAnswerPipelineError(
                "non-deliverable artifact must not expose answer_text"
            )

        lineage = artifact.get("lineage")
        if not isinstance(lineage, Mapping):
            raise EndToEndAnswerPipelineError("lineage must be an object")
        prefixes = {
            "customer_fact_id": "cdfact_",
            "understanding_match_id": "cumatch_",
            "understanding_asset_id": "ua_",
            "interpretation_packet_id": "ipacket_",
            "route_decision_id": "aroute_",
            "approved_content_bundle_id": "acbundle_",
            "verbalizer_request_id": "vreq_",
            "verbalized_draft_id": "vdraft_",
            "validation_id": "vcheck_",
        }
        for key, prefix in prefixes.items():
            cls._require_prefixed(lineage.get(key), prefix, f"lineage.{key}")

        sha = lineage.get("customer_source_sha256")
        if (
            not isinstance(sha, str)
            or len(sha) != 64
            or any(ch not in "0123456789abcdef" for ch in sha)
        ):
            raise EndToEndAnswerPipelineError(
                "lineage.customer_source_sha256 must be lowercase SHA-256"
            )

        for key, expected in {
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }.items():
            if artifact.get(key) != expected:
                raise EndToEndAnswerPipelineError(f"{key} must be {expected}")

    @classmethod
    def validate_run(cls, run: Mapping[str, Any]) -> None:
        if not isinstance(run, Mapping):
            raise EndToEndAnswerPipelineError("pipeline run must be an object")
        if run.get("record_type") != cls.RUN_RECORD_TYPE:
            raise EndToEndAnswerPipelineError("unsupported run record_type")
        cls._require_prefixed(run.get("run_id"), "ansrun_", "run_id")
        if run.get("status") not in {
            "completed_approved",
            "completed_not_deliverable",
        }:
            raise EndToEndAnswerPipelineError("unsupported run status")
        artifacts = run.get("artifacts")
        if not isinstance(artifacts, Mapping):
            raise EndToEndAnswerPipelineError("artifacts must be an object")
        required = {
            "candidate_document",
            "customer_fact",
            "understanding_match",
            "interpretation_packet",
            "route_decision",
            "approved_content_bundle",
            "verbalizer_request",
            "verbalized_draft",
            "validation_result",
            "delivery_artifact",
        }
        if set(artifacts) != required:
            raise EndToEndAnswerPipelineError(
                "pipeline run must contain the complete governed artifact set"
            )
        cls.validate_delivery_artifact(artifacts["delivery_artifact"])

    @staticmethod
    def _delivery_id(*, validation_id: str, validation_state: str) -> str:
        material = {
            "validation_id": validation_id,
            "validation_state": validation_state,
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()[:20]
        return f"delivery_{digest}"

    @staticmethod
    def _run_id(*, source_sha256: str, delivery_artifact_id: str) -> str:
        material = {
            "source_sha256": source_sha256,
            "delivery_artifact_id": delivery_artifact_id,
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()[:20]
        return f"ansrun_{digest}"

    @staticmethod
    def _require_prefixed(value: Any, prefix: str, name: str) -> None:
        if not isinstance(value, str) or not value.startswith(prefix):
            raise EndToEndAnswerPipelineError(
                f"{name} must start with {prefix}"
            )
