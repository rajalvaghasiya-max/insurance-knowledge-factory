from scripts._orchestration_cli import emit, knowledge_adapters, parser, request_from_args
from insurance_intelligence.orchestration.service import run_knowledge_build

def main():
    args = parser("KNOWLEDGE_BUILD").parse_args()
    emit(run_knowledge_build(request=request_from_args(args, "KNOWLEDGE_BUILD"), adapters=knowledge_adapters()))
if __name__ == "__main__": main()
