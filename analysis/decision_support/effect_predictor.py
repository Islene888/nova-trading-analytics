"""
Pricing Decision Effect Predictor — Weighted KNN.

Finds the K most similar historical pricing cases from the case library
and uses their actual outcomes as the prediction (weighted by inverse distance).

The case library is built by analysis/decision_support/build_case_library.py
from accumulated sales history once enough data exists.

Adapted from the ad-decision effect prediction framework developed
at a previous employer (WorkMagic), repurposed for Nova Trading Inc.
e-commerce pricing decisions.

Usage:
    predictor = PricingEffectPredictor.get()
    estimate = predictor.predict(
        action_type='decrease_price',
        margin_before=0.45,
        scope='sku',
        product_age_days=21,
        units_before_7d=15.0,
        conversion_rate_before=0.025,
        price_change_pct=-0.10,
        channel='shopify',
    )
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional, List

from analysis.decision_support.models.effect_estimate import PricingEffectEstimate

_LIBRARY_PATH = (
    Path(__file__).resolve().parent / "case_library.json"
)

# KNN parameters
DEFAULT_K = 20
EPSILON = 1e-6
HIGH_CONFIDENCE_MIN_K = 20
HIGH_CONFIDENCE_MAX_SPREAD = 0.5
MEDIUM_CONFIDENCE_MIN_K = 10

# Numerical features used for distance computation
_DISTANCE_FEATURES = [
    "margin_before",
    "units_before_7d",
    "conversion_rate_before",
    "product_age_days",
    "price_change_pct",
    "competitor_price_gap_pct",
]

# Low-confidence fallback qualitative labels
_QUALITATIVE = {
    "increase_price": "expected margin uplift but unit-volume compression",
    "decrease_price": "expected volume uplift but margin compression",
    "promotional_discount": "expected short-term spike with post-promo dip risk",
    "hold": "expected drift along natural trajectory",
}


class PricingEffectPredictor:
    """Weighted KNN pricing-effect predictor. Singleton; lazy-loads on first call."""

    _instance: Optional["PricingEffectPredictor"] = None

    def __init__(self):
        self._cases: list[dict] = []
        self._scaling: dict[str, dict] = {}
        self._natural_baseline: dict[str, dict] = {}
        self._meta: dict = {}
        self._loaded = False

    @classmethod
    def get(cls) -> "PricingEffectPredictor":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load()
        return cls._instance

    @classmethod
    def reload(cls) -> None:
        cls._instance = None

    def _load(self) -> None:
        if not _LIBRARY_PATH.exists():
            print(f"[PricingEffectPredictor] case library not found at {_LIBRARY_PATH}")
            self._loaded = False
            return

        data = json.loads(_LIBRARY_PATH.read_text())
        self._cases = data.get("cases", [])
        self._scaling = data.get("scaling", {})
        self._natural_baseline = data.get("natural_baseline", {})
        self._meta = data.get("meta", {})
        self._loaded = True
        print(
            f"[PricingEffectPredictor] Loaded {len(self._cases)} cases "
            f"(built {self._meta.get('built_at', 'unknown')})"
        )

    def predict(
        self,
        action_type: str,
        margin_before: Optional[float] = None,
        scope: str = "sku",
        product_age_days: Optional[int] = None,
        units_before_7d: Optional[float] = None,
        conversion_rate_before: Optional[float] = None,
        price_change_pct: Optional[float] = None,
        competitor_price_gap_pct: Optional[float] = None,
        channel: Optional[str] = None,
        k: int = DEFAULT_K,
    ) -> PricingEffectEstimate:
        """Predict the effect of a pricing action."""
        if not self._loaded or not self._cases:
            return self._low_confidence(action_type, margin_before, units_before_7d)

        # ── 1. Exact-match filtering (action_type must match) ──
        candidates = [c for c in self._cases if c["action_type"] == action_type]

        scope_candidates = [c for c in candidates if c["scope"] == scope]
        if len(scope_candidates) >= k:
            candidates = scope_candidates

        if channel and len(candidates) >= k * 2:
            channel_candidates = [c for c in candidates if c.get("channel") == channel]
            if len(channel_candidates) >= k:
                candidates = channel_candidates

        if len(candidates) < MEDIUM_CONFIDENCE_MIN_K:
            return self._low_confidence(action_type, margin_before, units_before_7d)

        # ── 2. Compute distances ──
        query_vec = self._scale_features({
            "margin_before": margin_before,
            "units_before_7d": units_before_7d,
            "conversion_rate_before": conversion_rate_before,
            "product_age_days": float(product_age_days) if product_age_days is not None else None,
            "price_change_pct": price_change_pct,
            "competitor_price_gap_pct": competitor_price_gap_pct,
        })

        scored = []
        for c in candidates:
            c_vec = self._scale_features({f: c.get(f) for f in _DISTANCE_FEATURES})
            dist = self._euclidean(query_vec, c_vec)
            scored.append((dist, c))

        scored.sort(key=lambda x: x[0])
        nearest = scored[:k]

        # ── 3. Weighted quantiles ──
        distances = [d for d, _ in nearest]
        weights = [1.0 / (d + EPSILON) for d in distances]
        total_w = sum(weights)
        weights = [w / total_w for w in weights]

        margin_retentions = [c["margin_retention"] for _, c in nearest if c.get("margin_retention")]
        units_changes = [c.get("units_change") for _, c in nearest if c.get("units_change")]

        if not margin_retentions:
            return self._low_confidence(action_type, margin_before, units_before_7d)

        mr_p25 = _weighted_percentile(margin_retentions, weights[:len(margin_retentions)], 0.25)
        mr_p50 = _weighted_percentile(margin_retentions, weights[:len(margin_retentions)], 0.50)
        mr_p75 = _weighted_percentile(margin_retentions, weights[:len(margin_retentions)], 0.75)

        uc_p25, uc_p50, uc_p75 = None, None, None
        if units_changes and len(units_changes) >= 5:
            uc_w = weights[:len(units_changes)]
            uc_p25 = _weighted_percentile(units_changes, uc_w, 0.25)
            uc_p50 = _weighted_percentile(units_changes, uc_w, 0.50)
            uc_p75 = _weighted_percentile(units_changes, uc_w, 0.75)

        # ── 4. Confidence ──
        import statistics as stats
        spread = stats.stdev(margin_retentions) if len(margin_retentions) >= 2 else 999
        avg_dist = sum(distances) / len(distances) if distances else 999

        if len(nearest) >= HIGH_CONFIDENCE_MIN_K and spread < HIGH_CONFIDENCE_MAX_SPREAD:
            confidence = "high"
        elif len(nearest) >= MEDIUM_CONFIDENCE_MIN_K:
            confidence = "medium"
        else:
            confidence = "low"

        # ── 5. Natural baseline (counterfactual: hold-price outcome) ──
        natural_retention_p50 = self._get_natural_retention(margin_before, product_age_days)

        incremental_lift_p50 = None
        if natural_retention_p50 is not None:
            incremental_lift_p50 = round(mr_p50 - natural_retention_p50, 4)

        # ── 6. Build output ──
        m_b = margin_before or 0.0
        u_b = units_before_7d or 0.0

        margin_no_action = (
            round(m_b * natural_retention_p50, 4)
            if natural_retention_p50 and margin_before else None
        )

        note_parts = [f"Based on {len(nearest)} most-similar historical cases"]
        if natural_retention_p50 is not None:
            note_parts.append(f"natural baseline retention {natural_retention_p50:.0%}")
        if incremental_lift_p50 is not None:
            direction = "uplift" if incremental_lift_p50 > 0 else "decline"
            note_parts.append(f"incremental {direction} {abs(incremental_lift_p50):.1%}")

        return PricingEffectEstimate(
            action_type=action_type,
            confidence=confidence,
            margin_before=margin_before,
            margin_after_p25=round(m_b * mr_p25, 4) if margin_before else None,
            margin_after_p50=round(m_b * mr_p50, 4) if margin_before else None,
            margin_after_p75=round(m_b * mr_p75, 4) if margin_before else None,
            margin_no_action=margin_no_action,
            incremental_lift_p50=incremental_lift_p50,
            units_before=units_before_7d,
            units_after_p25=round(u_b * uc_p25, 2) if uc_p25 and units_before_7d else None,
            units_after_p50=round(u_b * uc_p50, 2) if uc_p50 and units_before_7d else None,
            units_after_p75=round(u_b * uc_p75, 2) if uc_p75 and units_before_7d else None,
            neighbor_count=len(nearest),
            neighbor_ids=[c["case_id"] for _, c in nearest[:5]],
            avg_distance=round(avg_dist, 4),
            note="; ".join(note_parts),
        )

    def _get_natural_retention(
        self, margin_before: Optional[float], product_age_days: Optional[int]
    ) -> Optional[float]:
        """Look up the natural-baseline P50 retention for matching segment."""
        if not self._natural_baseline:
            return None
        margin_t = self._margin_tier_str(margin_before)
        age_t = self._age_tier_str(product_age_days)

        key = f"{margin_t}|{age_t}"
        seg = self._natural_baseline.get(key)
        if seg:
            return seg.get("p50")

        for k, v in self._natural_baseline.items():
            if k.startswith(f"{margin_t}|"):
                return v.get("p50")

        return None

    @staticmethod
    def _margin_tier_str(margin: Optional[float]) -> str:
        if margin is None: return "unknown"
        if margin < 0.10: return "thin"
        if margin < 0.30: return "modest"
        if margin < 0.50: return "healthy"
        if margin < 0.70: return "strong"
        return "premium"

    @staticmethod
    def _age_tier_str(age: Optional[int]) -> str:
        if age is None: return "unknown"
        if age < 14: return "new"
        if age < 60: return "ramping"
        return "established"

    def _low_confidence(
        self, action_type: str, margin_before=None, units_before=None
    ) -> PricingEffectEstimate:
        return PricingEffectEstimate(
            action_type=action_type,
            confidence="low",
            margin_before=margin_before,
            units_before=units_before,
            qualitative=_QUALITATIVE.get(action_type, "outcome uncertain"),
            note="Insufficient similar historical cases; treat as exploratory",
        )

    def _scale_features(self, raw: dict) -> List[float]:
        result = []
        for feat in _DISTANCE_FEATURES:
            val = raw.get(feat)
            params = self._scaling.get(feat, {"mean": 0, "std": 1})
            if val is None:
                result.append(0.0)
            else:
                std = params["std"] if params["std"] > 0 else 1.0
                result.append((float(val) - params["mean"]) / std)
        return result

    def _euclidean(self, a: List[float], b: List[float]) -> float:
        return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def _weighted_percentile(values: list, weights: list, percentile: float) -> float:
    """Compute weighted percentile. values and weights must be same length."""
    if not values:
        return 0.0
    paired = sorted(zip(values, weights), key=lambda x: x[0])
    cumulative = 0.0
    target = percentile * sum(w for _, w in paired)
    for val, w in paired:
        cumulative += w
        if cumulative >= target:
            return val
    return paired[-1][0]
