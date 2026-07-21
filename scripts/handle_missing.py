"""
Missing Value Detection and Imputation Module

This module identifies incomplete records across all columns, applies strategy-specific
imputation based on column type and business context, documents every decision with
reasoning, and validates before/after metrics.

Strategies:
  - Numerical (median): Resistant to outliers, preserves distribution
  - Categorical (mode): Most common value, preserves category meaning
  - Time-series (forward fill): Previous value, assumes no change between observations
  - Critical IDs (drop rows): Cannot impute identifiers, only strategy for critical columns
"""

from datetime import datetime
from pathlib import Path
import json
import pandas as pd
import numpy as np


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "output"


def analyze_missing_values(df):
    """
    Compute null counts and percentages before treatment.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        DataFrame with analysis of missing data by column
    """
    missing_analysis = pd.DataFrame({
        'column': df.columns,
        'null_count': df.isnull().sum().values,
        'null_percentage': (df.isnull().sum() / len(df) * 100).round(2).values,
        'data_type': df.dtypes.values
    })
    
    print("\n" + "="*80)
    print("BEFORE IMPUTATION - Missing Value Analysis")
    print("="*80)
    print(missing_analysis.to_string(index=False))
    print(f"\nTotal rows: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Total cells: {len(df) * len(df.columns):,}")
    print(f"Missing cells: {df.isnull().sum().sum():,}")
    print("="*80 + "\n")
    
    return missing_analysis


def impute_mean_median(df, numerical_cols, strategy='median'):
    """
    Fill numerical nulls with mean or median.
    
    Args:
        df: DataFrame to impute
        numerical_cols: List of numerical column names
        strategy: 'median' or 'mean'
        
    Returns:
        DataFrame with imputed values
    """
    df_imputed = df.copy()
    print("Imputing numerical columns with {}:".format(strategy))
    
    for col in numerical_cols:
        if col in df_imputed.columns and df_imputed[col].isnull().sum() > 0:
            if strategy == 'median':
                fill_value = df_imputed[col].median()
            else:
                fill_value = df_imputed[col].mean()
            
            null_count = df_imputed[col].isnull().sum()
            df_imputed[col] = df_imputed[col].fillna(fill_value)
            print(f"  ✓ {col}: filled {null_count} nulls with {strategy} ({fill_value:.2f})")
    
    return df_imputed


def impute_mode(df, categorical_cols):
    """
    Fill categorical nulls with mode (most common value).
    
    Args:
        df: DataFrame to impute
        categorical_cols: List of categorical column names
        
    Returns:
        DataFrame with imputed values
    """
    df_imputed = df.copy()
    print("Imputing categorical columns with mode:")
    
    for col in categorical_cols:
        if col in df_imputed.columns and df_imputed[col].isnull().sum() > 0:
            mode_val = df_imputed[col].mode()[0] if len(df_imputed[col].mode()) > 0 else 'UNKNOWN'
            null_count = df_imputed[col].isnull().sum()
            df_imputed[col] = df_imputed[col].fillna(mode_val)
            print(f"  ✓ {col}: filled {null_count} nulls with mode '{mode_val}'")
    
    return df_imputed


def impute_forward_fill(df, time_series_cols):
    """
    Fill with previous value (for time-series data).
    Assumes data is sorted by time and values do not change between observations.
    
    Args:
        df: DataFrame to impute
        time_series_cols: List of time-series column names
        
    Returns:
        DataFrame with forward-filled values
    """
    df_imputed = df.copy()
    print("Imputing time-series columns with forward fill:")
    
    for col in time_series_cols:
        if col in df_imputed.columns and df_imputed[col].isnull().sum() > 0:
            null_count = df_imputed[col].isnull().sum()
            df_imputed[col] = df_imputed[col].fillna(method='ffill')
            # Backward fill for any remaining nulls at the start
            df_imputed[col] = df_imputed[col].fillna(method='bfill')
            print(f"  ✓ {col}: forward-filled {null_count} nulls")
    
    return df_imputed


def drop_rows_with_nulls(df, critical_cols):
    """
    Drop rows where critical columns are null.
    Only strategy for critical identifiers that cannot be imputed.
    
    Args:
        df: DataFrame to filter
        critical_cols: List of critical column names
        
    Returns:
        DataFrame with rows containing nulls in critical columns removed
    """
    rows_before = len(df)
    # Only drop for columns that actually exist in the dataframe
    cols_to_check = [col for col in critical_cols if col in df.columns]
    
    if cols_to_check:
        df_imputed = df.dropna(subset=cols_to_check)
        rows_dropped = rows_before - len(df_imputed)
        print(f"Dropping rows with nulls in critical columns:")
        print(f"  ✓ Dropped {rows_dropped} rows with null in: {cols_to_check}")
        return df_imputed
    
    return df


def document_imputation_decisions(df_before, df_after, decisions_config):
    """
    Document all imputation decisions with business justification.
    
    Args:
        df_before: Original DataFrame before imputation
        df_after: DataFrame after imputation
        decisions_config: Dictionary of decisions with business reasoning
        
    Returns:
        Dictionary of documented decisions
    """
    decisions = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'rows_before': len(df_before),
            'rows_after': len(df_after),
            'rows_removed': len(df_before) - len(df_after),
            'total_nulls_before': int(df_before.isnull().sum().sum()),
            'total_nulls_after': int(df_after.isnull().sum().sum())
        },
        'decisions': decisions_config
    }
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / 'imputation_decisions.json'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(decisions, f, indent=2, default=str)
    
    print(f"\n✓ Imputation decisions documented to {output_path}")
    
    return decisions


