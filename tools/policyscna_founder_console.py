"""Local founder console for exercising the current proven PolicyScna D0 runtime.

This is an evaluation harness, not a production frontend. It deliberately reuses the
existing D0 runtime composition from the regression harness so no second reasoning or
answer path is introduced.

Run from the repository root:

    python -m streamlit run tools/policyscna_founder_console.py

Current scope:
- free-form questions through the proven Star Comprehensive factual/PED runtime path;
- two frozen waiting-period scenarios used by the D0 acceptance work.

Unsupported questions are allowed to fail closed. No answer text is hardcoded here.
"""

from __future__ import annotations

import importlib.util
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import streamlit as st

from insurance_intelligence.orchestration.intelligence_adapters import (
    execute_intelligence_stage,
)
from insurance_intelligence.orchestration.real_response_assembly import (
    build_real_response_assembly_adapters,
)
from insurance_intelligence.response.human_answer import project_human_answer


ROOT = Path(__file__).resolve().parents[1]


def _load_harness(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load runtime harness: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FACTUAL = _load_harness(
    "policyscna_founder_factual",
    "tests/insurance_intelligence/test_real_response_assembly.py",
)
RESOLVED_WAITING = _load_harness(
    "policyscna_founder_resolved_waiting",
    "tests/insurance_intelligence/test_d0_resolved_waiting_period_human_answer_rerun.py",
)
BOUNDARY_WAITING = _load_harness(
    "policyscna_founder_boundary_waiting",
    "tests/insurance_intelligence/test_d0_exact_boundary_fail_closed_human_answer.py",
)


def _run(module, request):
    dependencies = module._dependencies(request)
    adapters = build_real_response_assembly_adapters(
        dependencies=dependencies,
        style_registry=module._styles(),
        response_registry=module._responses(),
    )

    prior = (request.knowledge_snapshot_id,)
    stages = []

    for sequence, adapter in enumerate(adapters, start=1):
        result = execute_intelligence_stage(
            request=request,
            adapter=adapter,
            sequence=sequence,
            input_ids=prior,
        )
        stages.append((result.stage, result.status))
        if result.status not in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"}:
            detail = (
                result.failure.message
                if result.failure is not None
                else "; ".join(result.limitations)
            )
            raise RuntimeError(f"{result.stage}: {detail}")
        prior = tuple(item.output_id for item in result.outputs)

    response = dependencies.store.get(
        f"{request.execution_id}:real:response_assembly"
    )
    return response, project_human_answer(response), tuple(stages)


def _run_frozen_factual():
    base = FACTUAL._request()
    request = replace(
        base,
        execution_id=f"founder-console-{uuid4().hex}",
    )
    return request, *_run(FACTUAL, request)


def _run_factual_question(question: str):
    base = FACTUAL._request()
    request = replace(
        base,
        execution_id=f"founder-console-{uuid4().hex}",
        question=question.strip(),
    )
    return request, *_run(FACTUAL, request)


def _run_resolved_waiting():
    base = RESOLVED_WAITING._request()
    request = replace(
        base,
        execution_id=f"founder-console-{uuid4().hex}",
    )
    return request, *_run(RESOLVED_WAITING, request)


def _run_boundary_waiting():
    base = BOUNDARY_WAITING._request()
    request = replace(
        base,
        execution_id=f"founder-console-{uuid4().hex}",
    )
    return request, *_run(BOUNDARY_WAITING, request)


def _render_answer(request, response, projection, stages):
    human = projection.human_view

    st.subheader("PolicyScna answer")
    st.write(human.answer)

    if human.meaning:
        st.markdown("**What this means**")
        for item in human.meaning:
            st.markdown(f"- {item}")

    if human.unknowns:
        st.markdown("**Important qualifications / unknowns**")
        for item in human.unknowns:
            st.markdown(f"- {item}")

    if human.next_step:
        st.markdown("**What you can do next**")
        st.write(human.next_step)

    with st.expander("Developer / provenance details"):
        st.write(
            {
                "execution_id": request.execution_id,
                "response_status": response.response_status,
                "source_response_id": projection.source_response_id,
                "stages": stages,
                "evidence_references": [
                    {
                        "reference_id": item.reference_id,
                        "reference_type": item.reference_type,
                        "source_id": item.source_id,
                        "label": item.label,
                        "locator": item.locator,
                    }
                    for item in projection.provenance_panel.evidence_references
                ],
                "response_trace_count": len(
                    projection.provenance_panel.response_trace
                ),
            }
        )


def _execute(run_callable):
    try:
        request, response, projection, stages = run_callable()
    except Exception as exc:  # founder harness: surface exact runtime failure
        st.error("PolicyScna could not produce a canonical response.")
        st.exception(exc)
        return
    _render_answer(request, response, projection, stages)


st.set_page_config(
    page_title="PolicyScna Founder Console",
    page_icon="🛡️",
    layout="centered",
)

st.title("PolicyScna — Founder Console")
st.caption(
    "Local evaluation harness over the current governed D0 runtime. "
    "This is not a consumer frontend."
)

st.warning(
    "This founder console currently exposes only the three frozen D0 scenarios. "
    "A general free-form Ask interface is not yet proven: equivalent paraphrases can "
    "fall out of the governed evidence-resolution lane. See Issue #296."
)

scenarios_tab, = st.tabs(["Proven D0 scenarios"])

with scenarios_tab:
    st.markdown(
        "These scenarios execute the same frozen requests/contexts used in the D0 "
        "regression suite. Their question and context are intentionally not editable."
    )

    st.markdown("### Case A — factual PED")
    st.code(
        "What is the PED waiting period in Star Comprehensive?",
        language=None,
    )
    if st.button(
        "Run Case A",
        use_container_width=True,
        key="factual_ped",
    ):
        _execute(_run_frozen_factual)

    st.divider()

    st.markdown("### Case B — resolved waiting-period scenario")
    st.code(
        "If I claim for an illness on 2026-01-15, will the initial waiting period apply?",
        language=None,
    )
    if st.button(
        "Run resolved scenario",
        use_container_width=True,
        key="resolved_waiting",
    ):
        _execute(_run_resolved_waiting)

    st.divider()

    st.markdown("### Case C — exact-boundary fail-closed scenario")
    st.code(
        "If I claim for an illness on 2026-01-31, will the initial waiting period apply?",
        language=None,
    )
    if st.button(
        "Run exact-boundary scenario",
        use_container_width=True,
        key="boundary_waiting",
    ):
        _execute(_run_boundary_waiting)
