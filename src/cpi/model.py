"""Prédiction précoce du risque d'abandon au point de décision (envoi de la 1re offre).

Usage visé : **prioriser les relances** des offres envoyées. Ce n'est ni un modèle
d'octroi ni un score de solvabilité : il n'intervient pas dans la décision de crédit
(voir ``docs/06-conformite-ia-rgpd.md``).

Protocole :

* découpage temporel strict (:func:`cpi.features.temporal_split`) ;
* trois candidats : une **règle simple** (délai avant la 1re offre), une **régression
  logistique** et un **gradient boosting** LightGBM ;
* hyperparamètres choisis par validation croisée temporelle (fenêtres croissantes) à
  l'intérieur de la période d'apprentissage ;
* évaluation unique sur la période de test, avec intervalles de confiance bootstrap et
  confrontation à des seuils d'acceptation fixés à l'avance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from cpi.config import OBSERVATION_DAYS, SEED, TEST_START, TOP_K_SHARES, TRAIN_END, TRAIN_START
from cpi.features import FEATURES, FOLLOW_UP_FEATURES, Split, observe_after_offer

FEATURE_NAMES = list(FEATURES)
RULE_FEATURE = "hours_to_offer"
NON_NEGATIVE = {
    "amount_req",
    "hours_to_offer",
    "hours_precheck",
    "hours_completion",
    "n_events",
    "completion_calls",
    "completion_work_min",
    "completion_wait_h",
    "max_gap_completion_h",
    "lead_calls",
    "n_resources",
    "offer_calls",
    "offer_call_min",
    "offer_call_max_min",
    "since_last_call_h",
    "offers_sent",
    "offers_cancelled",
}

#: Seuils d'acceptation fixés avant l'évaluation (voir docs/07-plan-de-recette.md).
ACCEPTANCE = {
    "roc_auc_min": 0.65,
    "lift_at_20_min": 1.5,
    "score_psi_max": 0.2,
    "calibration_gap_max": 0.05,
}

BASE_PARAMS: dict[str, Any] = {
    "objective": "binary",
    "learning_rate": 0.03,
    "subsample": 0.8,
    "subsample_freq": 1,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "random_state": SEED,
    "deterministic": True,
    "force_col_wise": True,
    "n_jobs": 1,
    "verbose": -1,
}
GBM_GRID = [
    {"num_leaves": nl, "min_child_samples": mcs, "n_estimators": ne}
    for nl in (7, 15)
    for mcs in (40, 80)
    for ne in (50, 100, 200, 400)
]
LOGREG_GRID = [0.01, 0.1, 1.0]


def _log_skewed(x: pd.DataFrame) -> pd.DataFrame:
    x = x.copy()
    for col in x.columns:
        if col in NON_NEGATIVE:
            x[col] = np.log1p(x[col].clip(lower=0))
    return x


def make_logreg(c: float = 1.0) -> Pipeline:
    return Pipeline(
        [
            ("log", FunctionTransformer(_log_skewed)),
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(C=c, max_iter=5000)),
        ]
    )


def make_gbm(params: dict[str, Any]) -> lgb.LGBMClassifier:
    return lgb.LGBMClassifier(**{**BASE_PARAMS, **params})


def temporal_folds(n: int, k: int = 3) -> list[tuple[np.ndarray, np.ndarray]]:
    """Validation croisée à fenêtres croissantes sur des lignes triées par date."""
    edges = np.linspace(0, n, k + 2).astype(int)
    return [(np.arange(0, edges[i]), np.arange(edges[i], edges[i + 1])) for i in range(1, k + 1)]


def _cv_auc(make: Any, x: pd.DataFrame, y: pd.Series) -> float:
    scores = []
    for tr, va in temporal_folds(len(x)):
        model = make().fit(x.iloc[tr], y.iloc[tr])
        scores.append(roc_auc_score(y.iloc[va], np.asarray(model.predict_proba(x.iloc[va]))[:, 1]))
    return float(np.mean(scores))


@dataclass
class Trained:
    logreg: Pipeline
    gbm: lgb.LGBMClassifier
    logreg_c: float
    gbm_params: dict[str, Any]
    cv: dict[str, Any]


def fit_models(split: Split, features: list[str] | None = None) -> Trained:
    feats = features or FEATURE_NAMES
    x, y = split.train[feats], split.train["label"]
    lr_scores = {c: _cv_auc(lambda c=c: make_logreg(c), x, y) for c in LOGREG_GRID}
    best_c = max(lr_scores, key=lambda c: lr_scores[c])
    gbm_scores = [(_cv_auc(lambda p=p: make_gbm(p), x, y), p) for p in GBM_GRID]
    best_score, best_params = max(gbm_scores, key=lambda t: t[0])
    return Trained(
        logreg=make_logreg(best_c).fit(x, y),
        gbm=make_gbm(best_params).fit(x, y),
        logreg_c=best_c,
        gbm_params=best_params,
        cv={
            "folds": 3,
            "logreg_auc_by_c": {str(k): round(v, 4) for k, v in lr_scores.items()},
            "gbm_best_cv_auc": round(best_score, 4),
            "gbm_grid_size": len(GBM_GRID),
        },
    )


def _thin(x: np.ndarray, y: np.ndarray, n: int = 120) -> list[list[float]]:
    idx = np.unique(np.linspace(0, len(x) - 1, min(n, len(x))).astype(int))
    return [[round(float(x[i]), 4), round(float(y[i]), 4)] for i in idx]


def calibration_bins(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict[str, float]]:
    """Diagramme de fiabilité : déciles de probabilité prédite."""
    order = np.argsort(p, kind="mergesort")
    return [
        {
            "mean_predicted": round(float(p[chunk].mean()), 4),
            "observed_rate": round(float(y[chunk].mean()), 4),
            "n": len(chunk),
        }
        for chunk in np.array_split(order, bins)
    ]


def expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    cal = calibration_bins(y, p, bins)
    n = len(y)
    return float(sum(b["n"] / n * abs(b["mean_predicted"] - b["observed_rate"]) for b in cal))


def gains(y: np.ndarray, p: np.ndarray, shares: tuple[float, ...] = TOP_K_SHARES) -> dict[str, Any]:
    """Courbe de gain et lecture métier « appeler d'abord les k % les plus à risque »."""
    order = np.argsort(-p, kind="mergesort")
    y_sorted = y[order]
    total_pos = y.sum()
    n = len(y)
    cum = np.cumsum(y_sorted) / total_pos
    curve = [[0.0, 0.0]] + [
        [round((i + 1) / n, 4), round(float(cum[i]), 4)]
        for i in np.unique(np.linspace(0, n - 1, 101).astype(int))
    ]
    at_k = []
    for k in shares:
        m = max(round(k * n), 1)
        top = y_sorted[:m]
        at_k.append(
            {
                "share": k,
                "cases": m,
                "recall": round(float(top.sum() / total_pos), 4),
                "precision": round(float(top.mean()), 4),
                "lift": round(float(top.mean() / y.mean()), 3),
            }
        )
    deciles = [
        {
            "decile": d,
            "n": len(chunk),
            "positives": int(y[chunk].sum()),
            "rate": round(float(y[chunk].mean()), 4),
        }
        for d, chunk in enumerate(np.array_split(order, 10), start=1)
    ]
    return {"curve": curve, "at_k": at_k, "deciles": deciles}


