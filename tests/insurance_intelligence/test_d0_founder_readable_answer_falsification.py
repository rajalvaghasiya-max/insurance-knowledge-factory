from importlib import import_module, util


def test_d0_requires_a_separate_generic_human_projection_boundary():
    """Freeze the pre-D0 fact: machine response != human presentation contract."""
    module_name = "insurance_intelligence.presentation.human_answer"
    spec = util.find_spec(module_name)
    assert spec is not None, (
        "D0 falsification: there is no separate generic human-answer projection boundary. "
        "Do not add human presentation fields to the canonical machine response; introduce "
        "a separate projector instead."
    )

    module = import_module(module_name)
    assert callable(getattr(module, "project_human_answer", None)), (
        "D0 falsification: the separate presentation boundary does not expose one generic "
        "project_human_answer path for all governed response cases."
    )
