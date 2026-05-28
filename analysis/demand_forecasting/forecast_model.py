"""
Demand Forecasting Model — Nova Trading Inc.
E-Commerce Operations Research Analyst

Multi-channel demand forecasting using Prophet with
seasonality decomposition and promotional lift adjustment.

Channels: Shopify, Amazon Marketplace, TikTok Shop
"""

import pandas as pd
import numpy as np
from typing import Optional


def prepare_time_series(
    df: pd.DataFrame,
    sku: str,
    channel: Optional[str] = None,
) -> pd.DataFrame:
    """
    Aggregate daily sales for a given SKU (optionally by channel)
    into Prophet-compatible format (ds, y).
    """
    mask = df["sku"] == sku
    if channel:
        mask &= df["channel"] == channel

    daily = (
        df[mask]
        .assign(date=lambda x: pd.to_datetime(x["created_at"]).dt.date)
        .groupby("date")["quantity"]
        .sum()
        .reset_index()
        .rename(columns={"date": "ds", "quantity": "y"})
    )
    # fill missing dates with 0
    date_range = pd.date_range(daily["ds"].min(), daily["ds"].max())
    daily = daily.set_index("ds").reindex(date_range, fill_value=0).reset_index()
    daily.columns = ["ds", "y"]
    return daily


def evaluate_forecast(actual: pd.Series, predicted: pd.Series) -> dict:
    """
    Compute forecast accuracy metrics.

    Returns:
        dict with MAE, RMSE, MAPE
    """
    mae = np.mean(np.abs(actual - predicted))
    rmse = np.sqrt(np.mean((actual - predicted) ** 2))
    # avoid division by zero for MAPE
    nonzero = actual != 0
    mape = np.mean(np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero])) * 100

    return {"MAE": round(mae, 4), "RMSE": round(rmse, 4), "MAPE_%": round(mape, 2)}


def compute_safety_stock(
    forecast_std: float,
    lead_time_days: int,
    service_level_z: float = 1.645,  # 95% service level
) -> float:
    """
    Safety stock = Z * sigma_demand * sqrt(lead_time)

    Args:
        forecast_std: standard deviation of daily demand
        lead_time_days: supplier lead time in days
        service_level_z: Z-score for target service level
            1.28 = 90%, 1.645 = 95%, 2.05 = 98%

    Returns:
        Safety stock quantity (units)
    """
    return service_level_z * forecast_std * np.sqrt(lead_time_days)


def compute_reorder_point(
    avg_daily_demand: float,
    lead_time_days: int,
    safety_stock: float,
) -> float:
    """
    Reorder point = avg_demand * lead_time + safety_stock
    """
    return avg_daily_demand * lead_time_days + safety_stock
