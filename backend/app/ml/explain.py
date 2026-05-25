"""SHAP explanations.

Uses TreeSHAP (XGBoost's ``pred_contribs``) to decompose a single prediction
into per-feature contributions, then surfaces the top drivers with a direction
and a normalised contribution share, plus a one-line plain-English summary — the
material the dashboard's detail panel renders.
"""

from __future__ import annotations

import numpy as np
import xgboost as xgb

from app.features.engineering import FEATURE_LABELS, FEATURE_NAMES


def explain_prediction(
    booster: xgb.Booster,
    vector: list[float],
    class_idx: int,
    n_classes: int,
    top_n: int = 4,
) -> tuple[list[dict], str]:
    """Return (drivers, plain_english) for the predicted class."""
    dmatrix = xgb.DMatrix(np.array([vector], dtype=float), feature_names=FEATURE_NAMES)
    contribs = booster.predict(dmatrix, pred_contribs=True)

    # Multiclass -> (1, n_classes, n_features+1); else (1, n_features+1).
    if contribs.ndim == 3:
        row = contribs[0, class_idx]
    else:
        row = contribs[0]
    feature_contribs = row[:-1]  # drop bias term

    total = float(np.sum(np.abs(feature_contribs))) or 1.0
    order = np.argsort(np.abs(feature_contribs))[::-1][:top_n]

    drivers: list[dict] = []
    for j in order:
        contrib = float(feature_contribs[j])
        if contrib > 1e-6:
            direction = "Positive"
        elif contrib < -1e-6:
            direction = "Negative"
        else:
            direction = "Neutral"
        drivers.append(
            {
                "feature": FEATURE_NAMES[j],
                "label": FEATURE_LABELS.get(FEATURE_NAMES[j], FEATURE_NAMES[j]),
                "direction": direction,
                "contribution": round(abs(contrib) / total, 4),
            }
        )

    return drivers, _plain_english(drivers)


def _plain_english(drivers: list[dict]) -> str:
    if not drivers:
        return "No dominant driver identified."
    top = drivers[0]
    lead = top["label"].lower()
    if top["direction"] == "Positive":
        return f"Driven mainly by favourable {lead}."
    if top["direction"] == "Negative":
        return f"Driven mainly by unfavourable {lead}."
    return f"Primarily influenced by {lead}."
