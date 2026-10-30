"""
Stream 1 - Acoustic Emission feature extraction.

Reads the raw AE export files Kevin shared (format: two columns, "x" and
"Plot 1", tab/space separated, one header row). Each file represents one
AE recording for one test/sample. This script turns each raw file into a
handful of numeric features that can later be joined with the literature
risk score (Stream 2) and fed into the Stream 3 ML model.

Usage:
    python extract_ae_features.py <folder_with_txt_files>

Output:
    ae_features.csv in the current directory, one row per input file.
"""

import sys
import re
import glob
import os
import csv


def read_xy_file(path):
    """Parse the 'x    Plot 1' two-column export format."""
    xs, ys = [], []
    with open(path, "r", errors="ignore") as f:
        first_line = True
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            if first_line:
                first_line = False
                # header row looks like: x    Plot 1
                if not re.match(r"^-?\d", parts[0]):
                    continue
            if len(parts) < 2:
                continue
            try:
                x = float(parts[0])
                y = float(parts[1])
            except ValueError:
                continue
            xs.append(x)
            ys.append(y)
    return xs, ys


def extract_features(xs, ys, noise_threshold=None):
    """
    Compute simple, defensible features from one AE trace.

    noise_threshold: values below this are treated as baseline noise.
    If not given, uses 3x the median of the trace as a rough floor -
    good enough for a first pass, should be sanity-checked against a
    few real traces once Kevin confirms the AE system/units in use.
    """
    if not ys:
        return None

    n = len(ys)
    peak_value = max(ys)
    peak_index = ys.index(peak_value)
    peak_x = xs[peak_index]

    # total energy proxy: trapezoidal area under the curve
    area = 0.0
    for i in range(1, n):
        dx = xs[i] - xs[i - 1]
        area += dx * (ys[i] + ys[i - 1]) / 2.0

    if noise_threshold is None:
        sorted_ys = sorted(ys)
        median = sorted_ys[n // 2]
        noise_threshold = max(3 * median, 1.0)

    above = [i for i, v in enumerate(ys) if v > noise_threshold]
    if above:
        event_start_x = xs[above[0]]
        event_end_x = xs[above[-1]]
        event_duration = event_end_x - event_start_x
        n_points_above = len(above)
    else:
        event_start_x = None
        event_end_x = None
        event_duration = 0.0
        n_points_above = 0

    return {
        "n_points": n,
        "x_min": xs[0],
        "x_max": xs[-1],
        "peak_value": peak_value,
        "peak_x": peak_x,
        "total_area": round(area, 3),
        "noise_threshold_used": round(noise_threshold, 3),
        "event_start_x": event_start_x,
        "event_end_x": event_end_x,
        "event_duration": event_duration,
        "n_points_above_threshold": n_points_above,
        "has_event": n_points_above > 0,
    }


def guess_test_name(filename):
    """Strip common prefixes/suffixes to get a readable test identifier."""
    base = os.path.splitext(os.path.basename(filename))[0]
    return base


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_ae_features.py <folder_with_txt_files>")
        sys.exit(1)

    folder = sys.argv[1]
    pattern = os.path.join(folder, "*.[Tt][Xx][Tt]")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"No .txt/.TXT files found in {folder}")
        sys.exit(1)

    rows = []
    for path in files:
        xs, ys = read_xy_file(path)
        feats = extract_features(xs, ys)
        if feats is None:
            print(f"  skipped (unreadable/empty): {path}")
            continue
        feats["file"] = os.path.basename(path)
        feats["test_name"] = guess_test_name(path)
        rows.append(feats)
        print(f"  processed: {feats['file']}  peak={feats['peak_value']}  "
              f"event={'yes' if feats['has_event'] else 'no'}")

    out_path = "ae_features.csv"
    fieldnames = ["file", "test_name", "n_points", "x_min", "x_max",
                  "peak_value", "peak_x", "total_area",
                  "noise_threshold_used", "event_start_x", "event_end_x",
                  "event_duration", "n_points_above_threshold", "has_event"]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {out_path}")
    print("\nNEXT STEP: add a 'crack_occurred' (Yes/No) column to this CSV "
          "for each test_name once that ground truth is available - without "
          "it these features can't be used to train or validate anything.")


if __name__ == "__main__":
    main()
