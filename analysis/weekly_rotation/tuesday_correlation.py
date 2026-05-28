"""
Tuesday Rotation: Cross-Keyword Correlation Analysis.

Computes pairwise Pearson correlation between all tracked keywords
using 12-month weekly data. High positive correlation = keywords
co-trend (likely substitutes or category-level demand drivers).
"""

import json
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "trends"
OUT_DIR = Path(__file__).resolve().parent.parent.parent / "analysis" / "correlation"


def latest_trends_file() -> Path:
    files = sorted(DATA_DIR.glob("*.json"))
    return files[-1] if files else None


def pearson(x: list, y: list) -> float:
    if len(x) != len(y) or len(x) < 3:
        return 0.0
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)
    denom = (var_x * var_y) ** 0.5
    return cov / denom if denom > 0 else 0.0


def align_series(series_a: dict, series_b: dict) -> tuple:
    common = sorted(set(series_a.keys()) & set(series_b.keys()))
    return [series_a[d] for d in common], [series_b[d] for d in common]


def run() -> Path:
    trends_path = latest_trends_file()
    if not trends_path:
        print("  No trends data")
        return None

    trends = json.loads(trends_path.read_text())
    today = str(date.today())

    # Flatten all keywords
    all_kw = {}  # kw -> {date: value}
    kw_category = {}  # kw -> category
    for category, cat_data in trends.get("categories", {}).items():
        weekly = cat_data.get("weekly_12m", {})
        for kw, series in weekly.items():
            all_kw[kw] = series
            kw_category[kw] = category

    if len(all_kw) < 2:
        print("  Not enough keywords for correlation analysis")
        return None

    # Compute pairwise correlations
    keywords = list(all_kw.keys())
    pairs = []
    for i, kw_a in enumerate(keywords):
        for kw_b in keywords[i + 1:]:
            xs, ys = align_series(all_kw[kw_a], all_kw[kw_b])
            r = pearson(xs, ys)
            pairs.append({
                "kw_a": kw_a,
                "kw_b": kw_b,
                "cat_a": kw_category[kw_a],
                "cat_b": kw_category[kw_b],
                "r": round(r, 3),
                "abs_r": abs(r),
            })

    # Sort by absolute correlation desc
    pairs.sort(key=lambda p: -p["abs_r"])

    # Build report
    lines = [
        f"# Cross-Keyword Correlation Analysis — {today}",
        "",
        f"**Company:** Nova Trading Inc.",
        f"**Method:** Pearson correlation on 12-month weekly Google Trends data",
        f"**Sample size per pair:** ~52 weeks",
        "",
        "---",
        "",
        "## Strongest Positive Correlations (co-trending keywords)",
        "",
        "| r | Keyword A | Category A | Keyword B | Category B |",
        "|---|-----------|------------|-----------|------------|",
    ]
    for p in [p for p in pairs if p["r"] > 0][:15]:
        lines.append(
            f"| {p['r']:+.3f} | `{p['kw_a']}` | {p['cat_a']} | `{p['kw_b']}` | {p['cat_b']} |"
        )

    lines += [
        "",
        "## Strongest Negative Correlations (substitution patterns)",
        "",
        "| r | Keyword A | Category A | Keyword B | Category B |",
        "|---|-----------|------------|-----------|------------|",
    ]
    for p in [p for p in pairs if p["r"] < 0][:10]:
        lines.append(
            f"| {p['r']:+.3f} | `{p['kw_a']}` | {p['cat_a']} | `{p['kw_b']}` | {p['cat_b']} |"
        )

    # Within-category averages
    within_cat = {}
    cross_cat = []
    for p in pairs:
        if p["cat_a"] == p["cat_b"]:
            within_cat.setdefault(p["cat_a"], []).append(p["r"])
        else:
            cross_cat.append(p["r"])

    lines += [
        "",
        "## Within vs Cross-Category Correlation",
        "",
        "| Category | Within-category avg r | # pairs |",
        "|----------|----------------------|---------|",
    ]
    for cat, rs in within_cat.items():
        lines.append(f"| {cat} | {sum(rs)/len(rs):+.3f} | {len(rs)} |")
    if cross_cat:
        lines.append(f"| **Cross-category** | {sum(cross_cat)/len(cross_cat):+.3f} | {len(cross_cat)} |")

    lines += [
        "",
        "## Interpretation",
        "",
        "- **High within-category r**: keywords share a common demand driver (e.g., seasonality, fashion cycle)",
        "- **High cross-category r**: broader consumer-spending or platform-traffic effect; useful for multi-category demand forecasting",
        "- **Negative r**: potential substitution; one keyword's demand grows at the other's expense",
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{today}-correlation.md"
    out_path.write_text("\n".join(lines))
    print(f"  Report: {out_path.name}")
    return out_path


if __name__ == "__main__":
    run()
