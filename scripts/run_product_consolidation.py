from agents.product_consolidation_agent import ProductConsolidationAgent


def run_product_consolidation():
    agent = ProductConsolidationAgent()
    result = agent.consolidate_all()

    print()
    print("=" * 70)
    print("PRODUCT CONSOLIDATION SUMMARY")
    print("=" * 70)

    for key, value in result.items():
        print(f"{key}: {value}")

    print("=" * 70)


if __name__ == "__main__":
    run_product_consolidation()