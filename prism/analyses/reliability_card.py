"""Reliability card (EXPLORATORY, post hoc): the lookup table of measured results by situation, the pathway
agreement summary, card-augmented report records, and the new faithfulness rule evaluated on the existing reports.

Definitions, tier rule and agreement rule: prism/audit/reliability.py (module docstring) and
docs/results/RELIABILITY_CARD.md. Nothing is fitted except re-creating scores that earlier analyses computed but did
not save (MU I_pure and B1+I_pure out-of-fold, exactly as scripts/exploratory_pure_imaging_detection.py; LUMIERE
image-only locked, exactly as scripts/exploratory_pure_imaging_forward_lumiere.py). Every re-created score is checked
against the published AUC before it is used.

Scores used (pathway -> arm), grade 4 throughout:
  mu             timeline B1, images I_pure, both B1+I_pure   detection OOF, 5 x 5 CV, all scans, primary negatives
  lumiere        timeline Tbase, images T_img, both T          locked MU fit (transportable designs; no RT dates)
  ucsf_locked    timeline A-Tbase, images A-Ipure, both A-T    locked MU fit, scan 2, pos_s2_pm30 vs primary negatives
  ucsf_internal  timeline B-Tl, images Ipure, both B-Tl+Ipure  UCSF-trained 5 x 5 CV, same set

    PYTHONPATH=. .venv/bin/python -m prism.analyses.reliability_card [--steps scores table records evaluate]
    -> outputs/results/analyses/reliability_card/  (patient-level files stay there; git-ignored)
"""

from __future__ import annotations

import argparse
import json
import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

from prism.audit import reliability as R
from prism.config import MEASUREMENTS, OUTPUTS, RESULTS

OUT = RESULTS / "analyses" / "reliability_card"
ARMS = {"mu": ("B1", "I_pure", "B1+I_pure"), "lumiere": ("Tbase", "T_img", "T"),
        "ucsf_locked": ("A-Tbase@grade4", "A-Ipure@grade4", "A-T@grade4"),
        "ucsf_internal": ("B-Tl", "Ipure", "B-Tl+Ipure")}
# published AUCs the re-created / re-read scores must reproduce (DETECTION_TASK.md, STORY.md, UCSF_RESULTS.md)
EXPECTED = {("mu", "timeline"): 0.845, ("mu", "images"): 0.712, ("lumiere", "timeline"): 0.689,
            ("lumiere", "images"): 0.655, ("lumiere", "both"): 0.773, ("ucsf_locked", "timeline"): 0.561,
            ("ucsf_locked", "images"): 0.726, ("ucsf_locked", "both"): 0.856, ("ucsf_internal", "timeline"): 0.669,
            ("ucsf_internal", "images"): 0.863, ("ucsf_internal", "both"): 0.871}
UCSF_SET = "grade4|scan2|pos_s2_pm30"


# ---------------------------------------------------------------- MU
@lru_cache(maxsize=1)
def mu_designs():
    """(detection frame, {B1, I_pure, B1+I_pure} designs), as scripts/exploratory_pure_imaging_detection.py."""
    from prism.analyses import detection as D
    from prism.analyses.triage_feasibility import _features_one
    from prism.features.tabular import measurement_groups
    index, _, _, meas = D._base()
    d, X, _, _, F = D.context("grade4", "primary")
    mg = measurement_groups(d)
    by_pat = {p: g.sort_values("mri_day") for p, g in meas.groupby("patient_id")}
    nad = []
    for pid, day in zip(d.patient_id, d.mri_day):
        g = by_pat[pid]
        f = _features_one(g[g.mri_day <= day], day, -np.inf)
        nad.append({"nadir_all_et": f["traj_logratio_nadir_et"], "nadir_all_lesion": f["traj_logratio_nadir_lesion"]})
    nad = pd.DataFrame(nad, index=d.index)
    prevr = F[[c for c in F.columns if c.startswith("logratio_prev_")]]
    ipure = pd.concat([mg["volumes"], mg["morphology"], prevr, nad], axis=1)
    return d, {"B1": X["B1"], "I_pure": ipure, "B1+I_pure": pd.concat([X["B1"], ipure], axis=1)}


