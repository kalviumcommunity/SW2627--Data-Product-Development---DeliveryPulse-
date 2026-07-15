from datetime import datetime
from pathlib import Path
import json
import os

import chardet
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "output"
DEFAULT_INPUT_FILE = RAW_DIR / "sample.csv"
REPORT_FILE = OUTPUT_DIR / "intake_report.json"
EXPECTED_COLUMNS = ["customer_id", "customer_name", "transaction_amount", "transaction_date"]


def validate_file_exists(filepath):
    """Check if file exists and is non-empty."""
    if not os.path.exists(filepath):
        return False, f"File does not exist: {filepath}"

    if os.path.getsize(filepath) == 0:
        return False, f"File is empty: {filepath}"

    return True, "File exists and has content"


def validate_file_format(filepath, allowed_formats=None):
    """Check if file extension is supported."""
    if allowed_formats is None:
        allowed_formats = ["csv", "json", "xlsx"]

    extension = str(filepath).split(".")[-1].lower()

    if extension not in allowed_formats:
        return False, f"Unsupported format: {extension}. Allowed: {allowed_formats}"

    return True, f"Format valid: {extension}"


def validate_schema(df, expected_columns):
    """Validate that DataFrame has all expected columns."""
    missing = set(expected_columns) - set(df.columns)
    extra = set(df.columns) - set(expected_columns)

    issues = []
    if missing:
        issues.append(f"Missing columns: {missing}")
    if extra:
        issues.append(f"Unexpected columns: {extra}")

    if not issues:
        return True, f"Schema valid: {len(df.columns)} columns present"
    return False, " | ".join(issues)


def detect_encoding(filepath):
    """Detect file encoding with confidence."""
    with open(filepath, "rb") as handle:
        result = chardet.detect(handle.read(10000))

    encoding = result.get("encoding", "utf-8")
    confidence = result.get("confidence", 0)

    return encoding, f"Detected: {encoding} (confidence: {confidence:.1%})"


def capture_dataset_stats(filepath, df):
    """Log row count and file size."""
    file_size_bytes = os.path.getsize(filepath)
    file_size_mb = file_size_bytes / (1024 * 1024)

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "file_size_mb": round(file_size_mb, 5),
        "bytes": file_size_bytes,
    }


def generate_intake_report(filepath, expected_columns):
    """Generate complete intake validation report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "filepath": str(filepath),
        "validations": {},
    }

    file_exists, message = validate_file_exists(filepath)
    report["validations"]["file_exists"] = message
    if not file_exists:
        return report

    format_valid, message = validate_file_format(filepath)
    report["validations"]["format"] = message
    if not format_valid:
        return report

    df = pd.read_csv(filepath)

    schema_valid, message = validate_schema(df, expected_columns)
    report["validations"]["schema"] = message

    encoding, message = detect_encoding(filepath)
    report["validations"]["encoding"] = message
    report["validations"]["encoding_name"] = encoding

    report["statistics"] = capture_dataset_stats(filepath, df)
    report["schema_valid"] = schema_valid

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, default=str)

    return report


def ensure_sample_data(filepath=DEFAULT_INPUT_FILE):
    """Create the expected sample dataset if it does not already exist."""
    if filepath.exists():
        return filepath

    filepath.parent.mkdir(parents=True, exist_ok=True)
    sample = pd.DataFrame(
        [
            [1, "José Smith", 150.50, "2025-01-15"],
            [2, "Bob Johnson", 200.00, "2025-01-20"],
            [3, "Carol White", 75.25, "2025-02-01"],
        ],
        columns=EXPECTED_COLUMNS,
    )
    sample.to_csv(filepath, index=False)
    return filepath


def main():
    """Run intake validation against the sample dataset."""
    filepath = ensure_sample_data()
    report = generate_intake_report(filepath, EXPECTED_COLUMNS)
    print(json.dumps(report, indent=2, default=str))
    print(f"Validation report saved to {REPORT_FILE}")


if __name__ == "__main__":
    main()