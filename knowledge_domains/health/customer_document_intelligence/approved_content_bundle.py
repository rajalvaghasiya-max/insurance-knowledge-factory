"""Approved content bundle for a constrained LLM verbalizer."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


class ApprovedContentBundleError(ValueError):
    """Raised when a route decision cannot produce a safe content bundle."""


class ApprovedContentBundleAssembler:
    VERSION = "1.0"
    SCHEMA_VERSION = "1.0"
    RECORD_TYPE = "health_approved_answer_content_bundle_v1"

    def assemble(
        self,
        *,
        packet: Mapping[str, Any],
        route_decision: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate_packet(packet)
        self._validate_route(route_decision)
        self._validate_cross_binding(packet, route_decision)

        route = route_decision["route"]
        if route == "answerable_from_grounded_packet":
            allowed_facts = self._allowed_facts(packet)
            required_caveats = [
                "The deductible amount is taken from the supplied customer document.",
                "The exact frequency, applicability, and claim treatment are not established by this packet.",
                "Claim admissibility and final insurer payment are not determined.",
            ]
            approved_example_refs = ["deductible_basic_claim_example_v1"]
            runtime_generation_allowed = True
            verbalizer_instruction = (
                "Explain only the approved facts in simple language. Preserve every "
                "required caveat. Do not add product mechanics, claim outcomes, or advice."
            )
        elif route == "clarification_required":
            allowed_facts = []
            required_caveats = []
            approved_example_refs = []
            runtime_generation_allowed = False
            verbalizer_instruction = (
                "Ask only the approved clarification questions. Do not explain a "
                "customer-specific deductible value."
            )
        else:
            allowed_facts = []
            required_caveats = []
            approved_example_refs = []
            runtime_generation_allowed = False
            verbalizer_instruction = (
                "Do not create a customer-specific answer. State that the available "
                "grounding is insufficient or blocked."
            )

        bundle = {
            "schema_version": self.SCHEMA_VERSION,
            "record_type": self.RECORD_TYPE,
            "contract_version": self.VERSION,
            "bundle_id": self._bundle_id(
                packet_id=str(packet["packet_id"]),
                route_decision_id=str(route_decision["decision_id"]),
                route=route,
            ),
            "packet_id": packet["packet_id"],
            "route_decision_id": route_decision["decision_id"],
            "concept_id": packet["concept_id"],
            "route": route,
            "target_audience": "insurance_consumer",
            "language": "en",
            "allowed_facts": allowed_facts,
            "required_caveats": required_caveats,
            "required_clarifications": list(
                route_decision.get("required_clarifications") or []
            ),
            "example_policy": {
                "mode": (
                    "approved_or_runtime_generated"
                    if runtime_generation_allowed
                    else "not_allowed"
                ),
                "approved_example_refs": approved_example_refs,
                "runtime_generation_allowed": runtime_generation_allowed,
                "runtime_constraints": [
                    "Clearly label every runtime example as an illustration.",
                    "Use only approved concept meaning and approved customer facts.",
                    "Do not present an illustration as the customer's actual claim outcome.",
                    "Do not imply guaranteed claim admissibility or insurer payment.",
                    "Do not invent per-claim, annual, benefit-specific, or product-specific mechanics.",
                    "Keep all arithmetic internally consistent.",
                ] if runtime_generation_allowed else [],
            },
            "blocked_claims": list(route_decision["blocked_claims"]),
            "source_refs": dict(route_decision["source_refs"]),
            "verbalizer_instruction": verbalizer_instruction,
            "llm_role": "verbalizer_not_source_of_insurance_truth",
            "customer_answer_state": "not_created",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }
        self.validate(bundle)
        return bundle

    @staticmethod
    def _allowed_facts(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
        value = packet["customer_fact_ref"]["normalized_value"]
        generic = packet["generic_understanding_ref"]
        return [
            {
                "fact_id": "customer_selected_deductible_value",
                "scope": "customer_specific",
                "statement": (
                    f"The supplied policy schedule shows a deductible of "
                    f"INR {int(value['value'])}."
                ),
                "structured_value": dict(value),
                "source_ref": packet["customer_fact_ref"]["fact_id"],
            },
            {
                "fact_id": "generic_deductible_meaning",
                "scope": "generic",
                "statement": (
                    "A deductible is an amount that applies before eligible insurer "
                    "benefits are considered, subject to the policy terms."
                ),
                "source_ref": generic["understanding_asset_id"],
            },
        ]

    @classmethod
    def validate(cls, bundle: Mapping[str, Any]) -> None:
        if not isinstance(bundle, Mapping):
            raise ApprovedContentBundleError("content bundle must be an object")
        if bundle.get("schema_version") != cls.SCHEMA_VERSION:
            raise ApprovedContentBundleError("schema_version must be 1.0")
        if bundle.get("record_type") != cls.RECORD_TYPE:
            raise ApprovedContentBundleError("unsupported record_type")
        if bundle.get("contract_version") != cls.VERSION:
            raise ApprovedContentBundleError("unsupported contract_version")
        cls._require_prefixed(bundle.get("bundle_id"), "acbundle_", "bundle_id")
        cls._require_prefixed(bundle.get("packet_id"), "ipacket_", "packet_id")
        cls._require_prefixed(
            bundle.get("route_decision_id"), "aroute_", "route_decision_id"
        )
        if bundle.get("concept_id") != "deductible":
            raise ApprovedContentBundleError("concept_id must be deductible")
        cls._require_nonempty(bundle.get("route"), "route")
        cls._require_nonempty(bundle.get("target_audience"), "target_audience")
        cls._require_nonempty(bundle.get("language"), "language")
        cls._require_nonempty(
            bundle.get("verbalizer_instruction"), "verbalizer_instruction"
        )
        if bundle.get("llm_role") != "verbalizer_not_source_of_insurance_truth":
            raise ApprovedContentBundleError("invalid llm_role")

        for key in (
            "allowed_facts",
            "required_caveats",
            "required_clarifications",
            "blocked_claims",
        ):
            if not isinstance(bundle.get(key), list):
                raise ApprovedContentBundleError(f"{key} must be a list")

        policy = bundle.get("example_policy")
        if not isinstance(policy, Mapping):
            raise ApprovedContentBundleError("example_policy must be an object")
        if policy.get("runtime_generation_allowed") is True:
            if policy.get("mode") != "approved_or_runtime_generated":
                raise ApprovedContentBundleError(
                    "runtime examples require approved_or_runtime_generated mode"
                )
            constraints = policy.get("runtime_constraints")
            if not isinstance(constraints, list) or not constraints:
                raise ApprovedContentBundleError(
                    "runtime examples require constraints"
                )

        if bundle["route"] == "answerable_from_grounded_packet":
            if len(bundle["allowed_facts"]) < 2:
                raise ApprovedContentBundleError(
                    "answerable bundle requires customer and generic facts"
                )
            scopes = {item.get("scope") for item in bundle["allowed_facts"]}
            if scopes != {"customer_specific", "generic"}:
                raise ApprovedContentBundleError(
                    "answerable bundle requires customer_specific and generic scopes"
                )
            if not bundle["required_caveats"]:
                raise ApprovedContentBundleError(
                    "answerable bundle requires caveats"
                )

        required_states = {
            "customer_answer_state": "not_created",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }
        for key, expected in required_states.items():
            if bundle.get(key) != expected:
                raise ApprovedContentBundleError(f"{key} must be {expected}")

    @staticmethod
    def _validate_cross_binding(
        packet: Mapping[str, Any],
        route: Mapping[str, Any],
    ) -> None:
        if route.get("packet_id") != packet.get("packet_id"):
            raise ApprovedContentBundleError("route decision packet_id mismatch")
        if route.get("concept_id") != packet.get("concept_id"):
            raise ApprovedContentBundleError("route decision concept_id mismatch")
        if (
            route.get("source_refs", {}).get("customer_fact_id")
            != packet.get("customer_fact_ref", {}).get("fact_id")
        ):
            raise ApprovedContentBundleError("customer fact binding mismatch")

    @staticmethod
    def _validate_packet(packet: Mapping[str, Any]) -> None:
        if not isinstance(packet, Mapping):
            raise ApprovedContentBundleError("packet must be an object")
        if packet.get("packet_type") != (
            "health_customer_document_interpretation_packet_v1"
        ):
            raise ApprovedContentBundleError("unsupported packet type")
        ApprovedContentBundleAssembler._require_prefixed(
            packet.get("packet_id"), "ipacket_", "packet_id"
        )

    @staticmethod
    def _validate_route(route: Mapping[str, Any]) -> None:
        if not isinstance(route, Mapping):
            raise ApprovedContentBundleError("route decision must be an object")
        if route.get("record_type") != "health_answer_route_decision_v1":
            raise ApprovedContentBundleError("unsupported route decision type")
        ApprovedContentBundleAssembler._require_prefixed(
            route.get("decision_id"), "aroute_", "decision_id"
        )

    @staticmethod
    def _bundle_id(
        *,
        packet_id: str,
        route_decision_id: str,
        route: str,
    ) -> str:
        material = {
            "packet_id": packet_id,
            "route_decision_id": route_decision_id,
            "route": route,
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()[:20]
        return f"acbundle_{digest}"

    @staticmethod
    def _require_nonempty(value: Any, name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ApprovedContentBundleError(f"{name} must be non-empty")

    @classmethod
    def _require_prefixed(cls, value: Any, prefix: str, name: str) -> None:
        cls._require_nonempty(value, name)
        if not value.startswith(prefix):
            raise ApprovedContentBundleError(f"{name} must start with {prefix}")