def metrics(y: np.ndarray, p: np.ndarray, probabilistic: bool = True) -> dict[str, float | None]:
    out: dict[str, float | None] = {
        "roc_auc": round(float(roc_auc_score(y, p)), 4),
        "pr_auc": round(float(average_precision_score(y, p)), 4),
        "base_rate": round(float(y.mean()), 4),
    }
    if probabilistic:
        out |= {
            "brier": round(float(brier_score_loss(y, p)), 4),
            "log_loss": round(float(log_loss(y, p)), 4),
            "mean_predicted": round(float(p.mean()), 4),
            "ece": round(expected_calibration_error(y, p), 4),
        }
    return out


def bootstrap_ci(y: np.ndarray, scores: dict[str, np.ndarray], n_boot: int = 1000) -> dict:
    """IC à 95 % (bootstrap apparié) des AUC, PR-AUC et des écarts au modèle de référence."""
    rng = np.random.default_rng(SEED)
    names = list(scores)
    acc: dict[str, list[float]] = {}
    n = len(y)
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        if y[i].min() == y[i].max():
            continue
        aucs = {k: roc_auc_score(y[i], scores[k][i]) for k in names}
        for k in names:
            acc.setdefault(f"{k}_roc_auc", []).append(aucs[k])
            acc.setdefault(f"{k}_pr_auc", []).append(average_precision_score(y[i], scores[k][i]))
        for k in names[1:]:
            acc.setdefault(f"{k}_minus_{names[0]}_auc", []).append(aucs[k] - aucs[names[0]])
    return {
        k: [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]
        for k, v in acc.items()
    }


