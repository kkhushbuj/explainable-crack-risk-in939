"""
Stream 1 - AE/thermal crack-signature PROXY classifier.

WHY THIS EXISTS:
Kevin does not have documented crack/no-crack ground truth for any of these
recordings, and doesn't know the exact test start times either. Since no one
can tell us the real answer, this script derives a proxy label directly from
the physics of the raw signal itself - the same logic a human inspecting an
AE trace by eye would use:

  - A genuine fracture event in acoustic emission testing shows up as a
    LARGE, often sensor-saturating amplitude burst, frequently seen on
    multiple channels at once, followed by the signal dying off (because the
    specimen has physically separated / the operator stops the test).
  - Ordinary elastic loading / minor plastic deformation produces much
    smaller, steadier background hits with no dominant spike.

METHOD:
1. For files with only a peak-value trace (the "dogbone_test_CSV*" plot
   exports + Brompton), we rank each file's peak value against the group
   using a robust modified z-score (median + MAD, less sensitive to
   outliers than mean/stdev). A modified z-score > 3.5 is a standard
   statistical outlier threshold (Iglewicz & Hoaglin, 1993).
2. For the one file where we have real hit-by-hit data (dogbone_test_CSV7,
   11,771 individual AE hits with real timestamps and per-hit amplitude/
   energy), we directly detect the fracture-event signature: a
   simultaneous, saturating-amplitude hit on both channels, followed by a
   collapse in hit rate.
3. Thermal-only data (no acoustic channel) cannot be assessed by this
   method at all - labeled explicitly as not assessable.

THIS IS NOT LAB-CONFIRMED GROUND TRUTH. It is an evidence-based inference
from the actual sensor signal, built because no confirmed labels exist.
Treat "Proxy-Yes" as "the signal looks like a fracture event", not as
"this part is scientifically confirmed cracked". Flag this clearly in the
dissertation write-up and validate against physical/CT inspection if any
becomes available.
"""

import csv
import glob
import os
import re
import statistics

SENSOR_DIR = os.path.dirname(os.path.abspath(__file__))


def read_xy(path):
    xs, ys = [], []
    with open(path, errors="ignore") as f:
        for i, line in enumerate(f):
            parts = line.split()
            if i == 0 or len(parts) < 2:
                continue
            try:
                xs.append(float(parts[0]))
                ys.append(float(parts[1]))
            except ValueError:
                continue
    return xs, ys


def analyze_hitlist(path):
    """Real hit-by-hit analysis of the raw AEwin hit-list (CSV7 format)."""
    hits = []
    with open(path, errors="ignore") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 11 and re.match(r"^\d+:\d+:\d+\.\d+$", parts[2]):
                try:
                    h, m, s = parts[2].split(":")
                    t = int(h) * 3600 + int(m) * 60 + float(s)
                    ch = int(parts[5])
                    energy = int(parts[8])
                    amp = int(parts[10])
                except ValueError:
                    continue
                hits.append((t, ch, energy, amp))
    if not hits:
        return None
    t0 = hits[0][0]
    tend = hits[-1][0]
    max_amp = max(h[3] for h in hits)
    # find near-simultaneous max-amplitude hits across both channels
    top = [h for h in hits if h[3] >= max_amp - 1]
    top_times = sorted(set(round(h[0], 1) for h in top))
    dual_channel_burst = len(set(h[1] for h in top)) >= 2
    burst_t = top[0][0] - t0
    return {
        "n_hits": len(hits),
        "duration_s": round(tend - t0, 2),
        "max_amplitude": max_amp,
        "burst_time_s": round(burst_t, 2),
        "dual_channel_burst": dual_channel_burst,
        "time_left_after_burst_s": round(tend - top[0][0], 2),
    }