def mu_scores() -> pd.DataFrame:
    from prism.analyses import detection as D
    from prism.experiments import c3_radiomics as c3
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    d, A = mu_designs()
    out = d[["scan_id", "patient_id"]].copy()
    for a, Xa in A.items():
        for r in range(5):
            f = D.fold_ids(d, r)
            v = np.full(len(d), np.nan)
            for k in range(5):
                tr, te = np.where(f != k)[0], np.where(f == k)[0]
                v[te] = c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr, te, seed=r)
            out[f"{a}#r{r}"] = v
    pub = pd.read_csv(D.OUT / "oof_grade4_primary.csv.gz").set_index("scan_id").reindex(out.scan_id)
    dev = max(float(np.nanmax(np.abs(pub[f"B1#r{r}"].to_numpy() - out[f"B1#r{r}"].to_numpy()))) for r in range(5))
    assert dev < 1e-9, f"B1 out-of-fold differs from the published detection OOF by {dev:.2e}"
    return out


def mu_frame(scores: pd.DataFrame) -> pd.DataFrame:
    """One row per MU detection scan: label (NaN = not in the evaluation set), cell, scores per repeat."""
    from prism.analyses import detection as D
    index, *_ = D._base()
    d, _ = mu_designs()
    m = pd.read_csv(MEASUREMENTS).set_index("scan_id")
    st = pd.to_numeric(index.clinical_number_of_days_from_diagnosis_to_radiation_therapy_start_date, errors="coerce")
    rt_known = index.assign(st=st.to_numpy()).groupby("patient_id").st.apply(lambda s: s.notna().any())
    phase = np.where(rt_known.reindex(d.patient_id).fillna(False).to_numpy(), [R.phase_cell(p) for p in d.phase],
                     "unknown")
    et = m.et_cc.reindex(d.scan_id).to_numpy(float)
    prev = m.et_cc.reindex(d.prev_scan_id.replace("", np.nan)).to_numpy(float)
    f = pd.DataFrame({"cohort": "mu", "scan_id": d.scan_id, "patient_id": d.patient_id, "label": d.label_120,
                      "phase": phase, "enhancement": [R.enhancement_state(a, b) for a, b in zip(et, prev)]})
    s = scores.set_index("scan_id").reindex(d.scan_id)
    for p, a in zip(R.PATHWAYS, ARMS["mu"]):
        for r in range(5):
            f[f"{p}#r{r}"] = s[f"{a}#r{r}"].to_numpy()
    return f


def mu_ood() -> pd.DataFrame:
    """Out-of-range reasons per scan and repeat for the card's inputs (B1 + I_pure), ranges from the training rows of
    the scan's outer fold (prism.audit.model.ood_ranges / ood_flags, unchanged)."""
    from prism.analyses import detection as D
    from prism.audit.model import ood_flags, ood_ranges
    d, A = mu_designs()
    Xc = A["B1+I_pure"]
    lab = d.label_120.notna().to_numpy()
    rows = []
    for r in range(5):
        f = D.fold_ids(d, r)
        for k in range(5):
            tr, te = np.where((f != k) & lab)[0], np.where(f == k)[0]
            reasons = ood_flags(Xc.iloc[te], d.iloc[te], ood_ranges(Xc, tr))
            rows += [{"scan_id": d.scan_id.iat[i], "repeat": r, "fold": k, "ood_reasons": "; ".join(x)}
                     for i, x in zip(te, reasons)]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- LUMIERE
def lumiere_frame() -> pd.DataFrame:
    from sklearn.base import clone
    from prism.analyses import detection as D
    from prism.experiments import c3_radiomics as c3
    L, LX, _ = D.lumiere_detection()
    dm, X, *_ = D.context("grade4", "primary")
    img = [c for c in X["T"].columns if c not in D.T_BASE + ["has_prev", "log_days_from_prev"]]
    tr = np.where(dm.label_120.notna())[0]
    f = pd.DataFrame({"cohort": "lumiere", "scan_id": L.scan_id, "patient_id": L.patient_id, "label": L.label_det,
                      "phase": "unknown",
                      "enhancement": [R.enhancement_state(a, b if p else np.nan)
                                      for a, b, p in zip(L.et, L.prev_et, L.prev_scan_id.ne(""))]})
    for p, (arm, cols) in zip(R.PATHWAYS, (("Tbase", D.T_BASE), ("T_img", img), ("T", list(X["T"].columns)))):
        bp = clone(c3.BASE_PRE).fit(X["T"][cols].iloc[tr])
        mdl = c3._ridge(bp.transform(X["T"][cols].iloc[tr]), dm, tr, 0)
        f[f"{p}#r0"] = mdl.predict_proba(bp.transform(LX[cols]))[:, 1]
    pub = pd.read_csv(D.OUT / "lumiere_predictions.csv").set_index("scan_id").reindex(f.scan_id)
    for p, a in (("timeline", "Tbase"), ("both", "T")):
        dev = float(np.abs(pub[f"{a}@grade4"].to_numpy() - f[f"{p}#r0"].to_numpy()).max())
        assert dev < 1e-9, f"LUMIERE {a} differs from the published locked predictions by {dev:.2e}"
    return f


