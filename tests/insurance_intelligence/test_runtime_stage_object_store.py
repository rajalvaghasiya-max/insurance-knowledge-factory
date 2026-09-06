from __future__ import annotations

from dataclasses import dataclass

import pytest

from insurance_intelligence.orchestration.execution_state import (
    ExecutionStateError,
    RuntimeStageObjectStore,
)


@dataclass(frozen=True)
class ExampleStageOutput:
    value: str


def test_runtime_stage_object_store_preserves_typed_outputs_by_canonical_output_id():
    store = RuntimeStageObjectStore(execution_id="execution-1")
    output = ExampleStageOutput("intent-output")

    assert store.put(output_id="output:intent", value=output) == "output:intent"
    assert store.get("output:intent", expected_type=ExampleStageOutput) is output
    assert store.resolve(("output:intent",)) == (output,)
    assert store.output_ids() == ("output:intent",)


def test_runtime_stage_object_store_fails_closed_on_missing_duplicate_or_wrong_type():
    store = RuntimeStageObjectStore(execution_id="execution-1")
    output = ExampleStageOutput("context-output")
    store.put(output_id="output:context", value=output)

    with pytest.raises(ExecutionStateError, match="already registered"):
        store.put(output_id="output:context", value=ExampleStageOutput("replacement"))

    with pytest.raises(ExecutionStateError, match="not registered"):
        store.get("output:missing")

    with pytest.raises(ExecutionStateError, match="must be str"):
        store.get("output:context", expected_type=str)

    with pytest.raises(ExecutionStateError, match="input IDs must be unique"):
        store.resolve(("output:context", "output:context"))


def test_runtime_stage_object_store_is_execution_scoped_and_does_not_share_objects():
    first = RuntimeStageObjectStore(execution_id="execution-1")
    second = RuntimeStageObjectStore(execution_id="execution-2")
    first.put(output_id="output:reasoning", value=ExampleStageOutput("reasoning"))

    assert first.execution_id == "execution-1"
    assert second.execution_id == "execution-2"
    assert second.output_ids() == ()
    with pytest.raises(ExecutionStateError, match="not registered"):
        second.get("output:reasoning")
