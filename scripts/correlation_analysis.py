import json
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / 'data' / 'raw'
OUTPUT_DIR = BASE_DIR / 'output'

ORDERS_CSV = RAW_DIR / 'orders.csv'
TRANSACTIONS_CSV = RAW_DIR / 'transactions_with_timestamps.csv'

OUTPUT_HEATMAP_PDF = OUTPUT_DIR / 'correlation_heatmap.png'
OUTPUT_TOP_PAIRS_CSV = OUTPUT_DIR / 'correlation_top_pairs.csv'
OUTPUT_SUMMARY_CSV = OUTPUT_DIR / 'correlation_analysis_summary.csv'
OUTPUT_REPORT_JSON = OUTPUT_DIR / 'correlation_analysis_report.json'


def _ensure_output_folder() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_orders() -> pd.DataFrame:
    if not ORDERS_CSV.exists():
        raise FileNotFoundError(f'Missing orders source file: {ORDERS_CSV}')

    df = pd.read_csv(ORDERS_CSV, parse_dates=['order_date'])
    print(f'Loaded orders: {len(df)} rows')
    return df


def load_transactions() -> pd.DataFrame:
    if TRANSACTIONS_CSV.exists():
        df = pd.read_csv(TRANSACTIONS_CSV, parse_dates=['transaction_date'])
        print(f'Loaded transactions: {len(df)} rows')
        return df
    print('No transaction file found; using orders only for relationship analysis')
    return pd.DataFrame()


