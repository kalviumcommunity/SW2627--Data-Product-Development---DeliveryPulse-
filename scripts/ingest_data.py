from pathlib import Path
import json

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

CUSTOMERS_CSV = RAW_DIR / "customers.csv"
TRANSACTIONS_JSON = RAW_DIR / "transactions.json"
TRANSACTIONS_NESTED_JSON = RAW_DIR / "transactions_nested.json"


def ingest_csv(filepath, delimiter=',', encoding='utf-8', dtype_dict=None):
    """
    Load CSV file with explicit parameters documented.

    Args:
        filepath: Path to CSV file
        delimiter: Field delimiter (comma by default, but could be semicolon or tab)
        encoding: File encoding (UTF-8 standard, but may be latin-1 or cp1252)
        dtype_dict: Dictionary mapping column names to data types

    Returns:
        Pandas DataFrame with shape and column names confirmed
    """
    try:
        df = pd.read_csv(
            filepath,
            delimiter=delimiter,
            encoding=encoding,
            dtype=dtype_dict,
        )
        print(f"✓ CSV loaded: {filepath}")
        print(f"  Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"  Columns: {list(df.columns)}")
        return df
    except FileNotFoundError:
        print(f"Error: File not found - {filepath}")
        raise
    except UnicodeDecodeError:
        print(f"Encoding error: Could not decode with {encoding}")
        print("Try: latin-1, iso-8859-1, or cp1252")
        raise


def ingest_json(filepath, is_nested=False):
    """
    Load JSON file, handling nested structures by flattening them.

    Args:
        filepath: Path to JSON file
        is_nested: If True, flatten nested JSON structures into columns

    Returns:
        Pandas DataFrame with nested structures expanded
    """
    try:
        if is_nested:
            with open(filepath, "r", encoding="utf-8") as handle:
                payload = json.load(handle)

            df = pd.json_normalize(payload)
            print("✓ Nested JSON flattened to tabular format")
        else:
            df = pd.read_json(filepath)

        print(f"✓ JSON loaded: {filepath}")
        print(f"  Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"  Columns: {list(df.columns)}")
        return df
    except FileNotFoundError:
        print(f"Error: File not found - {filepath}")
        raise


def ingest_csv_with_fallback(filepath, delimiters=(',',), fallback_encodings=None):
    """
    Load CSV with fallback encodings if initial attempt fails.

    Tries multiple encodings and delimiters in sequence.
    """
    if fallback_encodings is None:
        fallback_encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']

    for delimiter in delimiters:
        for encoding in fallback_encodings:
            try:
                df = pd.read_csv(filepath, delimiter=delimiter, encoding=encoding)
                print(f"✓ Successfully loaded with delimiter='{delimiter}', encoding='{encoding}'")
                return df
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue

    raise ValueError(f"Could not load {filepath} with any encoding/delimiter combination")


def document_ingestion(df, source_file):
    """
    Print detailed ingestion report for audit trail.
    """
    print(f"\n{'='*60}")
    print(f"INGESTION REPORT: {source_file}")
    print(f"{'='*60}")
    print(f"Rows: {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")
    print("\nColumn Names & Data Types:")
    print(df.dtypes)
    print("\nNull Values Per Column:")
    print(df.isnull().sum())
    print("\nFirst 3 Rows:")
    print(df.head(3).to_string())
    print(f"{'='*60}\n")
    return df


def ensure_sample_inputs():
    """Create the sample raw inputs used by the ingestion demo if they are missing."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if not CUSTOMERS_CSV.exists():
        CUSTOMERS_CSV.write_text(
            "customer_id,name,email,signup_date\n"
            "1,Alice,alice@example.com,2025-01-15\n"
            "2,Bob,bob@example.com,2025-02-20\n"
            "3,Carol,carol@example.com,2025-03-10\n",
            encoding='utf-8',
        )

    if not TRANSACTIONS_JSON.exists():
        TRANSACTIONS_JSON.write_text(
            "[\n"
            "  {\"id\": 1, \"customer_id\": 1, \"amount\": 100, \"status\": \"completed\"},\n"
            "  {\"id\": 2, \"customer_id\": 2, \"amount\": 250, \"status\": \"pending\"},\n"
            "  {\"id\": 3, \"customer_id\": 1, \"amount\": 150, \"status\": \"completed\"}\n"
            "]\n",
            encoding='utf-8',
        )

    if not TRANSACTIONS_NESTED_JSON.exists():
        TRANSACTIONS_NESTED_JSON.write_text(
            "[\n"
            "  {\"id\": 1, \"customer\": {\"id\": 1, \"name\": \"Alice\"}, \"amount\": 100, \"status\": \"completed\"},\n"
            "  {\"id\": 2, \"customer\": {\"id\": 2, \"name\": \"Bob\"}, \"amount\": 250, \"status\": \"pending\"},\n"
            "  {\"id\": 3, \"customer\": {\"id\": 1, \"name\": \"Alice\"}, \"amount\": 150, \"status\": \"completed\"}\n"
            "]\n",
            encoding='utf-8',
        )


def main():
    """Run the multi-format ingestion demo end to end."""
    ensure_sample_inputs()

    print("Starting multi-format ingestion...\n")

    print("CSV parameters: delimiter=',' because the customer file is comma-separated; encoding='utf-8' because the sample source is standard UTF-8; dtype_dict=None so pandas can infer types.")
    csv_df = ingest_csv(
        CUSTOMERS_CSV,
        delimiter=',',
        encoding='utf-8',
    )
    document_ingestion(csv_df, CUSTOMERS_CSV.name)

    print("JSON flat example: is_nested=False reads the record array directly without expansion.")
    flat_json_df = ingest_json(
        TRANSACTIONS_JSON,
        is_nested=False,
    )
    document_ingestion(flat_json_df, TRANSACTIONS_JSON.name)

    print("JSON nested example: is_nested=True flattens nested dictionaries into dot-separated columns.")
    nested_json_df = ingest_json(
        TRANSACTIONS_NESTED_JSON,
        is_nested=True,
    )
    document_ingestion(nested_json_df, TRANSACTIONS_NESTED_JSON.name)

    csv_df.to_csv(PROCESSED_DIR / "customers_ingested.csv", index=False)
    flat_json_df.to_csv(PROCESSED_DIR / "transactions_ingested.csv", index=False)
    nested_json_df.to_csv(PROCESSED_DIR / "transactions_nested_ingested.csv", index=False)

    print("✓ All data ingested and saved to processed/")


if __name__ == "__main__":
    main()