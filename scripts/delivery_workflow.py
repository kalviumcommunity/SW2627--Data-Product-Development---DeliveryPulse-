from pathlib import Path
import logging

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = BASE_DIR / "data" / "raw" / "deliverypulse_raw.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "deliverypulse_processed.csv"
LOG_FILE = BASE_DIR / "data" / "processed" / "deliverypulse_workflow.log"
MIN_DELIVERY_MINUTES = 30
SLA_MINUTES = 45


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def create_sample_raw_data(path: Path = INPUT_FILE) -> pd.DataFrame:
    """Create a small synthetic delivery dataset for local demo runs."""
    path.parent.mkdir(parents=True, exist_ok=True)

    sample = pd.DataFrame(
        {
            "order_id": [101, 102, 103, 104, 105],
            "delivery_minutes": [28, 52, 41, 36, None],
            "distance_km": [3.2, 5.8, 4.1, 2.5, 6.0],
            "zone": ["North", "East", "North", "West", "East"],
            "rider_delay_minutes": [2, 14, 6, 4, 10],
        }
    )
    sample.to_csv(path, index=False)
    logging.info("Created sample input data at %s", path)
    return sample


def ingest_data(filepath: Path) -> pd.DataFrame:
    """Read delivery data from a CSV source and return it unchanged."""
    try:
        df = pd.read_csv(filepath)
        logging.info("Ingested %s rows from %s", len(df), filepath)
        return df
    except FileNotFoundError:
        logging.error("File not found: %s", filepath)
        raise


def process_data(df: pd.DataFrame, min_delivery_minutes: int = MIN_DELIVERY_MINUTES) -> pd.DataFrame:
    """Clean and transform delivery data without file I/O or side effects."""
    if df.empty:
        raise ValueError("Input DataFrame cannot be empty")

    processed = df.copy()
    processed = processed.drop_duplicates()
    processed["delivery_minutes"] = processed["delivery_minutes"].fillna(processed["delivery_minutes"].median())

    processed = processed[processed["delivery_minutes"] >= min_delivery_minutes]
    processed["sla_violation"] = processed["delivery_minutes"] > SLA_MINUTES
    processed["delay_bucket"] = pd.cut(
        processed["rider_delay_minutes"],
        bins=[-1, 5, 10, float("inf")],
        labels=["low", "medium", "high"],
    )

    logging.info("Processed %s rows into %s rows", len(df), len(processed))
    return processed


def output_results(df: pd.DataFrame, filepath: Path) -> Path:
    """Write processed results to a CSV destination and report success."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    logging.info("Output saved to %s", filepath)
    print(f"Processed {len(df)} records and saved to {filepath}")
    return filepath


def summarize_delay_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize which delay buckets have the highest SLA risk."""
    summary = (
        df.groupby("delay_bucket", observed=True)["sla_violation"]
        .mean()
        .reset_index()
        .rename(columns={"sla_violation": "sla_violation_rate"})
    )

    summary["sla_violation_rate"] = summary["sla_violation_rate"].round(2)
    return summary


def main(raw_path: Path = INPUT_FILE, output_path: Path = OUTPUT_FILE) -> Path:
    """Run the full delivery workflow with error handling."""
    try:
        if not raw_path.exists():
            create_sample_raw_data(raw_path)

        print("Starting delivery workflow...")
        data = ingest_data(raw_path)
        processed = process_data(data)
        saved_path = output_results(processed, output_path)

        print("Workflow completed successfully")
        print(summarize_delay_risk(processed).to_string(index=False))
        return saved_path
    except Exception:
        logging.exception("Workflow failed")
        raise


if __name__ == "__main__":
    main()