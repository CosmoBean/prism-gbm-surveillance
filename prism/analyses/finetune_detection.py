"""Deep arms of the detection study (stream B): fine-tuned SwinUNETR for "does this MRI show progression?".

ANALYSIS PLAN: docs/results/DETECTION_TASK.md, section "Plan (pre-specified)" (git 2b4c927), snapshotted to
outputs/results/analyses/finetune_detection/PLAN_snapshot.md before the first real-label job. Results of this module
are written up in docs/results/DETECTION_DEEP.md. Network, hyperparameters, cross-fit splits, seeds, runner and
TTA prediction are those of prism/analyses/finetune_deep.py (FINETUNE_DEEP.md), reused by import; that module's
behaviour is unchanged.

Cohort, labels and folds: outputs/data/detection_cohort.csv only (written by stream A; scan_id, patient_id, grade4,
label_det, neg_primary, neg_secondary, intended_use, phase, prev_scan_id, days_from_prev, fold_r0..fold_r4).

Arms (each 5 repeats x 5 outer folds x 4 inner folds = 100 fine-tunes):
    G1      current scan (4 channels)                                       grade 4, detection label
    G4      G1 with training labels permuted within each outer training set (control, seed 1000r+k)
    G3      current scan + 4 subtraction channels (current - previous, both brain-z-scored, SRI24 voxelwise; zeros
            when there is no previous scan) = 8 channels, has-previous flag appended to the pooled features.
            Patch embedding adapted: pretrained weights for the 4 image channels, the same weights x 0.5 for the 4
            difference channels (frozen, like the rest of the patch embedding in finetune_deep).
    G5      G3's network on the forward 120-day label (label_120, grade-4 index scans, the shared folds), exactly the
            grade-4 arm of finetune_deep except for the input; stacked onto C2 and evaluated in the intended use
    G2      siamese current + previous (finetune_deep's +prev head: [f_cur, f_cur - f_prev, has_prev])
    G1_all, G3_all, G4_all, G2_all   all gliomas (secondary, last; same order as grade 4)
Detection arms train on detection scans with label_det == 1 (progression scan) or neg_primary (index scan with
label_120 == 0); every population scan of the outer test fold is scored (incl. secondary-only negatives).

Stages (`python -m prism finetune_det <command>`):
    cache     current-scan crops of every detection scan (same rules as finetune_deep, shared cache dir; existing
              files are not rewritten) and previous-scan crops at the current scan's box ->
              outputs/features/finetune_cache/detection_prev/<scan>__<prev>.npy (CPU, no labels)
    smoke     shuffled labels only: memory, speed, determinism for cur / diff / siamese inputs
    run       resumable lock-file runner (as finetune_deep) on --gpus x --per-gpu
    scores    job files -> outputs/results/analyses/detection/deep/<arm>/scores.csv
    evaluate  image-only AUC per arm (intended use / overall), G4 validity, G5 rule 3 (C2 + G5 - C2)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from prism.analyses import finetune_deep as fd
from prism.config import OUTPUTS, REPO, RESULTS

COHORT = OUTPUTS / "data" / "detection_cohort.csv"
CACHE = fd.CACHE
PREV = CACHE / "detection_prev"
OUT = Path(os.environ.get("PRISM_FINETUNE_DET_OUT", RESULTS / "analyses" / "finetune_detection"))
SCORES = Path(os.environ.get("PRISM_DET_SCORES", RESULTS / "analyses" / "detection" / "deep"))
HP = fd.HP
N_REPEATS, N_FOLDS = fd.N_REPEATS, fd.N_FOLDS
ARMS = {
    "G1": dict(pop="grade4", task="det", inp="cur", lab="real"),
    "G4": dict(pop="grade4", task="det", inp="cur", lab="perm"),
    "G3": dict(pop="grade4", task="det", inp="diff", lab="real"),
    "G5": dict(pop="grade4", task="fwd120", inp="diff", lab="real"),
    "G2": dict(pop="grade4", task="det", inp="siamese", lab="real"),
    "G1_all": dict(pop="all_glioma", task="det", inp="cur", lab="real"),
    "G3_all": dict(pop="all_glioma", task="det", inp="diff", lab="real"),
    "G4_all": dict(pop="all_glioma", task="det", inp="cur", lab="perm"),
    "G2_all": dict(pop="all_glioma", task="det", inp="siamese", lab="real"),
    # runner / smoke tests only (labels permuted over the whole population, never evaluated)
    "S1": dict(pop="grade4", task="det", inp="cur", lab="shuf"),
    "S3": dict(pop="grade4", task="det", inp="diff", lab="shuf"),
    "S2": dict(pop="grade4", task="det", inp="siamese", lab="shuf"),
}
PRIORITY = ("G1", "G4", "G3", "G5", "G2", "G1_all", "G3_all", "G4_all", "G2_all")


# ---------------------------------------------------------------- cohort
def load_detection():
    d = pd.read_csv(COHORT)
    need = {"scan_id", "patient_id", "grade4", "label_det", "neg_primary", "neg_secondary", "intended_use", "phase",
            "prev_scan_id", "days_from_prev", *(f"fold_r{r}" for r in range(N_REPEATS))}
    assert need <= set(d.columns), need - set(d.columns)
    assert d.scan_id.is_unique
    return d


def check_previous(d):
    """Leakage rule 5: every previous scan is of the same patient and dated strictly before the scan."""
    from prism.data.mu import load_index
    idx = load_index().set_index("scan_id")
    day = pd.to_numeric(idx.days_from_diagnosis_to_mri, errors="coerce")
    p = d[d.prev_scan_id.notna()]
    assert (idx.loc[p.prev_scan_id, "patient_id"].to_numpy() == p.patient_id.to_numpy()).all()
    gap = day.loc[p.scan_id].to_numpy() - day.loc[p.prev_scan_id].to_numpy()
    assert (gap > 0).all(), "previous scan not strictly before the scan"
    assert np.allclose(gap, p.days_from_prev.to_numpy())
    return len(p)


class Population:
    """Rows of one arm: scan ids, patients, training labels (NaN = not trained on), folds (n x 5), previous scans."""

    def __init__(self, arm):
        a = ARMS[arm]
        d = load_detection()
        if a["task"] == "det":
            if a["pop"] == "grade4":
                d = d[d.grade4.astype(bool)]
            d = d.reset_index(drop=True)
            y = np.where(d.label_det.eq(1), 1.0, np.where(d.neg_primary.astype(bool), 0.0, np.nan))
            self.frame = d
        else:  # forward 120-day label on the index scans, exactly finetune_deep's grade-4 population and folds
            from prism.data.mu import load_cohort
            from prism.models.folds import load_folds
            c = load_cohort(a["pop"]).reset_index(drop=True)
            folds = load_folds()
            dd = d.set_index("scan_id")
            assert c.scan_id.isin(dd.index).all() and dd.loc[c.scan_id, "label_det"].eq(0).all()
            for r in range(N_REPEATS):
                c[f"fold_r{r}"] = fd.fold_ids(c, folds, r)
                assert (c[f"fold_r{r}"].to_numpy() == dd.loc[c.scan_id, f"fold_r{r}"].to_numpy()).all()
            for col in ("prev_scan_id", "days_from_prev", "intended_use", "phase"):
                c[col] = dd.loc[c.scan_id, col].to_numpy()
            y = c[f"label_{fd.H}"].to_numpy(float)
            self.frame = c
        self.scan_id = self.frame.scan_id.to_numpy().astype(str)
        self.patient_id = self.frame.patient_id
        self.y = y
        self.folds = np.stack([self.frame[f"fold_r{r}"].to_numpy() for r in range(N_REPEATS)], 1)
        self.prev = self.frame.prev_scan_id.where(self.frame.prev_scan_id.notna(), None).tolist()


@lru_cache(maxsize=None)
def population(arm):
    return Population(arm)


# ---------------------------------------------------------------- cache (CPU, no labels)
def prev_path(scan_id, prev_id):
    return PREV / f"{scan_id}__{prev_id}.npy"


def _cache_one(job):
    scan_id, prev_id = job
    import torch
    torch.set_num_threads(1)
    row = None
    if not (CACHE / f"{scan_id}.npy").exists():
        row = fd.cache_scan((scan_id, None))
    if prev_id is not None and not prev_path(scan_id, prev_id).exists():
        # the current scan's crop box (same rule as fd.cache_scan, recomputed from the mask)
        img, mask = fd._load_norm(scan_id)
        lesion = np.isin(mask, (fd.LABEL_ET, fd.LABEL_NETC, fd.LABEL_SNFH))
        roi = lesion | (mask == fd.LABEL_RC)
        w = np.where(roi) if roi.any() else np.where((img != 0).any(0))
        lo, hi = np.array([a.min() for a in w]), np.array([a.max() + 1 for a in w])
        side = int(max(fd.SIDE, (hi - lo).max() + 2 * fd.MARGIN))
        start = np.round((lo + hi) / 2 - side / 2).astype(int)
        pimg, _ = fd._load_norm(prev_id)
        tmp = prev_path(scan_id, prev_id).with_suffix(".tmp.npy")
        np.save(tmp, fd._resize(fd._crop(pimg, start, side), "trilinear").astype(np.float16))
        os.replace(tmp, prev_path(scan_id, prev_id))
    return row


def build_cache(workers):
    d = load_detection()
    n_prev = check_previous(d)
    PREV.mkdir(parents=True, exist_ok=True)
    jobs = [(s, p if isinstance(p, str) else None) for s, p in zip(d.scan_id, d.prev_scan_id)]
    todo = [j for j in jobs if not (CACHE / f"{j[0]}.npy").exists() or (j[1] and not prev_path(*j).exists())]
    print(f"detection cache: {len(d)} scans ({n_prev} with a previous scan), {len(todo)} to build", flush=True)
    t = time.time()
    with ProcessPoolExecutor(workers) as ex:
        rows = [r for r in ex.map(_cache_one, todo) if r is not None]
    if rows:
        mp = CACHE / "detection_meta.csv"
        meta = pd.concat([pd.read_csv(mp), pd.DataFrame(rows)]) if mp.exists() else pd.DataFrame(rows)
        meta.drop_duplicates("scan_id", keep="last").to_csv(mp, index=False)
    print(f"built in {time.time() - t:.0f}s; new current crops {len(rows)}", flush=True)


# ---------------------------------------------------------------- data and network (GPU)
class DetData:
    """X (n,4,S,S,S), M (n,1,..) float16 on the GPU; with previous scans also P (prev crop, = X when none) and has."""

    def __init__(self, pop, device, need_prev):
        torch, _, _ = fd._torch()
        arr = [np.load(CACHE / f"{s}.npy", mmap_mode="r") for s in pop.scan_id]
        self.X = torch.stack([torch.from_numpy(np.ascontiguousarray(a[:4])) for a in arr]).to(device)
        self.M = torch.stack([torch.from_numpy(np.ascontiguousarray(a[4:5])) for a in arr]).to(device)
        self.P = self.has = None
        if need_prev:
            self.has = torch.tensor([p is not None for p in pop.prev], device=device)
            self.P = torch.stack([torch.from_numpy(np.load(prev_path(s, p))) if p is not None else self.X[i].cpu()
                                  for i, (s, p) in enumerate(zip(pop.scan_id, pop.prev))]).to(device)


def make_net(inp, dropout):
    if inp in ("cur", "siamese"):
        return fd.make_net("brats21", inp == "siamese", dropout)
    torch, nn, F = fd._torch()
    base = fd.make_net("brats21", False, dropout)
    features = type(base).features

    class DiffNet(nn.Module):
        """8 channels: current + (current - previous) * has_prev; has_prev appended to the pooled features."""

        def __init__(self):
            super().__init__()
            self.vit = base.vit
            old = self.vit.patch_embed.proj
            new = nn.Conv3d(8, old.out_channels, old.kernel_size, old.stride)
            with torch.no_grad():
                new.weight.copy_(torch.cat([old.weight, 0.5 * old.weight], 1))
                new.bias.copy_(old.bias)
            new.requires_grad_(False)
            self.vit.patch_embed.proj = new
            dim = 192 + 384 + 768 + 768 + 1
            self.head = nn.Sequential(nn.LayerNorm(dim), nn.Dropout(dropout), nn.Linear(dim, 1))

        def forward(self, x, m, prev, has):
            hp = has.to(x.dtype)[:, None]
            f = features(self, torch.cat([x, (x - prev) * hp[:, :, None, None, None]], 1), m)
            return self.head(torch.cat([f, hp.to(f.dtype)], 1).float()).squeeze(1)

        def train(self, mode=True):
            super().train(mode)
            for mod in (self.vit.patch_embed, self.vit.layers1, self.vit.layers2):
                mod.eval()
            return self

    return DiffNet()


def fine_tune(inp, data, fit, val, y, seed, max_epochs=None, log=print):
    """fd.fine_tune with the network chosen by input mode (identical optimisation, schedule, early stopping)."""
    torch, nn, F = fd._torch()
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed)
    rng = np.random.default_rng(seed)
    max_epochs = max_epochs or HP["max_epochs"]
    net = make_net(inp, HP["dropout"])
    torch.manual_seed(seed)
    for mod in net.head:
        if hasattr(mod, "reset_parameters"):
            mod.reset_parameters()
    net = net.cuda()
    enc = [p for p in net.vit.parameters() if p.requires_grad]
    opt = torch.optim.AdamW([{"params": enc, "lr": HP["lr_enc"]}, {"params": net.head.parameters(), "lr": HP["lr_head"]}],
                            weight_decay=HP["wd"])
    spe = math.ceil(len(fit) / HP["batch"])
    total, warm = HP["max_epochs"] * spe, HP["warmup"] * spe
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / warm if s < warm else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(total - warm, 1))))
    yv = torch.tensor(y[val], dtype=torch.float32)
    frozen = ("vit.patch_embed", "vit.layers1", "vit.layers2")
    best, best_state, bad, hist = np.inf, None, 0, []
    for ep in range(max_epochs):
        net.train()
        t0, losses = time.time(), []
        order = fit[rng.permutation(len(fit))]
        for b in range(0, len(order), HP["batch"]):
            rows = order[b:b + HP["batch"]]
            x, m, p, h = fd._batch(data, rows)
            x, m, p = fd.augment(x, m, p, g)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logit = net(x, m, p, h)
            loss = F.binary_cross_entropy_with_logits(logit.float(), torch.tensor(y[rows], dtype=torch.float32, device="cuda"))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
            losses.append(loss.item())
        vl = float(F.binary_cross_entropy_with_logits(torch.tensor(fd.predict(net, data, val, tta=False),
                                                                   dtype=torch.float32), yv))
        hist.append({"epoch": ep, "train_loss": float(np.mean(losses)), "val_loss": vl, "sec": time.time() - t0})
        log(f"    ep {ep} train {hist[-1]['train_loss']:.4f} val {vl:.4f} {hist[-1]['sec']:.1f}s")
        if vl < best - 1e-4:
            best, bad = vl, 0
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items() if not k.startswith(frozen)}
        else:
            bad += 1
            if ep + 1 >= HP["min_epochs"] and bad >= HP["patience"]:
                break
    net.load_state_dict(best_state, strict=False)
    return net, hist


# ---------------------------------------------------------------- jobs
def train_labels(pop, lab, r, k, tr):
    y = pop.y.copy()
    if lab == "perm":
        y[tr] = np.random.default_rng(1000 * r + k).permutation(y[tr])
    elif lab == "shuf":
        known = np.where(~np.isnan(y))[0]
        y[known] = np.random.default_rng(999).permutation(y[known])
    return y


def job_spec(arm, r, k, j, pop=None):
    """As fd.job_spec: outer split on the arm's folds, GroupKFold(4) inner, StratifiedGroupKFold(5) early-stop split."""
    from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
    pop = pop or population(arm)
    lab = ARMS[arm]["lab"]
    f = pop.folds[:, r]
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    tr = tr[~np.isnan(pop.y[tr])]
    if lab == "shuf":
        tr = tr[np.random.default_rng(999).permutation(len(tr))[:len(tr) // 2]]  # quick runner test
    y = train_labels(pop, lab, r, k, tr)
    a, b = list(GroupKFold(n_splits=HP["n_inner"]).split(tr, groups=pop.patient_id.iloc[tr]))[j]
    pool, hold = tr[a], tr[b]
    seed = fd.job_seed(r, k, j)
    sgkf = StratifiedGroupKFold(n_splits=HP["val_folds"], shuffle=True, random_state=seed)
    fit_i, val_i = next(sgkf.split(pool, y[pool].astype(int), pop.patient_id.iloc[pool]))
    return dict(fit=pool[fit_i], val=pool[val_i], hold=hold, test=te, y=y, seed=seed)


def all_jobs(arms, limit=None):
    js = [[(a, r, k, j) for r in range(N_REPEATS) for k in range(N_FOLDS) for j in range(HP["n_inner"])] for a in arms]
    return [jb for x in js for jb in x[:limit]]


def job_path(arm, r, k, j):
    return OUT / "jobs" / arm / f"r{r}_k{k}_j{j}.npz"


def run_job(arm, r, k, j, pop, data, log):
    torch = fd.setup_torch()
    s = job_spec(arm, r, k, j, pop)
    pid = pop.patient_id.to_numpy()
    parts = [set(pid[s[x]]) for x in ("fit", "val", "hold", "test")]
    assert all(not (parts[a] & parts[b]) for a in range(4) for b in range(a + 1, 4)), "patient overlap"
    t = time.time()
    torch.cuda.reset_peak_memory_stats()
    net, hist = fine_tune(ARMS[arm]["inp"], data, s["fit"], s["val"], s["y"], s["seed"], log=log)
    rows = np.concatenate([s["hold"], s["test"]])
    logit = fd.predict(net, data, rows)
    path = job_path(arm, r, k, j)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.npz")
    np.savez(tmp, rows=rows, is_test=np.r_[np.zeros(len(s["hold"]), bool), np.ones(len(s["test"]), bool)], logit=logit,
             scan_id=pop.scan_id[rows],
             info=json.dumps({"best_epoch": int(np.argmin([h["val_loss"] for h in hist])), "epochs": len(hist),
                              "hist": hist, "sec": time.time() - t, "peak_gb": torch.cuda.max_memory_allocated() / 1e9,
                              "n_fit": len(s["fit"]), "n_val": len(s["val"]), "seed": s["seed"]}))
    os.replace(tmp, path)
    return time.time() - t


def worker(arms, tag, limit=None):
    lock_dir = OUT / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    loaded = {}
    log = lambda m: print(f"[{tag}] {time.strftime('%H:%M:%S')} {m}", flush=True)
    for arm, r, k, j in all_jobs(arms, limit):
        if job_path(arm, r, k, j).exists():
            continue
        lock = lock_dir / f"{arm}_r{r}_k{k}_j{j}.lock"
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            continue
        a = ARMS[arm]
        key = (a["pop"], a["task"], a["inp"] != "cur")
        if key not in loaded:
            loaded.clear()
            torch = fd.setup_torch()
            torch.cuda.empty_cache()
            pop = population(arm)
            loaded[key] = (pop, DetData(pop, "cuda", a["inp"] != "cur"))
        pop, data = loaded[key]
        log(f"{arm} r{r} k{k} j{j} start")
        try:
            sec = run_job(arm, r, k, j, pop, data, lambda m: None)
        except Exception as e:  # keep the lock-free state consistent; the job is retried by the next launch
            log(f"{arm} r{r} k{k} j{j} FAILED {type(e).__name__}: {str(e)[:200]}")
            lock.unlink(missing_ok=True)
            raise
        log(f"{arm} r{r} k{k} j{j} done {sec / 60:.1f} min")
        lock.unlink(missing_ok=True)


def launch(arms, gpus, per_gpu, limit=None):
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    if any(ARMS[a]["lab"] != "shuf" for a in arms):
        snapshot_plan()
    for lock in (OUT / "locks").glob("*.lock") if (OUT / "locks").exists() else []:
        lock.unlink()
    todo = [jb for jb in all_jobs(arms, limit) if not job_path(*jb).exists()]
    print(f"{time.strftime('%H:%M:%S')} {len(todo)} of {len(all_jobs(arms, limit))} jobs to run on GPUs {gpus} x {per_gpu}",
          flush=True)
    procs = []
    for g in gpus:
        for s in range(per_gpu):
            env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(g), "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2",
                   "OPENBLAS_NUM_THREADS": "2", "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
                   "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}
            logf = open(OUT / "logs" / f"worker_gpu{g}_{s}.log", "a")
            procs.append(subprocess.Popen([sys.executable, "-m", "prism.analyses.finetune_detection", "worker", "--arms",
                                           *arms, "--tag", f"gpu{g}.{s}"] + (["--limit", str(limit)] if limit else []),
                                          env=env, stdout=logf, stderr=subprocess.STDOUT))
            time.sleep(15)
    codes = [p.wait() for p in procs]
    left = [jb for jb in all_jobs(arms, limit) if not job_path(*jb).exists()]
    print(f"{time.strftime('%H:%M:%S')} workers exited {codes}; {len(left)} jobs left", flush=True)


def snapshot_plan():
    snap = OUT / "PLAN_snapshot.md"
    if snap.exists():
        return
    from prism.audit.provenance import git_state
    OUT.mkdir(parents=True, exist_ok=True)
    doc = (REPO / "docs" / "results" / "DETECTION_TASK.md").read_text()
    plan = doc.split("## Plan (pre-specified)", 1)[1].split("\n## ", 1)[0]
    snap.write_text(f"# PLAN snapshot ({time.strftime('%Y-%m-%dT%H:%M:%S')}, git {git_state()['commit'][:10]})\n\n"
                    "## Plan (pre-specified)" + plan)


# ---------------------------------------------------------------- scores and evaluation (CPU)
def write_scores(arm):
    rows = []
    for r in range(N_REPEATS):
        for k in range(N_FOLDS):
            for j in range(HP["n_inner"]):
                z = np.load(job_path(arm, r, k, j))
                rows.append(pd.DataFrame({"scan_id": z["scan_id"], "repeat": r, "fold": k, "inner": j,
                                          "is_test": z["is_test"].astype(int), "logit": z["logit"]}))
    out = SCORES / arm
    out.mkdir(parents=True, exist_ok=True)
    s = pd.concat(rows, ignore_index=True)
    s.to_csv(out / "scores.csv", index=False)
    info = [{"repeat": r, "fold": k, "inner": j, **{a: b for a, b in json.loads(str(np.load(job_path(arm, r, k, j))["info"])).items()
                                                    if a != "hist"}}
            for r in range(N_REPEATS) for k in range(N_FOLDS) for j in range(HP["n_inner"])]
    pd.DataFrame(info).to_csv(out / "jobs.csv", index=False)
    return s


def arm_done(arm):
    return all(job_path(*jb).exists() for jb in all_jobs([arm]))


def test_matrix(scores, scan_ids):
    """(repeats x scans) mean test logit over the 4 inner networks; and per (r, k) the inner OOF logits."""
    pos = {s: i for i, s in enumerate(scan_ids)}
    T = np.full((N_REPEATS, len(scan_ids)), np.nan)
    t = scores[scores.is_test == 1].groupby(["repeat", "scan_id"]).logit.agg(["mean", "size"]).reset_index()
    assert (t["size"] == HP["n_inner"]).all()
    T[t.repeat.to_numpy(), t.scan_id.map(pos).to_numpy()] = t["mean"].to_numpy()
    oof = {}
    for (r, k), g in scores[scores.is_test == 0].groupby(["repeat", "fold"]):
        o = np.full(len(scan_ids), np.nan)
        o[g.scan_id.map(pos).to_numpy()] = g.logit.to_numpy()
        oof[(r, k)] = o
    return T, oof


def eval_detection(arm, n_boot):
    from prism.analyses.diagnostics_imaging import boot_auc
    from sklearn.metrics import roc_auc_score
    pop = population(arm)
    d = pop.frame
    T, _ = test_matrix(pd.read_csv(SCORES / arm / "scores.csv"), pop.scan_id)
    assert np.isfinite(T).all()
    pos, negp, negs = d.label_det.eq(1).to_numpy(), d.neg_primary.astype(bool).to_numpy(), d.neg_secondary.astype(bool).to_numpy()
    iu = d.intended_use.astype(bool).to_numpy()
    out = []
    for name, neg in (("primary_negatives", negp), ("secondary_negatives", negs)):
        for setname, m in (("intended_use", iu), ("overall", np.ones(len(d), bool))):
            sel = (pos | neg) & m
            y = pos[sel].astype(int)
            a, lo, hi = boot_auc(y, T[:, sel], d.patient_id.to_numpy()[sel], n_boot=n_boot)
            out.append({"arm": arm, "negatives": name, "set": setname, "n_pos": int(y.sum()), "n_neg": int((1 - y).sum()),
                        "n_patients": int(d.patient_id[sel].nunique()), "auc": a, "auc_lo": lo, "auc_hi": hi})
        for ph in sorted(d.phase.unique()):  # within-phase (point estimates)
            sel = (pos | neg) & d.phase.eq(ph).to_numpy()
            if len(np.unique(pos[sel])) == 2:
                out.append({"arm": arm, "negatives": name, "set": f"phase:{ph}", "n_pos": int(pos[sel].sum()),
                            "n_neg": int((~pos[sel]).sum()), "n_patients": int(d.patient_id[sel].nunique()),
                            "auc": float(np.mean([roc_auc_score(pos[sel], t[sel]) for t in T]))})
    return pd.DataFrame(out)


def eval_g5(n_boot):
    """Rule 3: C2 + G5 score (z-scored with its inner OOF on T_ver) vs C2 in the intended use (models trained on all
    grade-4 scans), IPCW AUC(120 d), paired patient-cluster bootstrap (evaluate_repeated, reference C2)."""
    from prism.analyses import phase_censoring as pc
    from prism.audit.model import fit_pipeline
    from prism.experiments import c3_radiomics as c3
    from prism.models.metrics import evaluate_repeated
    cohort, folds, index, p4, _ = pc.load("grade4")
    pop = population("G5")
    assert (cohort.scan_id.to_numpy() == pop.scan_id).all()
    Xc, gc = pc.arm_design("C2", cohort, index)
    T, oof = test_matrix(pd.read_csv(SCORES / "G5" / "scores.csv"), pop.scan_id)
    y = cohort[f"label_{fd.H}"].to_numpy(float)
    n = len(cohort)
    res = {k: np.zeros((N_REPEATS, n)) for k in ("C2", "C2+G5")}
    res["G5_image"] = 1 / (1 + np.exp(-T))
    for r in range(N_REPEATS):
        f = c3._fold_ids(cohort, folds, r)
        for k in range(N_FOLDS):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            res["C2"][r, te] = fit_pipeline(Xc, cohort, tr, gc, seed=r).predict(Xc.iloc[te])
            tv = tr[~np.isnan(y[tr])]
            o = oof[(r, k)]
            assert np.isfinite(o[tv]).all()
            mu, sd = o[tv].mean(), o[tv].std() + 1e-8
            X = Xc.copy()
            X["g5_score"] = np.where(np.isin(np.arange(n), te), (T[r] - mu) / sd, (o - mu) / sd)
            res["C2+G5"][r, te] = fit_pipeline(X, cohort, tr, {**gc, "g5_score": "deep"}, seed=r).predict(X.iloc[te])
    ref = pd.read_csv(pc.OUT / "oof_grade4_full.csv.gz").set_index("scan_id").loc[cohort.scan_id]
    dev = float(np.abs(np.array([ref[f"C2#r{r}"] for r in range(N_REPEATS)]) - res["C2"]).max())
    iu = p4 != "pre_rt"
    rows = []
    for name, m in (("intended_use", iu), ("grade4_overall", np.ones(n, bool))):
        ev = evaluate_repeated(cohort[m].reset_index(drop=True), {k: v[:, m] for k, v in res.items()}, fd.H,
                               reference="C2", n_boot=n_boot)
        for arm, rr in ev.iterrows():
            rows.append({"set": name, "model": arm, "n": int(m.sum()), **{c: rr.get(c) for c in (
                "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "d_auc_ipcw_vs_C2", "d_auc_ipcw_lo", "d_auc_ipcw_hi",
                "cal_slope", "oe_ratio", "brier_ipcw")}})
    return pd.DataFrame(rows), dev, res, cohort


def evaluate(arms, n_boot):
    out = SCORES / "evaluation"
    out.mkdir(parents=True, exist_ok=True)
    det = [a for a in arms if ARMS[a]["task"] == "det" and (SCORES / a / "scores.csv").exists()]
    tabs = [eval_detection(a, n_boot) for a in det]
    if tabs:
        t = pd.concat(tabs)
        t.to_csv(out / "image_only_auc.csv", index=False)
        print(t[~t.set.str.startswith("phase")].round(3).to_string(index=False))
        print(t[t.set.str.startswith("phase")].round(3).to_string(index=False))
        if "G4" in det:
            g = t[(t.arm == "G4") & (t.negatives == "primary_negatives")]
            for _, r in g.iterrows():
                print(f"G4 validity ({r.set}): CI [{r.auc_lo:.3f}, {r.auc_hi:.3f}] covers 0.5: {r.auc_lo <= 0.5 <= r.auc_hi}")
    if "G5" in arms and (SCORES / "G5" / "scores.csv").exists():
        g5, dev, res, cohort = eval_g5(n_boot)
        g5.to_csv(out / "g5_triage.csv", index=False)
        pd.concat([pd.DataFrame(o.T, columns=[f"{k}#r{r}" for r in range(N_REPEATS)]) for k, o in res.items()], axis=1
                  ).assign(scan_id=cohort.scan_id.to_numpy()).to_csv(out / "g5_oof_repeats.csv.gz", index=False)
        print(f"C2 reproduces phase_censoring/oof_grade4_full: max dev {dev:.2e}")
        print(g5.round(3).to_string(index=False))
        x = g5[(g5.set == "intended_use") & (g5.model == "C2+G5")].iloc[0]
        ok = x.d_auc_ipcw_vs_C2 >= 0.03 and x.d_auc_ipcw_lo > 0
        print(f"Rule 3 (C2 + G5 - C2 >= +0.03, CI excluding 0, intended use): {x.d_auc_ipcw_vs_C2:+.3f} "
              f"[{x.d_auc_ipcw_lo:+.3f}, {x.d_auc_ipcw_hi:+.3f}] -> {'SUCCEEDS' if ok else 'FAILS'}")
        (out / "g5_rule3.json").write_text(json.dumps({"c2_max_dev": dev, "d_auc": x.d_auc_ipcw_vs_C2,
                                                       "lo": x.d_auc_ipcw_lo, "hi": x.d_auc_ipcw_hi, "succeeds": bool(ok)}))


# ---------------------------------------------------------------- smoke test (shuffled labels only)
def smoke(n, epochs, inputs):
    torch = fd.setup_torch()
    pop = population("S3")  # cohort rows only; labels below are a random permutation, never evaluated
    have = [i for i, (s, p) in enumerate(zip(pop.scan_id, pop.prev)) if p is not None][: n // 2]
    have += [i for i, p in enumerate(pop.prev) if p is None][: n - len(have)]

    class Sub:
        pass
    sub = Sub()
    sub.scan_id, sub.prev = pop.scan_id[have], [pop.prev[i] for i in have]
    y = np.random.default_rng(0).permutation(np.r_[np.ones(n // 2), np.zeros(n - n // 2)])
    rows = np.arange(n)
    fit, val, test = rows[: n - 8], rows[n - 8: n - 4], rows[n - 4:]
    report = {}
    for inp in inputs:
        data = DetData(sub, "cuda", inp != "cur")
        preds = []
        for rep in range(2):
            torch.cuda.reset_peak_memory_stats()
            t = time.time()
            net, hist = fine_tune(inp, data, fit, val, y, seed=123, max_epochs=epochs, log=lambda m: print(m, flush=True))
            preds.append(fd.predict(net, data, test))
            step = np.mean([h["sec"] for h in hist[1:]] or [hist[0]["sec"]]) / math.ceil(len(fit) / HP["batch"])
            report.setdefault(inp, {"runs": []})["runs"].append(
                {"peak_gb": torch.cuda.max_memory_allocated() / 1e9, "sec": time.time() - t, "sec_per_step": step})
            del net
        report[inp]["max_abs_diff_between_runs"] = float(np.abs(preds[0] - preds[1]).max())
        report[inp]["test_logits"] = [list(map(float, p)) for p in preds]
        t = time.time()
        net = make_net(inp, HP["dropout"]).cuda()
        fd.predict(net, data, test)
        report[inp]["sec_tta_predict_per_scan"] = (time.time() - t) / len(test)
        report[inp]["data_gb_for_n_scans"] = sum(x.numel() * x.element_size() for x in (data.X, data.M, data.P)
                                                 if x is not None) / 1e9
        del data, net
        torch.cuda.empty_cache()
    print(json.dumps(report, indent=1))
    (OUT / "smoke").mkdir(parents=True, exist_ok=True)
    (OUT / "smoke" / f"smoke_n{n}.json").write_text(json.dumps(report, indent=1))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism finetune_det", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["cache", "smoke", "run", "worker", "scores", "evaluate"])
    ap.add_argument("--arms", nargs="+", default=list(PRIORITY))
    ap.add_argument("--gpus", nargs="+", type=int, default=[0, 1, 2, 3])
    ap.add_argument("--per-gpu", type=int, default=2)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int, help="run/worker: first N jobs per arm (runner test)")
    ap.add_argument("--tag", default="w")
    ap.add_argument("--n", type=int, default=24, help="smoke: number of scans")
    ap.add_argument("--epochs", type=int, default=3, help="smoke: epochs")
    ap.add_argument("--inputs", nargs="+", default=["cur", "diff", "siamese"], help="smoke: input modes")
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    if a.command == "cache":
        build_cache(a.workers)
    elif a.command == "smoke":
        smoke(a.n, a.epochs, a.inputs)
    elif a.command == "run":
        launch(a.arms, a.gpus, a.per_gpu, a.limit)
    elif a.command == "worker":
        worker(a.arms, a.tag, a.limit)
    elif a.command == "scores":
        for arm in a.arms:
            if arm_done(arm):
                print(arm, len(write_scores(arm)), "rows")
            else:
                print(arm, "not finished")
    else:
        evaluate(a.arms, a.n_boot)


if __name__ == "__main__":
    main()