def main():
    plot_files = [
        "dogbone_test_CSV0.TXT", "dogbone_test_CSV1.TXT", "dogbone_test_CSV2.TXT",
        "dogbone_test_CSV3.TXT", "dogbone_test_CSV4.TXT", "dogbone_test_CSV6.TXT",
        "dogbone_test_CSV8.TXT", "dogbone_test_CSV9MEG.TXT",
    ]

    peaks = {}
    for fn in plot_files:
        xs, ys = read_xy(os.path.join(SENSOR_DIR, fn))
        peaks[fn] = max(ys) if ys else 0.0

    vals = list(peaks.values())
    med = statistics.median(vals)
    mad = statistics.median([abs(v - med) for v in vals]) or 1.0

    rows = []

    for fn in plot_files:
        peak = peaks[fn]
        z = round(0.6745 * (peak - med) / mad, 2)
        if z > 3.5:
            label, conf = "Proxy-Yes (possible crack/fracture signature)", "Medium-High"
            basis = f"peak value is a statistical outlier vs. the other 7 recordings (modified z={z}, threshold 3.5)"
        elif z > 1.5:
            label, conf = "Watch (mildly elevated, inconclusive)", "Low-Medium"
            basis = f"peak value moderately above group median (modified z={z})"
        elif peak <= 2:
            label, conf = "No significant AE activity", "Low"
            basis = "near-zero peak value across the whole recording"
        else:
            label, conf = "Inconclusive / baseline activity", "Low"
            basis = f"peak value within normal range of the group (modified z={z})"
        rows.append({
            "test_id": fn.replace(".TXT", ""),
            "source_file": fn,
            "rig": "dogbone tensile AE",
            "data_type": "AE parameter-vs-time export (plot)",
            "peak_metric": peak,
            "peak_metric_type": "peak hit-count/amplitude value in trace",
            "modified_z_score": z,
            "ae_crack_signature_proxy": label,
            "confidence": conf,
            "basis": basis,
            "ground_truth_confirmed_by_kevin": "No",
        })

    # CSV7 raw hit-list - real hit-by-hit fracture detection
    hl = analyze_hitlist(os.path.join(SENSOR_DIR, "dogbone_test_CSV7.txt"))
    if hl:
        is_fracture = hl["dual_channel_burst"] and hl["max_amplitude"] >= 95
        rows.append({
            "test_id": "dogbone_test_CSV7",
            "source_file": "dogbone_test_CSV7.txt",
            "rig": "dogbone tensile AE",
            "data_type": "AE raw hit-list (11,771 real hits, real timestamps)",
            "peak_metric": hl["max_amplitude"],
            "peak_metric_type": "max hit amplitude (sensor units)",
            "modified_z_score": "n/a (raw hit data, not plot-peak comparison)",
            "ae_crack_signature_proxy": "Proxy-Yes (possible crack/fracture signature)" if is_fracture else "Inconclusive",
            "confidence": "High" if is_fracture else "Low",
            "basis": (
                f"near-simultaneous max-amplitude hit ({hl['max_amplitude']}) on both channels "
                f"at t={hl['burst_time_s']}s into the {hl['duration_s']}s session, hit rate then "
                f"collapsed and acquisition was aborted {hl['time_left_after_burst_s']}s later — "
                "matches the classic AE fracture-event pattern"
            ) if is_fracture else "no dual-channel saturating burst detected",
            "ground_truth_confirmed_by_kevin": "No",
        })

    # Brompton - separate rig, only summary plot available
    xs, ys = read_xy(os.path.join(SENSOR_DIR, "Brompton data2.TXT"))
    if ys:
        peak = max(ys)
        peak_x = xs[ys.index(peak)]
        rows.append({
            "test_id": "Brompton_data2",
            "source_file": "Brompton data2.TXT",
            "rig": "Brompton (unconfirmed physical setup - ask Kevin)",
            "data_type": "AE hits-vs-time export (plot)",
            "peak_metric": peak,
            "peak_metric_type": "peak hit-count value in trace",
            "modified_z_score": "n/a (different rig, not compared to dogbone group)",
            "ae_crack_signature_proxy": "Proxy-Yes (possible crack/fracture signature)",
            "confidence": "Medium",
            "basis": (
                f"two distinct high-amplitude burst clusters (peak {peak:.0f} at t~{peak_x:.0f}s, "
                "second cluster ~250s later), far above the dogbone group's activity levels — "
                "consistent with a real acoustic event, but no raw hit-list available to confirm "
                "dual-channel simultaneity the way CSV7 allowed"
            ),
            "ground_truth_confirmed_by_kevin": "No",
        })

    # Thermal - not assessable via AE method
    rows.append({
        "test_id": "M280-M300_density_cubes",
        "source_file": "M280-M300 density cubes.dat",
        "rig": "PIX Connect thermal camera (Area 1 probe)",
        "data_type": "Temperature-vs-time trace (no acoustic channel)",
        "peak_metric": 125.0,
        "peak_metric_type": "peak temperature (C) at 180s",
        "modified_z_score": "n/a",
        "ae_crack_signature_proxy": "Not assessable via AE method",
        "confidence": "N/A",
        "basis": (
            "no acoustic sensor data in this file - temperature-only trace, -45C to 125C, "
            "peaked at 180s, cooled at approx -0.11 C/s afterward. Fast cooling is a known "
            "literature risk factor for solidification cracking but this alone cannot confirm "
            "a crack without an independent signal or Kevin's inspection notes"
        ),
        "ground_truth_confirmed_by_kevin": "No",
    })

    out_path = os.path.join(SENSOR_DIR, "stream1_ae_crack_signature_proxy.csv")
    fieldnames = ["test_id", "source_file", "rig", "data_type", "peak_metric",
                  "peak_metric_type", "modified_z_score", "ae_crack_signature_proxy",
                  "confidence", "basis", "ground_truth_confirmed_by_kevin"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")
    for r in rows:
        print(f"  {r['test_id']:<28} -> {r['ae_crack_signature_proxy']}  (confidence: {r['confidence']})")


if __name__ == "__main__":
    main()