def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """Indice de stabilité de population (déciles de la distribution de référence)."""
    qs = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    if len(qs) < 3:
        return 0.0
    qs[0], qs[-1] = -np.inf, np.inf
    e = np.clip(np.histogram(expected, qs)[0] / len(expected), 1e-4, None)
    a = np.clip(np.histogram(actual, qs)[0] / len(actual), 1e-4, None)
    return float(np.sum((a - e) * np.log(a / e)))


def shap_summary(
    gbm: lgb.LGBMClassifier, x: pd.DataFrame, top: int = 8, sample: int = 400
) -> dict[str, Any]:
    """Valeurs SHAP exactes (TreeSHAP natif de LightGBM) sur la période de test."""
    contrib = np.asarray(gbm.predict(x, pred_contrib=True))[:, :-1]
    mean_abs = np.abs(contrib).mean(axis=0)
    order = np.argsort(-mean_abs)
    rng = np.random.default_rng(SEED)
    idx = rng.choice(len(x), size=min(sample, len(x)), replace=False)
    points = []
    for j in order[:top]:
        col = x.columns[j]
        ranks = pd.Series(x[col].to_numpy(dtype=float)).rank(pct=True).to_numpy()
        points.append(
            {
                "feature": col,
                "label": FEATURES[col],
                "points": [
                    [round(float(contrib[i, j]), 4), round(float(ranks[i]), 3)] for i in idx
                ],
            }
        )
    return {
        "importance": [
            {
                "feature": x.columns[j],
                "label": FEATURES[x.columns[j]],
                "mean_abs_shap": round(float(mean_abs[j]), 4),
            }
            for j in order
        ],
        "beeswarm": points,
    }


def acceptance(gbm: dict[str, Any], score_psi: float) -> dict[str, Any]:
    m = gbm["metrics"]
    lift20 = next(a["lift"] for a in gbm["gains"]["at_k"] if a["share"] == 0.2)
    checks = [
        {
            "criterion": "ROC-AUC sur la période de test",
            "threshold": f"≥ {ACCEPTANCE['roc_auc_min']}",
            "value": m["roc_auc"],
            "passed": m["roc_auc"] >= ACCEPTANCE["roc_auc_min"],
        },
        {
            "criterion": "Lift à 20 % des dossiers",
            "threshold": f"≥ {ACCEPTANCE['lift_at_20_min']}",
            "value": lift20,
            "passed": lift20 >= ACCEPTANCE["lift_at_20_min"],
        },
        {
            "criterion": "Écart de calibration (ECE)",
            "threshold": f"≤ {ACCEPTANCE['calibration_gap_max']}",
            "value": m["ece"],
            "passed": m["ece"] <= ACCEPTANCE["calibration_gap_max"],
        },
        {
            "criterion": "Stabilité du score (PSI apprentissage → test)",
            "threshold": f"< {ACCEPTANCE['score_psi_max']}",
            "value": round(score_psi, 4),
            "passed": score_psi < ACCEPTANCE["score_psi_max"],
        },
    ]
    return {"checks": checks, "deployable": all(c["passed"] for c in checks)}