def build_customer_metrics(orders: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    orders_metrics = (
        orders.groupby('customer_id', observed=True, sort=False)
        .agg(
            order_count=('order_id', 'count'),
            total_order_amount=('amount', 'sum'),
            average_order_amount=('amount', 'mean'),
            returned_order_count=('status', lambda s: (s == 'returned').sum()),
            pending_order_count=('status', lambda s: (s == 'pending').sum()),
            completed_order_count=('status', lambda s: (s == 'completed').sum()),
            first_order_date=('order_date', 'min'),
            last_order_date=('order_date', 'max'),
        )
        .reset_index()
    )

    orders_metrics['return_rate'] = (
        orders_metrics['returned_order_count'] / orders_metrics['order_count']
    ).fillna(0.0)
    orders_metrics['pending_rate'] = (
        orders_metrics['pending_order_count'] / orders_metrics['order_count']
    ).fillna(0.0)
    orders_metrics['completed_rate'] = (
        orders_metrics['completed_order_count'] / orders_metrics['order_count']
    ).fillna(0.0)
    orders_metrics['order_span_days'] = (
        orders_metrics['last_order_date'] - orders_metrics['first_order_date']
    ).dt.days.fillna(0).astype(int)

    if transactions.empty:
        return orders_metrics

    transactions_metrics = (
        transactions.groupby('customer_id', observed=True, sort=False)
        .agg(
            transaction_count=('transaction_date', 'count'),
            transaction_amount_sum=('amount', 'sum'),
            transaction_amount_mean=('amount', 'mean'),
            unique_products=('product_id', 'nunique'),
            first_transaction_date=('transaction_date', 'min'),
            last_transaction_date=('transaction_date', 'max'),
        )
        .reset_index()
    )

    transactions_metrics['transaction_span_days'] = (
        transactions_metrics['last_transaction_date'] - transactions_metrics['first_transaction_date']
    ).dt.days.fillna(0).astype(int)

    customer_metrics = orders_metrics.merge(
        transactions_metrics,
        on='customer_id',
        how='outer',
        suffixes=('_orders', '_transactions'),
    )

    customer_metrics['total_spend'] = (
        customer_metrics[['total_order_amount', 'transaction_amount_sum']].sum(axis=1, skipna=True)
    )
    customer_metrics['average_amount'] = (
        customer_metrics[['average_order_amount', 'transaction_amount_mean']].mean(axis=1, skipna=True)
    )
    customer_metrics['engagement_score'] = (
        customer_metrics['order_count'].fillna(0) * 0.6
        + customer_metrics['transaction_count'].fillna(0) * 0.4
    )

    return customer_metrics


def select_numeric_features(df: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    return df[numeric_columns].drop(columns=[col for col in ['customer_id'] if col in numeric_columns])


def compute_correlations(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    pearson = df.corr(method='pearson')
    spearman = df.corr(method='spearman')
    return {'pearson': pearson, 'spearman': spearman}


def flatten_strong_correlations(corr: pd.DataFrame, threshold: float = 0.7) -> pd.DataFrame:
    pairs = []
    for i, row in corr.iterrows():
        for j, value in row.items():
            if i == j:
                continue
            if abs(value) >= threshold:
                pairs.append({'feature_a': i, 'feature_b': j, 'correlation': float(value)})

    strong_pairs = pd.DataFrame(pairs).drop_duplicates(subset=['correlation', 'feature_a', 'feature_b'])
    strong_pairs['pair'] = strong_pairs.apply(
        lambda row: tuple(sorted([row['feature_a'], row['feature_b']])), axis=1
    )
    strong_pairs = strong_pairs.drop(columns=['feature_a', 'feature_b']).drop_duplicates(subset=['pair'])
    strong_pairs = strong_pairs.sort_values(by='correlation', ascending=False)
    return strong_pairs[['pair', 'correlation']]


def plot_heatmap(corr: pd.DataFrame, title: str, output_path: Path) -> None:
    plt.figure(figsize=(12, 10))
    plt.imshow(corr, cmap='coolwarm', vmin=-1, vmax=1)
    plt.colorbar(label='Correlation')
    ticks = np.arange(len(corr.columns))
    plt.xticks(ticks, corr.columns, rotation=45, ha='right')
    plt.yticks(ticks, corr.index)

    for i in range(len(corr.index)):
        for j in range(len(corr.columns)):
            plt.text(j, i, f'{corr.iloc[i, j]:.2f}', ha='center', va='center', color='black', fontsize=8)

    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f'Saved heatmap to {output_path}')


def build_business_interpretation(pearson: pd.DataFrame, spearman: pd.DataFrame) -> List[Dict[str, str]]:
    report = []
    if 'return_rate' in pearson.columns and 'total_order_amount' in pearson.columns:
        report.append({
            'insight': 'Return rate often differs from total spend.',
            'suggestion': 'A high return rate can reduce customer lifetime value even when total spend looks strong.'
        })

    if 'order_count' in pearson.columns and 'transaction_count' in pearson.columns:
        report.append({
            'insight': 'Order count and transaction count are strongly related.',
            'suggestion': 'Keep one metric when they are redundant; choose the one that best matches business interpretation.'
        })

    top_pearson = flatten_strong_correlations(pearson, threshold=0.7)
    if top_pearson.shape[0] > 0:
        report.append({
            'insight': 'Strong correlations do not prove causation.',
            'suggestion': (
                'Review whether the relationship is due to a hidden confounder, or whether one metric is simply an outcome of another. '
                'Use these correlations for feature selection and signal discovery, not causal decisions.'
            )
        })

    if not report:
        report.append({
            'insight': 'No strong relationships detected at the threshold.',
            'suggestion': 'Lower threshold or create additional derived metrics to surface business signals.'
        })

    return report


def run_correlation_analysis() -> None:
    _ensure_output_folder()
    orders = load_orders()
    transactions = load_transactions()
    customer_metrics = build_customer_metrics(orders, transactions)

    numeric_features = select_numeric_features(customer_metrics)
    if numeric_features.shape[1] < 2:
        raise RuntimeError('Not enough numeric data to compute correlations.')

    correlation_matrices = compute_correlations(numeric_features)
    pearson_corr = correlation_matrices['pearson']
    spearman_corr = correlation_matrices['spearman']

    plot_heatmap(pearson_corr, 'Pearson Correlation Matrix', OUTPUT_HEATMAP_PDF)

    top_pearson = flatten_strong_correlations(pearson_corr, threshold=0.7)
    top_spearman = flatten_strong_correlations(spearman_corr, threshold=0.7)

    top_pearson.to_csv(OUTPUT_TOP_PAIRS_CSV, index=False)
    summary_data = numeric_features.describe().transpose()
    summary_data.to_csv(OUTPUT_SUMMARY_CSV)

    report = {
        'input_rows': int(len(customer_metrics)),
        'features': numeric_features.columns.tolist(),
        'pearson_corr': pearson_corr.round(3).to_dict(),
        'spearman_corr': spearman_corr.round(3).to_dict(),
        'top_pearson_pairs': [
            {'pair': pair, 'correlation': float(corr)}
            for pair, corr in zip(top_pearson['pair'], top_pearson['correlation'])
        ],
        'top_spearman_pairs': [
            {'pair': pair, 'correlation': float(corr)}
            for pair, corr in zip(top_spearman['pair'], top_spearman['correlation'])
        ],
        'interpretation': build_business_interpretation(pearson_corr, spearman_corr),
    }

    with open(OUTPUT_REPORT_JSON, 'w', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)

    print(f'Saved report to {OUTPUT_REPORT_JSON}')
    print(f'Saved summary to {OUTPUT_SUMMARY_CSV}')
    print(f'Saved top correlation pairs to {OUTPUT_TOP_PAIRS_CSV}')


if __name__ == '__main__':
    run_correlation_analysis()
