"""
Diagnostic Scenario: sales_volume_drop

Detects when a SKU's units-sold has dropped substantially and classifies
the root cause using cross-signal analysis.

Adapted from the ad-performance volume_drop diagnostic scenario at a
previous employer (WorkMagic), repurposed for e-commerce product sales
anomaly detection at Nova Trading Inc.

Sub-scenario classification (analogous to original CPM-based logic):
  - competitive_pressure: competitor prices dropped → relative-price gap widened
  - listing_quality:      conversion rate fell → listing assets degrading
  - traffic_throttle:     traffic dropped but conversion held → platform/algorithm shift
  - unknown:              insufficient signals

Applies to: sku / category (level = "all")
"""

from typing import Optional
from analysis.diagnostics.models import DiagnosisResult


def _classify_sub_scenario_by_signals(
    competitor_gap_3d: Optional[float],
    competitor_gap_14d: Optional[float],
    conversion_rate_3d: Optional[float],
    conversion_rate_14d: Optional[float],
    t: dict,
) -> str:
    """
    Cross-signal root-cause classification.

    Returns one of: 'competitive_pressure' / 'listing_quality' / 'traffic_throttle' / 'unknown'
    """
    # ── Competitive pressure detection ──
    if (
        competitor_gap_3d is not None
        and competitor_gap_14d is not None
        and competitor_gap_3d > competitor_gap_14d * t.get(
            "volume_drop_competitor_gap_widen_ratio", 1.5
        )
    ):
        return "competitive_pressure"

    # ── Listing quality detection ──
    if (
        conversion_rate_3d is not None
        and conversion_rate_14d is not None
        and conversion_rate_14d > 0
        and conversion_rate_3d / conversion_rate_14d < t.get(
            "volume_drop_cvr_decline_ratio", 0.75
        )
    ):
        return "listing_quality"

    # ── Default: if conversion rate held, traffic is the issue ──
    if conversion_rate_3d is not None and conversion_rate_14d is not None:
        return "traffic_throttle"

    return "unknown"


def _refine_traffic_throttle(traffic_sub: str, sku, t: dict) -> str:
    """
    Refine the 'traffic_throttle' sub-scenario into more specific causes.

    Classification rationale (heuristic, will be calibrated with real data):
    ┌─────────────────────────────────────────────────────────────────────┐
    │ 1. New product warmup failure                                       │
    │    - Product age < 14 days but already showing volume drop          │
    │    - Platform algorithm not amplifying the listing                  │
    │    - Signal: product_age_days < 14 AND units_7d_avg low             │
    │                                                                     │
    │ 2. Established product traffic loss                                 │
    │    - Product age >= 14 days, was steady, now dropped                │
    │    - Possibly seasonality, search-rank change, or platform shift    │
    │    - Action: investigate search-rank position, seasonality          │
    │                                                                     │
    │ 3. Low-volume noise                                                 │
    │    - units_7d_avg < threshold → not worth investigating             │
    │    - Natural recovery rate high, intervention not cost-effective    │
    └─────────────────────────────────────────────────────────────────────┘

    Returns: 'new_product_warmup' | 'established_traffic_loss' | 'low_volume_noise' | original
    """
    if traffic_sub != "traffic_throttle":
        return traffic_sub  # not our concern

    min_units = t.get("volume_drop_min_units_for_refine", 3.0)
    units = sku.units_7d_avg if sku.units_7d_avg is not None else 0.0
    if units < min_units:
        return "low_volume_noise"

    warmup_age_threshold = t.get("volume_drop_warmup_age_threshold", 14)
    age = sku.product_age_days if sku.product_age_days is not None else 999

    if age < warmup_age_threshold:
        return "new_product_warmup"
    return "established_traffic_loss"


