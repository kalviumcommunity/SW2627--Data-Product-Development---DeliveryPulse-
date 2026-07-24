import json
from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / 'data' / 'raw'
OUTPUT_DIR = BASE_DIR / 'output'

ORDERS_CSV = RAW_DIR / 'orders.csv'
TRANSACTIONS_CSV = RAW_DIR / 'transactions_with_timestamps.csv'

OUTPUT_STATS_JSON = OUTPUT_DIR / 'distribution_analysis_report.json'
OUTPUT_SUMMARY_CSV = OUTPUT_DIR / 'distribution_analysis_summary.csv'
OUTPUT_HIST_AMOUNT = OUTPUT_DIR / 'distribution_amount_histogram.png'
OUTPUT_KDE_AMOUNT = OUTPUT_DIR / 'distribution_amount_kde.png'
OUTPUT_SEGMENT_COMPARISON = OUTPUT_DIR / 'distribution_segment_comparison.png'
OUTPUT_CUSTOMER_SPEND = OUTPUT_DIR / 'distribution_customer_spend.png'
OUTPUT_CUSTOMER_SEGMENT = OUTPUT_DIR / 'distribution_customer_segment_comparison.png'


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
        return pd.read_csv(TRANSACTIONS_CSV, parse_dates=['transaction_date'])
    return pd.DataFrame()


def aggregate_customer_spend(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby('customer_id', observed=True, sort=False)
        .agg(
            total_spent=('amount', 'sum'),
            transaction_count=('order_id', 'count'),
            average_order_value=('amount', 'mean'),
        )
        .reset_index()
    )
    return grouped


def compute_distribution_stats(values: np.ndarray, label: str) -> Dict[str, float]:
    if len(values) == 0:
        return {
            'label': label,
            'count': 0,
            'mean': float('nan'),
            'median': float('nan'),
            'std': float('nan'),
            'skewness': float('nan'),
            'kurtosis': float('nan'),
            'min': float('nan'),
            'max': float('nan'),
        }

    skewness = float(stats.skew(values, nan_policy='omit'))
    kurtosis = float(stats.kurtosis(values, fisher=False, nan_policy='omit'))

    return {
        'label': label,
        'count': int(np.count_nonzero(~np.isnan(values))),
        'mean': float(np.nanmean(values)),
        'median': float(np.nanmedian(values)),
        'std': float(np.nanstd(values, ddof=0)),
        'skewness': skewness,
        'kurtosis': kurtosis,
        'min': float(np.nanmin(values)),
        'max': float(np.nanmax(values)),
    }


def detect_bimodal(values: np.ndarray) -> Tuple[bool, int, np.ndarray, np.ndarray]:
    if len(values) < 10 or np.nanstd(values) == 0:
        return False, 0, np.array([]), np.array([])

    cleaned = values[~np.isnan(values)]
    kde = stats.gaussian_kde(cleaned)
    x = np.linspace(cleaned.min(), cleaned.max(), 300)
    y = kde(x)
    peaks = ((y[1:-1] > y[:-2]) & (y[1:-1] > y[2:])).sum()
    return peaks >= 2, int(peaks), x, y


def plot_histogram(values: np.ndarray, label: str, output_path: Path, bins: int = 40) -> None:
    plt.figure(figsize=(10, 5))
    plt.hist(values, bins=bins, edgecolor='black', alpha=0.7)
    plt.title(f'{label} Distribution')
    plt.xlabel(label)
    plt.ylabel('Count')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f'Saved histogram to {output_path}')


def plot_kde(values: np.ndarray, label: str, output_path: Path) -> None:
    plt.figure(figsize=(10, 5))
    pd.Series(values).plot(kind='density')
    plt.title(f'{label} KDE')
    plt.xlabel(label)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f'Saved KDE plot to {output_path}')


