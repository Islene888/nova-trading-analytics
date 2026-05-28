"""
Thursday Rotation: Anomaly Detection.

For each tracked keyword, applies a robust z-score test (MAD-based)
to identify weeks where search interest deviated significantly from
the recent trend. Flagged weeks become inputs to the sales_volume_drop
diagnostic scenario once we have first-party sales data.
"""

import json
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "trends"
OUT_DIR = Path(__file__).resolve().parent.parent.parent / "analysis" / "anomaly"


def latest_trends_file() -> Path:
    files = sorted(DATA_DIR.glob("*.json"))
    return files[-1] if files else None


def median(values: list) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    if n % 2 == 1:
        return float(s[n // 2])
    return (s[n // 2 - 1] + s[n // 2]) / 2


def mad_zscore(values: list, threshold: float = 3.5) -> list:
    """Median Absolute Deviation z-score test.

    Returns list of (index, value, z-score, is_anomaly) tuples.
    Robust to outliers (uses median, not mean).
    """
    if len(values) < 4:
        return []

    med = median(values)
    abs_devs = [abs(v - med) for v in values]
    mad = median(abs_devs)
    if mad == 0:
        return [(i, v, 0.0, False) for i, v in enumerate(values)]

    # 0.6745 is the consistency constant for normal distribution
    z_scores = [(i, v, 0.6745 * (v - med) / mad) for i, v in enumerate(values)]
    return [(i, v, z, abs(z) > threshold) for i, v, z in z_scores]


def run() -> Path:
    trends_path = latest_trends_file()
    if not trends_path:
        print("  No trends data")
        return None

    trends = json.loads(trends_path.read_text())
    today = str(date.today())

    lines = [
        f"# Anomaly Detection Report — {today}",
        "",
        f"**Company:** Nova Trading Inc.",
        f"**Method:** MAD-based modified z-score (robust to outliers)",
        f"**Threshold:** |z| > 3.5 (Iglewicz & Hoaglin convention)",
        "",
        "---",
        "",
    ]

    total_anomalies = 0
    by_category = {}

    for category, cat_data in trends.get("categories", {}).items():
        weekly = cat_data.get("weekly_12m", {})
        cat_anomalies = []
        for kw, series_dict in weekly.items():
            if not series_dict:
                continue
            sorted_dates = sorted(series_dict.keys())
            values = [series_dict[d] for d in sorted_dates]
            scored = mad_zscore(values)
            anomalies = [
                (sorted_dates[i], v, z)
                for i, v, z, is_anom in scored
                if is_anom
            ]
            for dt, v, z in anomalies:
                cat_anomalies.append({
                    "kw": kw,
                    "date": dt,
                    "value": v,
                    "z": round(z, 2),
                    "direction": "spike" if z > 0 else "drop",
                })
        by_category[category] = cat_anomalies
        total_anomalies += len(cat_anomalies)

    lines.append(f"**Anomalies detected: {total_anomalies}**")
    lines.append("")

    if total_anomalies == 0:
        lines.append("_No anomalies detected in the 12-month window. Demand patterns are within normal variation._")
    else:
        for category, anomalies in by_category.items():
            if not anomalies:
                continue
            lines += [
                f"## {category}",
                "",
                "| Date | Keyword | Value | z-score | Direction |",
                "|------|---------|-------|---------|-----------|",
            ]
            anomalies.sort(key=lambda a: a["date"], reverse=True)
            for a in anomalies:
                emoji = "🔺" if a["direction"] == "spike" else "🔻"
                lines.append(
                    f"| {a['date']} | `{a['kw']}` | {a['value']} | {a['z']:+.2f} | {emoji} {a['direction']} |"
                )
            lines.append("")

    lines += [
        "## Methodology Note",
        "",
        "The modified z-score uses the median and MAD instead of mean and standard deviation, "
        "making it robust to the very outliers we're trying to detect. The consistency constant "
        "0.6745 calibrates the MAD to be comparable to the standard deviation under normality.",
        "",
        "**Action triggers (once sales data exists):**",
        "- Spike anomalies → check inventory readiness, capture demand",
        "- Drop anomalies → run sales_volume_drop diagnostic (see analysis/diagnostics/)",
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{today}-anomaly-report.md"
    out_path.write_text("\n".join(lines))
    print(f"  Report: {out_path.name}, {total_anomalies} anomalies")
    return out_path


if __name__ == "__main__":
    run()
