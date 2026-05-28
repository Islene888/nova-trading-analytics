"""
Shopify Admin API — Order Data Ingestion
Nova Trading Inc. | E-Commerce Operations Research Analyst

Pulls order data from Shopify Admin REST API and loads into
the unified analytical data model.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")  # e.g. nova-trading.myshopify.com
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN")


def fetch_orders(
    created_at_min: Optional[str] = None,
    created_at_max: Optional[str] = None,
    limit: int = 250,
) -> pd.DataFrame:
    """
    Fetch orders from Shopify Admin REST API.

    Args:
        created_at_min: ISO 8601 date string (default: 90 days ago)
        created_at_max: ISO 8601 date string (default: now)
        limit: page size, max 250

    Returns:
        DataFrame with normalized order data
    """
    if created_at_min is None:
        created_at_min = (datetime.utcnow() - timedelta(days=90)).isoformat() + "Z"
    if created_at_max is None:
        created_at_max = datetime.utcnow().isoformat() + "Z"

    url = f"https://{SHOPIFY_STORE}/admin/api/2024-01/orders.json"
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
    params = {
        "status": "any",
        "created_at_min": created_at_min,
        "created_at_max": created_at_max,
        "limit": limit,
        "fields": "id,created_at,total_price,line_items,customer,financial_status,fulfillment_status",
    }

    all_orders = []
    while url:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        all_orders.extend(data.get("orders", []))

        # pagination via Link header
        link = resp.headers.get("Link", "")
        url = _parse_next_link(link)
        params = {}  # params are in the next URL

    return _normalize_orders(all_orders)


def _parse_next_link(link_header: str) -> Optional[str]:
    for part in link_header.split(","):
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")
    return None


def _normalize_orders(orders: list) -> pd.DataFrame:
    rows = []
    for order in orders:
        for item in order.get("line_items", []):
            rows.append({
                "order_id": order["id"],
                "created_at": order["created_at"],
                "channel": "shopify",
                "sku": item.get("sku"),
                "product_title": item.get("title"),
                "quantity": item.get("quantity"),
                "unit_price": float(item.get("price", 0)),
                "total_price": float(item.get("quantity", 0)) * float(item.get("price", 0)),
                "financial_status": order.get("financial_status"),
                "fulfillment_status": order.get("fulfillment_status"),
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = fetch_orders()
    print(f"Fetched {len(df)} order line items from Shopify")
    print(df.head())
