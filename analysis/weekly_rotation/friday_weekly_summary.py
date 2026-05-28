"""
Friday Rotation: Weekly Market Summary.

Synthesizes the week's daily reports, correlation analysis, seasonality
findings, and anomaly detection into a single weekly memo with
actionable recommendations.
"""

import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "trends"
WEEKLY_DIR = ROOT / "reports" / "weekly"


def files_in_window(folder: Path, pattern: str, days: int = 7) -> list:
    if not folder.exists():
        return []
    cutoff = date.today() - timedelta(days=days)
    files = []
    for f in folder.glob(pattern):
        try:
            file_date = date.fromisoformat(f.stem.split("-")[0] + "-" + f.stem.split("-")[1] + "-" + f.stem.split("-")[2])
            if file_date >= cutoff:
                files.append(f)
        except (ValueError, IndexError):
            continue
    return sorted(files)


def collect_week_momentum(days: int = 7) -> list:
    """Pull momentum data from this week's daily trends snapshots."""
    if not DATA_DIR.exists():
        return []
    cutoff = date.today() - timedelta(days=days)
    rows = []
    for f in sorted(DATA_DIR.glob("*.json")):
        try:
            file_date = date.fromisoformat(f.stem)
        except ValueError:
            continue
        if file_date < cutoff:
            continue
        data = json.loads(f.read_text())
        for cat, cat_data in data.get("categories", {}).items():
            momentum = cat_data.get("momentum", {})
            for kw, m in momentum.items():
                rows.append({
                    "date": file_date,
                    "category": cat,
                    "kw": kw,
                    "momentum_12w": m.get("momentum_12w_pct"),
                    "momentum_4w": m.get("momentum_4w_pct"),
                    "latest": m.get("latest_week"),
                })
    return rows


def run() -> Path:
    today = date.today()
    iso_year, iso_week, _ = today.isocalendar()
    week_label = f"{iso_year}-W{iso_week:02d}"
    cutoff = today - timedelta(days=7)

    rows = collect_week_momentum(days=7)

    lines = [
        f"# Weekly Market Summary — {week_label}",
        "",
        f"**Company:** Nova Trading Inc.",
        f"**Week:** {cutoff.isoformat()} to {today.isoformat()}",
        f"**Categories:** Fashion Jewelry | Press-On Nails | Wigs & Hair Extensions",
        "",
        "---",
        "",
        "## Week-Over-Week Momentum Aggregation",
        "",
    ]

    if not rows:
        lines.append("_Insufficient daily data this week._")
    else:
        # Latest snapshot per (kw)
        latest_per_kw = {}
        for r in rows:
            existing = latest_per_kw.get(r["kw"])
            if existing is None or r["date"] > existing["date"]:
                latest_per_kw[r["kw"]] = r

        # Category-level summary
        cat_groups = {}
        for r in latest_per_kw.values():
            cat_groups.setdefault(r["category"], []).append(r)

        lines += [
            "### Category-Level Momentum (most recent snapshot)",
            "",
            "| Category | Avg 4w Δ | Avg 12w Δ | Direction |",
            "|----------|----------|-----------|-----------|",
        ]
        cat_summary = []
        for cat, rs in cat_groups.items():
            m4 = [r["momentum_4w"] for r in rs if r["momentum_4w"] is not None]
            m12 = [r["momentum_12w"] for r in rs if r["momentum_12w"] is not None]
            avg_m4 = sum(m4) / len(m4) if m4 else 0
            avg_m12 = sum(m12) / len(m12) if m12 else 0
            direction = "expanding" if avg_m12 > 2 else ("contracting" if avg_m12 < -2 else "stable")
            cat_summary.append((cat, avg_m4, avg_m12, direction))
            lines.append(
                f"| {cat} | {avg_m4:+.1f}% | {avg_m12:+.1f}% | {direction} |"
            )

        # Top movers
        sorted_kws = sorted(
            [r for r in latest_per_kw.values() if r["momentum_12w"] is not None],
            key=lambda r: -r["momentum_12w"],
        )
        lines += [
            "",
            "### Top 5 Rising Keywords (this week's snapshot)",
            "",
            "| Keyword | Category | 12w Δ | 4w Δ | Latest |",
            "|---------|----------|-------|------|--------|",
        ]
        for r in sorted_kws[:5]:
            lines.append(
                f"| `{r['kw']}` | {r['category']} | {r['momentum_12w']:+.1f}% | "
                f"{r['momentum_4w']:+.1f}% | {r['latest']} |"
            )

        lines += [
            "",
            "### Top 5 Declining Keywords",
            "",
            "| Keyword | Category | 12w Δ | 4w Δ | Latest |",
            "|---------|----------|-------|------|--------|",
        ]
        for r in sorted_kws[-5:][::-1]:
            lines.append(
                f"| `{r['kw']}` | {r['category']} | {r['momentum_12w']:+.1f}% | "
                f"{r['momentum_4w']:+.1f}% | {r['latest']} |"
            )

    # Reference: analyses produced this week
    lines += [
        "",
        "---",
        "",
        "## Analyses Produced This Week",
        "",
    ]
    folders_to_check = [
        ("Daily market reports", ROOT / "reports", "*market-report.md"),
        ("Correlation analyses", ROOT / "analysis" / "correlation", "*.md"),
        ("Seasonality decompositions", ROOT / "analysis" / "seasonality", "*.md"),
        ("Anomaly reports", ROOT / "analysis" / "anomaly", "*.md"),
        ("Trend charts", ROOT / "reports" / "charts", "*.png"),
    ]
    for label, folder, pattern in folders_to_check:
        files = files_in_window(folder, pattern, days=7)
        if files:
            lines.append(f"- **{label}** ({len(files)} this week):")
            for f in files[-3:]:
                lines.append(f"  - `{f.relative_to(ROOT)}`")

    # Action items
    lines += [
        "",
        "---",
        "",
        "## Recommended Actions for Next Week",
        "",
        "Based on the trend signals aggregated this week:",
        "",
    ]
    if rows:
        # Identify expanding categories
        expanding = [c for c in cat_summary if c[2] > 5]
        contracting = [c for c in cat_summary if c[2] < -5]
        if expanding:
            lines.append(f"- **Expand product depth** in {', '.join(c[0] for c in expanding)} — demand momentum is positive")
        if contracting:
            lines.append(f"- **Tighten inventory commitments** in {', '.join(c[0] for c in contracting)} — demand momentum is negative")
        if not (expanding or contracting):
            lines.append("- Maintain current product mix; trends are stable")

    lines += [
        "- Run anomaly detection on the new week of data (Thursday rotation)",
        "- Re-evaluate correlation matrix for shifts in cross-category co-movement (Tuesday rotation)",
    ]

    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    out_path = WEEKLY_DIR / f"{week_label}-summary.md"
    out_path.write_text("\n".join(lines))
    print(f"  Weekly summary: {out_path.name}")
    return out_path


if __name__ == "__main__":
    run()