def diagnose_sku(sku, baseline, category, peer, t: dict) -> Optional[DiagnosisResult]:
    """
    Diagnose volume drop at the SKU level.

    Args:
        sku: SkuMetrics with fields: id, units_3d_avg, units_14d_avg, units_7d_avg,
             conversion_rate_3d, conversion_rate_14d, competitor_price_gap_3d,
             competitor_price_gap_14d, product_age_days, channel
        baseline: category-level baseline metrics
        category: parent category metrics
        peer: peer SKU statistics (for relative comparison)
        t: thresholds dict

    Returns:
        DiagnosisResult or None if no anomaly detected.
    """
    # ── Anomaly detection: 3d units significantly below 14d baseline ──
    if sku.units_3d_avg is None or sku.units_14d_avg is None or sku.units_14d_avg == 0:
        return None
    units_ratio = sku.units_3d_avg / sku.units_14d_avg
    drop_threshold = t.get("volume_drop_units_ratio_threshold", 0.7)
    if units_ratio >= drop_threshold:
        return None  # not a drop

    # ── Root-cause classification ──
    sub_scenario = _classify_sub_scenario_by_signals(
        sku.competitor_price_gap_3d,
        sku.competitor_price_gap_14d,
        sku.conversion_rate_3d,
        sku.conversion_rate_14d,
        t,
    )
    sub_scenario = _refine_traffic_throttle(sub_scenario, sku, t)

    # ── Confidence: based on signal strength + sample size ──
    # Stronger drop + more data = higher confidence
    drop_magnitude = 1.0 - units_ratio  # 0 to 1
    sample_factor = min(sku.units_14d_avg / 10.0, 1.0)  # cap at 1
    confidence = round(min(drop_magnitude * sample_factor * 1.5, 0.95), 2)

    # ── Human-readable root cause ──
    cause_descriptions = {
        "competitive_pressure": (
            f"Competitor pricing tightened relative to this SKU "
            f"(3d gap {sku.competitor_price_gap_3d:.1%} vs 14d gap {sku.competitor_price_gap_14d:.1%}); "
            f"recommend price-position review."
        ),
        "listing_quality": (
            f"Conversion rate dropped from {sku.conversion_rate_14d:.2%} (14d) "
            f"to {sku.conversion_rate_3d:.2%} (3d); listing assets may be degrading "
            f"(stale photos, declining review velocity, or out-of-stock variants)."
        ),
        "new_product_warmup": (
            f"New product (age {sku.product_age_days}d) failing to gain platform momentum; "
            f"consider promotional boost or improved listing optimization."
        ),
        "established_traffic_loss": (
            f"Established SKU (age {sku.product_age_days}d) lost traffic without "
            f"conversion degradation; investigate search-rank position and seasonality."
        ),
        "low_volume_noise": (
            f"Low-volume SKU (7d avg {sku.units_7d_avg:.1f} units); "
            f"natural variance, intervention not cost-effective."
        ),
        "unknown": "Insufficient signals to classify root cause; manual review recommended.",
    }

    return DiagnosisResult(
        diagnosis=f"sales_volume_drop:{sub_scenario}",
        confidence=confidence,
        affected_scope="sku",
        affected_targets=[sku.id],
        root_cause=cause_descriptions.get(sub_scenario, "unknown"),
        evidence={
            "units_3d_avg": sku.units_3d_avg,
            "units_14d_avg": sku.units_14d_avg,
            "units_drop_pct": round((1 - units_ratio) * 100, 1),
            "conversion_rate_3d": sku.conversion_rate_3d,
            "conversion_rate_14d": sku.conversion_rate_14d,
            "competitor_price_gap_3d": sku.competitor_price_gap_3d,
            "competitor_price_gap_14d": sku.competitor_price_gap_14d,
            "product_age_days": sku.product_age_days,
            "channel": getattr(sku, "channel", None),
        },
        metadata={
            "sub_scenario": sub_scenario,
            "scenario_version": "1.0",
        },
    )


# Default thresholds — to be calibrated once 90+ days of sales data exist
DEFAULT_THRESHOLDS = {
    "volume_drop_units_ratio_threshold": 0.7,           # 3d/14d < 0.7 = drop
    "volume_drop_competitor_gap_widen_ratio": 1.5,      # 3d gap > 1.5x 14d gap
    "volume_drop_cvr_decline_ratio": 0.75,              # 3d cvr < 0.75x 14d cvr
    "volume_drop_min_units_for_refine": 3.0,            # skip refinement below this
    "volume_drop_warmup_age_threshold": 14,             # new product cutoff
}
