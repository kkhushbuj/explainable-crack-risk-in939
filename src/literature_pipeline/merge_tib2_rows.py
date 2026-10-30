import pandas as pd
import re

# Load both files
full_df = pd.read_csv("data/literature_extracted/high_value_data.csv")
clean = pd.read_csv("data/literature_extracted/clean_dataset_117.csv")

# Get the TiB2 paper rows
tib2_rows = full_df[full_df["source_file"] == "ssrn-4823280.pdf"].copy()

# Extract VED directly from the notes text
def extract_ved_from_notes(notes):
    match = re.search(r'VED:\s*(\d+\.?\d*)', str(notes))
    if match:
        return float(match.group(1))
    return None

tib2_rows["ved"] = tib2_rows["notes"].apply(extract_ved_from_notes)
tib2_usable = tib2_rows.dropna(subset=["ved"])
tib2_usable = tib2_usable[tib2_usable["crack_occurred"].isin(["Yes", "No"])]

print(f"Recovered {len(tib2_usable)} usable rows from TiB2 paper")
print(tib2_usable[["sample_id", "ved", "crack_occurred"]].to_string(index=False))

# Add 'ved' column to clean dataset (calculated the normal way) if missing
if "ved" not in clean.columns:
    clean["ved"] = None

# Merge and save
combined = pd.concat([clean, tib2_usable], ignore_index=True)
combined.to_csv("data/literature_extracted/clean_dataset_125.csv", index=False)

print(f"\nNew combined clean dataset: {len(combined)} rows")
yes_count = (combined["crack_occurred"] == "Yes").sum()
no_count = (combined["crack_occurred"] == "No").sum()
print(f"  Yes: {yes_count}, No: {no_count}")
print("Saved to data/literature_extracted/clean_dataset_125.csv")