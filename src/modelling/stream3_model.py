"""
Stream 3 - ML Detection + SHAP explainability.

Trains an actual supervised classifier (Random Forest) on the 129-sample
literature dataset (Stream 2's output) - this is the one dataset large
enough to support real training, cross-validation, and meaningful SHAP
explainability.

The real sensor specimens (Stream 1) are NOT used to train this model -
there are only ~10 of them and no confirmed ground truth, which is not
enough to train or rigorously validate a classifier. Instead, the trained
model is applied to the real specimens' estimated process parameters
(from the borrowed reference recipe) to produce a second, independent
risk estimate, which is then placed side-by-side with the AE-signal-based
proxy classification from Stream 1 as an illustrative case-study
comparison - not a statistically validated result.
"""

import re
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RANDOM_SEED = 42


def parse_num(v):
    if pd.isna(v):
        return None
    nums = re.findall(r'\d+\.?\d*', str(v))
    return sum(float(n) for n in nums) / len(nums) if nums else None


def calc_ved(row):
    p, s, h, l = (parse_num(row.get(c)) for c in
                  ["laser_power_W", "scan_speed_mms", "hatch_spacing_mm", "layer_thickness_um"])
    if None in (p, s, h, l) or s == 0 or h == 0 or l == 0:
        return None
    return p / (s * h * (l / 1000.0))


def build_dataset(path):
    df = pd.read_csv(path)
    df["ved_final"] = pd.to_numeric(df.get("ved"), errors="coerce")
    df["ved_final"] = df["ved_final"].fillna(df.apply(calc_ved, axis=1))
    df["laser_power_W_n"] = df["laser_power_W"].apply(parse_num)
    df["scan_speed_mms_n"] = df["scan_speed_mms"].apply(parse_num)
    df["hatch_spacing_mm_n"] = df["hatch_spacing_mm"].apply(parse_num)
    df["layer_thickness_um_n"] = df["layer_thickness_um"].apply(parse_num)
    df["doped_label"] = df["is_doped"].apply(
        lambda v: 1 if str(v).strip().lower() == "yes" else 0) if "is_doped" in df.columns else 0
    df["crack_label"] = df["crack_occurred"].apply(
        lambda v: 1 if str(v).strip().lower() == "yes" else (0 if str(v).strip().lower() == "no" else None))

    feature_cols = ["ved_final", "laser_power_W_n", "scan_speed_mms_n",
                     "hatch_spacing_mm_n", "layer_thickness_um_n", "doped_label"]
    usable = df.dropna(subset=["ved_final", "crack_label"]).copy()
    usable["crack_label"] = usable["crack_label"].astype(int)
    for c in feature_cols:
        if c != "doped_label":
            usable[c] = usable[c].fillna(usable[c].median())
    return usable, feature_cols


def main():
    df, feature_cols = build_dataset("/home/claude/clean_dataset_125.csv")
    X = df[feature_cols].values
    y = df["crack_label"].values

    print(f"Dataset: {len(df)} samples, {y.sum()} Yes / {len(y) - y.sum()} No")
    print(f"Features used: {feature_cols}\n")

    # Stratified 5-fold cross-validation (appropriate for a small, imbalanced
    # dataset - every sample gets used for both training and testing across
    # folds, giving a more honest performance estimate than one fixed split).
    clf = RandomForestClassifier(
        n_estimators=200, max_depth=4, min_samples_leaf=3,
        class_weight="balanced", random_state=RANDOM_SEED)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    y_pred = cross_val_predict(clf, X, y, cv=skf)

    acc = accuracy_score(y, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y, y_pred, labels=[0], average=None, zero_division=0)
    cm = confusion_matrix(y, y_pred)

    print("=" * 70)
    print("RANDOM FOREST - 5-FOLD CROSS-VALIDATED PERFORMANCE")
    print("=" * 70)
    print(f"Overall accuracy: {acc * 100:.1f}%")
    print(f"'No' (no-crack) class: Precision={prec[0]:.2f}  Recall={rec[0]:.2f}  F1={f1[0]:.2f}")
    print(f"Confusion matrix [[TN, FP], [FN, TP]] (0=No, 1=Yes):\n{cm}\n")

    # Fit final model on all data for SHAP + real-specimen application
    clf.fit(X, y)

    explainer = shap.TreeExplainer(clf)
    shap_values = explainer.shap_values(X)
    # shap_values shape handling across shap versions (list vs array)
    if isinstance(shap_values, list):
        sv_class1 = shap_values[1]
    elif shap_values.ndim == 3:
        sv_class1 = shap_values[:, :, 1]
    else:
        sv_class1 = shap_values

    mean_abs_shap = np.abs(sv_class1).mean(axis=0)
    importance = sorted(zip(feature_cols, mean_abs_shap), key=lambda x: -x[1])
    print("SHAP feature importance (mean |SHAP value|, predicting crack=Yes):")
    for feat, val in importance:
        print(f"  {feat:<22} {val:.4f}")

    # SHAP summary plot
    plt.figure()
    shap.summary_plot(sv_class1, X, feature_names=feature_cols, show=False)
    plt.tight_layout()
    plt.savefig("/home/claude/shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("\nSaved SHAP summary plot to shap_summary.png")

    # ---- Apply trained model to the real sensor specimens ----
    # Using the two candidate estimated recipes from the matched reference
    # paper (metals-10-00882): S38 (lowest-cracking-density condition,
    # VED=88) and S19 (lowest-porosity condition, VED=158). Power/speed/
    # hatch/layer are approximate too since only VED was carried over
    # earlier; here we use the paper's actual reported values for those two
    # conditions directly for a fuller feature vector.
    real_specimens = [
        {"name": "M280/M300 density cubes - est. via S38 recipe (lowest-cracking-density)",
         "laser_power_W_n": 95, "scan_speed_mms_n": 1800, "hatch_spacing_mm_n": 0.03,
         "layer_thickness_um_n": 20.0, "doped_label": 0},
        {"name": "M280/M300 density cubes - est. via S19 recipe (lowest-porosity)",
         "laser_power_W_n": 95, "scan_speed_mms_n": 1000, "hatch_spacing_mm_n": 0.03,
         "layer_thickness_um_n": 20.0, "doped_label": 0},
    ]
    print("\n" + "=" * 70)
    print("MODEL PREDICTION ON REAL SPECIMENS (estimated recipe, illustrative only)")
    print("=" * 70)
    rows = []
    for spec in real_specimens:
        ved = spec["laser_power_W_n"] / (spec["scan_speed_mms_n"] * spec["hatch_spacing_mm_n"] * (spec["layer_thickness_um_n"] / 1000.0))
        x_query = np.array([[ved, spec["laser_power_W_n"], spec["scan_speed_mms_n"],
                              spec["hatch_spacing_mm_n"], spec["layer_thickness_um_n"], spec["doped_label"]]])
        proba = clf.predict_proba(x_query)[0]
        pred = clf.predict(x_query)[0]
        print(f"{spec['name']}")
        print(f"  VED = {ved:.1f} J/mm3 -> P(crack) = {proba[1]:.2f}  predicted = {'Yes' if pred==1 else 'No'}")
        rows.append({"specimen": spec["name"], "ved": round(ved, 1),
                      "model_p_crack": round(proba[1], 2), "model_predicted": "Yes" if pred == 1 else "No"})

    pd.DataFrame(rows).to_csv("/home/claude/stream3_model_predictions_on_real_specimens.csv", index=False)
    print("\nSaved predictions to stream3_model_predictions_on_real_specimens.csv")


if __name__ == "__main__":
    main()
