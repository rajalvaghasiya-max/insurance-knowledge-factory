from scripts._orchestration_cli import emit, intelligence_adapters, knowledge_adapters, parser, request_from_args
from insurance_intelligence.orchestration.service import run_full_cycle_certification

def main():
    args = parser("FULL_CYCLE_CERTIFICATION").parse_args()
    emit(run_full_cycle_certification(request=request_from_args(args, "FULL_CYCLE_CERTIFICATION"), knowledge_adapters=knowledge_adapters(), intelligence_adapters=intelligence_adapters()))
if __name__ == "__main__": main()
