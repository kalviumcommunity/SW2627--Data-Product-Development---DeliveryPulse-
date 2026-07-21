# Video Explanation Guide - Missing Value Detection & Imputation

## Point 1: Mean vs Median vs Mode - When Each is Appropriate

### The Three Methods:
1. **Mean (Arithmetic Average)**
   - Sum of all values divided by count
   - Example: (100 + 200 + 300) / 3 = 200
   - **Risk**: Heavily skewed by outliers
   - Example: Salaries of [30k, 35k, 40k, 1000k] → mean is 276k (misleading!)

2. **Median (50th Percentile)**
   - Middle value when sorted; same example → median is 37.5k (accurate)
   - **Advantage**: Ignores extreme values, robust to outliers
   - **When to use**: Revenue, purchase amounts, transaction values
   - **Example in code**: `df['amount'].median()` → fills with 187.88

3. **Mode (Most Frequent Value)**
   - The value that appears most often
   - **When to use**: Category, region, segment, status
   - Example: ["A", "B", "A", "A", "C"] → mode is "A"
   - **Why it works**: Preserves categorical distribution

### Risk Assessment:
| Strategy | Risk | When to Use |
|----------|------|------------|
| Mean | HIGH - skewed by outliers | Few nulls in clean data only |
| Median | LOW - stable, distribution-preserving | Numerical columns (quantities, amounts) |
| Mode | LOW - maintains categories | Categorical columns (regions, types) |

## Point 2: Forward Fill for Time-Series Data

### What is Forward Fill (ffill)?
- Fills null with the most recent non-null value
- Assumes the status hasn't changed between observations

### Example Timeline:
```
Date        | Status    | After Forward Fill
------------|-----------|------------------
2025-01-01  | Active    | Active
2025-01-02  | Active    | Active  (copied from above)
2025-01-03  | NULL      | Active  (copied from 2025-01-02)
2025-01-04  | NULL      | Active  (copied from 2025-01-03)
2025-01-05  | Inactive  | Inactive
```

