"""
Google Trends Tracker — Nova Trading Inc.
E-Commerce Operations Research Analyst

Tracks search interest for target product keywords across Nova Trading's
three categories: jewelry, press-on nails, wigs.

Two timeframes are pulled:
  - 12-month weekly data (for momentum + seasonality analysis)
  - 7-day daily data (for short-term signal)

Output: data/trends/YYYY-MM-DD.json
"""

import json
import time
from datetime import date
from pathlib import Path
from typing import List

from pytrends.request import TrendReq


KEYWORD_GROUPS = {
    "jewelry": [
        "fashion jewelry women",
        "trendy jewelry set",
        "statement necklace",
        "gold chain necklace",
        "minimalist jewelry",
    ],
    "press_on_nails": [
        "press on nails",
        "fake nails set",
        "stick on nails",
        "press on nails coffin",
        "press on nails short",
    ],
    "wigs": [
        "lace front wig",
        "human hair wig",
        "synthetic wig",
        "short bob wig",
        "headband wig",
    ],
}

GEO = "US"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "trends"


def fetch_interest(pytrends: TrendReq, keywords: List[str], timeframe: str) -> dict:
    """Fetch interest-over-time for keywords with given timeframe."""
    pytrends.build_payload(keywords, geo=GEO, timeframe=timeframe)
    df = pytrends.interest_over_time()
    if df.empty:
        return {}
    df = df.drop(columns=["isPartial"], errors="ignore")
    result = {}
    for kw in keywords:
        if kw in df.columns:
            result[kw] = {
                str(dt.date()): int(val)
                for dt, val in df[kw].items()
            }
    return result


def compute_momentum(weekly_data: dict) -> dict:
    """
    For each keyword, compute trend momentum metrics.
    - latest_week: most recent week value
    - prev_4w_avg: average of 4 weeks before latest
    - prev_12w_avg: average of 12 weeks before latest
    - momentum_4w: latest / prev_4w_avg - 1  (recent vs medium-term)
    - momentum_12w: latest / prev_12w_avg - 1 (recent vs long-term)
    """
    out = {}
    for kw, weekly in weekly_data.items():
        if not weekly:
            continue
        sorted_dates = sorted(weekly.keys())
        values = [weekly[d] for d in sorted_dates]
        if len(values) < 13:
            continue

        latest = values[-1]
        prev_4w = values[-5:-1]
        prev_12w = values[-13:-1]

        avg_4w = sum(prev_4w) / len(prev_4w) if prev_4w else 0
        avg_12w = sum(prev_12w) / len(prev_12w) if prev_12w else 0

        out[kw] = {
            "latest_week": latest,
            "prev_4w_avg": round(avg_4w, 1),
            "prev_12w_avg": round(avg_12w, 1),
            "momentum_4w_pct": round((latest / avg_4w - 1) * 100, 1) if avg_4w > 0 else None,
            "momentum_12w_pct": round((latest / avg_12w - 1) * 100, 1) if avg_12w > 0 else None,
        }
    return out


def compute_volatility(weekly_data: dict) -> dict:
    """Compute coefficient of variation (std/mean) for each keyword - stability metric."""
    out = {}
    for kw, weekly in weekly_data.items():
        values = list(weekly.values())
        if len(values) < 4:
            continue
        mean = sum(values) / len(values)
        if mean == 0:
            continue
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        out[kw] = {
            "mean": round(mean, 1),
            "std": round(std, 1),
            "cv": round(std / mean, 3),
        }
    return out


def run() -> dict:
    pytrends = TrendReq(hl="en-US", tz=360)
    today = str(date.today())
    results = {
        "date": today,
        "geo": GEO,
        "categories": {},
    }

    for category, keywords in KEYWORD_GROUPS.items():
        print(f"  Fetching trends: {category}...")
        try:
            weekly = fetch_interest(pytrends, keywords, "today 12-m")
            time.sleep(2)
            daily = fetch_interest(pytrends, keywords, "now 7-d")
            time.sleep(2)

            results["categories"][category] = {
                "weekly_12m": weekly,
                "daily_7d": daily,
                "momentum": compute_momentum(weekly),
                "volatility": compute_volatility(weekly),
            }
        except Exception as e:
            print(f"  WARNING: {category} fetch failed: {e}")
            results["categories"][category] = {}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{today}.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"  Saved: {out_path}")
    return results


if __name__ == "__main__":
    run()
