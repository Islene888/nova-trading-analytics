"""
Wednesday Rotation: Seasonality Decomposition.

For each keyword, decomposes the 12-month weekly series into:
  - trend component (centered moving average)
  - seasonal component (period-13 = quarterly seasonality on weekly data)
  - residual component

Uses additive classical decomposition (no SciPy/statsmodels dependency).
"""

import json
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "trends"
OUT_DIR = Path(__file__).resolve().parent.parent.parent / "analysis" / "seasonality"


def latest_trends_file() -> Path:
    files = sorted(DATA_DIR.glob("*.json"))
    return files[-1] if files else None


def moving_average(series: list, window: int) -> list:
    """Centered moving average; pads with None at edges."""
    half = window // 2
    out = []
    for i in range(len(series)):
        if i < half or i >= len(series) - half:
            out.append(None)
        else:
            chunk = series[i - half: i + half + 1]
            out.append(sum(chunk) / len(chunk))
    return out


def decompose_additive(series: list, period: int) -> dict:
    """Classical additive decomposition: Y = T + S + R."""
    n = len(series)
    if n < 2 * period:
        return None

    trend = moving_average(series, period)

    # Detrended series
    detrended = [
        (series[i] - trend[i]) if trend[i] is not None else None
        for i in range(n)
    ]

    # Average detrended values at each position within the period
    seasonal_pattern = [0.0] * period
    counts = [0] * period
    for i, v in enumerate(detrended):
        if v is not None:
            pos = i % period
            seasonal_pattern[pos] += v
            counts[pos] += 1
    seasonal_pattern = [
        seasonal_pattern[i] / counts[i] if counts[i] > 0 else 0.0
        for i in range(period)
    ]

    # Center seasonal pattern (sum to zero)
    mean_seasonal = sum(seasonal_pattern) / period
    seasonal_pattern = [s - mean_seasonal for s in seasonal_pattern]

    # Expand seasonal across full series
    seasonal = [seasonal_pattern[i % period] for i in range(n)]

    # Residual
    residual = [
        (series[i] - (trend[i] or 0) - seasonal[i]) if trend[i] is not None else None
        for i in range(n)
    ]

    # Strength metrics
    # Seasonality strength = 1 - var(residual) / var(detrended)
    valid_residuals = [r for r in residual if r is not None]
    valid_detrended = [d for d in detrended if d is not None]
    if valid_residuals and valid_detrended:
        var_r = sum(r ** 2 for r in valid_residuals) / len(valid_residuals)
        var_d = sum(d ** 2 for d in valid_detrended) / len(valid_detrended)
        seasonality_strength = max(0.0, min(1.0, 1.0 - var_r / var_d)) if var_d > 0 else 0.0
    else:
        seasonality_strength = 0.0

    return {
        "trend": trend,
        "seasonal_pattern": [round(s, 2) for s in seasonal_pattern],
        "seasonality_strength": round(seasonality_strength, 3),
        "peak_week_in_cycle": int(seasonal_pattern.index(max(seasonal_pattern))),
        "trough_week_in_cycle": int(seasonal_pattern.index(min(seasonal_pattern))),
    }


def run() -> Path:
    trends_path = latest_trends_file()
    if not trends_path:
        print("  No trends data")
        return None

    trends = json.loads(trends_path.read_text())
    today = str(date.today())

    PERIOD = 13  # weekly data, quarterly cycle

    lines = [
        f"# Seasonality Decomposition — {today}",
        "",
        f"**Company:** Nova Trading Inc.",
        f"**Method:** Classical additive decomposition (Y = Trend + Seasonal + Residual)",
        f"**Period:** 13 weeks (quarterly cycle on weekly data)",
        "",
        "---",
        "",
        "## Seasonality Strength Ranking",
        "",
        "| Keyword | Category | Strength | Peak (cycle wk) | Trough (cycle wk) |",
        "|---------|----------|----------|-----------------|-------------------|",
    ]

    rows = []
    for category, cat_data in trends.get("categories", {}).items():
        weekly = cat_data.get("weekly_12m", {})
        for kw, series_dict in weekly.items():
            if not series_dict:
                continue
            sorted_dates = sorted(series_dict.keys())
            values = [series_dict[d] for d in sorted_dates]
            result = decompose_additive(values, PERIOD)
            if result is None:
                continue
            rows.append({
                "kw": kw,
                "cat": category,
                "strength": result["seasonality_strength"],
                "peak": result["peak_week_in_cycle"],
                "trough": result["trough_week_in_cycle"],
                "pattern": result["seasonal_pattern"],
            })

    rows.sort(key=lambda r: -r["strength"])
    for r in rows:
        lines.append(
            f"| `{r['kw']}` | {r['cat']} | {r['strength']:.3f} | wk {r['peak']} | wk {r['trough']} |"
        )

    # Detail: top-3 most seasonal keywords
    lines += [
        "",
        "## Seasonal Pattern Detail (Top 3)",
        "",
    ]
    for r in rows[:3]:
        lines += [
            f"### `{r['kw']}` ({r['cat']})",
            "",
            f"Seasonal effect at each week of cycle (deviation from trend):",
            "",
            "```",
        ]
        for i, val in enumerate(r["pattern"]):
            bar_len = int(abs(val))
            bar = ("+" if val >= 0 else "-") * bar_len
            lines.append(f"  Week {i:2d}: {val:+6.2f}  {bar}")
        lines += ["```", ""]

    lines += [
        "## Business Implications",
        "",
        "- **High seasonality (strength > 0.3)**: forecasting model must explicitly model seasonal component; safety stock should peak ahead of seasonal peaks",
        "- **Low seasonality (strength < 0.1)**: simple level-based forecasting acceptable; smoother inventory cycle",
        "- **Peak/trough timing**: informs procurement lead-time planning",
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{today}-seasonality.md"
    out_path.write_text("\n".join(lines))
    print(f"  Report: {out_path.name}")
    return out_path


if __name__ == "__main__":
    run()
