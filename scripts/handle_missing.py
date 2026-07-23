"""Detect, treat, and document missing values for the DeliveryPulse datasets.

The delivery dataset has business-specific rules:
- order_id is a critical identifier and cannot be invented.
- delivery_minutes and distance_km are numeric measures; the median is used
  because operational measures can contain outliers.
- zone is categorical and is filled with its mode when required for reporting.
- rider_delay_minutes may be unavailable when attribution was not recorded, so
  it is deliberately left null rather than inventing a rider delay.

The functions are intentionally reusable so the same audit process can be used
for other DeliveryPulse input files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = BASE_DIR / "data" / "raw" / "deliverypulse_raw.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "deliverypulse_missing_handled.csv"
DECISIONS_FILE = BASE_DIR / "output" / "imputation_decisions.json"


def _existing_columns(df: pd.DataFrame, columns: Iterable[str]) -> list[str]:
    """Return requested columns that exist in the input, without duplicates."""
    return [column for column in dict.fromkeys(columns) if column in df.columns]


def analyze_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Compute null counts and percentages before treatment."""
    row_count = len(df)
    null_counts = df.isna().sum()
    missing_analysis = pd.DataFrame(
        {
            "column": df.columns,
            "null_count": null_counts.values,
            "null_percentage": (
                (null_counts / row_count * 100).round(2).values
                if row_count
                else np.zeros(len(df.columns))
            ),
            "data_type": df.dtypes.astype(str).values,
            "null_meaning": "",
        }
    )

    print("=" * 70)
    print("BEFORE IMPUTATION - Missing Value Analysis")
    print("=" * 70)
    print(missing_analysis.to_string(index=False))
    print(f"\nTotal rows: {len(df)}")
    print(f"Total cells: {df.size}")
    print(f"Missing cells: {int(null_counts.sum())}")
    print("=" * 70)
    return missing_analysis


def impute_mean_median(
    df: pd.DataFrame, numerical_cols: Iterable[str], strategy: str = "median"
) -> pd.DataFrame:
    """Fill numeric nulls with the mean or median of each column."""
    if strategy not in {"mean", "median"}:
        raise ValueError("strategy must be either 'mean' or 'median'")

    df_imputed = df.copy()
    for col in _existing_columns(df, numerical_cols):
        null_count = int(df_imputed[col].isna().sum())
        if not null_count:
            continue
        fill_value = getattr(df_imputed[col], strategy)()
        if pd.isna(fill_value):
            print(f"  - {col}: skipped because every value is null")
            continue
        df_imputed[f"{col}_was_imputed"] = df_imputed[col].isna()
        df_imputed[col] = df_imputed[col].fillna(fill_value)
        print(f"  OK {col}: filled {null_count} nulls with {strategy} ({fill_value:.2f})")
    return df_imputed


def impute_mode(df: pd.DataFrame, categorical_cols: Iterable[str]) -> pd.DataFrame:
    """Fill categorical nulls with the most common observed value."""
    df_imputed = df.copy()
    for col in _existing_columns(df, categorical_cols):
        null_count = int(df_imputed[col].isna().sum())
        if not null_count:
            continue
        modes = df_imputed[col].mode(dropna=True)
        if modes.empty:
            print(f"  - {col}: skipped because every value is null")
            continue
        mode_value = modes.iloc[0]
        df_imputed[f"{col}_was_imputed"] = df_imputed[col].isna()
        df_imputed[col] = df_imputed[col].fillna(mode_value)
        print(f"  OK {col}: filled {null_count} nulls with mode '{mode_value}'")
    return df_imputed


def impute_forward_fill(
    df: pd.DataFrame, time_series_cols: Iterable[str]
) -> pd.DataFrame:
    """Fill time-series nulls with the previous observed value."""
    df_imputed = df.copy()
    for col in _existing_columns(df, time_series_cols):
        null_count = int(df_imputed[col].isna().sum())
        if not null_count:
            continue
        df_imputed[f"{col}_was_imputed"] = df_imputed[col].isna()
        df_imputed[col] = df_imputed[col].ffill()
        remaining = int(df_imputed[col].isna().sum())
        print(f"  OK {col}: forward-filled {null_count - remaining} nulls")
        if remaining:
            print(f"    - {col}: {remaining} leading null(s) remain unresolved")
    return df_imputed


def drop_rows_with_nulls(df: pd.DataFrame, critical_cols: Iterable[str]) -> pd.DataFrame:
    """Drop rows where critical identifiers are null."""
    critical_cols = _existing_columns(df, critical_cols)
    if not critical_cols:
        return df.copy()
    rows_before = len(df)
    df_imputed = df.dropna(subset=critical_cols).copy()
    rows_dropped = rows_before - len(df_imputed)
    print(f"  OK Dropped {rows_dropped} rows with null in: {critical_cols}")
    return df_imputed


