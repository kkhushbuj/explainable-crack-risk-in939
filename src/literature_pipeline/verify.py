import pandas as pd
import numpy as np

df = pd.read_csv("data/literature_extracted/high_value_data.csv")

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 80)

print(f"Total rows in dataset: {len(df)}\n")

# ---- CHECK 1: Row count per paper ----
print("=" * 70)
print("ROW COUNT PER PAPER")
print("=" * 70)
print(df['source_file'].value_counts())

# ---- CHECK 2: Show the flagged rows specifically (already known, not deleted) ----
print("\n" + "=" * 70)
print("FLAGGED ROWS (kept, just marked for awareness)")
print("=" * 70)
if 'flagged_for_review' in df.columns:
    flagged = df[df['flagged_for_review'].notna()]
    print(f"Found {len(flagged)} flagged rows\n")
    review_cols = ['source_file', 'sample_id', 'laser_power_W', 'scan_speed_mms',
                   'layer_thickness_um', 'hatch_spacing_mm', 'flagged_for_review', 'notes']
    review_cols = [c for c in review_cols if c in flagged.columns]
    print(flagged[review_cols].to_string())
else:
    print("No 'flagged_for_review' column found.")

# ---- CHECK 3: Automated sanity checks (excluding flagged rows, since those are expected) ----
print("\n" + "=" * 70)
print("AUTOMATED ERROR-CATCHING (unflagged rows only)")
print("=" * 70)

issues_found = []

def to_numeric_safe(val):
    if pd.isna(val):
        return None
    import re
    numbers = re.findall(r'\d+\.?\d*', str(val))
    return [float(n) for n in numbers] if numbers else None

unflagged = df[df['flagged_for_review'].isna()] if 'flagged_for_review' in df.columns else df

for idx, row in unflagged.iterrows():
    nums = to_numeric_safe(row.get('relative_density_percent'))
    if nums:
        for n in nums:
            if n < 0 or n > 100:
                issues_found.append(f"Row {idx} ({row['source_file']}): relative_density_percent = {row['relative_density_percent']} is impossible")

core_fields = ['laser_power_W', 'scan_speed_mms', 'layer_thickness_um', 'hatch_spacing_mm']
core_fields = [c for c in core_fields if c in df.columns]
mostly_empty = unflagged[core_fields].isna().sum(axis=1) == len(core_fields)
if mostly_empty.any():
    for idx in unflagged[mostly_empty].index:
        issues_found.append(f"Row {idx} ({df.loc[idx, 'source_file']}): ALL core parameter fields are empty")

if issues_found:
    print(f"Found {len(issues_found)} potential issues:\n")
    for issue in issues_found:
        print(f"  - {issue}")
else:
    print("No obvious errors detected in unflagged rows.")

# ---- CHECK 4: Random sample for manual verification ----
print("\n" + "=" * 70)
print("RANDOM SAMPLE FOR MANUAL VERIFICATION (20 rows)")
print("=" * 70)

sample_size = min(20, len(df))
sample = df.sample(n=sample_size, random_state=1)

review_cols = ['source_file', 'sample_id', 'laser_power_W', 'scan_speed_mms',
               'layer_thickness_um', 'hatch_spacing_mm', 'relative_density_percent',
               'crack_occurred', 'notes']
review_cols = [c for c in review_cols if c in df.columns]

for idx, row in sample.iterrows():
    print(f"\n--- Row {idx} ---")
    for col in review_cols:
        print(f"  {col}: {row[col]}")

sample.to_csv("data/literature_extracted/random_sample_for_review.csv", index=False)
print(f"\n\nSaved {sample_size}-row random sample to data/literature_extracted/random_sample_for_review.csv")

print("\n" + "=" * 70)
print("DONE.")
print("=" * 70)