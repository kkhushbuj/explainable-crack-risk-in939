"""
Parses the raw AE hit-list export format (seen in dogbone_test_CSV7.txt):

  ID DDD HH:MM:SS.mmmuuun      PARA1      PARA2   <extra numeric columns>

This is genuine hit-by-hit acoustic emission acquisition data (one row per
detected AE event), as opposed to the 'x / Plot 1' files which are
pre-summarized plot exports (histograms etc.) derived from a run like this
one. The timestamp here is elapsed/session time (HH:MM:SS from acquisition
start), not a calendar date - there's no absolute date in this file format.

Usage: python parse_ae_hitlist.py <file.txt>
"""
import sys
import re


def parse_hitlist(path):
    rows = []
    footer_notes = []
    with open(path, "r", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            m = re.match(
                r"^\s*(\d+)\s+(\d+)\s+(\d{2}:\d{2}:\d{2}\.\d+)\s+"
                r"([\-\d\.]+)\s+([\-\d\.]+)\s*(.*)$",
                line,
            )
            if m:
                hit_id, ddd, ts, para1, para2, rest = m.groups()
                extra = rest.split() if rest.strip() else []
                rows.append({
                    "id": int(hit_id),
                    "ddd": int(ddd),
                    "timestamp": ts,
                    "para1": float(para1),
                    "para2": float(para2),
                    "extra": extra,
                })
            else:
                # header/footer lines (column names, channel summary,
                # "Acquisition Aborted" etc.) - keep for visibility
                footer_notes.append(line.strip())
    return rows, footer_notes


def hhmmss_to_seconds(ts):
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def summarize(path):
    rows, notes = parse_hitlist(path)
    if not rows:
        print(f"No hit rows parsed from {path}")
        return None

    t0 = hhmmss_to_seconds(rows[0]["timestamp"])
    t1 = hhmmss_to_seconds(rows[-1]["timestamp"])

    summary = {
        "file": path,
        "n_hits": len(rows),
        "session_start": rows[0]["timestamp"],
        "session_end": rows[-1]["timestamp"],
        "duration_seconds": round(t1 - t0, 3),
        "aborted": any("abort" in n.lower() for n in notes),
    }
    return summary, notes


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_ae_hitlist.py <file.txt>")
        sys.exit(1)
    summary, notes = summarize(sys.argv[1])
    print("Summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("\nNon-data lines found in file (headers/footers/warnings):")
    for n in notes:
        print(f"  {n}")
