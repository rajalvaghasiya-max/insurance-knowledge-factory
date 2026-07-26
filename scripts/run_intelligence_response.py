from scripts._orchestration_cli import emit, intelligence_adapters, parser, request_from_args
from insurance_intelligence.orchestration.service import run_intelligence_response

def main():
    args = parser("INTELLIGENCE_RESPONSE").parse_args()
    emit(run_intelligence_response(request=request_from_args(args, "INTELLIGENCE_RESPONSE"), adapters=intelligence_adapters()))
if __name__ == "__main__": main()