# ---------------------------------------------------------------- UCSF
def ucsf_frames() -> list[pd.DataFrame]:
    U = RESULTS / "analyses" / "ucsf"
    o = pd.read_csv(U / "internal" / "oof.csv.gz")
    o = o[o.set == UCSF_SET].reset_index(drop=True)
    s = pd.read_csv(OUTPUTS / "data" / "ucsf" / "scans.csv", dtype={"subject_id": str}).set_index("scan_id")
    im = pd.read_csv(OUTPUTS / "data" / "ucsf" / "imaging_features.csv").set_index("scan_id")
    e2 = im.et_cc.reindex(o.scan_id).to_numpy(float)
    e1 = im.et_cc.reindex(o.scan_id.str.replace("_time2", "_time1", regex=False)).to_numpy(float)
    assert o.scan_id.str.endswith("_time2").all() and s.has_prev.reindex(o.scan_id).astype(bool).all()
    base = pd.DataFrame({"scan_id": o.scan_id, "patient_id": s.subject_id.reindex(o.scan_id).to_numpy(),
                         "label": o.label.to_numpy(float),
                         "phase": [R.phase_cell(p) for p in s.rt_phase.reindex(o.scan_id)],
                         "enhancement": [R.enhancement_state(a, b) for a, b in zip(e2, e1)]})
    loc = pd.read_csv(U / "locked" / "scores.csv").set_index("scan_id").reindex(o.scan_id)
    fl = base.assign(cohort="ucsf_locked")
    fi = base.assign(cohort="ucsf_internal")
    for p, a in zip(R.PATHWAYS, ARMS["ucsf_locked"]):
        fl[f"{p}#r0"] = loc[a].to_numpy()
    for p, a in zip(R.PATHWAYS, ARMS["ucsf_internal"]):
        for r in range(5):
            fi[f"{p}#r{r}"] = o[f"{a}#r{r}"].to_numpy()
    return [fl, fi]


# ---------------------------------------------------------------- table
def score_matrix(f: pd.DataFrame, p: str) -> np.ndarray:
    return f[sorted(c for c in f.columns if c.startswith(p + "#r"))].to_numpy(float).T


def medians(f: pd.DataFrame) -> dict:
    """Per pathway, per repeat: median score over the cohort's evaluation set (no labels used)."""
    e = f[f.label.notna()]
    return {p: np.median(score_matrix(e, p), axis=1) for p in R.PATHWAYS}


def cohort_table(f: pd.DataFrame, n_boot=R.N_BOOT) -> tuple[list[dict], list[dict]]:
    """Lookup rows (every cell present + 'overall') and agreement rows for one cohort."""
    e = f[f.label.notna()].reset_index(drop=True)
    y, g = e.label.to_numpy(int), e.patient_id.to_numpy()
    S = {p: score_matrix(e, p) for p in R.PATHWAYS}
    cells = (e.phase + "|" + e.enhancement).to_numpy()
    rows, masks = [], {}
    for c in sorted(set(cells)) + ["overall"]:
        m = np.ones(len(e), bool) if c == "overall" else cells == c
        npos, nneg = int(y[m].sum()), int((y[m] == 0).sum())
        t = R.tier(npos, nneg)
        rows.append({"cohort": f.cohort.iat[0], "cell": c, "phase": c.split("|")[0],
                     "enhancement": c.split("|")[-1], "n_scans": int(m.sum()), "n_pos": npos, "n_neg": nneg,
                     "n_patients": int(len(np.unique(g[m]))), "tier": t})
        if t == "tested":
            masks[c] = m
    med = medians(f)
    side = {p: S[p] > med[p][:, None] for p in ("timeline", "images")}
    agree = side["timeline"] == side["images"]
    amasks = {"agree": agree, "disagree": ~agree}
    res = R.bootstrap_auc(y, S, g, {**masks, **amasks}, n_boot)
    for r in rows:
        for p in R.PATHWAYS:
            v = res.get((p, r["cell"]), (np.nan, np.nan, np.nan))
            r.update({f"{p}_auc": v[0], f"{p}_auc_lo": v[1], f"{p}_auc_hi": v[2]})
    arows = []
    for sn, M in amasks.items():
        npos = [int(y[m].sum()) for m in M]
        nneg = [int((y[m] == 0).sum()) for m in M]
        t = R.tier(min(npos), min(nneg))
        r = {"cohort": f.cohort.iat[0], "subset": sn, "n_scans": int(round(np.mean([m.sum() for m in M]))),
             "n_pos": int(round(np.mean(npos))), "n_neg": int(round(np.mean(nneg))),
             "n_pos_min": min(npos), "n_neg_min": min(nneg), "n_patients": int(len(np.unique(g[M[0]]))), "tier": t}
        for p in R.PATHWAYS:
            v = res[(p, sn)] if t == "tested" else (np.nan, np.nan, np.nan)
            r.update({f"{p}_auc": v[0], f"{p}_auc_lo": v[1], f"{p}_auc_hi": v[2]})
        # descriptive: progression rate when both point up / both down / they split
        if sn == "agree":
            up = side["timeline"] & side["images"]
            r["pct_progression_both_above"] = float(np.mean([y[m].mean() for m in up]))
            r["pct_progression_both_below"] = float(np.mean([y[m].mean() for m in agree & ~up]))
        else:
            ti = side["timeline"] & ~side["images"]
            r["pct_progression_timeline_above_images_below"] = float(np.mean([y[m].mean() for m in ti]))
            r["pct_progression_images_above_timeline_below"] = float(np.mean([y[m].mean() for m in ~agree & ~ti]))
        arows.append(r)
    return rows, arows


