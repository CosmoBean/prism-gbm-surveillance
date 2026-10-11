"""Do frozen deep (SwinUNETR) features add to the clinical + timing + treatment baseline? C3 protocol, deep features.

Families (all ridge on verified 120-d labels, same 5x5 patient-grouped folds, every step fitted in-fold; c3.fit_predict):
  D1   pretrained encoders brats21 | bsf  x  pooling lesion | compartments  x  selection top10 | pca10 | pca30 | l1
       x  integration stack | concat  (32 configs; nested choice over all 32 = the honest estimate)
  D0   random-weight SwinUNETR, same 16 pooling/selection/integration configs (pretraining is credited only if D1 > D0)
  D1b  legacy radiomics + deep features in one stacked score (16 configs, stack only)
  DS   pooling over regions that exist in both cohorts (et, snfh, et|snfh; no cavity/necrosis): 16 configs; its nested
       choice made on all MU is refitted on all MU and applied once to LUMIERE (locked) on top of the shared baseline
       (clinical+timing[+volumes], no treatment); controls: the same config with the random encoder, and image-only scores
  DV   baseline + volumes, +- nested D1 (does deep add beyond lesion volumes?)
Deep features: prism.features.deep (outputs/features/deep_*.parquet), swinViT stages 0-3 (720 per region; the
brats21 768-d bottleneck is ~constant across scans and is dropped for all encoders). Cohort, labels, folds and baseline features are
read from the current code at run time.

    uv run --frozen --no-sync python -m prism.analyses.deep_features [--population grade4 all_glioma --workers 24]
    # -> outputs/results/analyses/deep/<population>/, outputs/results/analyses/deep/lumiere/
"""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits

from prism.config import REPO, RESULTS
from prism.data import lumiere
from prism.experiments import c3_radiomics as c3
from prism.features.deep import load_features
from prism.features.tabular import SHARED, groups as feature_groups, shared_lumiere, shared_mu
from prism.models.metrics import cluster_bootstrap, evaluate_repeated, point_metrics

H = c3.H
OUT = RESULTS / "analyses" / "deep"
POOLS = {"lesion": ("lesion",), "compartments": ("lesion", "et", "netc", "snfh", "rim"), "shared": ("et", "snfh", "etsnfh")}
SELECTIONS = ("top10", "pca10", "pca30", "l1")
PRETRAINED = ("brats21", "bsf")
STAGES = ("s0", "s1", "s2", "s3")  # 48+96+192+384 = 720 per region; the 768-d bottleneck (s4) of brats21 is ~constant


# c3.selector has no pca30; extend it in place so c3.fit_predict picks it up (no copy of the stacking code).
_c3_selector = c3.selector


def selector(name):
    if name == "pca30":
        return _c3_selector("pca10").set_params(sel__n_components=30)
    return _c3_selector(name)


c3.selector = selector


def _cfgs(variants, integrations=("stack", "concat")):
    return [(v, "none", s, i, "ridge") for v, s, i in itertools.product(variants, SELECTIONS, integrations)]


FAMILIES = {
    "D1": _cfgs([f"{e}:{p}" for e in PRETRAINED for p in ("lesion", "compartments")]),
    "D0": _cfgs([f"random:{p}" for p in ("lesion", "compartments")]),
    "D1b": _cfgs([f"rad+{e}:{p}" for e in PRETRAINED for p in ("lesion", "compartments")], ("stack",)),
    "DS": _cfgs([f"{e}:shared" for e in PRETRAINED]),
}
BASELINE = (None, "none", "none", "none", "ridge")
key = lambda c: "|".join(map(str, c))


# ---------------------------------------------------------------- data
def deep_block(encoder, pool, scan_ids, cohort="mu"):
    f = load_features(encoder, scan_ids, cohort)
    return f[[c for c in f.columns if c.split("_")[0] in POOLS[pool] and c.split("_")[1] in STAGES]]


