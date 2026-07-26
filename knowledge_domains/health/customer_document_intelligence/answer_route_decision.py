"""Deterministic answer routing for governed Health interpretation packets."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


class AnswerRouteDecisionError(ValueError):
    """Raised when an interpretation packet or route decision is invalid."""


class AnswerRouteDecisionEngine:
    VERSION = "1.0"
    SCHEMA_VERSION = "1.0"
    RECORD_TYPE = "health_answer_route_decision_v1"

    ANSWERABLE = "answerable_from_grounded_packet"
    CLARIFICATION = "clarification_required"
    NOT_ANSWERABLE = "not_answerable"
    BLOCKED = "blocked"

    ALLOWED_ROUTES = {
        ANSWERABLE,
        CLARIFICATION,
        NOT_ANSWERABLE,
        BLOCKED,
    }

    def decide(self, packet: Mapping[str, Any]) -> dict[str, Any]:
        self._validate_packet(packet)

        readiness = packet.get("answer_readiness")
        fact_status = packet["customer_fact_ref"].get("status")
        match_status = packet["understanding_match_ref"].get("status")

        if packet.get("customer_answer_state") != "not_created":
            route = self.BLOCKED
            reason = "interpretation_packet_customer_answer_state_is_not_pristine"
            allowed_scope = "none"
            required_clarifications: list[str] = []
        elif readiness == "grounded_but_not_answered":
            route = self.ANSWERABLE
            reason = "grounded_customer_fact_and_generic_understanding_available"
            allowed_scope = "customer_fact_plus_generic_explanation"
            required_clarifications = []
        elif fact_status == "ambiguous":
            route = self.CLARIFICATION
            reason = "multiple_customer_deductible_values_require_resolution"
            allowed_scope = "clarification_only"
            required_clarifications = [
                "Ask the user which deductible value applies to the relevant coverage or schedule entry."
            ]
        elif fact_status == "not_found":
            route = self.CLARIFICATION
            reason = "customer_deductible_not_found_in_supplied_document"
            allowed_scope = "clarification_only"
            required_clarifications = [
                "Ask the user to provide the policy schedule, endorsement, renewal notice, or quote page showing the selected deductible."
            ]
        elif fact_status == "blocked" or match_status == "asset_not_found":
            route = self.BLOCKED
            reason = "required_grounding_source_is_blocked_or_missing"
            allowed_scope = "none"
            required_clarifications = []
        else:
            route = self.NOT_ANSWERABLE
            reason = "interpretation_packet_is_not_grounded_for_customer_answer"
            allowed_scope = "generic_concept_only"
            required_clarifications = []

        decision = {
            "schema_version": self.SCHEMA_VERSION,
            "record_type": self.RECORD_TYPE,
            "contract_version": self.VERSION,
            "decision_id": self._decision_id(
                packet_id=str(packet["packet_id"]),
                route=route,
                reason=reason,
            ),
            "packet_id": packet["packet_id"],
            "concept_id": packet["concept_id"],
            "route": route,
            "route_reason": reason,
            "allowed_answer_scope": allowed_scope,
            "required_clarifications": required_clarifications,
            "blocked_claims": [
                "final_claim_payout",
                "claim_admissibility",
                "deductible_frequency_or_applicability_not_in_evidence",
                "product_suitability_or_recommendation",
                "guaranteed_insurer_payment",
            ],
            "source_refs": {
                "customer_fact_id": packet["customer_fact_ref"]["fact_id"],
                "customer_source_document_id": packet["customer_fact_ref"]["source_document_id"],
                "customer_source_sha256": packet["customer_fact_ref"]["source_sha256"],
                "understanding_match_id": packet["understanding_match_ref"]["match_id"],
                "understanding_asset_id": (
                    packet["generic_understanding_ref"]["understanding_asset_id"]
                    if isinstance(packet.get("generic_understanding_ref"), Mapping)
                    else None
                ),
            },
            "customer_answer_state": "not_created",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }
        self.validate(decision)
        return decision

    @classmethod
    def validate(cls, decision: Mapping[str, Any]) -> None:
        if not isinstance(decision, Mapping):
            raise AnswerRouteDecisionError("route decision must be an object")
        if decision.get("schema_version") != cls.SCHEMA_VERSION:
            raise AnswerRouteDecisionError("schema_version must be 1.0")
        if decision.get("record_type") != cls.RECORD_TYPE:
            raise AnswerRouteDecisionError("unsupported record_type")
        if decision.get("contract_version") != cls.VERSION:
            raise AnswerRouteDecisionError("unsupported contract_version")
        cls._require_prefixed(decision.get("decision_id"), "aroute_", "decision_id")
        cls._require_prefixed(decision.get("packet_id"), "ipacket_", "packet_id")
        if decision.get("concept_id") != "deductible":
            raise AnswerRouteDecisionError("concept_id must be deductible")
        if decision.get("route") not in cls.ALLOWED_ROUTES:
            raise AnswerRouteDecisionError("unsupported route")
        cls._require_nonempty(decision.get("route_reason"), "route_reason")
        cls._require_nonempty(
            decision.get("allowed_answer_scope"), "allowed_answer_scope"
        )

        clarifications = decision.get("required_clarifications")
        if not isinstance(clarifications, list) or not all(
            isinstance(item, str) and item.strip() for item in clarifications
        ):
            raise AnswerRouteDecisionError(
                "required_clarifications must be a list of non-empty strings"
            )

        blocked = decision.get("blocked_claims")
        if not isinstance(blocked, list) or not blocked:
            raise AnswerRouteDecisionError("blocked_claims must be a non-empty list")

        refs = decision.get("source_refs")
        if not isinstance(refs, Mapping):
            raise AnswerRouteDecisionError("source_refs must be an object")
        cls._require_prefixed(
            refs.get("customer_fact_id"), "cdfact_", "source_refs.customer_fact_id"
        )
        cls._require_nonempty(
            refs.get("customer_source_document_id"),
            "source_refs.customer_source_document_id",
        )
        cls._require_sha(
            refs.get("customer_source_sha256"),
            "source_refs.customer_source_sha256",
        )
        cls._require_prefixed(
            refs.get("understanding_match_id"),
            "cumatch_",
            "source_refs.understanding_match_id",
        )

        if decision["route"] == cls.ANSWERABLE:
            if decision.get("allowed_answer_scope") != (
                "customer_fact_plus_generic_explanation"
            ):
                raise AnswerRouteDecisionError(
                    "answerable route must allow customer fact plus generic explanation"
                )
            cls._require_prefixed(
                refs.get("understanding_asset_id"),
                "ua_",
                "source_refs.understanding_asset_id",
            )

        required_states = {
            "customer_answer_state": "not_created",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }
        for key, expected in required_states.items():
            if decision.get(key) != expected:
                raise AnswerRouteDecisionError(f"{key} must be {expected}")

    @staticmethod
    def _validate_packet(packet: Mapping[str, Any]) -> None:
        if not isinstance(packet, Mapping):
            raise AnswerRouteDecisionError("interpretation packet must be an object")
        if packet.get("packet_type") != (
            "health_customer_document_interpretation_packet_v1"
        ):
            raise AnswerRouteDecisionError("unsupported interpretation packet type")
        AnswerRouteDecisionEngine._require_prefixed(
            packet.get("packet_id"), "ipacket_", "packet_id"
        )
        if packet.get("concept_id") != "deductible":
            raise AnswerRouteDecisionError("packet concept_id must be deductible")
        if not isinstance(packet.get("customer_fact_ref"), Mapping):
            raise AnswerRouteDecisionError("customer_fact_ref must be an object")
        if not isinstance(packet.get("understanding_match_ref"), Mapping):
            raise AnswerRouteDecisionError(
                "understanding_match_ref must be an object"
            )

    @staticmethod
    def _decision_id(*, packet_id: str, route: str, reason: str) -> str:
        material = {"packet_id": packet_id, "route": route, "reason": reason}
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()[:20]
        return f"aroute_{digest}"

    @staticmethod
    def _require_nonempty(value: Any, name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise AnswerRouteDecisionError(f"{name} must be non-empty")

    @classmethod
    def _require_prefixed(cls, value: Any, prefix: str, name: str) -> None:
        cls._require_nonempty(value, name)
        if not value.startswith(prefix):
            raise AnswerRouteDecisionError(f"{name} must start with {prefix}")

    @staticmethod
    def _require_sha(value: Any, name: str) -> None:
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(ch not in "0123456789abcdef" for ch in value)
        ):
            raise AnswerRouteDecisionError(f"{name} must be lowercase SHA-256")
