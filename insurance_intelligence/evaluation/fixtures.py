"""Deterministic end-to-end evaluation fixture builder for MO-021B."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from insurance_intelligence.contracts.evaluation import EvaluationScenario
from insurance_intelligence.evaluation.scenarios import EvaluationScenarioRegistry, build_default_registry


class EvaluationFixtureError(ValueError):
    """Raised when an evaluation fixture is invalid."""


FIXTURE_STATES = frozenset(
    {
        "GOVERNED",
        "FAILED_LINEAGE",
        "VERSION_UNRESOLVED",
        "MATERIAL_CONFLICT",
        "UNSUPPORTED_RECOMMENDATION",
    }
)
TRIGGER_STATES = frozenset({"UNSPECIFIED", "CONFIRMED", "DISPROVED"})
AUDIENCES = frozenset({"CUSTOMER", "ADVISOR", "INTERNAL_REVIEWER"})
STRICT_MODES = frozenset({"STRICT", "PERMISSIVE"})


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvaluationFixtureError(f"{label} must be a non-empty string")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise EvaluationFixtureError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


@dataclass(frozen=True)
class PipelineFixture:
    fixture_id: str
    scenario_id: str
    scenario_version: str
    request_id: str
    request_text: str
    domain: str
    topic: str
    audience: str
    strict_mode: str
    fixture_state: str
    trigger_state: str
    repository_roots: tuple[str, ...]
    approved_context: Mapping[str, object]
    stage_overrides: Mapping[str, object]
    repeat_count: int

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.scenario_id, self.scenario_version)


def build_fixture(
    scenario: EvaluationScenario,
    *,
    repository_roots: Iterable[str] = ("knowledge/factory/registry_backed",),
    strict_mode: str = "STRICT",
    fixture_state: str = "GOVERNED",
    trigger_state: str = "UNSPECIFIED",
    approved_context: Mapping[str, object] | None = None,
    stage_overrides: Mapping[str, object] | None = None,
    repeat_count: int = 1,
) -> PipelineFixture:
    if not isinstance(scenario, EvaluationScenario):
        raise EvaluationFixtureError("scenario must be an EvaluationScenario")
    roots = tuple(_text(root, "repository_roots[]") for root in repository_roots)
    if not roots:
        raise EvaluationFixtureError("repository_roots must not be empty")
    if len(roots) != len(set(roots)):
        raise EvaluationFixtureError("repository_roots must be unique")
    if isinstance(repeat_count, bool) or not isinstance(repeat_count, int) or repeat_count < 1:
        raise EvaluationFixtureError("repeat_count must be a positive integer")

    context = dict(scenario.input_context)
    context.update(dict(approved_context or {}))
    if trigger_state == "CONFIRMED":
        context["copayment_trigger_status"] = "CONFIRMED"
    elif trigger_state == "DISPROVED":
        context["copayment_trigger_status"] = "DISPROVED"
    else:
        context.pop("copayment_trigger_status", None)

    state = _member(fixture_state, FIXTURE_STATES, "fixture_state")
    context["fixture_state"] = state
    context["scenario_id"] = scenario.scenario_id
    context["scenario_version"] = scenario.scenario_version

    request_id = f"eval:{scenario.scenario_id}:{scenario.scenario_version}"
    return PipelineFixture(
        fixture_id=f"fixture:{scenario.scenario_id}:{scenario.scenario_version}",
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.scenario_version,
        request_id=request_id,
        request_text=scenario.request_text,
        domain=scenario.domain,
        topic=scenario.topic,
        audience=_member(scenario.audience, AUDIENCES, "audience"),
        strict_mode=_member(strict_mode, STRICT_MODES, "strict_mode"),
        fixture_state=state,
        trigger_state=_member(trigger_state, TRIGGER_STATES, "trigger_state"),
        repository_roots=roots,
        approved_context=MappingProxyType(context),
        stage_overrides=MappingProxyType(dict(stage_overrides or {})),
        repeat_count=repeat_count,
    )


class PipelineFixtureRegistry:
    def __init__(self, fixtures: Iterable[PipelineFixture] = ()) -> None:
        self._items: dict[tuple[str, str], PipelineFixture] = {}
        for fixture in fixtures:
            self.register(fixture)

    def register(self, fixture: PipelineFixture) -> None:
        if not isinstance(fixture, PipelineFixture):
            raise EvaluationFixtureError("fixture must be a PipelineFixture")
        if fixture.registry_key in self._items:
            raise EvaluationFixtureError(
                f"duplicate fixture registration: {fixture.scenario_id}@{fixture.scenario_version}"
            )
        self._items[fixture.registry_key] = fixture

    def all_fixtures(self) -> tuple[PipelineFixture, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: (item.scenario_id, item.scenario_version)))

    def get(self, scenario_id: str) -> PipelineFixture:
        matches = [item for item in self._items.values() if item.scenario_id == scenario_id]
        if not matches:
            raise EvaluationFixtureError(f"unknown scenario_id: {scenario_id}")
        return matches[0]


def build_default_fixtures(
    scenario_registry: EvaluationScenarioRegistry | None = None,
) -> tuple[PipelineFixture, ...]:
    registry = scenario_registry or build_default_registry()
    fixtures: list[PipelineFixture] = []
    for scenario in registry.all_scenarios():
        state = str(scenario.input_context.get("fixture_state", "GOVERNED"))
        trigger = str(scenario.input_context.get("copayment_trigger_status", "UNSPECIFIED"))
        repeat_count = 2 if scenario.scenario_kind == "DETERMINISM" else 1
        if scenario.scenario_kind == "UNSUPPORTED_REQUEST":
            state = "UNSUPPORTED_RECOMMENDATION"
        fixtures.append(
            build_fixture(
                scenario,
                fixture_state=state,
                trigger_state=trigger,
                approved_context=scenario.input_context,
                repeat_count=repeat_count,
            )
        )
    return tuple(fixtures)


def build_default_fixture_registry(
    scenario_registry: EvaluationScenarioRegistry | None = None,
) -> PipelineFixtureRegistry:
    return PipelineFixtureRegistry(build_default_fixtures(scenario_registry))
