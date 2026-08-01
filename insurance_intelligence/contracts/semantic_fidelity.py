"""Canonical semantic fidelity and human-review contracts for MO-022G.

These immutable contracts separate approved meaning from rendered language.  They
are provider-neutral and intentionally contain no text-matching heuristics.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class SemanticFidelityContractError(ValueError):
    """Raised when a semantic-fidelity contract violates an invariant."""


SemanticScalar = str | int | float | bool
SemanticValue = SemanticScalar | tuple[str, ...]


class SemanticKind(str, Enum):
    FACT = "FACT"
    TRIGGER = "TRIGGER"
    EFFECT = "EFFECT"
    EXCEPTION = "EXCEPTION"
    APPLICABILITY_SCOPE = "APPLICABILITY_SCOPE"
    LIMITATION = "LIMITATION"
    UNCERTAINTY = "UNCERTAINTY"
    EVIDENCE_REFERENCE = "EVIDENCE_REFERENCE"


class SemanticRiskTier(str, Enum):
    EXACT_VALUE = "EXACT_VALUE"
    RULE_LOGIC = "RULE_LOGIC"
    PRESENTATION = "PRESENTATION"


class SemanticComparisonStatus(str, Enum):
    MATCHED = "MATCHED"
    MISSING = "MISSING"
    SURPLUS = "SURPLUS"
    MISMATCHED = "MISMATCHED"
    UNRESOLVED = "UNRESOLVED"


class FidelityRoutingDecision(str, Enum):
    AUTO_APPROVED = "AUTO_APPROVED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    AUTO_REJECTED = "AUTO_REJECTED"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class CertificationStatus(str, Enum):
    CERTIFIED = "CERTIFIED"
    REVIEW_ONLY = "REVIEW_ONLY"
    SUSPENDED = "SUSPENDED"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SemanticFidelityContractError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(
    values: Iterable[str] | tuple[str, ...],
    field_name: str,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    if isinstance(values, str):
        raise SemanticFidelityContractError(f"{field_name} must be a sequence")
    result = tuple(_text(value, field_name) for value in values)
    if not allow_empty and not result:
        raise SemanticFidelityContractError(f"{field_name} must not be empty")
    if len(result) != len(set(result)):
        raise SemanticFidelityContractError(f"{field_name} must not contain duplicates")
    return result


def _score(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SemanticFidelityContractError(f"{field_name} must be numeric")
    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise SemanticFidelityContractError(f"{field_name} must be between 0 and 1")
    return result


def _semantic_value(value: object, field_name: str) -> SemanticValue:
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int, float)):
        if isinstance(value, str):
            return _text(value, field_name)
        return value
    if isinstance(value, tuple) and all(isinstance(item, str) and item.strip() for item in value):
        result = tuple(item.strip() for item in value)
        if len(result) != len(set(result)):
            raise SemanticFidelityContractError(f"{field_name} tuple must not contain duplicates")
        return result
    raise SemanticFidelityContractError(
        f"{field_name} must be a scalar or a tuple of non-empty strings"
    )


@dataclass(frozen=True, order=True)
class SemanticAttribute:
    name: str
    value: SemanticValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "name"))
        object.__setattr__(self, "value", _semantic_value(self.value, "value"))


@dataclass(frozen=True)
class CanonicalSemanticComponent:
    component_id: str
    kind: SemanticKind
    risk_tier: SemanticRiskTier
    attributes: tuple[SemanticAttribute, ...]
    evidence_ids: tuple[str, ...]
    required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_id", _text(self.component_id, "component_id"))
        if not isinstance(self.kind, SemanticKind):
            raise SemanticFidelityContractError("kind must be a SemanticKind")
        if not isinstance(self.risk_tier, SemanticRiskTier):
            raise SemanticFidelityContractError("risk_tier must be a SemanticRiskTier")
        if not isinstance(self.attributes, tuple) or not self.attributes:
            raise SemanticFidelityContractError("attributes must be a non-empty tuple")
        if not all(isinstance(item, SemanticAttribute) for item in self.attributes):
            raise SemanticFidelityContractError("attributes must contain SemanticAttribute values")
        names = tuple(item.name for item in self.attributes)
        if len(names) != len(set(names)):
            raise SemanticFidelityContractError("attribute names must be unique")
        object.__setattr__(self, "attributes", tuple(sorted(self.attributes)))
        object.__setattr__(
            self,
            "evidence_ids",
            _text_tuple(self.evidence_ids, "evidence_ids", allow_empty=False),
        )
        if not isinstance(self.required, bool):
            raise SemanticFidelityContractError("required must be boolean")


@dataclass(frozen=True)
class ExplanationSemanticContract:
    contract_id: str
    contract_version: str
    rule_family: str
    components: tuple[CanonicalSemanticComponent, ...]
    approved_finding_ids: tuple[str, ...]
    prohibited_operations: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in ("contract_id", "contract_version", "rule_family"):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if not isinstance(self.components, tuple) or not self.components:
            raise SemanticFidelityContractError("components must be a non-empty tuple")
        if not all(isinstance(item, CanonicalSemanticComponent) for item in self.components):
            raise SemanticFidelityContractError(
                "components must contain CanonicalSemanticComponent values"
            )
        ids = tuple(item.component_id for item in self.components)
        if len(ids) != len(set(ids)):
            raise SemanticFidelityContractError("component IDs must be unique")
        object.__setattr__(
            self,
            "approved_finding_ids",
            _text_tuple(self.approved_finding_ids, "approved_finding_ids", allow_empty=False),
        )
        object.__setattr__(
            self,
            "prohibited_operations",
            _text_tuple(self.prohibited_operations, "prohibited_operations", allow_empty=False),
        )


@dataclass(frozen=True)
class ReconstructedSemanticComponent:
    component_id: str
    kind: SemanticKind
    attributes: tuple[SemanticAttribute, ...]
    confidence: float
    extractor_ids: tuple[str, ...]
    extractor_agreement: float
    unresolved_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_id", _text(self.component_id, "component_id"))
        if not isinstance(self.kind, SemanticKind):
            raise SemanticFidelityContractError("kind must be a SemanticKind")
        if not isinstance(self.attributes, tuple):
            raise SemanticFidelityContractError("attributes must be a tuple")
        if not all(isinstance(item, SemanticAttribute) for item in self.attributes):
            raise SemanticFidelityContractError("attributes must contain SemanticAttribute values")
        names = tuple(item.name for item in self.attributes)
        if len(names) != len(set(names)):
            raise SemanticFidelityContractError("attribute names must be unique")
        object.__setattr__(self, "attributes", tuple(sorted(self.attributes)))
        object.__setattr__(self, "confidence", _score(self.confidence, "confidence"))
        object.__setattr__(
            self,
            "extractor_ids",
            _text_tuple(self.extractor_ids, "extractor_ids", allow_empty=False),
        )
        object.__setattr__(
            self,
            "extractor_agreement",
            _score(self.extractor_agreement, "extractor_agreement"),
        )
        object.__setattr__(
            self,
            "unresolved_reasons",
            _text_tuple(self.unresolved_reasons, "unresolved_reasons"),
        )


@dataclass(frozen=True)
class SemanticComponentComparison:
    component_id: str
    status: SemanticComparisonStatus
    risk_tier: SemanticRiskTier
    mismatch_codes: tuple[str, ...]
    expected_attributes: tuple[SemanticAttribute, ...]
    observed_attributes: tuple[SemanticAttribute, ...]
    confidence: float | None = None
    extractor_agreement: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_id", _text(self.component_id, "component_id"))
        if not isinstance(self.status, SemanticComparisonStatus):
            raise SemanticFidelityContractError("status must be a SemanticComparisonStatus")
        if not isinstance(self.risk_tier, SemanticRiskTier):
            raise SemanticFidelityContractError("risk_tier must be a SemanticRiskTier")
        object.__setattr__(
            self,
            "mismatch_codes",
            _text_tuple(self.mismatch_codes, "mismatch_codes"),
        )
        for field_name in ("expected_attributes", "observed_attributes"):
            value = getattr(self, field_name)
            if not isinstance(value, tuple) or not all(
                isinstance(item, SemanticAttribute) for item in value
            ):
                raise SemanticFidelityContractError(
                    f"{field_name} must contain SemanticAttribute values"
                )
            object.__setattr__(self, field_name, tuple(sorted(value)))
        if self.confidence is not None:
            object.__setattr__(self, "confidence", _score(self.confidence, "confidence"))
        if self.extractor_agreement is not None:
            object.__setattr__(
                self,
                "extractor_agreement",
                _score(self.extractor_agreement, "extractor_agreement"),
            )


@dataclass(frozen=True)
class SemanticFidelityReport:
    report_id: str
    contract_id: str
    comparisons: tuple[SemanticComponentComparison, ...]
    hard_failure_codes: tuple[str, ...]
    unresolved_component_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "report_id", _text(self.report_id, "report_id"))
        object.__setattr__(self, "contract_id", _text(self.contract_id, "contract_id"))
        if not isinstance(self.comparisons, tuple) or not self.comparisons:
            raise SemanticFidelityContractError("comparisons must be a non-empty tuple")
        if not all(isinstance(item, SemanticComponentComparison) for item in self.comparisons):
            raise SemanticFidelityContractError(
                "comparisons must contain SemanticComponentComparison values"
            )
        ids = tuple(item.component_id for item in self.comparisons)
        if len(ids) != len(set(ids)):
            raise SemanticFidelityContractError("comparison component IDs must be unique")
        object.__setattr__(
            self,
            "hard_failure_codes",
            _text_tuple(self.hard_failure_codes, "hard_failure_codes"),
        )
        object.__setattr__(
            self,
            "unresolved_component_ids",
            _text_tuple(self.unresolved_component_ids, "unresolved_component_ids"),
        )


@dataclass(frozen=True)
class RuleFamilyCertification:
    certification_id: str
    rule_family: str
    model_id: str
    prompt_version: str
    extractor_policy_id: str
    status: CertificationStatus

    def __post_init__(self) -> None:
        for field_name in (
            "certification_id",
            "rule_family",
            "model_id",
            "prompt_version",
            "extractor_policy_id",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if not isinstance(self.status, CertificationStatus):
            raise SemanticFidelityContractError("status must be a CertificationStatus")


@dataclass(frozen=True)
class FidelityRoutingPolicy:
    policy_id: str
    minimum_confidence: float
    minimum_extractor_agreement: float
    require_certified_rule_family: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _text(self.policy_id, "policy_id"))
        object.__setattr__(
            self,
            "minimum_confidence",
            _score(self.minimum_confidence, "minimum_confidence"),
        )
        object.__setattr__(
            self,
            "minimum_extractor_agreement",
            _score(self.minimum_extractor_agreement, "minimum_extractor_agreement"),
        )
        if not isinstance(self.require_certified_rule_family, bool):
            raise SemanticFidelityContractError(
                "require_certified_rule_family must be boolean"
            )


@dataclass(frozen=True)
class FidelityRoutingResult:
    routing_id: str
    decision: FidelityRoutingDecision
    reason_codes: tuple[str, ...]
    report_id: str
    certification_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "routing_id", _text(self.routing_id, "routing_id"))
        if not isinstance(self.decision, FidelityRoutingDecision):
            raise SemanticFidelityContractError("decision must be a FidelityRoutingDecision")
        object.__setattr__(
            self,
            "reason_codes",
            _text_tuple(self.reason_codes, "reason_codes", allow_empty=False),
        )
        object.__setattr__(self, "report_id", _text(self.report_id, "report_id"))
        if self.certification_id is not None:
            object.__setattr__(
                self,
                "certification_id",
                _text(self.certification_id, "certification_id"),
            )


@dataclass(frozen=True)
class HumanReviewPacket:
    review_packet_id: str
    contract_id: str
    report_id: str
    routing_id: str
    component_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in ("review_packet_id", "contract_id", "report_id", "routing_id"):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "component_ids",
            _text_tuple(self.component_ids, "component_ids", allow_empty=False),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _text_tuple(self.reason_codes, "reason_codes", allow_empty=False),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _text_tuple(self.evidence_ids, "evidence_ids", allow_empty=False),
        )
