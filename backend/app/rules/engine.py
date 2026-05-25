"""Rules & guardrails.

Takes the raw model recommendation plus the stock's context and applies the
per-portfolio guardrails from the outline. Guardrails only ever make a signal
*more* conservative (Buy -> Hold) or flag a position for review — they never
manufacture a Buy the model didn't produce. Because rules are read at scoring
time, editing them in the UI changes signals on the next run with no deploy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.config import settings
from app.db.models import Rule
from app.ml.score import Prediction


@dataclass
class RuleOutcome:
    signal: str
    confidence: float
    notes: list[str] = field(default_factory=list)
    breach_min: bool = False
    breach_max: bool = False


def _is_nan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def apply_rules(prediction: Prediction, context: dict, rule: Rule) -> RuleOutcome:
    signal = prediction.signal
    confidence = prediction.confidence
    notes: list[str] = []

    weight = context.get("weight_pct")
    momentum = context.get("momentum_vs_benchmark_pct")
    vol_ratio = context.get("vol_ratio")
    derisked = context.get("derisked") == 1.0

    breach_min = not _is_nan(weight) and weight < rule.min_weight_pct
    breach_max = not _is_nan(weight) and weight > rule.max_weight_pct

    # Confidence floor: only show conviction above the floor.
    if confidence < rule.confidence_floor:
        notes.append(
            f"Confidence {confidence:.0f}% below floor "
            f"{rule.confidence_floor:.0f}% — downgraded to Hold."
        )
        signal = "HOLD"

    if signal == "BUY":
        if not _is_nan(weight) and weight >= rule.min_weight_pct:
            signal = "HOLD"
            notes.append(
                f"Weight {weight:.1f}% at/above buy ceiling "
                f"{rule.min_weight_pct:.0f}% — Buy suppressed."
            )
        if not _is_nan(momentum) and momentum < rule.momentum_threshold_pct:
            signal = "HOLD"
            notes.append(
                f"3M alpha {momentum:.1f}% below momentum threshold "
                f"{rule.momentum_threshold_pct:.0f}% — Buy suppressed."
            )
        if not _is_nan(vol_ratio) and vol_ratio > rule.volatility_ceiling:
            signal = "HOLD"
            notes.append(
                f"Volatility {vol_ratio:.2f}x exceeds ceiling "
                f"{rule.volatility_ceiling:.2f}x — Buy suppressed."
            )
        if (
            rule.derisk_override and derisked
            and confidence < rule.confidence_floor + settings.derisk_extra_confidence
        ):
            signal = "HOLD"
            notes.append(
                "Position already de-risked — higher confidence required for "
                "further Buy; suppressed."
            )

    if breach_max:
        notes.append(
            f"Weight {weight:.1f}% exceeds max {rule.max_weight_pct:.0f}% — "
            "flagged for Sell review."
        )

    return RuleOutcome(
        signal=signal, confidence=confidence, notes=notes,
        breach_min=breach_min, breach_max=breach_max,
    )
