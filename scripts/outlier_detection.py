import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def load_data(path='data/raw/outlier_data.csv'):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    return pd.read_csv(path)


def detect_zscore_outliers(series, threshold=3.0):
    """Detect outliers using the Z-score method."""
    z_scores = np.abs(stats.zscore(series, nan_policy='omit'))
    return z_scores > threshold, z_scores


def detect_iqr_outliers(series, multiplier=1.5):
    """Detect outliers using the IQR method."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    outliers = (series < lower) | (series > upper)
    return outliers, lower, upper, q1, q3, iqr


def cap_outliers(series, lower, upper):
    """Cap outliers at the IQR boundaries."""
    capped = series.clip(lower=lower, upper=upper)
    return capped


def flag_outliers(df, column, outlier_mask, label='is_outlier'):
    """Flag outliers in a binary column."""
    df_flagged = df.copy()
    df_flagged[label] = outlier_mask.astype(int)
    print(f"Flagged {df_flagged[label].sum()} outliers in {column}")
    return df_flagged


def remove_outlier_rows(df, outlier_mask):
    """Remove rows where the outlier mask is True."""
    df_removed = df.loc[~outlier_mask].copy()
    print(f"Removed {outlier_mask.sum()} rows due to outliers")
    return df_removed


def create_cleaning_log(entries, path='output/outlier_cleaning_log.json'):
    """Save the cleaning log as JSON."""
    output_path = Path('output')
    output_path.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(entries, f, indent=2, default=str)
    print(f"Saved cleaning log to {path}")
    return path


def summarize_column_outliers(column, series, outlier_mask):
    """Return a summary dict for outliers in a column."""
    return {
        'column': column,
        'count_total': int(len(series)),
        'count_outliers': int(outlier_mask.sum()),
        'pct_outliers': float(outlier_mask.mean() * 100),
        'mean': float(series.mean()),
        'median': float(series.median()),
        'std': float(series.std()),
    }


def run_outlier_pipeline():
    df = load_data()

    # Salary: cap by IQR because extreme salary values should not be removed entirely.
    outlier_salary, lower_salary, upper_salary, q1_salary, q3_salary, iqr_salary = detect_iqr_outliers(
        df['salary']
    )
    df['salary_capped'] = cap_outliers(df['salary'], lower_salary, upper_salary)
    df['is_salary_outlier'] = outlier_salary.astype(int)

    # Vacation days: remove invalid outlier rows because values above reasonable bounds indicate bad data.
    outlier_vac, lower_vac, upper_vac, q1_vac, q3_vac, iqr_vac = detect_iqr_outliers(
        df['vacation_days']
    )
    df_vac_clean = remove_outlier_rows(df, outlier_vac)
    df_vac_clean['is_vacation_outlier'] = outlier_vac.astype(int)

    # Revenue: flag outliers using Z-score because distribution is expected to be roughly normal and we want to preserve data.
    outlier_rev, z_scores_rev = detect_zscore_outliers(df['revenue'])
    df['revenue_zscore'] = z_scores_rev
    df['is_revenue_outlier'] = outlier_rev.astype(int)

    cleaning_log = [
        {
            'column': 'salary',
            'method': 'IQR',
            'action': 'cap',
            'lower_bound': lower_salary,
            'upper_bound': upper_salary,
            'outlier_count': int(outlier_salary.sum()),
            'reasoning': 'Cap extreme salary values to preserve records while reducing skew.',
        },
        {
            'column': 'vacation_days',
            'method': 'IQR',
            'action': 'remove',
            'lower_bound': lower_vac,
            'upper_bound': upper_vac,
            'outlier_count': int(outlier_vac.sum()),
            'reasoning': 'Remove rows with impossible vacation days values that indicate bad data.',
        },
        {
            'column': 'revenue',
            'method': 'Z-score',
            'action': 'flag',
            'threshold': 3.0,
            'outlier_count': int(outlier_rev.sum()),
            'reasoning': 'Flag revenue anomalies to allow downstream analysis to filter or weight them.',
        },
    ]

    log_path = create_cleaning_log(cleaning_log)

    output_path = Path('data/processed')
    output_path.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path / 'outlier_flagged.csv', index=False)
    df_vac_clean.to_csv(output_path / 'outlier_vacation_removed.csv', index=False)
    print(f"Saved flagged outlier dataset to {output_path / 'outlier_flagged.csv'}")
    print(f"Saved vacation-cleaned dataset to {output_path / 'outlier_vacation_removed.csv'}")

    return df, df_vac_clean, cleaning_log, log_path


if __name__ == '__main__':
    run_outlier_pipeline()
