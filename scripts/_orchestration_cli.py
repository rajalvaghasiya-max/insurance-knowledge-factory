"""Shared deterministic offline CLI helpers for MO-023E."""
from __future__ import annotations
import argparse
import json
from dataclasses import asdict

from insurance_intelligence.contracts.full_cycle import build_orchestration_request, build_product_scope
from insurance_intelligence.orchestration.intelligence_adapters import build_intelligence_stage_adapter, deterministic_fake_intelligence_capability
from insurance_intelligence.orchestration.knowledge_adapters import build_knowledge_stage_adapter, deterministic_fake_capability
from insurance_intelligence.contracts.full_cycle import KNOWLEDGE_BUILD_STAGE_ORDER, INTELLIGENCE_RESPONSE_STAGE_ORDER


def parser(mode: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--execution-id", required=True)
    p.add_argument("--domain", default="health")
    p.add_argument("--insurer", required=True)
    p.add_argument("--product", required=True)
    if mode in {"INTELLIGENCE_RESPONSE", "FULL_CYCLE_CERTIFICATION"}:
        p.add_argument("--question", required=True)
        p.add_argument("--audience", default="customer")
        p.add_argument("--disable-llm", action="store_true")
    if mode == "INTELLIGENCE_RESPONSE":
        p.add_argument("--knowledge-snapshot-id", required=True)
    return p


def request_from_args(args, mode: str):
    scope = build_product_scope(domain=args.domain, insurer_id=args.insurer, product_id=args.product)
    return build_orchestration_request(
        execution_id=args.execution_id,
        mode=mode,
        product_scope=scope,
        question=getattr(args, "question", None),
        audience=getattr(args, "audience", None),
        knowledge_snapshot_id=getattr(args, "knowledge_snapshot_id", None),
        force_refresh=mode == "KNOWLEDGE_REFRESH",
        allow_llm_rendering=not getattr(args, "disable_llm", False),
    )


def knowledge_adapters():
    return tuple(build_knowledge_stage_adapter(stage=s, capability=deterministic_fake_capability(output_type=f"{s.lower()}_output")) for s in KNOWLEDGE_BUILD_STAGE_ORDER)


def intelligence_adapters():
    return tuple(build_intelligence_stage_adapter(stage=s, capability=deterministic_fake_intelligence_capability(output_type=f"{s.lower()}_output")) for s in INTELLIGENCE_RESPONSE_STAGE_ORDER)


def emit(execution) -> None:
    print(json.dumps(asdict(execution.result), sort_keys=True, indent=2))
