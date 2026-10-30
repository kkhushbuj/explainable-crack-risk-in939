"""
Parses Optris PIX Connect '.dat' exports (the temperature-vs-time trace
that PIX Connect exports alongside its .ravi raw thermal video).

Format:
    [Connect DataFile][1.1]
    Date:,DD/MM/YYYY
    Time:,HH:MM:SS.mmm      <- absolute recording start time
    Unit:,C
    Resolution:,0.05
    Values:,1
    Time,Area 1,
    00:00:00.000,-45.0,
    00:00:00.050,23.1,
    ...
    ---------------------------------
    End of File

Usage: python parse_thermal_dat.py <file.dat>
"""
import sys
import csv


def parse(path):
    meta = {}
    times, temps = [], []
    with open(path, errors="ignore") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if i < 6:
                if ":" in line and "," in line:
                    k, v = line.split(",", 1)
                    meta[k.strip(":")] = v.strip(",").strip()
                continue
            if line.startswith("Time,") or not line:
                continue
            if line.startswith("---") or "End of File" in line:
                break
            parts = line.split(",")
            if len(parts) >= 2:
                try:
                    h, m, s = parts[0].split(":")
                    t = int(h) * 3600 + int(m) * 60 + float(s)
                    temp = float(parts[1])
                    times.append(t)
                    temps.append(temp)
                except ValueError:
                    continue
    return meta, times, temps


def summarize(path):
    meta, times, temps = parse(path)
    if not temps:
        return None
    peak_i = temps.index(max(temps))
    dt = times[-1] - times[peak_i]
    dtemp = temps[-1] - temps[peak_i]
    return {
        "file": path,
        "recording_date": meta.get("Date"),
        "recording_start_time": meta.get("Time"),
        "unit": meta.get("Unit"),
        "n_samples": len(temps),
        "duration_seconds": round(times[-1] - times[0], 2),
        "temp_min": min(temps),
        "temp_max": max(temps),
        "peak_temp_at_s": round(times[peak_i] - times[0], 2),
        "cooling_rate_C_per_s": round(dtemp / dt, 4) if dt else None,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_thermal_dat.py <file.dat>")
        sys.exit(1)
    result = summarize(sys.argv[1])
    if result is None:
        print("No data parsed.")
        sys.exit(1)
    for k, v in result.items():
        print(f"  {k}: {v}")