def plot_segment_comparison(low: np.ndarray, high: np.ndarray, label: str, output_path: Path) -> None:
    plt.figure(figsize=(10, 5))
    plt.hist(low, bins=30, alpha=0.5, label='Low segment', color='tab:blue', density=True)
    plt.hist(high, bins=30, alpha=0.5, label='High segment', color='tab:orange', density=True)
    plt.title(f'{label} Distribution by Segment')
    plt.xlabel(label)
    plt.ylabel('Density')
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f'Saved segment comparison plot to {output_path}')


def build_interpretation(stats: Dict[str, float], label: str, bimodal: bool) -> str:
    messages = []
    if abs(stats['skewness']) > 1:
        direction = 'right' if stats['skewness'] > 0 else 'left'
        messages.append(
            f'{label} is highly skewed to the {direction}; median is more representative than mean.'
        )
    else:
        messages.append(f'{label} is approximately symmetric. Mean and median are similar.')

    if stats['kurtosis'] > 3:
        messages.append(f'{label} has heavy tails; extreme values are more likely.')
    elif stats['kurtosis'] < 3:
        messages.append(f'{label} is lighter-tailed than a normal distribution.')
    else:
        messages.append(f'{label} has kurtosis close to a normal distribution.')

    if bimodal:
        messages.append(f'{label} appears bimodal, suggesting at least two customer segments.')
    return ' '.join(messages)


def run_distribution_analysis() -> None:
    _ensure_output_folder()
    orders = load_orders()
    transactions = load_transactions()

    orders_amount = orders['amount'].to_numpy(dtype=float)
    orders_stats = compute_distribution_stats(orders_amount, 'Order Amount')
    orders_bimodal, orders_peaks, orders_x, orders_y = detect_bimodal(orders_amount)

    plot_histogram(orders_amount, 'Order Amount', OUTPUT_HIST_AMOUNT)
    plot_kde(orders_amount, 'Order Amount', OUTPUT_KDE_AMOUNT)

    customer_metrics = aggregate_customer_spend(orders)
    customer_spend = customer_metrics['total_spent'].to_numpy(dtype=float)
    customer_stats = compute_distribution_stats(customer_spend, 'Customer Total Spend')
    customer_bimodal, customer_peaks, customer_x, customer_y = detect_bimodal(customer_spend)

    plot_histogram(customer_spend, 'Customer Total Spend', OUTPUT_CUSTOMER_SPEND)
    plot_kde(customer_spend, 'Customer Total Spend', OUTPUT_CUSTOMER_SPEND)

    low_threshold = np.nanpercentile(customer_spend, 25)
    high_threshold = np.nanpercentile(customer_spend, 75)
    low_segment = customer_spend[customer_spend <= low_threshold]
    high_segment = customer_spend[customer_spend >= high_threshold]
    plot_segment_comparison(low_segment, high_segment, 'Customer Total Spend', OUTPUT_CUSTOMER_SEGMENT)

    report = {
        'dataset': str(ORDERS_CSV),
        'orders_stats': orders_stats,
        'orders_bimodal': orders_bimodal,
        'orders_peak_count': orders_peaks,
        'customer_stats': customer_stats,
        'customer_bimodal': customer_bimodal,
        'customer_peak_count': customer_peaks,
        'segment_thresholds': {
            'low_quartile': float(low_threshold),
            'high_quartile': float(high_threshold),
        },
        'interpretation': {
            'orders': build_interpretation(orders_stats, 'Order Amount', orders_bimodal),
            'customer_spend': build_interpretation(customer_stats, 'Customer Total Spend', customer_bimodal),
        },
    }

    summary = pd.DataFrame([orders_stats, customer_stats])
    summary.to_csv(OUTPUT_SUMMARY_CSV, index=False)

    with open(OUTPUT_STATS_JSON, 'w', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)

    print(json.dumps(report, indent=2))
    print(f'Saved report to {OUTPUT_STATS_JSON}')
    print(f'Saved summary to {OUTPUT_SUMMARY_CSV}')


if __name__ == '__main__':
    run_distribution_analysis()