def document_imputation_decisions(
    df_original: pd.DataFrame,
    df_imputed: pd.DataFrame,
    output_path: Path = DECISIONS_FILE,
) -> dict[str, Any]:
    """Write an auditable, column-level record of each null-handling decision."""
    policies = {
        "order_id": {
            "column_type": "critical_identifier",
            "strategy": "drop_rows",
            "business_reasoning": "Order IDs are required to trace deliveries and must never be invented.",
            "risk_assessment": "Low when the affected row count is small; otherwise investigate the source system.",
        },
        "delivery_minutes": {
            "column_type": "numerical_measure",
            "strategy": "median_imputation",
            "business_reasoning": "The median represents a typical delivery and is resistant to unusually long deliveries that could skew the mean.",
            "risk_assessment": "Medium because the filled value is synthetic and must be excluded or flagged in sensitive KPI analysis.",
        },
        "distance_km": {
            "column_type": "numerical_measure",
            "strategy": "median_imputation",
            "business_reasoning": "Route distance is needed for route-efficiency analysis; the median limits the influence of unusually long routes.",
            "risk_assessment": "Medium; imputed distances are flagged for downstream users.",
        },
        "zone": {
            "column_type": "categorical_dimension",
            "strategy": "mode_imputation",
            "business_reasoning": "Zone is required for hotspot reporting; the most common observed zone is the least disruptive categorical fallback.",
            "risk_assessment": "Medium because an unknown order may not actually belong to the most common zone.",
        },
        "rider_delay_minutes": {
            "column_type": "nullable_operational_measure",
            "strategy": "leave_null",
            "business_reasoning": "A missing rider attribution means the cause was not recorded. Filling it would falsely assign responsibility and distort rider performance metrics.",
            "risk_assessment": "Low for data integrity; downstream rider metrics must report the unresolved count.",
        },
    }

    decisions: dict[str, Any] = {
        "dataset": INPUT_FILE.relative_to(BASE_DIR).as_posix(),
        "rows_before": len(df_original),
        "rows_after": len(df_imputed),
        "total_nulls_before": int(df_original.isna().sum().sum()),
        "total_nulls_after": int(df_imputed.isna().sum().sum()),
        "columns": {},
    }

    for column in df_original.columns:
        policy = policies.get(
            column,
            {
                "column_type": str(df_original[column].dtype),
                "strategy": "leave_null",
                "business_reasoning": "No project-specific imputation rule exists; preserve the missing value for review.",
                "risk_assessment": "Review before using this field in analysis.",
            },
        )
        entry = dict(policy)
        entry.update(
            {
                "null_count_before": int(df_original[column].isna().sum()),
                "null_count_after": int(df_imputed[column].isna().sum())
                if column in df_imputed
                else None,
            }
        )
        if column in df_imputed and column in {"delivery_minutes", "distance_km"}:
            entry["value_used"] = float(df_original[column].median()) if not df_original[column].dropna().empty else None
        if column == "zone" and not df_original[column].mode(dropna=True).empty:
            entry["value_used"] = str(df_original[column].mode(dropna=True).iloc[0])
        if column == "order_id":
            entry["rows_affected"] = int(df_original[column].isna().sum())
        decisions["columns"][column] = entry

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(decisions, indent=2, default=str), encoding="utf-8")
    return decisions


def validate_imputation(df_original: pd.DataFrame, df_imputed: pd.DataFrame) -> pd.DataFrame:
    """Compare before-and-after row counts and null metrics."""
    row_count = len(df_imputed)
    missing_after = pd.DataFrame(
        {
            "column": df_imputed.columns,
            "null_count_after": df_imputed.isna().sum().values,
            "null_percentage_after": (
                (df_imputed.isna().sum() / row_count * 100).round(2).values
                if row_count
                else np.zeros(len(df_imputed.columns))
            ),
        }
    )

    print("\n" + "=" * 70)
    print("AFTER IMPUTATION - Validation Report")
    print("=" * 70)
    print(f"Total rows before: {len(df_original)}")
    print(f"Total rows after:  {len(df_imputed)}")
    print(f"Rows removed: {len(df_original) - len(df_imputed)}")
    print(f"\nTotal nulls before: {int(df_original.isna().sum().sum())}")
    print(f"Total nulls after:  {int(df_imputed.isna().sum().sum())}")
    print("\nNull values by column after imputation:")
    print(missing_after.to_string(index=False))
    print("=" * 70)
    return missing_after


def run_workflow(
    input_path: Path = INPUT_FILE,
    output_path: Path = OUTPUT_FILE,
    decisions_path: Path = DECISIONS_FILE,
) -> Path:
    """Run DeliveryPulse missing-value treatment and produce audit artifacts."""
    df_original = pd.read_csv(input_path)
    analyze_missing_values(df_original)

    print("\nApplying DeliveryPulse missing-value policies...")
    df_imputed = drop_rows_with_nulls(df_original, ["order_id"])
    df_imputed = impute_mean_median(df_imputed, ["delivery_minutes", "distance_km"], strategy="median")
    df_imputed = impute_mode(df_imputed, ["zone"])

    # No delivery timestamp exists in this dataset. Keep this strategy available
    # for future time-ordered inputs rather than applying it to rider attribution.
    df_imputed = impute_forward_fill(df_imputed, [])

    document_imputation_decisions(df_original, df_imputed, decisions_path)
    validate_imputation(df_original, df_imputed)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_imputed.to_csv(output_path, index=False)
    print(f"\nOK Cleaned data saved to {output_path}")
    print(f"OK Decision log saved to {decisions_path}")
    return output_path


if __name__ == "__main__":
    run_workflow()