@lru_cache(maxsize=4)
def load(population, with_volumes=False):
    cohort, folds, base, rad, er = c3.load(population)
    deep = {}
    for e, p in itertools.product(PRETRAINED + ("random",), POOLS):
        d = deep_block(e, p, cohort.scan_id)
        d.index = cohort.index
        deep[f"{e}:{p}"] = d
        if e != "random" and p != "shared":
            deep[f"rad+{e}:{p}"] = pd.concat([rad["legacy"], d], axis=1)
    if with_volumes:
        base = pd.concat([base, feature_groups(cohort, legacy_radiomics=False)["volumes"]], axis=1)
    return cohort, folds, base, deep, er


def _init():
    warnings.filterwarnings("ignore")
    threadpool_limits(1)


# ---------------------------------------------------------------- CV, nested CV (c3 helpers)
def run_config(job):
    population, vol, cfg = job
    cohort, folds, base, deep, er = load(population, vol)
    oof = np.zeros((folds.repeat.nunique(), len(cohort)))
    for r in range(oof.shape[0]):
        f = c3._fold_ids(cohort, folds, r)
        for k in np.unique(f):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            oof[r, te] = c3.fit_predict(cfg, cohort, base, deep, er, tr, te, seed=r)
    return (vol, cfg), oof


def run_nested(job):
    population, vol, family, r, k = job
    cohort, folds, base, deep, er = load(population, vol)
    f = c3._fold_ids(cohort, folds, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    scores = {c: c3.inner_auc(c, cohort, base, deep, er, tr) for c in FAMILIES[family]}
    best = max(scores, key=scores.get)
    return vol, family, r, te, c3.fit_predict(best, cohort, base, deep, er, tr, te, seed=r), key(best)


def deep_score(cfg, cohort, X, tr, te):
    """Image-only stacked score (as inside c3.fit_predict) for diagnostics."""
    y = cohort[f"label_{H}"].to_numpy()
    tr = tr[~np.isnan(y[tr])]
    sp = clone(selector(cfg[2])).fit(X[tr], y[tr].astype(int))
    return LogisticRegression(C=0.1, max_iter=5000).fit(sp.transform(X[tr]), y[tr].astype(int)).decision_function(sp.transform(X[te]))


def run_score(job):
    population, cfg = job
    cohort, folds, _, deep, _ = load(population)
    X = deep[cfg[0]].to_numpy(float)
    oof = np.zeros((folds.repeat.nunique(), len(cohort)))
    for r in range(oof.shape[0]):
        f = c3._fold_ids(cohort, folds, r)
        for k in np.unique(f):
            oof[r, f == k] = deep_score(cfg, cohort, X, np.where(f != k)[0], np.where(f == k)[0])
    return cfg, oof


def evaluate(population, workers, n_boot):
    out = OUT / population
    out.mkdir(parents=True, exist_ok=True)
    cohort, folds, *_ = load(population)
    n_rep = folds.repeat.nunique()
    single = [(False, c) for c in [BASELINE] + sum(FAMILIES.values(), [])] + [(True, BASELINE)]
    nested_jobs = [(population, False, fam, r, k) for fam in FAMILIES for r in range(n_rep) for k in range(5)]
    nested_jobs += [(population, True, "D1", r, k) for r in range(n_rep) for k in range(5)]
    with ProcessPoolExecutor(workers, initializer=_init) as ex:
        res = {}
        for (vol, c), o in ex.map(run_config, [(population, v, c) for v, c in single]):
            res[("base+vol|" if vol else "") + key(c)] = o
        nested = list(ex.map(run_nested, nested_jobs))
    choices = []
    for vol, fam, r, te, p, best in nested:
        name = f"{'base+vol|' if vol else ''}NESTED_{fam}"
        res.setdefault(name, np.zeros((n_rep, len(cohort))))[r, te] = p
        choices.append({"arm": name, "repeat": r, "chosen": best})
    choices = pd.DataFrame(choices)
    choices.to_csv(out / "nested_choices.csv", index=False)

    ref, ref_vol = key(BASELINE), "base+vol|" + key(BASELINE)
    preds = {k: o.mean(0) for k, o in res.items()}
    # headline: mean over repeats of the per-repeat IPCW AUC, paired patient-cluster bootstrap (prism.models.metrics)
    main_ = evaluate_repeated(cohort, {k: o for k, o in res.items() if not k.startswith("base+vol|")}, H, ref, n_boot)
    vol = evaluate_repeated(cohort, {k: res[k] for k in (ref_vol, "base+vol|NESTED_D1")}, H, ref_vol, n_boot)
    vol_vs_base = evaluate_repeated(cohort, {k: res[k] for k in (ref, ref_vol)}, H, ref, n_boot).loc[[ref_vol]]
    rows = []
    for ev, r_ref in ((main_, ref), (vol_vs_base, ref), (vol.drop(index=ref_vol), ref_vol)):
        ev = ev.rename(columns={f"d_auc_ipcw_vs_{r_ref}": "d_auc_ipcw"})
        rows += [{"arm": k, "reference": r_ref, **row.dropna().to_dict()} for k, row in ev.iterrows()]
    table = pd.DataFrame(rows)
    table.insert(1, "family", table.arm.map(lambda a: next((f for f, cs in FAMILIES.items() if a in map(key, cs)),
                                                           "DV" if a.startswith("base+vol|") else a.split("NESTED_")[-1] if "NESTED" in a else "baseline")))
    table.sort_values("auc_ipcw", ascending=False).to_csv(out / "results.csv", index=False)
    pd.DataFrame(preds).assign(scan_id=cohort.scan_id).to_csv(out / "oof.csv", index=False)
    pd.concat([pd.DataFrame(o.T, columns=[f"{k}#r{r}" for r in range(len(o))]) for k, o in res.items()], axis=1
              ).assign(scan_id=cohort.scan_id).to_csv(out / "oof_repeats.csv.gz", index=False)

    # Diagnostics: image-only stacked score of the most-chosen nested config per family vs volume and baseline.
    vols = feature_groups(cohort, legacy_radiomics=False)["volumes"]
    modal = {fam: choices[choices.arm == f"NESTED_{fam}"].chosen.mode().iloc[0] for fam in FAMILIES}
    cfgs = {fam: next(c for c in FAMILIES[fam] if key(c) == m) for fam, m in modal.items()}
    with ProcessPoolExecutor(min(workers, len(cfgs)), initializer=_init) as ex:
        scores = dict(ex.map(run_score, [(population, c) for c in cfgs.values()]))
    diag = []
    base_logit = np.log(preds[ref] / (1 - preds[ref]))
    for fam, c in cfgs.items():
        s = scores[c].mean(0)
        rep = [point_metrics(cohort, 1 / (1 + np.exp(-scores[c][r])), H)["auc_ipcw"] for r in range(n_rep)]
        diag.append({"family": fam, "modal_config": key(c), "n_chosen": int((choices.chosen == key(c)).sum()),
                     "image_only_auc_repeat_mean": float(np.mean(rep)),
                     "r_log_lesion_cc": float(np.corrcoef(s, vols.log_lesion_cc)[0, 1]),
                     "r_log_tumor_cc": float(np.corrcoef(s, vols.log_tumor_cc)[0, 1]),
                     "r_baseline_logit": float(np.corrcoef(s, base_logit)[0, 1])})
    pd.DataFrame(diag).to_csv(out / "diagnostics.csv", index=False)
    return table, pd.DataFrame(diag)


# ---------------------------------------------------------------- locked LUMIERE test
LUMIERE_BASES = {"clinical+timing": SHARED["clinical"] + SHARED["timing"],
                 "clinical+timing+volumes": SHARED["clinical"] + SHARED["timing"] + SHARED["volumes"]}
COLS = ["scan_id", "patient_id", f"label_{H}", f"naive_label_{H}", "event", "time_to_event", "status_known_indefinitely"]


def _inner(job):
    cfg, mc, base, deep, tr = job
    return cfg, c3.inner_auc(cfg, mc, base, deep, {}, tr)


def locked_lumiere(population, base_name, workers, n_boot):
    """Nested choice among DS configs by inner CV on all MU, refit on all MU, applied unchanged to LUMIERE."""
    mc = c3.load(population)[0]
    lc = lumiere.load_cohort()
    cols = LUMIERE_BASES[base_name]
    MX, LX = shared_mu(mc)[cols], shared_lumiere(lc)[cols]
    variants = sorted({c[0] for c in FAMILIES["DS"]}) + ["random:shared"]
    md = {v: deep_block(*v.split(":"), mc.scan_id).set_axis(mc.index) for v in variants}
    ld = {v: deep_block(*v.split(":"), lc.scan_id, "lumiere").set_axis(lc.index) for v in variants}
    tr = np.arange(len(mc))
    with ProcessPoolExecutor(workers, initializer=_init) as ex:
        scores = dict(ex.map(_inner, [(c, mc, MX, md, tr) for c in FAMILIES["DS"]]))
    best = max(scores, key=scores.get)
    # one table: MU rows (training) then LUMIERE rows (test)
    both = pd.concat([mc[COLS], lc[COLS]], ignore_index=True)
    X = pd.concat([MX, LX], ignore_index=True)
    D = {v: pd.concat([md[v], ld[v]], ignore_index=True) for v in variants}
    te = np.arange(len(mc), len(both))
    p_base = c3.fit_predict(BASELINE, both, X, D, {}, tr, te)
    rand = ("random:shared",) + best[1:]  # control: the chosen config with the random-weight encoder
    p_deep = c3.fit_predict(best, both, X, D, {}, tr, te)
    p_rand = c3.fit_predict(rand, both, X, D, {}, tr, te)
    img = {c: 1 / (1 + np.exp(-deep_score(c, both, D[c[0]].to_numpy(float), tr, te))) for c in (best, rand)}
    has = ld[best[0]].notna().any(axis=1).to_numpy()
    lc_ = lc[has].reset_index(drop=True)
    preds = {"baseline": p_base[has], "baseline+deep": p_deep[has], "baseline+random_deep": p_rand[has],
             "deep_only": img[best][has], "random_deep_only": img[rand][has]}
    b = cluster_bootstrap(lc_, preds, H, reference="baseline", n_boot=n_boot).set_index("formulation")
    rows = []
    for k, p in preds.items():
        rows.append({"train": population, "base": base_name, "arm": k, "config": "-" if k == "baseline" else key(rand if "random" in k else best),
                     "inner_auc": scores[best] if k == "baseline+deep" else np.nan, "n_scans": int(has.sum()),
                     "n_patients": lc_.patient_id.nunique(), **point_metrics(lc_, p, H), **b.loc[k].dropna().to_dict()})
    return pd.DataFrame(rows)


def git_state():
    run = lambda *a: subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"), "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": run("status", "--porcelain").splitlines()}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism deep_features", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--population", nargs="+", default=["grade4", "all_glioma"])
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--skip-lumiere", action="store_true")
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "run_info.json").write_text(json.dumps({**git_state(), "argv": vars(a)}, indent=1))
    show = ["arm", "family", "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "d_auc_ipcw", "d_auc_ipcw_lo", "d_auc_ipcw_hi",
            "auc_ipcw_averaged", "cal_slope"]
    for pop in a.population:
        table, diag = evaluate(pop, a.workers, a.n_boot)
        print(f"== {pop}")
        nested = table[table.arm.str.contains("NESTED") | table.family.eq("baseline")]
        print(nested[[c for c in show if c in table]].round(3).to_string(index=False))
        sig = table[table.family.isin(FAMILIES) & (table.d_auc_ipcw_lo > 0)]
        print(f"single configs with ΔAUC CI > 0: {len(sig)} / {table.family.isin(FAMILIES).sum()}")
        print(diag.round(3).to_string(index=False))
    if not a.skip_lumiere:
        res = pd.concat([locked_lumiere(pop, b, a.workers, a.n_boot) for pop in a.population for b in LUMIERE_BASES])
        (OUT / "lumiere").mkdir(exist_ok=True)
        res.to_csv(OUT / "lumiere" / "locked.csv", index=False)
        print("== LUMIERE locked")
        print(res[["train", "base", "arm", "config", "n_scans", "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi",
                   "d_auc_ipcw_vs_baseline", "d_auc_ipcw_lo", "d_auc_ipcw_hi", "oe_ratio", "cal_slope"]]
              .round(3).to_string(index=False))


if __name__ == "__main__":
    main()
