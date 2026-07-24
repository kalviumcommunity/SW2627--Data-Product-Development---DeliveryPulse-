import pandas as pd
from pathlib import Path


def parse_transaction_datetime(df, date_column='transaction_date', date_format='%Y-%m-%d %H:%M:%S'):
    """Parse transaction timestamp strings to datetime using an explicit format."""
    df_typed = df.copy()

    df_typed[date_column] = pd.to_datetime(
        df_typed[date_column],
        format=date_format,
        errors='raise'
    )

    print(f"Parsed {date_column} to datetime with format {date_format}")
    print(f"dtype: {df_typed[date_column].dtype}")
    return df_typed


def extract_time_features(df, date_column='transaction_date'):
    """Extract day-of-week, hour-of-day, week number, month, and quarter."""
    df_features = df.copy()
    df_features['day_of_week'] = df_features[date_column].dt.day_name()
    df_features['hour'] = df_features[date_column].dt.hour
    df_features['week_num'] = df_features[date_column].dt.isocalendar().week
    df_features['month'] = df_features[date_column].dt.month
    df_features['quarter'] = df_features[date_column].dt.quarter

    print("Extracted time features: day_of_week, hour, week_num, month, quarter")
    return df_features


def compute_recency(df, date_column='transaction_date', reference_time=None):
    """Compute days since event for each transaction."""
    df_recency = df.copy()

    if reference_time is None:
        reference_time = pd.Timestamp.now()

    df_recency['days_since_transaction'] = (
        reference_time - df_recency[date_column]
    ).dt.days

    print("Computed recency feature: days_since_transaction")
    return df_recency


def resample_weekly_metrics(df, date_column='transaction_date', value_column='amount'):
    """Resample transactions to weekly buckets and compute weekly metrics."""
    df_ts = df.copy()
    df_ts = df_ts.set_index(date_column).sort_index()

    weekly = df_ts[value_column].resample('W').agg(['sum', 'count', 'mean'])
    weekly = weekly.rename(columns={'sum': 'weekly_amount_sum', 'count': 'weekly_count', 'mean': 'weekly_amount_mean'})

    print("Computed weekly resampled metrics")
    return weekly


def hourly_daily_pivot(df):
    """Create an hour × day of week pivot table for amount sums."""
    pivot = pd.pivot_table(
        df,
        values='amount',
        index='hour',
        columns='day_of_week',
        aggfunc='sum',
        fill_value=0
    )
    print("Created hour × day_of_week pivot table")
    return pivot


def _ensure_processed_folder():
    processed_path = Path('data/processed')
    processed_path.mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    _ensure_processed_folder()

    input_file = Path('data/raw/transactions_with_timestamps.csv')
    if not input_file.exists():
        raise FileNotFoundError(f"Missing input file: {input_file}")

    df = pd.read_csv(input_file)

    print("\nInitial data sample:")
    print(df.head(10).to_string(index=False))

    df_typed = parse_transaction_datetime(df)
    df_features = extract_time_features(df_typed)
    df_features = compute_recency(df_features)

    weekly_metrics = resample_weekly_metrics(df_features)
    print("\nWeekly metrics sample:")
    print(weekly_metrics.head(10).to_string())

    pivot_table = hourly_daily_pivot(df_features)
    print("\nHourly × day_of_week pivot sample:")
    print(pivot_table.head(10).to_string())

    output_file = Path('data/processed/datetime_features.csv')
    df_features.to_csv(output_file, index=False)
    print(f"\nSaved processed data to {output_file}")

    weekly_file = Path('output/weekly_metrics.csv')
    weekly_metrics.to_csv(weekly_file)
    print(f"Saved weekly metrics to {weekly_file}")

    pivot_file = Path('output/hourly_day_pivot.csv')
    pivot_table.to_csv(pivot_file)
    print(f"Saved pivot table to {pivot_file}")
