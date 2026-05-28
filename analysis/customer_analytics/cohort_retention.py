"""
Customer Cohort Retention Heatmap.

Computes "point-in-time cohort" retention for Nova Trading customers:
1. Define a fixed cohort: all customers active on cohort_date
2. Track that cohort's daily active count from cohort_date through end_date
3. Retention = active_users_on_day_N / cohort_initial_size

Cohorted by acquisition channel (shopify / amazon / tiktok / offline) so we
can compare which channel produces the stickiest customers.

Adapted from the experiment retention heatmap framework developed at a
previous employer (FlowGPT) — original code analyzed A/B test variation
retention; this version analyzes acquisition-channel cohort retention.
"""

from sqlalchemy import text


def fetch_cohort_retention_heatmap(
    cohort_date: str,
    end_date: str,
    engine,
    channel_filter: str = None,
):
    """
    "Point-in-time cohort" retention logic.
    1. Cohort = all customers with at least one order on cohort_date.
    2. Track that cohort's daily active count (any order) through end_date.
    3. Retention rate per day = active_count_day_N / cohort_initial_size.

    Args:
        cohort_date: ISO date string, the cohort anchor day
        end_date: ISO date string, last day to track
        engine: SQLAlchemy engine for analytical warehouse
        channel_filter: optional channel name to restrict cohort

    Returns:
        list of dicts: {channel, cohort_date, cohort_day, cohort_size, retained_users, retention_rate}
    """
    channel_clause = ""
    if channel_filter:
        channel_clause = "AND o.acquisition_channel = :channel_filter"

    query = f"""
    WITH
      -- Step 1: Define the point-in-time cohort.
      -- All customers who placed at least one order on cohort_date,
      -- attributed to their first-touch acquisition channel.
      point_in_time_cohort AS (
        SELECT DISTINCT
          o.customer_id,
          ac.acquisition_channel
        FROM nova_orders.tbl_order o
        JOIN (
          SELECT customer_id, acquisition_channel
          FROM (
            SELECT customer_id, acquisition_channel,
                   ROW_NUMBER() OVER (
                     PARTITION BY customer_id
                     ORDER BY first_seen_at ASC
                   ) AS rn
            FROM nova_customers.tbl_customer_channel_attribution
          ) t
          WHERE rn = 1
        ) ac ON o.customer_id = ac.customer_id
        WHERE o.order_date = :cohort_date
          {channel_clause}
      ),
      -- Step 2: Cohort initial size (denominator for retention rate)
      cohort_initial_size AS (
        SELECT
          acquisition_channel AS channel,
          COUNT(DISTINCT customer_id) AS cohort_size
        FROM point_in_time_cohort
        GROUP BY acquisition_channel
      ),
      -- Step 3: Daily active (= placed at least one order) customers from cohort
      daily_active_counts AS (
        SELECT
          pic.acquisition_channel AS channel,
          o.order_date AS active_date,
          COUNT(DISTINCT pic.customer_id) AS retained_users
        FROM point_in_time_cohort pic
        JOIN nova_orders.tbl_order o ON pic.customer_id = o.customer_id
        WHERE o.order_date BETWEEN :cohort_date AND :end_date
        GROUP BY pic.acquisition_channel, o.order_date
      )
    -- Step 4: Final aggregation with retention rate
    SELECT
      dac.channel,
      :cohort_date AS cohort_date,
      DATEDIFF(dac.active_date, :cohort_date) AS cohort_day,
      cis.cohort_size,
      dac.retained_users,
      ROUND(dac.retained_users * 1.0 / NULLIF(cis.cohort_size, 0), 4) AS retention_rate
    FROM daily_active_counts dac
    JOIN cohort_initial_size cis ON dac.channel = cis.channel
    ORDER BY dac.channel, dac.active_date;
    """

    params = {
        "cohort_date": cohort_date,
        "end_date": end_date,
    }
    if channel_filter:
        params["channel_filter"] = channel_filter

    with engine.connect() as conn:
        result_proxy = conn.execute(text(query), params)
        all_results = [dict(row._mapping) for row in result_proxy]

    print(
        f"[COHORT-RETENTION-HEATMAP] cohort_date={cohort_date} → "
        f"{len(all_results)} rows"
    )
    return all_results


def fetch_rolling_cohort_retention(
    start_date: str,
    end_date: str,
    engine,
    horizon_days: int = 30,
):
    """
    Rolling cohort retention: for every day between start_date and end_date,
    treat that day's new customers as a cohort and compute their N-day retention.

    Useful for tracking whether retention is improving/degrading over time
    (the "are new customers becoming stickier?" question).

    Returns rows: {cohort_date, channel, cohort_size, day_n, retention_rate}
    """
    query = """
    WITH
      first_order_date AS (
        SELECT customer_id, MIN(order_date) AS first_order_date
        FROM nova_orders.tbl_order
        GROUP BY customer_id
      ),
      new_customer_cohorts AS (
        SELECT
          f.first_order_date AS cohort_date,
          ac.acquisition_channel AS channel,
          f.customer_id
        FROM first_order_date f
        JOIN (
          SELECT customer_id, acquisition_channel,
                 ROW_NUMBER() OVER (
                   PARTITION BY customer_id ORDER BY first_seen_at ASC
                 ) AS rn
          FROM nova_customers.tbl_customer_channel_attribution
        ) ac ON f.customer_id = ac.customer_id AND ac.rn = 1
        WHERE f.first_order_date BETWEEN :start_date AND :end_date
      ),
      cohort_sizes AS (
        SELECT cohort_date, channel, COUNT(DISTINCT customer_id) AS cohort_size
        FROM new_customer_cohorts
        GROUP BY cohort_date, channel
      ),
      activity_in_horizon AS (
        SELECT
          ncc.cohort_date,
          ncc.channel,
          DATEDIFF(o.order_date, ncc.cohort_date) AS day_n,
          COUNT(DISTINCT ncc.customer_id) AS retained_users
        FROM new_customer_cohorts ncc
        JOIN nova_orders.tbl_order o ON ncc.customer_id = o.customer_id
        WHERE o.order_date BETWEEN ncc.cohort_date
              AND DATE_ADD(ncc.cohort_date, INTERVAL :horizon_days DAY)
        GROUP BY ncc.cohort_date, ncc.channel,
                 DATEDIFF(o.order_date, ncc.cohort_date)
      )
    SELECT
      a.cohort_date,
      a.channel,
      cs.cohort_size,
      a.day_n,
      a.retained_users,
      ROUND(a.retained_users * 1.0 / NULLIF(cs.cohort_size, 0), 4) AS retention_rate
    FROM activity_in_horizon a
    JOIN cohort_sizes cs
      ON a.cohort_date = cs.cohort_date AND a.channel = cs.channel
    ORDER BY a.cohort_date, a.channel, a.day_n;
    """

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "horizon_days": horizon_days,
    }

    with engine.connect() as conn:
        result_proxy = conn.execute(text(query), params)
        all_results = [dict(row._mapping) for row in result_proxy]

    print(
        f"[ROLLING-COHORT-RETENTION] {start_date} → {end_date} "
        f"(horizon {horizon_days}d): {len(all_results)} rows"
    )
    return all_results
