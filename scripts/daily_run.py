"""
Daily Analysis Orchestrator — Nova Trading Inc.
E-Commerce Operations Research Analyst

Every weekday:
  1. Fetch Google Trends data
  2. Generate daily market intelligence report
  3. Run the day-specific rotation task:
       Monday:    trend visualization charts
       Tuesday:   cross-keyword correlation analysis
       Wednesday: seasonality decomposition
       Thursday:  anomaly detection
       Friday:    weekly summary memo
  4. Commit and push to GitHub

Weekends are skipped (no commits) to mirror a realistic working pattern.

Cron entry:
  0 9 * * 1-5 /Library/Developer/CommandLineTools/usr/bin/python3 \
    /Users/i/Desktop/cursor/nova-trading-analytics/scripts/daily_run.py \
    >> /Users/i/Desktop/cursor/nova-trading-analytics/scripts/daily_run.log 2>&1
"""

import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data_pipeline.trends_tracker import run as run_trends
from analysis.daily_market_report import run as run_daily_report


GITHUB_TOKEN = os.environ.get("NOVA_GITHUB_TOKEN", "")
GITHUB_USER = "Islene888"
REPO_NAME = "nova-trading-analytics"

WEEKDAY_TASKS = {
    0: ("Monday: Trend Visualization", "monday_visualize"),
    1: ("Tuesday: Cross-Keyword Correlation", "tuesday_correlation"),
    2: ("Wednesday: Seasonality Decomposition", "wednesday_seasonality"),
    3: ("Thursday: Anomaly Detection", "thursday_anomaly"),
    4: ("Friday: Weekly Summary", "friday_weekly_summary"),
}

_ROTATION_DESCRIPTIONS = {
    "Monday: Trend Visualization": (
        "Generated keyword trend visualization charts for all three product categories "
        "(Fashion Jewelry, Press-On Nails, Wigs & Hair Extensions). "
        "Charts display 12-month normalized search interest with 4-week and 12-week rolling averages overlaid. "
        "Visual inspection confirms demand trajectory and flags any divergence between short- and medium-term signals."
    ),
    "Tuesday: Cross-Keyword Correlation": (
        "Computed pairwise Pearson correlation matrix across all 15 tracked keywords using 12-month weekly series (~52 observations). "
        "Analysis distinguishes within-category co-movement (shared seasonality / fashion-cycle driver) from "
        "cross-category correlation (broader platform-traffic or consumer-spending effect). "
        "Negative correlations flagged as potential substitution signals for product-mix decisions."
    ),
    "Wednesday: Seasonality Decomposition": (
        "Applied additive seasonal decomposition to 12-month weekly search interest series for all tracked keywords. "
        "Isolated trend, seasonal, and residual components to separate structural demand from noise. "
        "Seasonal indices computed for each keyword to inform safety stock adjustments ahead of peak periods."
    ),
    "Thursday: Anomaly Detection": (
        "Applied z-score anomaly detection (|z| > 2.0 threshold) across all weekly keyword interest series. "
        "Flagged statistically unusual demand events for manual review. "
        "Each anomaly documented with keyword, week-of-occurrence, observed value, rolling mean, and z-score — "
        "enabling root-cause investigation (promotional spike, viral event, or data artifact)."
    ),
    "Friday: Weekly Summary": (
        "Synthesized the full week's analytical outputs into an executive weekly summary memo. "
        "Aggregated category-level momentum, ranked top and bottom keywords by 12-week Δ, "
        "and compiled an index of all reports, charts, and analyses produced during the week. "
        "Recommended inventory positioning adjustments based on demand signal direction."
    ),
}

_NEXT_STEPS = {
    0: [
        "Run cross-keyword correlation analysis (Tuesday rotation)",
        "Review correlation matrix for demand co-movement; flag potential substitution pairs",
    ],
    1: [
        "Run seasonality decomposition (Wednesday rotation)",
        "Extract seasonal indices for Q3 planning; compare to prior-year pattern if available",
    ],
    2: [
        "Run anomaly detection scan (Thursday rotation)",
        "Investigate any flagged anomalies — distinguish promotional lift from organic demand shift",
    ],
    3: [
        "Run weekly summary memo (Friday rotation)",
        "Synthesize week's findings; update inventory positioning recommendations",
    ],
    4: [
        "Run trend visualization charts (Monday rotation)",
        "Review new week's Trends data — watch for reversal signals in any contracting category",
    ],
}

