from pathlib import Path
import json

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "output"
DEFAULT_INPUT_FILE = RAW_DIR / "quality_test.csv"
REPORT_FILE = OUTPUT_DIR / "profile_report.json"


def profile_nulls_and_duplicates(df):
    """
    Compute null percentage and duplicate counts per column.

    Returns: Dictionary with null analysis by column
    """
    profile = {
        'null_counts': {},
        'null_percentages': {},
        'exact_duplicate_count': 0,
    }

    for col in df.columns:
        null_count = df[col].isna().sum()
        null_pct = (null_count / len(df)) * 100
        profile['null_counts'][col] = int(null_count)
        profile['null_percentages'][col] = round(null_pct, 2)

    duplicate_count = int(df.duplicated().sum())
    profile['exact_duplicate_count'] = duplicate_count
    profile['duplicate_percentage'] = round((duplicate_count / len(df)) * 100, 2)

    return profile


def profile_numerical_columns(df):
    """
    Summarise numerical columns with statistical measures.

    Returns: DataFrame with min, max, mean, median, std
    """
    numerical_cols = df.select_dtypes(include=[np.number]).columns

    stats = {}
    for col in numerical_cols:
        stats[col] = {
            'min': round(df[col].min(), 2),
            'max': round(df[col].max(), 2),
            'mean': round(df[col].mean(), 2),
            'median': round(df[col].median(), 2),
            'std': round(df[col].std(), 2),
            'null_count': int(df[col].isnull().sum()),
        }

    return pd.DataFrame(stats).T


def profile_categorical_columns(df, top_n=5):
    """
    Summarise categorical columns with value distributions.

    Returns: Dictionary with unique counts and top values
    """
    categorical_cols = df.select_dtypes(include=['object', 'string']).columns

    profile = {}
    for col in categorical_cols:
        profile[col] = {
            'unique_count': int(df[col].nunique(dropna=True)),
            'top_values': df[col].value_counts(dropna=False).head(top_n).to_dict(),
            'null_count': int(df[col].isnull().sum()),
        }

    return profile


def identify_quality_issues(df, null_threshold=30, duplicate_threshold=5):
    """
    Identify data quality problems based on thresholds.

    Returns: List of issues found with severity and recommendations
    """
    issues = []

    null_pcts = (df.isnull().sum() / len(df)) * 100
    for col, pct in null_pcts.items():
        if pct > null_threshold:
            issues.append({
                'type': 'High nulls',
                'column': col,
                'severity': 'HIGH',
                'value': f"{pct:.1f}% missing",
                'recommendation': 'Consider imputation or column exclusion',
            })

    dup_count = df.duplicated().sum()
    dup_pct = (dup_count / len(df)) * 100
    if dup_pct > duplicate_threshold:
        issues.append({
            'type': 'High duplicates',
            'column': 'Full row',
            'severity': 'HIGH',
            'value': f"{dup_pct:.1f}% duplicated",
            'recommendation': 'Deduplication required before analysis',
        })

    for col in df.select_dtypes(include=[np.number]).columns:
        if (df[col] < 0).any() and 'amount' in col.lower():
            issues.append({
                'type': 'Invalid range',
                'column': col,
                'severity': 'MEDIUM',
                'value': 'Contains negative values',
                'recommendation': 'Investigate negative entries',
            })

    return issues


def generate_profile_report(df, filepath):
    """
    Generate complete data quality report and save to JSON.

    Returns: Complete profile report dictionary
    """
    numerical_df = profile_numerical_columns(df)
    report = {
        'dataset': str(filepath),
        'record_count': int(len(df)),
        'column_count': int(len(df.columns)),
        'nulls_and_duplicates': profile_nulls_and_duplicates(df),
        'numerical_stats': numerical_df.to_dict(),
        'categorical_stats': profile_categorical_columns(df),
        'quality_issues': identify_quality_issues(df),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, 'w', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"DATA QUALITY PROFILE: {filepath}")
    print(f"{'='*60}")
    print(f"Records: {report['record_count']}")
    print(f"Columns: {report['column_count']}")
    print(f"\nQuality Issues Found: {len(report['quality_issues'])}")
    for issue in report['quality_issues']:
        print(f"  [{issue['severity']}] {issue['type']} in {issue['column']}")
        print(f"    Value: {issue['value']} -> {issue['recommendation']}")
    print(f"{'='*60}\n")

    return report


def ensure_sample_data(filepath=DEFAULT_INPUT_FILE):
    """Create the sample dataset with quality issues if it is missing."""
    if filepath.exists():
        return filepath

    filepath.parent.mkdir(parents=True, exist_ok=True)
    sample = pd.DataFrame(
        [
            [1, 'Alice', 'alice@example.com', 100, 'active'],
            [2, 'Bob', None, 250, 'active'],
            [1, 'Alice', 'alice@example.com', 100, 'active'],
            [4, None, 'charlie@example.com', 500, 'inactive'],
            [5, 'Diana', None, -50, None],
        ],
        columns=['customer_id', 'name', 'email', 'amount', 'status'],
    )
    sample.to_csv(filepath, index=False)
    return filepath


def main():
    """Run the data profiling workflow."""
    filepath = ensure_sample_data()
    df = pd.read_csv(filepath)
    generate_profile_report(df, filepath)
    print(json.dumps(json.loads(REPORT_FILE.read_text(encoding='utf-8')), indent=2))


if __name__ == '__main__':
    main()