"""Inference — turn a feature vector into a raw model recommendation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import xgboost as xgb

from app.features.engineering import FEATURE_NAMES
from app.ml.explain import explain_prediction


@dataclass
class Prediction:
    signal: str            # BUY | SELL | HOLD (raw, pre-rules)
    confidence: float      # 0-100
    class_idx: int
    drivers: list[dict]
    explanation: str


def predict(
    booster: xgb.Booster, classes: list[str], vector: list[float]
) -> Prediction:
    dmatrix = xgb.DMatrix(np.array([vector], dtype=float), feature_names=FEATURE_NAMES)
    proba = np.asarray(booster.predict(dmatrix))[0]
    class_idx = int(np.argmax(proba))
    signal = classes[class_idx]
    confidence = round(float(proba[class_idx]) * 100.0, 2)

    drivers, explanation = explain_prediction(
        booster, vector, class_idx, n_classes=len(classes)
    )
    return Prediction(
        signal=signal, confidence=confidence, class_idx=class_idx,
        drivers=drivers, explanation=explanation,
    )