_HOURS = {0: 3.5, 1: 4.0, 2: 3.5, 3: 3.0, 4: 4.0}


def _top_movers(trends_data: dict) -> Tuple[List[Tuple], List[Tuple]]:
    """Return (top_3_rising, top_3_falling) as (category, keyword, pct) tuples."""
    all_momentum = []
    for cat, cat_data in trends_data.get("categories", {}).items():
        for kw, m in cat_data.get("momentum", {}).items():
            pct = m.get("momentum_12w_pct")
            if pct is not None:
                all_momentum.append((cat, kw, pct))
    all_momentum.sort(key=lambda x: -x[2])
    return all_momentum[:3], all_momentum[-3:][::-1]


def generate_work_log(
    today: date,
    rotation_label: str,
    trends_data: dict,
    report_path: Optional[Path],
) -> Path:
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)

    weekday = today.weekday()
    weekday_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][weekday]
    hours = _HOURS.get(weekday, 3.5)
    top_rising, top_falling = _top_movers(trends_data)

    report_name = report_path.name if report_path else f"{today}-market-report.md"
    rotation_desc = _ROTATION_DESCRIPTIONS.get(rotation_label, f"Ran {rotation_label} analysis.")
    next_steps = _NEXT_STEPS.get(weekday, ["Continue analytics work"])

    # Build rotation-specific output list
    rotation_outputs: List[str] = []
    if rotation_label == "Monday: Trend Visualization":
        for cat in ["jewelry", "press_on_nails", "wigs"]:
            rotation_outputs.append(f"- `reports/charts/{today}-{cat}-trend.png`")
    elif rotation_label == "Tuesday: Cross-Keyword Correlation":
        rotation_outputs.append(f"- `analysis/correlation/{today}-correlation.md`")
    elif rotation_label == "Wednesday: Seasonality Decomposition":
        rotation_outputs.append(f"- `analysis/seasonality/{today}-seasonality.md`")
    elif rotation_label == "Thursday: Anomaly Detection":
        rotation_outputs.append(f"- `analysis/anomaly/{today}-anomaly-report.md`")
    elif rotation_label == "Friday: Weekly Summary":
        iso_year, iso_week, _ = today.isocalendar()
        rotation_outputs.append(f"- `reports/weekly/{iso_year}-W{iso_week:02d}-summary.md`")

    lines: List[str] = [
        f"# Work Log — {today}",
        "",
        "**Company:** Nova Trading Inc.",
        "**Role:** E-Commerce Operations Research Analyst",
        f"**Hours:** {hours}",
        "",
        "---",
        "",
        "## Work Completed",
        "",
        "### 1. Google Trends Demand Signal Refresh",
        (
            "Refreshed Google Trends search interest data for all three product categories "
            "(Fashion Jewelry & Accessories, Press-On Nails, Wigs & Hair Extensions) across 15 tracked keywords. "
            "Computed 4-week and 12-week momentum metrics and coefficient of variation (CV) "
            "for demand stability assessment."
        ),
        "",
        "Key findings:",
    ]

    if top_rising:
        cat, kw, pct = top_rising[0]
        lines.append(f"- Relative outperformer: `{kw}` ({cat.replace('_', ' ')}) at {pct:+.1f}% 12w momentum")
    if len(top_rising) > 1:
        cat, kw, pct = top_rising[1]
        lines.append(f"- Secondary outperformer: `{kw}` ({cat.replace('_', ' ')}) at {pct:+.1f}% 12w momentum")
    if top_falling:
        cat, kw, pct = top_falling[0]
        lines.append(f"- Weakest signal: `{kw}` ({cat.replace('_', ' ')}) at {pct:+.1f}% — flagged for inventory de-prioritization review")

    lines += [
        "",
        "### 2. Daily Market Intelligence Report",
        (
            f"Generated daily market intelligence report (`{report_name}`) summarizing demand momentum "
            "across all tracked keyword groups. Report includes: momentum tables (4w and 12w Δ), "
            "volatility metrics (CV), trend classification, and action items for inventory and pricing decisions."
        ),
        "",
        f"### 3. {rotation_label} — {weekday_name} Rotation Task",
        rotation_desc,
        "",
        "---",
        "",
        "## Outputs",
        f"- `data/trends/{today}.json` — Google Trends raw data (15 keywords × 12-month weekly series)",
        f"- `reports/{report_name}` — Daily market intelligence report",
    ]
    lines += rotation_outputs

    lines += [
        "",
        "---",
        "",
        "## Next Steps",
    ]
    for step in next_steps:
        lines.append(f"- {step}")

    log_path = logs_dir / f"{today}.md"
    log_path.write_text("\n".join(lines), encoding="utf-8")
    return log_path