def frames() -> list[pd.DataFrame]:
    p = OUT / "mu_scores.csv.gz"
    if not p.exists():
        OUT.mkdir(parents=True, exist_ok=True)
        mu_scores().to_csv(p, index=False)
    return [mu_frame(pd.read_csv(p)), lumiere_frame(), *ucsf_frames()]


def table_step(n_boot=R.N_BOOT):
    rows, arows, checks = [], [], []
    for f in frames():
        k = f.cohort.iat[0]
        e = f[f.label.notna()]
        for p in R.PATHWAYS:
            a = R.mean_auc(e.label.to_numpy(int), score_matrix(e, p), np.ones(len(e), bool))
            exp = EXPECTED.get((k, p))
            checks.append({"cohort": k, "pathway": p, "auc_overall": a, "published": exp,
                           "ok": exp is None or abs(a - exp) < 0.0051})
        r, ar = cohort_table(f, n_boot)
        rows += r
        arows += ar
        f.to_csv(OUT / f"scans_{k}.csv.gz", index=False)  # patient-level, git-ignored
    ch = pd.DataFrame(checks)
    ch.to_csv(OUT / "checks.csv", index=False)
    assert ch.ok.all(), ch[~ch.ok]
    pd.DataFrame(rows).to_csv(OUT / "lookup.csv", index=False)
    pd.DataFrame(arows).to_csv(OUT / "agreement.csv", index=False)
    mu_ood().to_csv(OUT / "mu_ood.csv.gz", index=False)
    print(pd.DataFrame(rows)[["cohort", "cell", "n_pos", "n_neg", "tier", "timeline_auc", "images_auc", "both_auc"]]
          .to_string(), flush=True)
    print(pd.DataFrame(arows).to_string(), flush=True)


def load_table() -> tuple[list[dict], list[dict]]:
    clean = lambda df: [{k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in r.items()}
                        for r in df.to_dict("records")]
    return clean(pd.read_csv(OUT / "lookup.csv")), clean(pd.read_csv(OUT / "agreement.csv"))


# ---------------------------------------------------------------- records
RECORD_SETS = {"report_agent_eval": (RESULTS / "analyses" / "report_agent" / "records" / "eval", 0),
               "report_usefulness_eval": (RESULTS / "analyses" / "report_usefulness" / "records" / "eval", 1)}


def card_for(scan_id: str, repeat: int, mu: pd.DataFrame, ood: pd.DataFrame, table, atable) -> dict:
    row = mu.set_index("scan_id").loc[scan_id]
    e = mu[mu.label.notna()]
    med = {p: float(np.median(e[f"{p}#r{repeat}"])) for p in ("timeline", "images")}
    reasons = ood.set_index(["scan_id", "repeat"]).ood_reasons.loc[(scan_id, repeat)]
    reasons = [] if not isinstance(reasons, str) or not reasons else reasons.split("; ")
    card = R.build_card(row.phase, row.enhancement, table, "mu",
                        {"timeline": row[f"timeline#r{repeat}"], "images": row[f"images#r{repeat}"]}, med, reasons,
                        atable)
    card["source"] = (f"detection out-of-fold scores, CV repeat {repeat} (patient not in training); lookup "
                      "outputs/results/analyses/reliability_card/lookup.csv")
    return card


