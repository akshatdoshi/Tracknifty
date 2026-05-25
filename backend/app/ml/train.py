"""Phase-1 model training — gradient boosting (XGBoost).

Chosen because it is interpretable via SHAP, handles missing features natively,
trains fast on this data size, and needs no GPU. A holdout split provides the
accuracy metrics stored with each model version.
"""

from __future__ import annotations

import logging

import numpy as np
import xgboost as xgb
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session

from app.db.models import ModelVersion
from app.features.engineering import FEATURE_NAMES
from app.ml.labels import build_training_frame
from app.ml.registry import save_model

logger = logging.getLogger(__name__)


def train_model(db: Session) -> ModelVersion:
    X, y, meta = build_training_frame(db)
    if len(X) < 50:
        raise RuntimeError(
            f"Not enough training samples ({len(X)}); seed price history first."
        )

    classes = sorted(set(y))
    class_to_idx = {c: i for i, c in enumerate(classes)}
    y_enc = np.array([class_to_idx[v] for v in y])

    counts = {c: int((y_enc == i).sum()) for c, i in class_to_idx.items()}
    stratify = y_enc if min(counts.values()) >= 2 else None
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=stratify
    )

    clf = xgb.XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9,
        eval_metric="mlogloss", tree_method="hist", n_jobs=4,
        random_state=42,
    )
    clf.fit(X_tr, y_tr)

    preds = clf.predict(X_te)
    metrics = {
        "accuracy": round(float(accuracy_score(y_te, preds)), 4),
        "macro_f1": round(float(f1_score(y_te, preds, average="macro")), 4),
        "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)),
        "class_distribution": counts,
    }
    logger.info("Trained model: %s", metrics)

    booster = clf.get_booster()
    booster.feature_names = FEATURE_NAMES
    return save_model(db, booster, FEATURE_NAMES, classes, metrics, len(X))