### When It's Appropriate:
- ✓ Inventory levels (assume quantity unchanged if not recorded)
- ✓ Account status (assume still active if not updated)
- ✗ Volatile metrics (stock prices, temperature - too risky)
- ✗ Event data (missed events shouldn't be assumed unchanged)

### The Assumption It Makes:
**"If I don't see an update, the previous value is still valid."**
- This is SAFE for slowly-changing dimensions
- This is DANGEROUS for fast-moving metrics

### In the Code:
```python
df['price'].fillna(method='ffill')  # Last known price carries forward
df[col].fillna(method='bfill')      # Backup fill if nulls at start
```

## Point 3: The Over-Imputation Risk

### The Core Risk:
**Imputing data artificially inflates confidence. You're inventing data that didn't exist.**

### Real Scenario Example:
- Dataset: 5,000 transactions
- Revenue column: 20% missing (1,000 nulls)
- You fill all 1,000 with median
- **Result**: Your data is now 20% synthetic!
- **Danger**: Downstream analysts believe it's all real
- **Problem**: Correlations become artificial, statistics become unreliable

### Visual Impact:
```
Before: 80% real data + 20% MISSING
After:  80% real data + 20% SYNTHETIC (but looks complete!)
```

### Why This Breaks Analysis:
1. **False confidence**: "No nulls" != "All real"
2. **Inflated sample size**: Using 5,000 rows when only 4,000 are real
3. **Artificial correlations**: If you filled based on median, those 1,000 are now identical
4. **Statistical distortion**: Standard deviation becomes artificially lower

### When to Drop Instead:
- ✓ Missing customer_id → Can't trace the record (DROP)
- ✓ Missing on critical dates → Data collection failure (DROP)
- ✓ 50%+ missing in a column → Too much synthetic data (DROP)
- ✗ <5% missing in non-critical columns → Safe to fill (FILL)

### Documentation is Critical:
```json
"amount": {
    "strategy": "median_imputation",
    "null_count_before": 1,
    "null_percentage": 0.01,  ← This is key! Track what % is synthetic
    "value_used": 187.88,
    "business_reasoning": "Only 0.01% of transactions missing"
}
```

### The Rule:
**For X% missing, ask: "Am I comfortable with X% synthetic data in this analysis?"**

## Point 4: Walk-Through of One Imputation Decision

### Example from cleaned_data.csv:
**Column: amount (Row 7 - Grace)**

**Before:**
```csv
customer_id,name,email,amount,category,region
7,Grace,grace@example.com,NULL,B,North
```

**After:**
```csv
customer_id,name,email,amount,category,region
7.0,Grace,grace@example.com,187.875,B,North
```

### The Decision Process:

**Step 1: Identify the Problem**
- Column: `amount` (numerical, purchase value)
- Type: NUMERICAL DATA
- Missing: 1 row out of 10 (10%)
- Business meaning: How much Grace spent

**Step 2: Why Median?**
- Amount is a transaction value
- Could be skewed by outliers (one big purchase)
- Data: [100.5, 250, 100.75, 200.25, 175.5, 187.88, 300, 425.75, 150]
- Median of these: 187.88 (middle value when sorted)
- Mean would be: 210.67 (higher, skewed by 425.75)

**Step 3: Business Reasoning**
```
"Median purchase amount (187.88) is representative of typical 
transaction. Mean would be skewed by high-value outliers. 
Maintains distribution integrity for downstream analysis."
```

**Step 4: Risk Assessment**
- Only 1 row missing (10%) → Low risk
- Not a critical identifier → Safe to fill
- Median is robust → Low statistical risk
- **Final decision**: FILL with median ✓

**Step 5: Log the Decision**
```json
{
    "column": "amount",
    "column_type": "numerical",
    "null_count_before": 1,
    "strategy": "median_imputation",
    "value_used": 187.88,
    "business_reasoning": "Median purchase...",
    "risk_assessment": "Low - median is stable..."
}
```

## Point 5: Handling Missing Values in Key Identifiers (customer_id)

### The Golden Rule:
**NEVER IMPUTE A PRIMARY KEY OR CRITICAL IDENTIFIER**

### Why Not?
1. **Cannot be traced**: If you don't know WHO the customer is, you can't use the record
2. **Creates ghost records**: Artificial customer with synthetic ID
3. **Breaks joins**: Can't link to other tables without real ID
4. **Violates data integrity**: Primary key must be unique and meaningful

### What You DO:
**DROP THE ROW ENTIRELY**
```python
df = df.dropna(subset=['customer_id'])  # Only strategy for IDs
```

### Real Impact Example:
```
Before: 10 rows (1 missing customer_id)
After:  9 rows (dropped the incomplete record)
```

### Why This is Better:
- ✓ No synthetic data
- ✓ No ghost records
- ✓ All remaining records are traceable
- ✓ Data integrity maintained
- ✓ Audit trail clear: "1 row dropped due to missing identifier"

### In the Test Data (Row 4 - Diana):
```csv
customer_id,name,email,amount,category,region
,Diana,diana@example.com,500.00,C,East  ← Empty customer_id
```

**Decision**: DROP THIS ROW
- Cannot identify Diana in the system
- Cannot link to transaction history
- Cannot contact for follow-up
- Record is incomplete and unusable
- **Result**: Row removed, data integrity maintained

### What You NEVER Do:
- ❌ Fill with "UNKNOWN" → Creates fake customer
- ❌ Fill with NULL_ID_001 → Synthetic ID
- ❌ Fill with 0 → False customer
- ❌ Generate random ID → Data integrity violation

### Contrast: What You CAN Fill:
| Column | Type | Can Fill? | Why |
|--------|------|-----------|-----|
| customer_id | Key | NO | Can't impute identifiers |
| email | Attribute | YES (mode) | Can guess from similar customers |
| purchase_amount | Numerical | YES (median) | Can estimate typical value |
| region | Category | YES (mode) | Can fill with most common |

### Summary for This Point:
- **Identifiers**: DROP rows with nulls
- **Critical columns**: Only drop, never fill
- **Other columns**: Choose strategy based on type
- **Documentation**: Always log why decision was made