def attach_cards(recs: dict, repeat: int) -> dict:
    """Card-augmented copies of report records (the record gains a 'reliability_card' block; nothing else changes)."""
    table, atable = load_table()
    mu = pd.read_csv(OUT / "scans_mu.csv.gz")
    ood = pd.read_csv(OUT / "mu_ood.csv.gz")
    return {k: {**r, "reliability_card": card_for(r["scan_id"], repeat, mu, ood, table, atable)} for k, r in recs.items()}


def records_step():
    for name, (src, rep) in RECORD_SETS.items():
        recs = {p.stem: json.loads(p.read_text()) for p in sorted(src.glob("*.json"))}
        out = OUT / "records" / name
        out.mkdir(parents=True, exist_ok=True)
        for k, r in attach_cards(recs, rep).items():
            (out / f"{k}.json").write_text(json.dumps(r, indent=1, default=float))
        print(f"{name}: {len(recs)} card-augmented records (repeat {rep})", flush=True)


# ---------------------------------------------------------------- the new checker rule on the existing reports
def evaluate_step():
    """Existing reports (no LLM run): the unchanged check must reproduce the published pass counts; the card rule is
    evaluated separately against card-augmented facts. The reports predate the card, so they were never asked to
    state it."""
    from prism.analyses import report_agent as RA
    from prism.analyses import report_usefulness as RU
    from prism.report import checker
    from prism.report.facts import facts
    from prism.report.facts_card import card_facts
    from prism.report.facts_v2 import facts_v2
    rows = []
    for name, loader, fx, claims_of in (
            ("report_agent_eval", lambda: RA.load_outputs("eval"), facts, RA.claims_of),
            ("report_usefulness_eval", lambda: RU.load_outputs("eval"), facts_v2,
             lambda arm, t: checker.parse_structured(t))):
        recs = {p.stem: json.loads(p.read_text()) for p in sorted((OUT / "records" / name).glob("*.json"))}
        for key, o in loader().items():
            _, arm, sid = key.split("|")
            r = recs[sid]
            F = fx(r)
            cl = claims_of(arm, o["text"])
            grounded = name == "report_usefulness_eval" or RA.ARMS[arm][1] == "grounded"
            ctx = None if grounded else {"prompt": RA.prompts.original(F, r["scan_id"])[1]["_prompt_text"]}
            old = checker.check(cl, F, cited=grounded, context=ctx)
            Fc = {**F, **card_facts(r)}
            new = checker.check(cl, Fc, cited=grounded, context=ctx, card=True)
            cc = new.get("card", {})
            rows.append({"set": name, "arm": arm, "scan_id": sid, "card_tier": Fc["card.tier"],
                         "pass_unchanged": old["pass"], "pass_with_card_rule": new["pass"],
                         "card_pass": cc.get("card_pass"), "card_tier_required": cc.get("tier_required"),
                         "card_tier_mentioned": cc.get("tier_mentioned"),
                         "n_performance_claims": cc.get("n_performance_claims"),
                         "n_unsupported_performance_numbers": len(cc.get("unsupported_performance", [])),
                         "n_overclaims": len(cc.get("overclaims", []))})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "checker_on_existing_reports.csv", index=False)
    sm = df.groupby(["set", "arm"]).agg(n=("scan_id", "size"), pass_unchanged=("pass_unchanged", "sum"),
                                        card_tier_required=("card_tier_required", "sum"),
                                        card_tier_mentioned=("card_tier_mentioned", "sum"),
                                        reports_with_performance_claim=("n_performance_claims", lambda v: int((v > 0).sum())),
                                        reports_unsupported_performance=("n_unsupported_performance_numbers",
                                                                         lambda v: int((v > 0).sum())),
                                        reports_overclaim=("n_overclaims", lambda v: int((v > 0).sum())),
                                        card_pass=("card_pass", "sum"),
                                        pass_with_card_rule=("pass_with_card_rule", "sum")).reset_index()
    tiers = df.drop_duplicates(["set", "scan_id"]).groupby(["set", "card_tier"]).size().rename("n_scans").reset_index()
    sm.to_csv(OUT / "checker_on_existing_reports_summary.csv", index=False)
    tiers.to_csv(OUT / "card_tiers_of_report_scans.csv", index=False)
    print(sm.to_string(), "\n", tiers.to_string(), flush=True)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", nargs="+", default=["table", "records", "evaluate"],
                    choices=["table", "records", "evaluate"])
    ap.add_argument("--n-boot", type=int, default=R.N_BOOT)
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    if "table" in a.steps:
        table_step(a.n_boot)
    if "records" in a.steps:
        records_step()
    if "evaluate" in a.steps:
        evaluate_step()


if __name__ == "__main__":
    main()