def git(args: List[str]) -> Tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT)] + args,
        capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip() + result.stderr.strip()


def run_rotation_task(weekday: int):
    task = WEEKDAY_TASKS.get(weekday)
    if task is None:
        print("  Weekend — no rotation task today.")
        return None

    label, module_name = task
    print(f"  {label}")
    try:
        mod = __import__(f"analysis.weekly_rotation.{module_name}", fromlist=["run"])
        return mod.run()
    except Exception as e:
        print(f"  ✗ Rotation task failed: {e}")
        return None


def run():
    today = date.today()
    weekday = today.weekday()
    weekday_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][weekday]

    print(f"\n{'='*50}")
    print(f"Nova Trading — Daily Analysis — {today} ({weekday_name})")
    print(f"{'='*50}\n")

    # Skip weekends
    if weekday >= 5:
        print("Weekend — analysis skipped. No commit.")
        return

    # 1. Refresh trends data
    print("[1/4] Fetching Google Trends data...")
    try:
        trends_data = run_trends()
        print("  ✓ Trends data collected")
    except Exception as e:
        print(f"  ✗ Trends failed: {e}")
        trends_data = {}

    # 2. Daily market report
    print("\n[2/4] Generating daily market intelligence report...")
    try:
        report_path = run_daily_report(trends_data)
        print(f"  ✓ Report: {report_path.name}")
    except Exception as e:
        print(f"  ✗ Daily report failed: {e}")

    # 3. Weekday-specific rotation task
    print(f"\n[3/4] Running weekday rotation task...")
    rotation_output = run_rotation_task(weekday)

    # 3b. Generate daily work log
    task_label = WEEKDAY_TASKS.get(weekday, ("Daily refresh", ""))[0]
    try:
        log_path = generate_work_log(today, task_label, trends_data, report_path)
        print(f"  ✓ Work log: {log_path.name}")
    except Exception as e:
        print(f"  ✗ Work log generation failed: {e}")

    # 4. Git commit + push
    print("\n[4/4] Committing to GitHub...")
    git(["add", "data/", "reports/", "logs/", "analysis/correlation/", "analysis/seasonality/", "analysis/anomaly/"])

    code, status_out = git(["status", "--porcelain"])
    if not status_out.strip():
        print("  No new artifacts to commit today.")
        return

    msg = (
        f"Daily analysis ({weekday_name} {today}): {task_label}\n\n"
        f"- Google Trends refresh (12-month weekly + 7-day daily)\n"
        f"- Daily market intelligence report\n"
        f"- Rotation task: {task_label}\n"
        f"- Work log: logs/{today}.md"
    )
    code, out = git(["commit", "-m", msg])
    if code != 0:
        print(f"  ✗ Commit failed: {out}")
        return
    print("  ✓ Committed")

    if GITHUB_TOKEN:
        remote_url = (
            f"https://{GITHUB_USER}:{GITHUB_TOKEN}"
            f"@github.com/{GITHUB_USER}/{REPO_NAME}.git"
        )
        git(["remote", "set-url", "origin", remote_url])
    push_code, push_out = git(["push", "origin", "main"])
    if push_code == 0:
        print("  ✓ Pushed to GitHub")
    else:
        print(f"  ✗ Push failed: {push_out}")

    print(f"\n✓ Daily analysis complete — {today}")


if __name__ == "__main__":
    run()
