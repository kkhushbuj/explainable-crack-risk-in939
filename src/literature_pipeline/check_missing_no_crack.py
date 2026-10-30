import pandas as pd

df = pd.read_csv("data/literature_extracted/high_value_data.csv")

# Get all rows where crack_occurred = "No"
no_crack_rows = df[df["crack_occurred"] == "No"].copy()
print(f"Total 'No' (didn't crack) rows: {len(no_crack_rows)}\n")

# Check which of these are MISSING at least one of the 4 needed parameters
needed_cols = ["laser_power_W", "scan_speed_mms", "hatch_spacing_mm", "layer_thickness_um"]

def is_missing_any(row):
    for col in needed_cols:
        val = row[col]
        if pd.isna(val) or str(val).strip().upper() in ("", "<UNKNOWN>", "NAN"):
            return True
    return False

no_crack_rows["missing_params"] = no_crack_rows.apply(is_missing_any, axis=1)

complete = no_crack_rows[~no_crack_rows["missing_params"]]
incomplete = no_crack_rows[no_crack_rows["missing_params"]]

print(f"'No' rows WITH complete parameters (already usable): {len(complete)}")
print(f"'No' rows MISSING parameters (worth double-checking manually): {len(incomplete)}\n")

print("=" * 80)
print("THESE ARE THE ROWS WORTH MANUALLY RE-CHECKING IN THE ORIGINAL PDF:")
print("=" * 80)
cols_to_show = ["source_file", "sample_id"] + needed_cols + ["notes"]
print(incomplete[cols_to_show].to_string(index=False))

incomplete.to_csv("data/literature_extracted/no_crack_missing_params.csv", index=False)
print("\nSaved to data/literature_extracted/no_crack_missing_params.csv")