def validate_imputation(df_before, df_after):
    """
    Compare metrics before and after imputation.
    
    Args:
        df_before: DataFrame before imputation
        df_after: DataFrame after imputation
        
    Returns:
        DataFrame with before/after null comparison
    """
    
    print("\n" + "="*80)
    print("AFTER IMPUTATION - Validation Report")
    print("="*80)
    print(f"Total rows before:    {len(df_before):,}")
    print(f"Total rows after:     {len(df_after):,}")
    print(f"Rows removed:         {len(df_before) - len(df_after):,}")
    print(f"\nTotal nulls before:   {df_before.isnull().sum().sum():,}")
    print(f"Total nulls after:    {df_after.isnull().sum().sum():,}")
    
    validation_report = pd.DataFrame({
        'column': df_after.columns,
        'null_count_before': df_before[df_after.columns].isnull().sum().values,
        'null_count_after': df_after.isnull().sum().values,
        'null_pct_before': (df_before[df_after.columns].isnull().sum() / len(df_before) * 100).round(2).values,
        'null_pct_after': (df_after.isnull().sum() / len(df_after) * 100).round(2).values
    })
    
    print("\nNull values by column - Before vs After:")
    print(validation_report.to_string(index=False))
    print("="*80 + "\n")
    
    return validation_report


def handle_missing_values_workflow(input_file, output_file=None):
    """
    End-to-end workflow for missing value detection and imputation.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file (default: data/processed/cleaned_data.csv)
        
    Returns:
        Imputed DataFrame
    """
    
    # Set default output path
    if output_file is None:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        output_file = PROCESSED_DIR / 'cleaned_data.csv'
    
    print("\n" + "="*80)
    print("MISSING VALUE IMPUTATION WORKFLOW")
    print("="*80)
    
    # Load data
    print(f"\n[1/5] Loading data from {input_file}...")
    df = pd.read_csv(input_file)
    print(f"✓ Loaded {len(df):,} rows and {len(df.columns)} columns")
    
    # Analyze missing before treatment
    print("\n[2/5] Analyzing missing values...")
    df_before = df.copy()
    analyze_missing_values(df_before)
    
    # Apply imputation strategies
    print("\n[3/5] Applying imputation strategies...")
    
    # Strategy 1: Drop rows with nulls in critical identifier columns
    critical_cols = [col for col in ['customer_id', 'id'] if col in df.columns]
    if critical_cols:
        df = drop_rows_with_nulls(df, critical_cols)
    
    # Strategy 2: Identify numerical and categorical columns
    numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'str']).columns.tolist()
    
    # Remove critical ID columns from imputation (already handled)
    numerical_cols = [col for col in numerical_cols if col not in critical_cols]
    categorical_cols = [col for col in categorical_cols if col not in critical_cols]
    
    # Impute numerical columns with median
    if numerical_cols:
        df = impute_mean_median(df, numerical_cols, strategy='median')
    
    # Impute categorical columns with mode
    if categorical_cols:
        df = impute_mode(df, categorical_cols)
    
    # Document decisions
    print("\n[4/5] Documenting imputation decisions...")
    
    decisions_config = {}
    
    # Document each imputation strategy
    if critical_cols:
        decisions_config['critical_identifiers'] = {
            'columns': critical_cols,
            'strategy': 'drop_rows',
            'business_reasoning': 'Critical identifiers (customer_id, id) cannot be imputed. Rows without identifiers are incomplete records and cannot be traced or linked to other data sources.',
            'risk_assessment': 'Low - removes only records missing key identifiers'
        }
    
    if numerical_cols:
        decisions_config['numerical_columns'] = {
            'columns': numerical_cols,
            'strategy': 'median_imputation',
            'business_reasoning': 'Median is robust to outliers and preserves the distribution of numerical values. Appropriate for quantities, amounts, and measurements.',
            'risk_assessment': 'Low - median is a stable central tendency measure'
        }
    
    if categorical_cols:
        decisions_config['categorical_columns'] = {
            'columns': categorical_cols,
            'strategy': 'mode_imputation',
            'business_reasoning': 'Mode (most common value) preserves categorical distributions. Filling with the most frequent category maintains data integrity.',
            'risk_assessment': 'Low - maintains category distribution'
        }
    
    document_imputation_decisions(df_before, df, decisions_config)
    
    # Validate results
    print("\n[5/5] Validating imputation...")
    validate_imputation(df_before, df)
    
    # Save cleaned data
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"✓ Cleaned data saved to {output_file}")
    
    print("\n" + "="*80)
    print("IMPUTATION WORKFLOW COMPLETE")
    print("="*80 + "\n")
    
    return df


if __name__ == "__main__":
    # Define input file - prioritize missing_data.csv if it exists, otherwise use sample.csv
    missing_data_file = RAW_DIR / 'missing_data.csv'
    sample_file = RAW_DIR / 'sample.csv'
    
    input_file = missing_data_file if missing_data_file.exists() else sample_file
    
    # Run imputation workflow
    df_cleaned = handle_missing_values_workflow(input_file)
