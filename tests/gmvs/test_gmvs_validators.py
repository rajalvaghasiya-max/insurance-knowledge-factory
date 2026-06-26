from pathlib import Path

from knowledge_factory.gmvs.architecture_validator import validate_architecture
from knowledge_factory.gmvs.governance_validator import validate_governance
from knowledge_factory.gmvs.readiness_validator import validate_readiness
from knowledge_factory.gmvs.reuse_analyzer import analyze_reuse


def test_gmvs_validators_return_results():
    repo_root = Path.cwd()

    architecture = validate_architecture(repo_root)
    readiness = validate_readiness(repo_root, "copay")
    reuse = analyze_reuse(repo_root, "copay")
    governance = validate_governance(repo_root)

    assert architecture.name == "architecture"
    assert readiness.name == "readiness"
    assert reuse.name == "reuse"
    assert governance.name == "governance"