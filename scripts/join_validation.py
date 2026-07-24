import json
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / 'data' / 'raw'
OUTPUT_DIR = BASE_DIR / 'output'


def load_data(customers_path: Path = RAW_DIR / 'customers.csv', orders_path: Path = RAW_DIR / 'orders.csv') -> Tuple[pd.DataFrame, pd.DataFrame]:
    if not customers_path.exists():
        raise FileNotFoundError(f'Missing customer source file: {customers_path}')
    if not orders_path.exists():
        raise FileNotFoundError(f'Missing orders source file: {orders_path}')

    customers = pd.read_csv(customers_path, dtype={'customer_id': 'Int64'})
    orders = pd.read_csv(orders_path, dtype={'customer_id': 'Int64'})

    print(f'Loaded customers: {len(customers)} rows, {customers.shape[1]} columns')
    print(f'Loaded orders: {len(orders)} rows, {orders.shape[1]} columns')

    return customers, orders


def summarize_key_space(customers: pd.DataFrame, orders: pd.DataFrame, key: str = 'customer_id') -> Dict[str, int]:
    left_keys = set(customers[key].dropna().astype(int).unique())
    right_keys = set(orders[key].dropna().astype(int).unique())
    matched_keys = left_keys & right_keys

    return {
        'left_rows': len(customers),
        'right_rows': len(orders),
        'unique_left_keys': len(left_keys),
        'unique_right_keys': len(right_keys),
        'matched_keys': len(matched_keys),
        'unmatched_left_keys': len(left_keys - matched_keys),
        'unmatched_right_keys': len(right_keys - matched_keys),
    }


def validate_join(customers: pd.DataFrame, orders: pd.DataFrame, key: str = 'customer_id', how: str = 'left') -> Tuple[pd.DataFrame, Dict[str, int]]:
    merged = pd.merge(
        customers,
        orders,
        on=key,
        how=how,
        indicator=True,
        validate='1:m',
    )

    audit = {
        'join_type': how,
        'left_rows': len(customers),
        'right_rows': len(orders),
        'result_rows': len(merged),
        'row_delta': len(merged) - len(customers),
        'merge_counts': merged['_merge'].value_counts().to_dict(),
    }

    print(f"Join type: {how}")
    print(f"Customer rows: {audit['left_rows']}")
    print(f"Order rows: {audit['right_rows']}")
    print(f"Merged rows: {audit['result_rows']}")
    print(f"Row delta: {audit['row_delta']}")
    print(f"Indicator counts: {audit['merge_counts']}")

    return merged, audit


def find_unmatched(customers: pd.DataFrame, orders: pd.DataFrame, key: str = 'customer_id') -> Tuple[pd.DataFrame, pd.DataFrame]:
    unmatched_customers = customers[~customers[key].isin(orders[key])].copy()
    unmatched_orders = orders[~orders[key].isin(customers[key])].copy()

    print(f"Unmatched customers: {len(unmatched_customers)}")
    print(f"Unmatched orders: {len(unmatched_orders)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    unmatched_customers.to_csv(OUTPUT_DIR / 'unmatched_customers.csv', index=False)
    unmatched_orders.to_csv(OUTPUT_DIR / 'unmatched_orders.csv', index=False)

    return unmatched_customers, unmatched_orders


def compare_join_types(customers: pd.DataFrame, orders: pd.DataFrame, key: str = 'customer_id') -> Dict[str, int]:
    counts = {}
    for how in ['inner', 'left', 'right', 'outer']:
        merged = pd.merge(customers, orders, on=key, how=how)
        counts[how] = len(merged)
        print(f"{how.capitalize()} join rows: {counts[how]}")
    return counts


def inspect_duplicates(orders: pd.DataFrame, key: str = 'customer_id') -> pd.Series:
    duplicate_counts = orders[key].value_counts()
    duplicates = duplicate_counts[duplicate_counts > 1]
    print(f"Duplicate order keys: {len(duplicates)} keys have multiple orders")
    if not duplicates.empty:
        print(duplicates.to_string())
    return duplicates


def build_report(customers: pd.DataFrame, orders: pd.DataFrame, audit: Dict[str, int], unmatched_customers: pd.DataFrame, unmatched_orders: pd.DataFrame, join_counts: Dict[str, int], key: str = 'customer_id') -> Dict:
    key_space = summarize_key_space(customers, orders, key=key)

    report = {
        'source_tables': {
            'customers': {
                'path': str(RAW_DIR / 'customers.csv'),
                'rows': len(customers),
                'unique_keys': key_space['unique_left_keys'],
            },
            'orders': {
                'path': str(RAW_DIR / 'orders.csv'),
                'rows': len(orders),
                'unique_keys': key_space['unique_right_keys'],
            },
        },
        'join_key': key,
        'chosen_join': audit['join_type'],
        'join_counts': join_counts,
        'audit': audit,
        'unmatched': {
            'customers': len(unmatched_customers),
            'orders': len(unmatched_orders),
        },
        'reasoning': (
            'A left join is selected to preserve all customer master records while enriching them with orders. '
            'This identifies customers without orders, preserves history for existing customers, and surfaces orphan orders via unmatched right-side keys. '
            'If the business instead required only customers with orders, an inner join would be appropriate. If the business required all orders including those with missing customers, a right or outer join should be used.'
        ),
    }

    print(json.dumps(report, indent=2))
    return report


def save_join_report(report: Dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / 'join_report.json'
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)
    print(f"Saved join report: {path}")
    return path


def save_merged_output(merged: pd.DataFrame) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / 'merged_customers_orders.csv'
    merged.to_csv(path, index=False)
    print(f"Saved merged output: {path}")
    return path


if __name__ == '__main__':
    customers, orders = load_data()
    merged, audit = validate_join(customers, orders, how='left')
    unmatched_customers, unmatched_orders = find_unmatched(customers, orders)
    join_counts = compare_join_types(customers, orders)
    inspect_duplicates(orders)
    report = build_report(customers, orders, audit, unmatched_customers, unmatched_orders, join_counts)
    save_join_report(report)
    save_merged_output(merged)
    print('Merge validation complete.')