def evaluate(split: Split, trained: Trained) -> dict[str, Any]:
    x_te = split.test[FEATURE_NAMES]
    y_te = split.test["label"].to_numpy()
    scores = {
        "rule": split.test[RULE_FEATURE].to_numpy(dtype=float),
        "logreg": np.asarray(trained.logreg.predict_proba(x_te))[:, 1],
        "gbm": np.asarray(trained.gbm.predict_proba(x_te))[:, 1],
    }
    out: dict[str, Any] = {"models": {}}
    for name, p in scores.items():
        fpr, tpr, _ = roc_curve(y_te, p)
        prec, rec, _ = precision_recall_curve(y_te, p)
        entry: dict[str, Any] = {
            "metrics": metrics(y_te, p, probabilistic=name != "rule"),
            "roc": _thin(fpr, tpr),
            "pr": _thin(rec[::-1], prec[::-1]),
            "gains": gains(y_te, p),
        }
        if name != "rule":
            entry["calibration"] = calibration_bins(y_te, p)
        out["models"][name] = entry
    out["bootstrap_ci"] = bootstrap_ci(y_te, scores)

    perm = permutation_importance(
        trained.gbm, x_te, y_te, scoring="roc_auc", n_repeats=10, random_state=SEED, n_jobs=1
    )
    out["permutation_importance"] = sorted(
        (
            {
                "feature": f,
                "label": FEATURES[f],
                "mean": round(float(m), 4),
                "std": round(float(s), 4),
            }
            for f, m, s in zip(
                FEATURE_NAMES, perm.importances_mean, perm.importances_std, strict=True
            )
        ),
        key=lambda d: -d["mean"],
    )
    out["shap"] = shap_summary(trained.gbm, x_te)
    coefs = trained.logreg.named_steps["clf"].coef_[0]
    out["logreg_coefficients"] = sorted(
        (
            {"feature": f, "label": FEATURES[f], "coef": round(float(c), 4)}
            for f, c in zip(FEATURE_NAMES, coefs, strict=True)
        ),
        key=lambda d: -abs(d["coef"]),
    )

    # Stabilité par segment de montant (lecture de robustesse, pas d'équité).
    seg = pd.cut(
        split.test["amount_req"],
        [0, 10_000, 20_000, np.inf],
        labels=["< 10 k€", "10–20 k€", "≥ 20 k€"],
        right=False,
    )
    rows = []
    for band in seg.cat.categories:
        mask = (seg == band).to_numpy()
        yy, pp = y_te[mask], scores["gbm"][mask]
        ok = mask.sum() >= 50 and 0 < yy.sum() < len(yy)
        rows.append(
            {
                "segment": str(band),
                "n": int(mask.sum()),
                "base_rate": round(float(yy.mean()), 4) if mask.any() else None,
                "roc_auc": round(float(roc_auc_score(yy, pp)), 4) if ok else None,
                "mean_predicted": round(float(pp.mean()), 4) if mask.any() else None,
            }
        )
    out["segments"] = rows

    p_tr = np.asarray(trained.gbm.predict_proba(split.train[FEATURE_NAMES]))[:, 1]
    score_psi = psi(p_tr, scores["gbm"])
    out["drift"] = {
        "score_psi_train_vs_test": round(score_psi, 4),
        "features": sorted(
            (
                {
                    "feature": f,
                    "label": FEATURES[f],
                    "psi": round(psi(split.train[f].to_numpy(float), x_te[f].to_numpy(float)), 4),
                }
                for f in FEATURE_NAMES
            ),
            key=lambda d: -d["psi"],
        ),
    }
    out["acceptance"] = acceptance(out["models"]["gbm"], score_psi)
    out["test_scores"] = {
        "case_id": split.test.index.tolist(),
        "p_gbm": [round(float(v), 5) for v in scores["gbm"]],
        "label": y_te.astype(int).tolist(),
    }
    return out


