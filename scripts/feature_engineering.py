import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / 'data' / 'raw'
OUTPUT_DIR = BASE_DIR / 'output'

CUSTOMERS_CSV = RAW_DIR / 'customers.csv'
ORDERS_CSV = RAW_DIR / 'orders.csv'
FEATURE_OUTPUT_CSV = OUTPUT_DIR / 'feature_engineered_customers.csv'
FEATURE_REPORT_JSON = OUTPUT_DIR / 'feature_engineering_report.json'
FEATURE_SUMMARY_CSV = OUTPUT_DIR / 'feature_engineering_summary.csv'

ENGAGEMENT_BINS = [0, 2, 10, float('inf')]
ENGAGEMENT_LABELS = ['low', 'medium', 'high']
SPEND_QUARTILE_LABELS = ['Q1', 'Q2', 'Q3', 'Q4']
RFM_LABELS = [5, 4, 3, 2, 1]
FREQUENCY_LABELS = [1, 2, 3, 4, 5]
MONETARY_LABELS = [1, 2, 3, 4, 5]


def _ensure_output_folder() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_source_data(customers_path: Path = CUSTOMERS_CSV, orders_path: Path = ORDERS_CSV) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if not customers_path.exists():
        raise FileNotFoundError(f'Missing customers source: {customers_path}')
    if not orders_path.exists():
        raise FileNotFoundError(f'Missing orders source: {orders_path}')

    customers = pd.read_csv(customers_path, parse_dates=['signup_date'])
    orders = pd.read_csv(orders_path, parse_dates=['order_date'])

    print(f'Loaded customers: {len(customers)} rows')
    print(f'Loaded orders: {len(orders)} rows')

    return customers, orders


