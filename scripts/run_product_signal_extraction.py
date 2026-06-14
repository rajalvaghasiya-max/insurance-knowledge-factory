from agents.product_signal_extractor import ProductSignalExtractor
from config.settings import BASE_DIR


MAX_FILES = 20


def run_product_signal_extraction():
    extractor = ProductSignalExtractor()

    parsed_dir = BASE_DIR / "parsed" / "html_sections"

    if not parsed_dir.exists():
        print(f"Parsed directory not found: {parsed_dir}")
        return

    extracted = 0
    skipped = 0

    for insurer_folder in parsed_dir.iterdir():
        if not insurer_folder.is_dir():
            continue

        for parsed_file in insurer_folder.glob("*.json"):
            if extracted >= MAX_FILES:
                break

            try:
                result = extractor.extract_from_parsed_file(parsed_file)
                extracted += 1

                print(
                    f"✓ Extracted {result['insurer_id']} "
                    f"intent={result['page_intent']} "
                    f"products={result['product_names']} "
                    f"uins={result['uins']} "
                    f"benefits={result['benefits']} "
                    f"exclusions={result['exclusions']} "
                    f"waiting={result['waiting_periods']} "
                    f"si={result['sum_insured_values']} "
                    f"premium={result['premium_values']} "
                    f"benefit_amt={result['benefit_amount_values']} "
                    f"tax_amt={result['tax_amount_values']} "
                    f"discount={result['discount_values']}"
                )

            except Exception as error:
                skipped += 1
                print(f"✗ Failed {parsed_file}: {error}")

        if extracted >= MAX_FILES:
            break

    print()
    print("=" * 70)
    print("PRODUCT SIGNAL EXTRACTION SUMMARY")
    print("=" * 70)
    print(f"Extracted : {extracted}")
    print(f"Skipped   : {skipped}")
    print("=" * 70)


if __name__ == "__main__":
    run_product_signal_extraction()