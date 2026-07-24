import pandas as pd
from pathlib import Path


def strip_all_strings(df):
    """Strip whitespace from all string columns."""
    df_clean = df.copy()
    string_cols = df_clean.select_dtypes(include=['object']).columns
    whitespace_report = []

    for col in string_cols:
        if df_clean[col].dtype == 'object':
            before = df_clean[col].nunique(dropna=False)
            whitespace_count = df_clean[col].astype(str).apply(lambda x: x != x.strip() if pd.notna(x) else False).sum()
            df_clean[col] = df_clean[col].str.strip()
            after = df_clean[col].nunique(dropna=False)
            whitespace_report.append((col, whitespace_count, before, after))
            print(f"{col}: stripped whitespace from {whitespace_count} values, unique {before} → {after}")

    print("\nTotal string columns cleaned:", len(string_cols))
    return df_clean, whitespace_report


def normalize_casing(df, columns_to_lower):
    """Normalize casing for specified columns."""
    df_clean = df.copy()

    for col in columns_to_lower:
        if col not in df_clean.columns:
            print(f"Warning: {col} not found in DataFrame")
            continue

        before_sample = df_clean[col].head(5).tolist()
        df_clean[col] = df_clean[col].str.lower()
        after_sample = df_clean[col].head(5).tolist()
        print(f"Normalized {col} to lowercase")
        print(f"  before: {before_sample}")
        print(f"  after:  {after_sample}")

    return df_clean


def remove_special_characters(df, columns):
    """Remove special characters from specified columns."""
    df_clean = df.copy()

    for col in columns:
        if col not in df_clean.columns:
            print(f"Warning: {col} not found")
            continue

        before_sample = df_clean[col].head(5).tolist()
        df_clean[col] = df_clean[col].astype(str).str.replace('[^a-zA-Z0-9 ]', '', regex=True)
        after_sample = df_clean[col].head(5).tolist()
        print(f"Removed special characters from {col}")
        print(f"  before: {before_sample}")
        print(f"  after:  {after_sample}")

    return df_clean


def clean_text_column(series, lowercase=True, strip=True,
                      remove_special=False, mapping=None):
    """Reusable text cleaning function for any string column."""
    result = series.copy()

    if result.isna().any():
        print(f"Warning: {result.isna().sum()} null values in column {series.name}")

    if strip:
        result = result.astype(str).str.strip()

    if lowercase:
        result = result.str.lower()

    if remove_special:
        result = result.str.replace('[^a-zA-Z0-9 ]', '', regex=True)

    if mapping:
        result = result.map(mapping).fillna(result)

    return result


def standardize_segment(df, mapping):
    """Standardize segment labels using a mapping dictionary."""
    df_clean = df.copy()
    before_counts = df_clean['segment'].value_counts(dropna=False)
    df_clean['segment'] = clean_text_column(df_clean['segment'], lowercase=True, strip=True, remove_special=True)
    df_clean['segment'] = df_clean['segment'].map(mapping).fillna(df_clean['segment'])
    after_counts = df_clean['segment'].value_counts(dropna=False)

    print("\nSegment mapping applied")
    print("Before mapping:\n", before_counts.to_dict())
    print("After mapping:\n", after_counts.to_dict())
    return df_clean


def _ensure_processed_folder():
    processed_path = Path('data/processed')
    processed_path.mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    _ensure_processed_folder()

    input_file = Path('data/raw/messy_text_data.csv')
    if not input_file.exists():
        raise FileNotFoundError(f"Missing input file: {input_file}")

    df = pd.read_csv(input_file)

    print("\nInitial sample data:")
    print(df.head(10).to_string(index=False))

    print("\n1. Stripping whitespace from all string columns")
    df_clean, whitespace_report = strip_all_strings(df)

    print("\n2. Normalizing casing for categories")
    columns_to_lower = ['customer_name', 'product_category', 'segment', 'city']
    df_clean = normalize_casing(df_clean, columns_to_lower)

    print("\n3. Removing special characters")
    df_clean = remove_special_characters(df_clean, ['segment', 'city'])

    print("\n4. Standardizing categorical labels with mapping")
    segment_map = {
        'b2b': 'B2B',
        'b 2 b': 'B2B',
        'business-to-business': 'B2B',
        'smb': 'SMB',
        'small medium enterprise': 'SMB',
        'small-business': 'SMB',
        'enterprise': 'Enterprise',
        'ent': 'Enterprise'
    }
    df_clean = standardize_segment(df_clean, segment_map)

    output_file = Path('data/processed/cleaned_text_data.csv')
    df_clean.to_csv(output_file, index=False)
    print(f"\n✓ Cleaned text data saved to {output_file}")
