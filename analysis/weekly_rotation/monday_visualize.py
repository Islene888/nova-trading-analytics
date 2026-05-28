"""
Monday Rotation: Trend Visualization.

Generates matplotlib charts of the 12-month trend data for each
product category. Output PNGs are committed to reports/charts/.
"""

import json
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "trends"
CHARTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports" / "charts"

CATEGORY_LABELS = {
    "jewelry": "Fashion Jewelry & Accessories",
    "press_on_nails": "Press-On Nails",
    "wigs": "Wigs & Hair Extensions",
}


def latest_trends_file() -> Path:
    files = sorted(DATA_DIR.glob("*.json"))
    return files[-1] if files else None


def plot_category_trends(category: str, weekly_data: dict, out_path: Path):
    if not weekly_data:
        return False

    fig, ax = plt.subplots(figsize=(12, 6))
    for kw, weekly in weekly_data.items():
        if not weekly:
            continue
        dates = sorted(weekly.keys())
        values = [weekly[d] for d in dates]
        ax.plot(dates, values, label=kw, marker="o", markersize=3, linewidth=1.2)

    ax.set_title(
        f"{CATEGORY_LABELS.get(category, category)} — Search Interest (12-month weekly)",
        fontsize=14, fontweight="bold",
    )
    ax.set_xlabel("Week")
    ax.set_ylabel("Search Interest Index (0–100)")
    ax.legend(loc="upper left", fontsize=9, frameon=True)
    ax.grid(True, alpha=0.3)

    # Reduce x-axis tick density
    ticks = ax.get_xticks()
    if len(ticks) > 12:
        step = len(ticks) // 12
        ax.set_xticks(ticks[::step])
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()
    return True


def run() -> Path:
    trends_path = latest_trends_file()
    if not trends_path:
        print("  No trends data available")
        return None

    today = str(date.today())
    trends = json.loads(trends_path.read_text())
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    generated = []
    for category in ["jewelry", "press_on_nails", "wigs"]:
        weekly = trends.get("categories", {}).get(category, {}).get("weekly_12m", {})
        out_path = CHARTS_DIR / f"{today}-{category}-trend.png"
        if plot_category_trends(category, weekly, out_path):
            generated.append(out_path)
            print(f"  Chart: {out_path.name}")

    return generated[0] if generated else None


if __name__ == "__main__":
    run()
