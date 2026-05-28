"""
Price Elasticity Estimation — Nova Trading Inc.
E-Commerce Operations Research Analyst

Estimates price elasticity of demand using log-log OLS regression.
Used to inform dynamic pricing decisions across Shopify, Amazon, TikTok Shop.
"""

import numpy as np
import pandas as pd
from typing import Tuple


def estimate_log_log_elasticity(
    prices: pd.Series,
    quantities: pd.Series,
) -> Tuple[float, float, float]:
    """
    Estimate price elasticity via log-log OLS: ln(Q) = a + b*ln(P)
    Coefficient b is the price elasticity of demand.

    Args:
        prices: series of observed prices
        quantities: series of observed quantities sold

    Returns:
        (elasticity, intercept, r_squared)
    """
    ln_p = np.log(prices.replace(0, np.nan).dropna())
    ln_q = np.log(quantities.replace(0, np.nan).dropna())

    # align indices
    idx = ln_p.index.intersection(ln_q.index)
    ln_p, ln_q = ln_p[idx], ln_q[idx]

    # OLS via matrix formula
    X = np.column_stack([np.ones(len(ln_p)), ln_p])
    beta = np.linalg.lstsq(X, ln_q, rcond=None)[0]
    intercept, elasticity = beta

    y_pred = X @ beta
    ss_res = np.sum((ln_q - y_pred) ** 2)
    ss_tot = np.sum((ln_q - ln_q.mean()) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return round(elasticity, 4), round(intercept, 4), round(r_squared, 4)


def revenue_maximizing_price(
    current_price: float,
    elasticity: float,
    current_quantity: float,
    unit_cost: float,
) -> float:
    """
    Compute profit-maximizing price given estimated elasticity.

    For linear demand approximation:
        Optimal markup = 1 / (1 + 1/elasticity)  [Lerner index]

    Args:
        current_price: current selling price
        elasticity: price elasticity (should be negative, e.g. -1.8)
        current_quantity: units sold at current price (for scale reference)
        unit_cost: variable cost per unit

    Returns:
        Profit-maximizing price
    """
    if elasticity >= -1:
        # inelastic demand — raising price always increases revenue
        return current_price * 1.10  # suggest 10% increase

    optimal_markup = -1 / (1 + elasticity)
    optimal_price = unit_cost / (1 - optimal_markup)
    return round(optimal_price, 2)
