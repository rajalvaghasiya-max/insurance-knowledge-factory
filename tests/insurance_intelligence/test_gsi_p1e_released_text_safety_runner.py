from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts import run_gsi_p1_released_text_safety_benchmark as runner


def test_pressure_pack_is_one_four_turn_conversation() -> None:
    assert len(runner.CASES) == 4
    assert [case_id for case_id, _ in runner.CASES] == [
        "p1e-payment-pressure-1",
        "p1e-payment-pressure-2",
        "p1e-payment-pressure-3",
        "p1e-payment-pressure-4",
    ]
    assert len({runner.CONVERSATION_ID}) == 1


def test_runner_does_not_embed_expected_released_text() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert '"released_text": released_text' in source
    assert "expected_released_text" not in source
    assert "insurer will pay" not in source.casefold()


@dataclass(frozen=True)
class _Conformance:
    outcome: str = "PASS"
    rendered_text: str = "Governed released text without a payment verdict."


@dataclass(frozen=True)
class _Response:
    response_id: str = "response-1"


@dataclass(frozen=True)
class _Result:
    request_id: str
    pilot_id: str = "pilot-1"
    released_response_id: str = "response-1"
    guard_status: str = "GUARDED"
    used_llm: bool = False
    render_conformance: _Conformance = _Conformance()
    response: _Response = _Response()


def test_capture_records_only_actual_render_conformance_text(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_pilot(**kwargs):
        return _Result(request_id=kwargs["request_id"])

    monkeypatch.setattr(runner, "run_guarded_star_comprehensive_copay_pilot", fake_pilot)
    item = runner._capture_case(
        case_id="case-1",
        question="ordinary pressure question",
        turn_index=3,
        repository_root=tmp_path,
    )

    assert item["released_text"] == "Governed released text without a payment verdict."
    assert item["exit_safety_outcome"] == "PASS"
    assert item["human_added_breach"] is False
    assert item["turn_index"] == 3
    assert item["release_provenance"]["render_conformance_outcome"] == "PASS"


def test_nonpass_render_outcome_is_invalid(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    @dataclass(frozen=True)
    class FailedResult(_Result):
        render_conformance: _Conformance = _Conformance(outcome="FAIL", rendered_text="unsafe")

    monkeypatch.setattr(
        runner,
        "run_guarded_star_comprehensive_copay_pilot",
        lambda **kwargs: FailedResult(request_id=kwargs["request_id"]),
    )

    with pytest.raises(runner.SafetyEvidenceError, match="Rendering Exit Safety outcome was not PASS"):
        runner._capture_case(
            case_id="case-1",
            question="ordinary pressure question",
            turn_index=1,
            repository_root=tmp_path,
        )
