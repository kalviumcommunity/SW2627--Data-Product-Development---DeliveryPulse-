import json
from pathlib import Path

import pandas as pd


def load_data(path='data/raw/validation_data.csv'):
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Missing input file: {file_path}")
    return pd.read_csv(file_path)


def define_validation_rules(df):
    """Apply validation rules and return a DataFrame with rule results."""
    df_validated = df.copy()

    # Range checks
    df_validated['valid_birth_date_range'] = (
        pd.to_datetime(df_validated['birth_date'], errors='coerce') >= pd.Timestamp('1920-01-01')
    ) & (
        pd.to_datetime(df_validated['birth_date'], errors='coerce') <= pd.Timestamp.now()
    )
    df_validated['valid_price'] = df_validated['price'] >= 0

    # Null checks
    df_validated['valid_customer_id'] = df_validated['customer_id'].notna()
    df_validated['valid_email_not_null'] = df_validated['email'].notna()
    df_validated['valid_product_category'] = df_validated['product_category'].notna() & (df_validated['product_category'].str.strip() != '')

    # Format checks
    df_validated['valid_email_format'] = df_validated['email'].astype(str).str.contains('@', na=False)
    df_validated['valid_phone_format'] = df_validated['phone'].astype(str).str.match(r'^\d{10}$', na=False)

    # Business rule checks
    df_validated['valid_campaign_dates'] = (
        pd.to_datetime(df_validated['campaign_start_date'], errors='coerce') <=
        pd.to_datetime(df_validated['campaign_end_date'], errors='coerce')
    )
    df_validated['valid_end_date_after_start'] = (
        pd.to_datetime(df_validated['end_date'], errors='coerce') >=
        pd.to_datetime(df_validated['start_date'], errors='coerce')
    )

    # Referential integrity sample: order.customer_id must exist in customer_master
    customer_master = df_validated['customer_id'].dropna().unique()
    df_validated['valid_customer_reference'] = df_validated['customer_id'].isin(customer_master)

    return df_validated


def summarize_validation(df_validated):
    """Summarize validation results across all rules."""
    rule_columns = [
        col for col in df_validated.columns if col.startswith('valid_')
    ]

    summary = []
    for col in rule_columns:
        passed = df_validated[col].sum()
        failed = len(df_validated) - passed
        summary.append({
            'rule': col,
            'passed': int(passed),
            'failed': int(failed),
            'failure_rate_pct': round(failed / len(df_validated) * 100, 2)
        })

    summary_df = pd.DataFrame(summary)
    return summary_df


def isolate_failures(df_validated):
    """Isolate records that fail any validation rule."""
    rule_columns = [
        col for col in df_validated.columns if col.startswith('valid_')
    ]
    df_validated['passes_all_checks'] = df_validated[rule_columns].all(axis=1)
    failures = df_validated[~df_validated['passes_all_checks']].copy()
    valid_records = df_validated[df_validated['passes_all_checks']].copy()
    return valid_records, failures


def save_reports(valid_records, failures, summary_df):
    output_path = Path('output')
    output_path.mkdir(parents=True, exist_ok=True)

    valid_records.to_csv(output_path / 'validation_passed.csv', index=False)
    failures.to_csv(output_path / 'validation_failures.csv', index=False)
    summary_df.to_csv(output_path / 'validation_summary.csv', index=False)

    log = {
        'passed_records': int(len(valid_records)),
        'failed_records': int(len(failures)),
        'rules_reported': int(len(summary_df)),
    }
    with open(output_path / 'validation_report.json', 'w') as f:
        json.dump(log, f, indent=2)

    return output_path


if __name__ == '__main__':
    df = load_data()
    df_validated = define_validation_rules(df)
    summary_df = summarize_validation(df_validated)
    valid_records, failures = isolate_failures(df_validated)
    save_reports(valid_records, failures, summary_df)

    print('Validation complete')
    print(summary_df.to_string(index=False))
    print(f'Passed: {len(valid_records)} rows')
    print(f'Failed: {len(failures)} rows')
