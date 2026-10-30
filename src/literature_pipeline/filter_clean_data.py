import pandas as pd

df = pd.read_csv("data/literature_extracted/high_value_data.csv")

# Remove rows where key parameters are missing OR literally say "<UNKNOWN>"
key_cols = ["laser_power_W", "scan_speed_mms", "hatch_spacing_mm", "layer_thickness_um"]

for col in key_cols:
    df = df[df[col].notna()]  # remove real blanks
    df = df[df[col].astype(str).str.upper() != "<UNKNOWN>"]  # remove literal "<UNKNOWN>" text

# Keep only rows with a clear Yes/No crack answer
df = df[df["crack_occurred"].isin(["Yes", "No"])]

print(f"Filtered dataset: {len(df)} rows")

df.to_csv("data/literature_extracted/clean_dataset_117.csv", index=False)
print("Saved to data/literature_extracted/clean_dataset_117.csv")