def horizon_study(
    dataset: pd.DataFrame,
    events: pd.DataFrame,
    sessions: pd.DataFrame,
    cases: pd.DataFrame,
    days: tuple[float, ...] = (0, 3, 7, 14),
) -> list[dict[str, Any]]:
    """Le signal augmente-t-il si l'on attend (avec l'historique des relances) ?"""
    from cpi.features import temporal_split

    log_end = events["timestamp"].max()
    feats = FEATURE_NAMES + list(FOLLOW_UP_FEATURES)
    rows = []
    for d in days:
        obs = observe_after_offer(dataset, events, sessions, cases, d)
        sp = temporal_split(obs, log_end)
        x_tr, y_tr = sp.train[feats], sp.train["label"]
        x_te, y_te = sp.test[feats], sp.test["label"].to_numpy()
        gbm = make_gbm({"num_leaves": 7, "min_child_samples": 80, "n_estimators": 100})
        gbm.fit(x_tr, y_tr)
        lr = make_logreg(0.1).fit(x_tr, y_tr)
        p_gb = np.asarray(gbm.predict_proba(x_te))[:, 1]
        p_lr = np.asarray(lr.predict_proba(x_te))[:, 1]
        rows.append(
            {
                "days_after_offer": d,
                "train_cases": len(sp.train),
                "test_cases": len(sp.test),
                "test_base_rate": round(float(y_te.mean()), 4),
                "gbm_roc_auc": round(float(roc_auc_score(y_te, p_gb)), 4),
                "logreg_roc_auc": round(float(roc_auc_score(y_te, p_lr)), 4),
                "gbm_recall_at_20": gains(y_te, p_gb)["at_k"][1]["recall"],
            }
        )
    return rows


def alternative_split_metrics(dataset: pd.DataFrame, split: Split, trained: Trained) -> dict:
    """Contrôle : découpage temporel simple (sans purge ni zone tampon)."""
    simple = dataset[(dataset["t_dec"] >= TRAIN_START) & (dataset["t_dec"] < TEST_START)]
    simple = simple[simple["outcome"] != "open"]
    gbm = make_gbm(trained.gbm_params).fit(simple[FEATURE_NAMES], simple["label"])
    p = np.asarray(gbm.predict_proba(split.test[FEATURE_NAMES]))[:, 1]
    return {"train_cases": len(simple), **metrics(split.test["label"].to_numpy(), p)}


def run(
    dataset: pd.DataFrame,
    split: Split,
    events: pd.DataFrame,
    sessions: pd.DataFrame,
    cases: pd.DataFrame,
) -> tuple[dict[str, Any], Trained]:
    trained = fit_models(split)
    results = evaluate(split, trained)
    results["alternative_split"] = alternative_split_metrics(dataset, split, trained)
    results["horizons"] = horizon_study(dataset, events, sessions, cases)
    results["selection"] = {
        "logreg_c": trained.logreg_c,
        "gbm_params": trained.gbm_params,
        **trained.cv,
    }
    results["protocol"] = {
        "decision_point": "Envoi de la première offre (O_SENT)",
        "label": "Dossier finalement annulé (1) contre approuvé ou refusé (0)",
        "train_window": [TRAIN_START.date().isoformat(), TRAIN_END.date().isoformat()],
        "deployment_date": TEST_START.date().isoformat(),
        "observation_days": OBSERVATION_DAYS,
        "train_cases": len(split.train),
        "train_positive_rate": round(float(split.train["label"].mean()), 4),
        "test_cases": len(split.test),
        "test_positive_rate": round(float(split.test["label"].mean()), 4),
        "test_window": [
            split.test["t_dec"].min().date().isoformat(),
            split.test["t_dec"].max().date().isoformat(),
        ],
        "excluded": split.excluded,
        "features": [{"feature": k, "label": v} for k, v in FEATURES.items()],
    }
    return results, trained
