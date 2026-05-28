"""
Customer Cumulative LTV by Acquisition Channel.

Computes, for each day in [start_date, end_date], the cumulative LTV
of customers acquired through each channel. LTV is computed as:

    cumulative_revenue / cumulative_active_customers

where revenue includes order revenue, returns adjustments, and shipping
revenue, attributed to the customer's first-touch acquisition channel.

Adapted from the experiment LTV computation framework developed at a
previous employer (FlowGPT) — original code analyzed A/B test variation LTV;
this version analyzes customer LTV by acquisition channel.
"""

from sqlalchemy import text


def fetch_channel_cumulative_ltv_daily(
    start_date: str,
    end_date: str,
    engine,
):
    """
    For each day in [start_date, end_date] and each acquisition channel,
    compute cumulative revenue, cumulative active customers, and cumulative LTV.

    LTV = cumulative_revenue / cumulative_active_customers

    Returns rows: {event_date, channel, cumulative_revenue, cumulative_customers, cumulative_ltv}
    """
    query = f"""
        WITH
        -- Step 1: First-touch acquisition channel per customer.
        customer_channel_map AS (
            SELECT customer_id, acquisition_channel AS channel
            FROM (
                SELECT customer_id, acquisition_channel,
                       ROW_NUMBER() OVER (
                         PARTITION BY customer_id
                         ORDER BY first_seen_at ASC
                       ) AS rn
                FROM nova_customers.tbl_customer_channel_attribution
                WHERE first_seen_at <= '{end_date}'
            ) t WHERE rn = 1
        ),

        -- Step 2: Per-customer per-day revenue across all sources.
        --   - tbl_order: product revenue, net of returns
        --   - tbl_shipping_revenue: shipping fees collected
        --   - tbl_order_adjustment: refunds, store credits, etc. (negative revenue)
        customer_revenue_by_day AS (
            SELECT
                s.customer_id,
                ccm.channel,
                DATE(s.activity_date) AS event_date,
                COALESCE(ord.revenue, 0)
                  + COALESCE(ship.revenue, 0)
                  + COALESCE(adj.revenue, 0)
                  AS revenue
            FROM (
                SELECT DISTINCT customer_id, activity_date
                FROM nova_analytics.tbl_customer_daily_activity
                WHERE activity_date BETWEEN '{start_date}' AND '{end_date}'
            ) s
            JOIN customer_channel_map ccm
              ON s.customer_id = ccm.customer_id
            LEFT JOIN (
                SELECT customer_id, order_date AS event_date, SUM(net_revenue) AS revenue
                FROM nova_orders.tbl_order
                WHERE order_date BETWEEN '{start_date}' AND '{end_date}'
                GROUP BY customer_id, order_date
            ) ord
              ON s.customer_id = ord.customer_id
              AND s.activity_date = ord.event_date
            LEFT JOIN (
                SELECT customer_id, order_date AS event_date, SUM(shipping_revenue) AS revenue
                FROM nova_orders.tbl_shipping_revenue
                WHERE order_date BETWEEN '{start_date}' AND '{end_date}'
                GROUP BY customer_id, order_date
            ) ship
              ON s.customer_id = ship.customer_id
              AND s.activity_date = ship.event_date
            LEFT JOIN (
                SELECT customer_id, adjustment_date AS event_date, SUM(adjustment_amount) AS revenue
                FROM nova_orders.tbl_order_adjustment
                WHERE adjustment_date BETWEEN '{start_date}' AND '{end_date}'
                GROUP BY customer_id, adjustment_date
            ) adj
              ON s.customer_id = adj.customer_id
              AND s.activity_date = adj.event_date
        ),

        -- Step 3: First-active date per customer (for cumulative customer count).
        customer_first_active AS (
            SELECT customer_id, channel, MIN(event_date) AS first_active_date
            FROM customer_revenue_by_day
            GROUP BY customer_id, channel
        ),

        -- Step 4: Date × channel matrix (to allow zero-row days).
        date_channel AS (
            SELECT DISTINCT event_date, channel FROM customer_revenue_by_day
        ),

        -- Step 5: Cumulative active customer count per (date, channel).
        customer_cumulative_by_day AS (
            SELECT
                dc.event_date,
                dc.channel,
                COUNT(*) AS cumulative_customers
            FROM date_channel dc
            JOIN customer_first_active cfa
              ON cfa.channel = dc.channel
              AND cfa.first_active_date <= dc.event_date
            GROUP BY dc.event_date, dc.channel
        ),

        -- Step 6: Per-day revenue sum per channel.
        revenue_per_day AS (
            SELECT event_date, channel, SUM(revenue) AS revenue
            FROM customer_revenue_by_day
            GROUP BY event_date, channel
        ),

        -- Step 7: Cumulative revenue per channel.
        cumulative_revenue AS (
            SELECT
                event_date,
                channel,
                SUM(revenue) OVER (
                  PARTITION BY channel
                  ORDER BY event_date
                  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS cumulative_revenue
            FROM revenue_per_day
        )

        SELECT
            cr.event_date,
            cr.channel,
            cr.cumulative_revenue,
            c.cumulative_customers,
            ROUND(
              cr.cumulative_revenue / NULLIF(c.cumulative_customers, 0),
              4
            ) AS cumulative_ltv
        FROM cumulative_revenue cr
        JOIN customer_cumulative_by_day c
          ON cr.event_date = c.event_date AND cr.channel = c.channel
        ORDER BY cr.channel, cr.event_date;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        all_results = [dict(row._mapping) for row in result]

    print(
        f"[CHANNEL-LTV-DAILY] {start_date} → {end_date}: "
        f"{len(all_results)} rows"
    )
    return all_results
