"""Generic evidence-backed co-payment composition semantics.

The contract preserves whether a documented co-payment is an ordinary cost share or
an additional/cumulative cost share.  It intentionally does not calculate a combined
customer liability and does not infer what other cost shares apply.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class CopaymentCompositionError(ValueError):
    """Raised when co-payment composition wording is internally unsafe."""


class CopaymentCompositionType(str, Enum):
    STANDALONE = "STANDALONE"
    ADDITIVE = "ADDITIVE"
    CUMULATIVE = "CUMULATIVE"


@dataclass(frozen=True)
class CopaymentComposition:
    composition_type: CopaymentCompositionType
    source_phrase: str | None = None
    stacks_with_other_cost_sharing: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.composition_type, CopaymentCompositionType):
            raise CopaymentCompositionError("composition_type must be a CopaymentCompositionType")
        if self.composition_type is CopaymentCompositionType.STANDALONE:
            if self.source_phrase is not None or self.stacks_with_other_cost_sharing:
                raise CopaymentCompositionError(
                    "standalone composition cannot carry a stacking phrase or stacking authorization"
                )
        else:
            if not isinstance(self.source_phrase, str) or not self.source_phrase.strip():
                raise CopaymentCompositionError(
                    "additive/cumulative composition requires an evidence-backed source phrase"
                )
            if self.stacks_with_other_cost_sharing is not True:
                raise CopaymentCompositionError(
                    "additive/cumulative composition must preserve stacking semantics"
                )


_EXPLICIT_OTHER_COST_SHARE = (
    re.compile(
        r"(?:in addition|additional) to any other co-payment(?:\s*/\s*| or )deductible[^.;]*",
        re.I,
    ),
    re.compile(
        r"(?:in addition|additional) to any other (?:applicable )?co-payment or deductible[^.;]*",
        re.I,
    ),
)
_ADDITIVE_MODIFIER = re.compile(
    r"\badditional(?:\s+cumulative)?\s+(?:co-payment|copayment|co-pay)\b",
    re.I,
)
_CUMULATIVE_MODIFIER = re.compile(
    r"\b(?:additional\s+)?cumulative\s+(?:co-payment|copayment|co-pay)\b",
    re.I,
)


def _clean(value: str) -> str:
    return " ".join(value.strip().rstrip(" .;").split())


def _first_phrase(text: str, patterns: tuple[re.Pattern[str], ...]) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return _clean(match.group(0))
    return None


def resolve_copayment_composition(text: str) -> CopaymentComposition:
    """Resolve only composition semantics explicitly stated by governed evidence.

    ``additional`` and ``cumulative`` are treated as stacking modifiers.  The
    function does not identify the other cost share, calculate arithmetic, or infer
    policy-instance applicability.
    """
    if not isinstance(text, str) or not text.strip():
        raise CopaymentCompositionError("text must be non-empty")
    normalized = " ".join(text.split())

    explicit = _first_phrase(normalized, _EXPLICIT_OTHER_COST_SHARE)
    if explicit:
        return CopaymentComposition(
            composition_type=CopaymentCompositionType.ADDITIVE,
            source_phrase=explicit,
            stacks_with_other_cost_sharing=True,
        )

    cumulative = _CUMULATIVE_MODIFIER.search(normalized)
    if cumulative:
        return CopaymentComposition(
            composition_type=CopaymentCompositionType.CUMULATIVE,
            source_phrase=_clean(cumulative.group(0)),
            stacks_with_other_cost_sharing=True,
        )

    additive = _ADDITIVE_MODIFIER.search(normalized)
    if additive:
        return CopaymentComposition(
            composition_type=CopaymentCompositionType.ADDITIVE,
            source_phrase=_clean(additive.group(0)),
            stacks_with_other_cost_sharing=True,
        )

    return CopaymentComposition(composition_type=CopaymentCompositionType.STANDALONE)


__all__ = [
    "CopaymentComposition",
    "CopaymentCompositionError",
    "CopaymentCompositionType",
    "resolve_copayment_composition",
]