def compute_reference_date(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.Timestamp:
    if not orders.empty:
        return orders['order_date'].max()
    return customers['signup_date'].max()


def aggregate_customer_orders(orders: pd.DataFrame) -> pd.DataFrame:
    orders_agg = (
        orders
        .groupby('customer_id', observed=True)
        .agg(
            total_transactions=('order_id', 'count'),
            total_spent=('amount', 'sum'),
            completed_orders=('status', lambda values: (values == 'completed').sum()),
            returned_orders=('status', lambda values: (values == 'returned').sum()),
            first_order_date=('order_date', 'min'),
            last_order_date=('order_date', 'max'),
        )
        .reset_index()
    )

    orders_agg['return_rate'] = orders_agg['returned_orders'] / orders_agg['total_transactions']
    orders_agg['return_rate'] = orders_agg['return_rate'].fillna(0)

    return orders_agg


def merge_customer_metrics(customers: pd.DataFrame, orders_agg: pd.DataFrame, reference_date: pd.Timestamp) -> pd.DataFrame:
    customers = customers.copy()
    merged = customers.merge(orders_agg, on='customer_id', how='left')

    merged[['total_transactions', 'total_spent', 'completed_orders', 'returned_orders']] = (
        merged[['total_transactions', 'total_spent', 'completed_orders', 'returned_orders']]
        .fillna(0)
    )

    merged['days_as_customer'] = (reference_date - merged['signup_date']).dt.days.clip(lower=1)
    merged['days_since_last_purchase'] = (
        reference_date - merged['last_order_date']
    ).dt.days
    merged['days_since_last_purchase'] = merged['days_since_last_purchase'].fillna(merged['days_as_customer']).astype(int)

    return merged


def safe_qcut(series: pd.Series, q: int, labels: Sequence, duplicates: str = 'drop') -> pd.Series:
    try:
        return pd.qcut(series, q=q, labels=labels, duplicates=duplicates)
    except ValueError:
        ranked = series.rank(method='first', na_option='bottom')
        return pd.cut(ranked, bins=q, labels=labels, include_lowest=True)


def compute_ratio_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['transactions_per_month'] = df['total_transactions'] / (df['days_as_customer'] / 30)
    df['transactions_per_month'] = df['transactions_per_month'].replace([np.inf, -np.inf], np.nan).fillna(0)

    df['avg_spend_per_transaction'] = np.where(
        df['total_transactions'] > 0,
        df['total_spent'] / df['total_transactions'],
        0.0,
    )

    df['lifetime_value_per_month'] = df['total_spent'] / (df['days_as_customer'] / 30)
    df['lifetime_value_per_month'] = df['lifetime_value_per_month'].replace([np.inf, -np.inf], np.nan).fillna(0)

    return df


def compute_tiered_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['engagement_tier'] = pd.cut(
        df['transactions_per_month'],
        bins=ENGAGEMENT_BINS,
        labels=ENGAGEMENT_LABELS,
        include_lowest=True,
    )

    df['spend_quartile'] = safe_qcut(df['total_spent'], q=4, labels=SPEND_QUARTILE_LABELS)
    if pd.api.types.is_categorical_dtype(df['spend_quartile']):
        df['spend_quartile'] = df['spend_quartile'].cat.add_categories(
            [label for label in SPEND_QUARTILE_LABELS if label not in df['spend_quartile'].cat.categories]
        )
    df['spend_quartile'] = df['spend_quartile'].fillna('Q1')

    return df


def compute_rfm_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['recency_score'] = safe_qcut(df['days_since_last_purchase'], q=5, labels=RFM_LABELS)
    df['frequency_score'] = safe_qcut(df['total_transactions'], q=5, labels=FREQUENCY_LABELS)
    df['monetary_score'] = safe_qcut(df['total_spent'], q=5, labels=MONETARY_LABELS)

    for col in ['recency_score', 'frequency_score', 'monetary_score']:
        df[col] = df[col].astype('Int64').fillna(1)

    df['rfm_score'] = (
        df['recency_score'].astype(int)
        + df['frequency_score'].astype(int)
        + df['monetary_score'].astype(int)
    )

    engagement_score_map = {'low': 1, 'medium': 2, 'high': 3}
    df['engagement_score'] = df['engagement_tier'].map(engagement_score_map).fillna(1).astype(int)
    spend_quartile_score_map = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
    df['spend_quartile_score'] = df['spend_quartile'].map(spend_quartile_score_map).fillna(1).astype(int)

    df['customer_health_score'] = (
        0.4 * df['frequency_score'].astype(int)
        + 0.35 * df['monetary_score'].astype(int)
        + 0.2 * df['engagement_score']
        + 0.05 * df['spend_quartile_score']
    ).round(2)

    return df


def validate_features(df: pd.DataFrame) -> Dict[str, Dict[str, int]]:
    feature_columns = [
        'transactions_per_month',
        'avg_spend_per_transaction',
        'lifetime_value_per_month',
        'engagement_tier',
        'spend_quartile',
        'recency_score',
        'frequency_score',
        'monetary_score',
        'rfm_score',
        'customer_health_score',
    ]

    validation = {
        'missing_values': df[feature_columns].isna().sum().to_dict(),
        'engagement_tier_counts': df['engagement_tier'].value_counts(dropna=False).to_dict(),
        'spend_quartile_counts': df['spend_quartile'].value_counts(dropna=False).to_dict(),
        'rfm_score_range': {
            'min': int(df['rfm_score'].min()),
            'max': int(df['rfm_score'].max()),
        },
        'health_score_range': {
            'min': float(df['customer_health_score'].min()),
            'max': float(df['customer_health_score'].max()),
        },
    }

    return validation


def summarize_features(df: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = [
        'total_transactions',
        'total_spent',
        'transactions_per_month',
        'avg_spend_per_transaction',
        'lifetime_value_per_month',
        'rfm_score',
        'customer_health_score',
    ]
    summary = df[numeric_columns].describe().transpose()
    return summary


def build_report(df: pd.DataFrame, validation: Dict[str, Dict]) -> Dict:
    report = {
        'record_count': len(df),
        'feature_columns': [
            'transactions_per_month',
            'avg_spend_per_transaction',
            'lifetime_value_per_month',
            'engagement_tier',
            'spend_quartile',
            'recency_score',
            'frequency_score',
            'monetary_score',
            'rfm_score',
            'customer_health_score',
        ],
        'validation': validation,
        'business_reasoning': (
            'The engineered features normalize raw counts for customer tenure, bin engagement into business-friendly tiers, and combine recency/frequency/monetary signals into a single health score. '
            'This prevents raw totals from being interpreted out of context and supports segment-level actions for retention and growth.'
        ),
    }
    return report


def save_outputs(df: pd.DataFrame, report: Dict) -> None:
    _ensure_output_folder()
    df.to_csv(FEATURE_OUTPUT_CSV, index=False)
    with open(FEATURE_REPORT_JSON, 'w', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)
    summary = summarize_features(df)
    summary.to_csv(FEATURE_SUMMARY_CSV)
    print(f'Saved features to {FEATURE_OUTPUT_CSV}')
    print(f'Saved feature report to {FEATURE_REPORT_JSON}')
    print(f'Saved feature summary to {FEATURE_SUMMARY_CSV}')


def run_feature_engineering() -> None:
    customers, orders = load_source_data()
    reference_date = compute_reference_date(orders, customers)
    orders_agg = aggregate_customer_orders(orders)
    customer_features = merge_customer_metrics(customers, orders_agg, reference_date)
    customer_features = compute_ratio_features(customer_features)
    customer_features = compute_tiered_features(customer_features)
    customer_features = compute_rfm_scores(customer_features)

    validation = validate_features(customer_features)
    report = build_report(customer_features, validation)
    save_outputs(customer_features, report)

    print('\nFeature validation results:')
    print(json.dumps(validation, indent=2))


if __name__ == '__main__':
    run_feature_engineering()
