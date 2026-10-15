"""The baseline pipeline as an inspectable object: fit, exact contributions, bootstrap, OOD ranges, locked artifact.

`fit_pipeline` reproduces `c3.fit_predict((None, 'none', 'none', 'none', 'ridge'), ...)` exactly (same BASE_PRE, same
verified-label ridge with inner patient-grouped choice of C, same seed), but keeps the fitted parts so that every
prediction can be decomposed: logit = intercept + sum_j coef_j * z_j, z = standardised (imputed) input.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.base import clone

from prism.experiments.c3_radiomics import BASE_PRE, H
from prism.features.tabular import clinical, timing, treatment
from prism.models.formulations import fit as fit_ridge

GROUPS = ("clinical", "timing", "treatment")


def design(cohort: pd.DataFrame, index: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict[str, str]]:
    """Raw baseline features (as in c3.load) and feature -> group."""
    blocks = {"clinical": clinical(cohort), "timing": timing(cohort), "treatment": treatment(cohort, index)}
    X = pd.concat(blocks.values(), axis=1)
    return X, {c: g for g, b in blocks.items() for c in b.columns}


def source_feature(col: str) -> str:
    """Raw feature behind a preprocessed column ('missingindicator_x' -> 'x')."""
    return col.removeprefix("missingindicator_")


@dataclass
class Fitted:
    pre: object
    coef: np.ndarray
    intercept: float
    C: float
    columns: list[str]               # preprocessed column names (raw features + missingness indicators)
    raw_columns: list[str]
    group_of: dict[str, str] = field(default_factory=dict)  # preprocessed column -> group

    def z(self, X: pd.DataFrame) -> np.ndarray:
        return self.pre.transform(X[self.raw_columns])

    def contributions(self, X: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(self.z(X) * self.coef, columns=self.columns, index=X.index)

    def logit(self, X: pd.DataFrame) -> np.ndarray:
        return self.intercept + self.z(X) @ self.coef

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-self.logit(X)))

    def group_contributions(self, X: pd.DataFrame) -> pd.DataFrame:
        c = self.contributions(X)
        return pd.DataFrame({g: c[[k for k in self.columns if self.group_of[k] == g]].sum(1) for g in GROUPS})

    def coef_series(self) -> pd.Series:
        return pd.Series(self.coef, index=self.columns)


def fit_pipeline(X: pd.DataFrame, cohort: pd.DataFrame, rows: np.ndarray, groups: dict[str, str],
                 seed: int = 0, C: float | None = None) -> Fitted:
    """Fit BASE_PRE + ridge on the verified scans among `rows` (C by inner CV unless given)."""
    y = cohort[f"label_{H}"].to_numpy()
    tr = np.asarray(rows)[~np.isnan(y[rows])]
    pre = clone(BASE_PRE).fit(X.iloc[tr])
    Z = pre.transform(X.iloc[tr])
    if C is None:
        model, C = fit_ridge("verified", Z, cohort.iloc[tr].reset_index(drop=True), H, seed=seed)
    else:
        from sklearn.linear_model import LogisticRegression
        model = LogisticRegression(penalty="l2", C=C, max_iter=5000, random_state=seed).fit(Z, y[tr].astype(int))
    cols = [str(c) for c in pre.get_feature_names_out()]
    return Fitted(pre, model.coef_[0].copy(), float(model.intercept_[0]), float(C), cols, list(X.columns),
                  {c: groups[source_feature(c)] for c in cols})


def bootstrap_fits(X, cohort, rows, groups, n_boot=200, seed=0) -> list[Fitted]:
    """Patient-cluster bootstrap of the whole training pipeline (imputation, scaling, choice of C, fit)."""
    rng = np.random.default_rng(seed)
    rows = np.asarray(rows)
    pid = cohort.patient_id.to_numpy()[rows]
    by_pat = {p: rows[pid == p] for p in np.unique(pid)}
    pats = np.array(list(by_pat))
    y = cohort[f"label_{H}"].to_numpy()
    out = []
    while len(out) < n_boot:
        idx = np.concatenate([by_pat[p] for p in rng.choice(pats, len(pats))])
        if len(np.unique(y[idx][~np.isnan(y[idx])])) < 2:
            continue
        out.append(fit_pipeline(X, cohort, idx, groups, seed=seed))
    return out


# ---------------------------------------------------------------- out-of-distribution ranges
def continuous_columns(X: pd.DataFrame) -> list[str]:
    return [c for c in X.columns if X[c].dropna().nunique() > 2]


def ood_ranges(X: pd.DataFrame, rows) -> pd.DataFrame:
    """Training 1st / 99th percentile of each continuous raw feature (non-missing values)."""
    Xt = X.iloc[np.asarray(rows)]
    cols = continuous_columns(Xt)
    return pd.DataFrame({"p01": Xt[cols].quantile(0.01), "p99": Xt[cols].quantile(0.99)})


def ood_flags(X: pd.DataFrame, cohort: pd.DataFrame, ranges: pd.DataFrame) -> list[list[str]]:
    """Reasons per scan: unknown molecular marker, or a continuous input outside the training 1st-99th percentile."""
    out = []
    for i in range(len(X)):
        r = []
        if cohort["idh"].iat[i] == "unknown":
            r.append("IDH status unknown")
        if cohort["mgmt"].iat[i] == "unknown":
            r.append("MGMT status unknown")
        for c, (lo, hi) in ranges.iterrows():
            v = X[c].iat[i]
            if pd.notna(v) and (v < lo or v > hi):
                r.append(f"{c} = {v:g} outside training 1-99% [{lo:g}, {hi:g}]")
        out.append(r)
    return out


# ---------------------------------------------------------------- locked artifact
@dataclass
class Locked:
    population: str
    model: Fitted
    boot: list[Fitted]
    conformal_model: Fitted
    conformal_q: dict[float, float]
    ranges: pd.DataFrame
    n_train_scans: int
    n_train_verified: int
    n_patients: int

    def predict(self, X):
        p = self.model.predict(X)
        B = np.array([b.predict(X) for b in self.boot])
        return p, np.percentile(B, 2.5, 0), np.percentile(B, 97.5, 0)
