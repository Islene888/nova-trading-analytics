"""
Daily Market Intelligence Report — Nova Trading Inc.
E-Commerce Operations Research Analyst

Generates a daily market intelligence report from Google Trends data.
Includes momentum analysis, volatility metrics, and trend ranking.

Output: reports/YYYY-MM-DD-market-report.md
"""

from datetime import date
from pathlib import Path
from typing import List
import json


REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CATEGORY_LABELS = {
    "jewelry": "Fashion Jewelry & Accessories",
    "press_on_nails": "Press-On Nails",
    "wigs": "Wigs & Hair Extensions",
}


def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def classify_momentum(pct: float) -> str:
    """Classify momentum into directional buckets."""
    if pct is None:
        return "n/a"
    if pct >= 20:
        return "⬆️ strong uptrend"
    if pct >= 5:
        return "↗ mild uptrend"
    if pct >= -5:
        return "→ flat"
    if pct >= -20:
        return "↘ mild downtrend"
    return "⬇️ strong downtrend"


def format_category_section(category: str, data: dict) -> str:
    label = CATEGORY_LABELS.get(category, category)
    momentum = data.get("momentum", {})
    volatility = data.get("volatility", {})

    if not momentum:
        return f"### {label}\n_No data available._\n"

    lines = [
        f"### {label}",
        "",
        "**Search Interest Momentum (12-month weekly data)**",
        "",
        "| Keyword | Latest | 4w avg | 12w avg | 4w Δ | 12w Δ | Trend |",
        "|---------|--------|--------|---------|------|-------|-------|",
    ]

    rows = []
    for kw, m in momentum.items():
        latest = m.get("latest_week", 0)
        avg_4w = m.get("prev_4w_avg", 0)
        avg_12w = m.get("prev_12w_avg", 0)
        mom_4w = m.get("momentum_4w_pct")
        mom_12w = m.get("momentum_12w_pct")
        trend = classify_momentum(mom_12w)
        mom_4w_str = f"{mom_4w:+.1f}%" if mom_4w is not None else "n/a"
        mom_12w_str = f"{mom_12w:+.1f}%" if mom_12w is not None else "n/a"
        rows.append((kw, latest, avg_4w, avg_12w, mom_4w_str, mom_12w_str, trend, mom_12w or -999))

    # sort by 12w momentum descending
    rows.sort(key=lambda x: -x[-1])

    for kw, latest, avg_4w, avg_12w, mom_4w_str, mom_12w_str, trend, _ in rows:
        lines.append(
            f"| `{kw}` | {latest} | {avg_4w} | {avg_12w} | {mom_4w_str} | {mom_12w_str} | {trend} |"
        )

    # Volatility table
    if volatility:
        lines += [
            "",
            "**Stability / Volatility (12-month CV — lower = more stable demand)**",
            "",
            "| Keyword | Mean | Std Dev | CV |",
            "|---------|------|---------|-----|",
        ]
        for kw, v in sorted(volatility.items(), key=lambda x: x[1]["cv"]):
            stability = "stable" if v["cv"] < 0.15 else ("moderate" if v["cv"] < 0.30 else "volatile")
            lines.append(f"| `{kw}` | {v['mean']} | {v['std']} | {v['cv']} ({stability}) |")

    lines.append("")
    return "\n".join(lines)


def generate_insights(trends_data: dict) -> List[str]:
    """Generate plain-language analytical observations."""
    insights = []
    all_momentum = []  # (category, keyword, momentum_12w_pct)

    for cat in ["jewelry", "press_on_nails", "wigs"]:
        cat_label = CATEGORY_LABELS.get(cat, cat)
        cat_data = trends_data.get("categories", {}).get(cat, {})
        momentum = cat_data.get("momentum", {})
        for kw, m in momentum.items():
            mom_12w = m.get("momentum_12w_pct")
            if mom_12w is not None:
                all_momentum.append((cat_label, kw, mom_12w))

    if not all_momentum:
        return ["_Insufficient data for observations today._"]

    all_momentum.sort(key=lambda x: -x[2])

    # Top 3 rising
    rising = all_momentum[:3]
    falling = all_momentum[-3:][::-1]

    insights.append("**Top Rising Keywords (12-week momentum):**")
    for cat, kw, pct in rising:
        if pct > 0:
            insights.append(f"- `{kw}` ({cat}): {pct:+.1f}% vs 12-week average")
    insights.append("")

    insights.append("**Top Declining Keywords:**")
    for cat, kw, pct in falling:
        if pct < 0:
            insights.append(f"- `{kw}` ({cat}): {pct:+.1f}% vs 12-week average")
    insights.append("")

    # Category-level summary
    cat_avg = {}
    for cat, kw, pct in all_momentum:
        cat_avg.setdefault(cat, []).append(pct)
    insights.append("**Category-Level Average Momentum:**")
    for cat, pcts in sorted(cat_avg.items(), key=lambda x: -sum(x[1]) / len(x[1])):
        avg = sum(pcts) / len(pcts)
        direction = "expanding" if avg > 2 else ("contracting" if avg < -2 else "stable")
        insights.append(f"- {cat}: {avg:+.1f}% avg → market {direction}")

    return insights


def run(trends_data: dict = None) -> Path:
    today = str(date.today())

    if trends_data is None:
        trends_data = load_json(DATA_DIR / "trends" / f"{today}.json")

    insights = generate_insights(trends_data)

    lines = [
        f"# Daily Market Intelligence Report — {today}",
        "",
        f"**Company:** Nova Trading Inc.",
        f"**Prepared by:** E-Commerce Operations Research Analyst",
        f"**Methodology:** Google Trends search interest analysis with 4-week and 12-week momentum decomposition",
        f"**Categories:** Fashion Jewelry | Press-On Nails | Wigs & Hair Extensions",
        f"**Geo:** {trends_data.get('geo', 'US')}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
    ]

    if insights:
        lines += insights
    else:
        lines.append("_Insufficient data for observations today._")

    lines += [
        "",
        "---",
        "",
        "## Category Detail",
        "",
    ]

    for cat in ["jewelry", "press_on_nails", "wigs"]:
        cat_data = trends_data.get("categories", {}).get(cat, {})
        lines.append(format_category_section(cat, cat_data))

    lines += [
        "---",
        "",
        "## Methodology Notes",
        "",
        "- **Search Interest Index**: Google Trends provides a 0–100 normalized index where 100 = peak interest for the queried keyword in the timeframe and geography.",
        "- **4-Week Momentum**: Latest week value ÷ trailing 4-week average − 1. Captures short-term shifts.",
        "- **12-Week Momentum**: Latest week value ÷ trailing 12-week average − 1. Captures medium-term trend direction.",
        "- **Coefficient of Variation (CV)**: Std deviation ÷ mean. A measure of demand stability. CV < 0.15 indicates stable demand; CV > 0.30 indicates volatile demand requiring tighter inventory control.",
        "",
        "## Action Items",
        "",
        "- Rising keywords with stable CV should be prioritized for inventory expansion",
        "- Falling keywords should be re-evaluated for de-prioritization in product mix",
        "- Volatile keywords require tighter safety stock formulas (higher Z-score for service level)",
    ]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{today}-market-report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Report saved: {out_path}")
    return out_path


if __name__ == "__main__":
    run()
