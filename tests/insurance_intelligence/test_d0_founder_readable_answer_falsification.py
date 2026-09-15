from dataclasses import fields

from insurance_intelligence.contracts.response import ResponseAssemblerOutput


def test_raw_response_contract_exposes_d0_human_projection_boundary():
    """Freeze the pre-D0 fact: machine response != human presentation contract."""
    raw_fields = {item.name for item in fields(ResponseAssemblerOutput)}
    required_human_projection_boundary = {
        "human_answer",
        "human_meaning",
        "human_unknowns",
        "resolution_next_step",
        "provenance_panel",
    }
    assert required_human_projection_boundary <= raw_fields, (
        "D0 falsification: canonical ResponseAssemblerOutput is still a machine contract; "
        "it does not expose a separate generic human-answer/provenance projection with an "
        "actionable uncertainty-resolution step. Freeze this failure before renderer work."
    )
