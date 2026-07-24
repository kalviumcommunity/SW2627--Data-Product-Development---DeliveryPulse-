import json
import time
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / 'data' / 'raw'
OUTPUT_DIR = BASE_DIR / 'output'

ORDERS_CSV = RAW_DIR / 'orders.csv'
OUTPUT_SAMPLE_CSV = OUTPUT_DIR / 'vectorized_optimization_sample.csv'
OUTPUT_REPORT_JSON = OUTPUT_DIR / 'vectorization_report.json'
OUTPUT_SUMMARY_CSV = OUTPUT_DIR / 'vectorization_summary.csv'


def _ensure_output_folder() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_orders(path: Path = ORDERS_CSV) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f'Missing input file: {path}')

    df = pd.read_csv(path, parse_dates=['order_date'])
    print(f'Loaded orders: {len(df)} rows, columns={list(df.columns)}')
    return df


def expand_to_rows(df: pd.DataFrame, target_rows: int = 100_000, seed: int = 42) -> pd.DataFrame:
    if len(df) == 0:
        raise ValueError('Input dataframe is empty')

    repeats = int(np.ceil(target_rows / len(df)))
    expanded = pd.concat([df] * repeats, ignore_index=True).iloc[:target_rows].copy()

    rng = np.random.RandomState(seed)
    if 'amount' in expanded.columns:
        expanded['amount'] = expanded['amount'] * (1 + rng.normal(scale=0.05, size=len(expanded)))
        expanded['amount'] = expanded['amount'].clip(lower=0)

    if 'distance_km' in expanded.columns:
        expanded['distance_km'] = expanded['distance_km'] * (1 + rng.normal(scale=0.1, size=len(expanded)))
        expanded['distance_km'] = expanded['distance_km'].clip(lower=0)

    if 'order_date' in expanded.columns:
        expanded['order_date'] = pd.to_datetime('2025-01-01') + pd.to_timedelta(rng.randint(0, 365, size=len(expanded)), unit='D')

    print(f'Expanded dataset to {len(expanded)} rows for benchmarking')
    return expanded


def normalize_min_max_loop(values: np.ndarray) -> np.ndarray:
    values = values.astype(float)
    min_val = values.min()
    max_val = values.max()
    span = max_val - min_val
    if span == 0:
        return np.zeros_like(values)

    normalized = []
    for value in values:
        normalized.append((value - min_val) / span)
    return np.array(normalized, dtype=float)


def normalize_min_max_vectorized(values: np.ndarray) -> np.ndarray:
    values = values.astype(float)
    min_val = values.min()
    max_val = values.max()
    span = max_val - min_val
    if span == 0:
        return np.zeros_like(values)
    return (values - min_val) / span


def zscore_vectorized(values: np.ndarray) -> np.ndarray:
    values = values.astype(float)
    mean = values.mean()
    std = values.std(ddof=0)
    if std == 0:
        return np.zeros_like(values)
    return (values - mean) / std


def rank_desc_vectorized(values: np.ndarray) -> np.ndarray:
    order = np.argsort(-values, kind='stable')
    ranks = np.empty_like(order, dtype=int)
    ranks[order] = np.arange(1, len(values) + 1)
    return ranks


def time_execution(func, *args, repeat: int = 3) -> float:
    timings = []
    for _ in range(repeat):
        start = time.perf_counter()
        func(*args)
        timings.append(time.perf_counter() - start)
    return float(np.min(timings))


def benchmark_normalization(df: pd.DataFrame) -> Dict[str, float]:
    values = df['amount'].values
    loop_time = time_execution(normalize_min_max_loop, values, repeat=5)
    vector_time = time_execution(normalize_min_max_vectorized, values, repeat=5)
    return {
        'loop_seconds': loop_time,
        'vectorized_seconds': vector_time,
        'speedup': float(loop_time / vector_time) if vector_time > 0 else float('inf'),
    }


def apply_vectorized_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    values = df['amount'].values

    df['amount_normalized'] = normalize_min_max_vectorized(values)
    df['amount_zscore'] = zscore_vectorized(values)
    df['amount_rank_desc'] = rank_desc_vectorized(values)

    return df


def validate_feature_output(df: pd.DataFrame) -> Dict:
    validation = {
        'missing_values': df[['amount_normalized', 'amount_zscore', 'amount_rank_desc']].isna().sum().to_dict(),
        'normalized_range': {
            'min': float(df['amount_normalized'].min()),
            'max': float(df['amount_normalized'].max()),
        },
        'zscore_mean': float(df['amount_zscore'].mean()),
        'zscore_std': float(df['amount_zscore'].std(ddof=0)),
        'rank_range': {
            'min': int(df['amount_rank_desc'].min()),
            'max': int(df['amount_rank_desc'].max()),
        },
    }
    return validation


def save_results(df: pd.DataFrame, report: Dict) -> None:
    _ensure_output_folder()
    df.head(100).to_csv(OUTPUT_SAMPLE_CSV, index=False)
    with open(OUTPUT_REPORT_JSON, 'w', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)
    pd.DataFrame(report['benchmark'], index=[0]).to_csv(OUTPUT_SUMMARY_CSV, index=False)

    print(f'Saved sample output to {OUTPUT_SAMPLE_CSV}')
    print(f'Saved benchmark report to {OUTPUT_REPORT_JSON}')
    print(f'Saved benchmark summary to {OUTPUT_SUMMARY_CSV}')


def run() -> None:
    orders = load_orders()
    benchmark_df = expand_to_rows(orders, target_rows=100_000)
    benchmark = benchmark_normalization(benchmark_df)
    optimized_df = apply_vectorized_features(benchmark_df)
    validation = validate_feature_output(optimized_df)

    report = {
        'dataset': str(ORDERS_CSV),
        'benchmark': benchmark,
        'validation': validation,
        'reasoning': (
            'A Python loop computes min-max normalization row-by-row and suffers interpreter overhead. '
            'NumPy vectorization computes the same result on the full array in compiled code, producing a large speedup and enabling the result to be attached back to the DataFrame as new columns.'
        ),
    }
    save_results(optimized_df, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    run()
