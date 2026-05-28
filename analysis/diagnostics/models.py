"""
Diagnosis output models.

Adapted from the ad-performance diagnostic framework developed at a
previous employer (WorkMagic), repurposed for e-commerce sales anomaly
detection at Nova Trading Inc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class DiagnosisResult:
    """Diagnosis output returned by diagnose() functions."""

    diagnosis: str                       # scenario ID, e.g. 'sales_volume_drop'
    confidence: float                    # 0-1
    affected_scope: str                  # 'sku' | 'category' | 'channel'
    affected_targets: List[str]          # list of affected entity IDs
    root_cause: str                      # human-readable cause description
    evidence: dict                       # raw signal values for prescription + audit
    metadata: dict = field(default_factory=dict)


@dataclass
class PrescriptionResult:
    """Prescribed action(s) generated from a diagnosis."""

    diagnosis_id: str
    actions: List[dict]                  # list of recommended actions with parameters
    expected_effect: dict                # forecasted outcome of actions
    priority: int                        # 1 = highest
    requires_approval: bool = True
