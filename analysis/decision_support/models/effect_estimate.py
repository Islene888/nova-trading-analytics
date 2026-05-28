"""
Pricing Decision Effect Estimate — Data Model.

Output of EffectPredictor, consumed by pricing decision workflow.
Based on weighted KNN: finds K most similar historical pricing cases
and uses their actual outcomes as the prediction.

Adapted from the ad-decision effect estimation framework developed
at a previous employer (WorkMagic), repurposed for e-commerce
pricing decisions at Nova Trading Inc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class PricingEffectEstimate:
    """Predicted effect of a single pricing action."""

    action_type: str                          # increase_price / decrease_price / promotional_discount / hold
    confidence: str = "low"                   # high / medium / low

    # ── Quantitative prediction (from neighbors' actual outcomes) ──
    margin_before: Optional[float] = None
    margin_after_p25: Optional[float] = None  # pessimistic (neighbor P25)
    margin_after_p50: Optional[float] = None  # expected (neighbor P50)
    margin_after_p75: Optional[float] = None  # optimistic (neighbor P75)

    # ── Counterfactual baseline (do-nothing scenario) ──
    margin_no_action: Optional[float] = None      # margin under natural trajectory
    incremental_lift_p50: Optional[float] = None  # action retention - natural retention

    units_before: Optional[float] = None
    units_after_p25: Optional[float] = None
    units_after_p50: Optional[float] = None
    units_after_p75: Optional[float] = None

    # ── KNN traceability ──
    neighbor_count: int = 0
    neighbor_ids: List[str] = field(default_factory=list)
    avg_distance: float = 0.0

    # ── Low-confidence fallback ──
    qualitative: Optional[str] = None         # "expected improvement" / "expected decline"
    note: str = ""

    def to_dict(self) -> dict:
        """Serialize for downstream consumption."""
        d: dict = {
            "action_type": self.action_type,
            "confidence": self.confidence,
            "neighbor_count": self.neighbor_count,
            "avg_distance": round(self.avg_distance, 4),
            "note": self.note,
        }

        if self.confidence in ("high", "medium"):
            d.update({
                "margin_before": self.margin_before,
                "margin_after_p25": self.margin_after_p25,
                "margin_after_p50": self.margin_after_p50,
                "margin_after_p75": self.margin_after_p75,
                "margin_no_action": self.margin_no_action,
                "incremental_lift_p50": self.incremental_lift_p50,
                "units_before": self.units_before,
                "units_after_p25": self.units_after_p25,
                "units_after_p50": self.units_after_p50,
                "units_after_p75": self.units_after_p75,
            })
        else:
            d.update({
                "qualitative": self.qualitative,
            })

        if self.neighbor_ids:
            d["neighbor_ids"] = self.neighbor_ids[:5]

        return d

    def summary(self) -> str:
        """Human-readable summary for review UI."""
        if self.confidence == "high":
            parts = [
                f"Based on {self.neighbor_count} most-similar historical cases, "
                f"margin projected {self.margin_after_p25:.2f} – {self.margin_after_p75:.2f} "
                f"(median {self.margin_after_p50:.2f})"
            ]
            if self.margin_no_action is not None:
                parts.append(f"hold-price margin projected {self.margin_no_action:.2f}")
            if self.incremental_lift_p50 is not None:
                direction = "uplift" if self.incremental_lift_p50 > 0 else "decline"
                parts.append(f"incremental {direction} {abs(self.incremental_lift_p50):.1%}")
            return "; ".join(parts)
        elif self.confidence == "medium":
            base = (
                f"Based on {self.neighbor_count} similar cases, "
                f"margin projected ~{self.margin_after_p50:.2f}"
            )
            if self.incremental_lift_p50 is not None:
                direction = "uplift" if self.incremental_lift_p50 > 0 else "decline"
                base += f" (incremental {direction} {abs(self.incremental_lift_p50):.1%})"
            return base
        else:
            return f"Insufficient similar historical cases; {self.qualitative or 'outcome uncertain'}, recommend manual review"
