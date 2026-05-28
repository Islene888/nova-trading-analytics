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
from typing import List, Tuple

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

    # 4. Git commit + push
    print("\n[4/4] Committing to GitHub...")
    git(["add", "data/", "reports/", "analysis/correlation/", "analysis/seasonality/", "analysis/anomaly/"])

    code, status_out = git(["status", "--porcelain"])
    if not status_out.strip():
        print("  No new artifacts to commit today.")
        return

    task_label = WEEKDAY_TASKS.get(weekday, ("Daily refresh", ""))[0]
    msg = (
        f"Daily analysis ({weekday_name} {today}): {task_label}\n\n"
        f"- Google Trends refresh (12-month weekly + 7-day daily)\n"
        f"- Daily market intelligence report\n"
        f"- Rotation task: {task_label}"
    )
    code, out = git(["commit", "-m", msg])
    if code != 0:
        print(f"  ✗ Commit failed: {out}")
        return
    print("  ✓ Committed")

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
