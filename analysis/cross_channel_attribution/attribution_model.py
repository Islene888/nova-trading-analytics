"""
Cross-Channel Attribution Model — Nova Trading Inc.
E-Commerce Operations Research Analyst

Multi-touch attribution across Shopify, Amazon, and TikTok Shop.
Implements last-touch, linear, and data-driven (Shapley value) attribution.
"""

import pandas as pd
import numpy as np
from itertools import combinations
from typing import Dict


CHANNELS = ["shopify_organic", "amazon_sponsored", "tiktok_shop", "offline_event"]


def last_touch_attribution(touchpoints: pd.DataFrame) -> pd.Series:
    """
    Assign 100% of conversion credit to the last touchpoint before purchase.

    Args:
        touchpoints: DataFrame with columns [customer_id, channel, timestamp, converted]

    Returns:
        Series with channel -> attributed revenue
    """
    converted = touchpoints[touchpoints["converted"] == 1]
    last_touch = (
        converted.sort_values("timestamp")
        .groupby("customer_id")
        .last()
        .reset_index()
    )
    return last_touch.groupby("channel")["revenue"].sum()


def linear_attribution(touchpoints: pd.DataFrame) -> pd.Series:
    """
    Distribute conversion credit equally across all touchpoints in the path.
    """
    converted_ids = touchpoints[touchpoints["converted"] == 1]["customer_id"].unique()
    paths = touchpoints[touchpoints["customer_id"].isin(converted_ids)].copy()

    # count touches per customer
    touch_counts = paths.groupby("customer_id")["channel"].transform("count")
    paths["attributed_revenue"] = paths["revenue"] / touch_counts

    return paths.groupby("channel")["attributed_revenue"].sum()


def shapley_attribution(conversion_data: Dict[frozenset, float]) -> Dict[str, float]:
    """
    Data-driven Shapley value attribution.

    Computes marginal contribution of each channel by averaging
    its incremental value across all possible channel coalitions.

    Args:
        conversion_data: dict mapping frozenset(channels) -> conversion_rate

    Returns:
        dict mapping channel -> Shapley value (attribution weight)
    """
    shapley = {ch: 0.0 for ch in CHANNELS}
    n = len(CHANNELS)

    for channel in CHANNELS:
        other_channels = [c for c in CHANNELS if c != channel]
        for size in range(len(other_channels) + 1):
            for subset in combinations(other_channels, size):
                coalition_with = frozenset(list(subset) + [channel])
                coalition_without = frozenset(subset)
                marginal = (
                    conversion_data.get(coalition_with, 0)
                    - conversion_data.get(coalition_without, 0)
                )
                weight = (
                    np.math.factorial(size)
                    * np.math.factorial(n - size - 1)
                    / np.math.factorial(n)
                )
                shapley[channel] += weight * marginal

    return shapley
