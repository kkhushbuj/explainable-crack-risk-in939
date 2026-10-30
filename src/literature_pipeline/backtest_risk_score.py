"""
Backtest using BOTH VED and doping status as clues, still predicting
a simple Yes/No crack outcome.
"""

import pandas as pd
import numpy as np
import re

CSV_PATH = "data/literature_extracted/clean_dataset_125.csv"
K_NEIGHBORS = 5
RANDOM_SEED = 42
BUILD_YES_COUNT = 15
BUILD_NO_COUNT = 8


def parse_single_number(val):
    if pd.isna(val):
        return None
    nums = re.findall(r'\d+\.?\d*', str(val))
    if not nums:
        return None
    return sum(float(n) for n in nums) / len(nums)


def calculate_ved_from_params(row):
    power = parse_single_number(row.get("laser_power_W"))
    speed = parse_single_number(row.get("scan_speed_mms"))
    hatch = parse_single_number(row.get("hatch_spacing_mm"))
    layer_um = parse_single_number(row.get("layer_thickness_um"))
    if None in (power, speed, hatch, layer_um) or speed == 0 or hatch == 0 or layer_um == 0:
        return None
    return power / (speed * hatch * (layer_um / 1000.0))


def normalize_crack_label(val):
    if pd.isna(val):
        return None
    val = str(val).strip().lower()
    if val == "yes":
        return 1
    if val == "no":
        return 0
    return None


def normalize_doped(val):
    if pd.isna(val):
        return 0  # treat unclear as "not doped" (majority case)
    val = str(val).strip().lower()
    return 1 if val == "yes" else 0


def calculate_metrics(results):
    tp_no = ((results["predicted"] == "No") & (results["actual"] == "No")).sum()
    fp_no = ((results["predicted"] == "No") & (results["actual"] == "Yes")).sum()
    fn_no = ((results["predicted"] == "Yes") & (results["actual"] == "No")).sum()

    def safe_div(a, b):
        return a / b if b > 0 else 0.0

    precision_no = safe_div(tp_no, tp_no + fp_no)
    recall_no = safe_div(tp_no, tp_no + fn_no)
    f1_no = safe_div(2 * precision_no * recall_no, precision_no + recall_no)
    return precision_no, recall_no, f1_no


def main():
    df = pd.read_csv(CSV_PATH)

    if "ved" in df.columns:
        existing_ved = pd.to_numeric(df["ved"], errors="coerce")
    else:
        existing_ved = pd.Series([None] * len(df), index=df.index)
    calculated_ved = df.apply(calculate_ved_from_params, axis=1)
    df["ved_final"] = existing_ved.fillna(calculated_ved)

    df["crack_label"] = df["crack_occurred"].apply(normalize_crack_label)
    df["doped_label"] = df["is_doped"].apply(normalize_doped) if "is_doped" in df.columns else 0

    usable = df.dropna(subset=["ved_final", "crack_label"]).copy()
    usable["crack_label"] = usable["crack_label"].astype(int)
    usable["ved"] = usable["ved_final"]

    n_yes = (usable["crack_label"] == 1).sum()
    n_no = (usable["crack_label"] == 0).sum()
    print(f"Loaded {len(usable)} usable rows: {n_yes} Yes, {n_no} No\n")

    yes_rows = usable[usable["crack_label"] == 1].sample(n=BUILD_YES_COUNT, random_state=RANDOM_SEED)
    no_rows = usable[usable["crack_label"] == 0].sample(n=BUILD_NO_COUNT, random_state=RANDOM_SEED)
    build_set = pd.concat([yes_rows, no_rows])
    test_set = usable.drop(build_set.index)

    print(f"Build set: {len(build_set)} rows ({BUILD_YES_COUNT} Yes, {BUILD_NO_COUNT} No)")
    print(f"Test set:  {len(test_set)} rows ({(test_set['crack_label']==1).sum()} Yes, "
          f"{(test_set['crack_label']==0).sum()} No)\n")

    build_ved = build_set["ved"].values
    build_doped = build_set["doped_label"].values
    build_labels = build_set["crack_label"].values

    # Normalize VED distance to 0-1 range so it's comparable to the doping match (0 or 1)
    ved_range = build_ved.max() - build_ved.min()

    predictions = []
    for _, row in test_set.iterrows():
        ved_dist = np.abs(build_ved - row["ved"]) / (ved_range if ved_range > 0 else 1)
        doping_dist = np.abs(build_doped - row["doped_label"])  # 0 if same doping status, 1 if different

        # Combined distance: both clues matter, doping mismatch is heavily penalized
        combined_dist = ved_dist + (doping_dist * 2)  # doping mismatch weighted 2x

        nearest_idx = np.argsort(combined_dist)[:K_NEIGHBORS]
        neighbor_labels = build_labels[nearest_idx]
        risk_score = neighbor_labels.mean()
        predicted_class = 1 if risk_score >= 0.5 else 0

        predictions.append({
            "source_file": row["source_file"],
            "sample_id": row.get("sample_id"),
            "ved": round(row["ved"], 1),
            "doped": "Yes" if row["doped_label"] == 1 else "No",
            "risk_score": round(risk_score, 2),
            "predicted": "Yes" if predicted_class == 1 else "No",
            "actual": "Yes" if row["crack_label"] == 1 else "No",
            "correct": predicted_class == row["crack_label"],
        })

    results = pd.DataFrame(predictions)
    accuracy = results["correct"].mean() * 100

    print("=" * 70)
    print(f"Overall accuracy: {accuracy:.1f}%")
    print("=" * 70)

    precision_no, recall_no, f1_no = calculate_metrics(results)
    n_no_test = (results["actual"] == "No").sum()
    print(f"\n'No' class metrics: Precision={precision_no:.2f}  Recall={recall_no:.2f}  "
          f"F1={f1_no:.2f}  (tested on {n_no_test} real 'No' examples)")

    no_actuals = results[results["actual"] == "No"]
    print("\nHow the model did specifically on the true 'No' rows:")
    print(no_actuals.to_string(index=False))

    yes_predicted_count = (results["predicted"] == "Yes").sum()
    no_predicted_count = (results["predicted"] == "No").sum()
    print(f"\nPrediction breakdown: {yes_predicted_count} predicted 'Yes', {no_predicted_count} predicted 'No'")

    results.to_csv("data/literature_extracted/backtest_results.csv", index=False)
    print("\nSaved detailed results to data/literature_extracted/backtest_results.csv")


if __name__ == "__main__":
    main()