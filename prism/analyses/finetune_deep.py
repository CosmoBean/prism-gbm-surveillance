"""Fine-tuned SwinUNETR encoder for the 120-day label, nested inside the shared 5x5 patient-grouped folds.

ANALYSIS PLAN (pre-specified before any fine-tuned model saw a real label; also in docs/results/FINETUNE_DEEP.md
"Analysis plan (pre-specified)", snapshot copied to outputs/results/analyses/finetune/PLAN_snapshot.md before the first
real-label run. Anything added after results is labelled EXPLORATORY.)

Question. The paper evaluated only FROZEN SwinUNETR encoders (DEEP_FEATURES.md: nested D1 dAUC -0.004 grade 4). Does
fine-tuning the encoder on the 120-d label give an image score that adds to the core model (ridge on clinical + timing
+ as-of-scan treatment, 0.698 grade 4 / 0.720 all gliomas)?

A. Task and label. label_120 (documented progression <= 120 d after the scan, death censored). Scans censored before
   120 d (label NaN) are EXCLUDED from the training loss ("verified" formulation, the same one the core ridge uses, so
   score and stack are trained on the same rows); they are still scored and enter the IPCW AUC(120 d) as in every
   other analysis. Grade 4 primary (249 scans / 126 patients), all gliomas secondary (308 / 155).
B. Splits. The shared folds (outputs/data/folds.csv), 5 repeats x 5 outer folds. Inside each outer training set T, the
   verified scans are split into 4 inner patient-grouped folds with GroupKFold(4) exactly as c3's stacking does. For
   inner fold j a network is fine-tuned on T_ver \\ fold j and predicts fold j (inner out-of-fold score for stacking)
   and the outer test fold. Early stopping uses a patient-grouped validation split (20% of patients,
   StratifiedGroupKFold(5, shuffle) first fold) drawn from T_ver \\ fold j only, so neither fold j nor the outer test fold
   influences training or stopping. 4 fine-tunes per outer split = 100 per arm; no network ever sees an outer-test label.
C. Scores. Outer-test image score = mean of the 4 inner networks' logits (cross-fit bagging: the training-side OOF score
   and the test score come from the same 4 networks, so their scales match without a 5th full-T fit). Stacking: the
   score is z-scored with the mean/SD of its inner OOF values on T_ver, appended to the core features (c3.BASE_PRE) and
   the core ridge (formulations.fit "verified", C by inner patient-grouped CV) is refitted on T_ver; it predicts the
   outer test fold. Image-only arm = sigmoid of the averaged logit.
D. Network (all hyperparameters fixed here, none tuned; HP below). MONAI SwinUNETR swinViT (feature size 48, 4 channels
   FLAIR/T1c/T1/T2), start from BraTS 2021 weights (primary) or BrainSegFounder (secondary arm), decoder discarded.
   Input: brain z-scored volume (as prism.features.deep), cube centred on the lesion+cavity bounding box, side =
   max(128, extent + 16 mm), resampled to 128^3 if larger (37 / 308 cohort scans). Mask-guided pooling: mask-weighted means of
   stages 2, 3, 4 within the lesion (ET|NETC|SNFH; lesion+cavity if lesion <= 30 voxels) + global mean of stage 4 ->
   2112 features -> LayerNorm -> Dropout(0.3) -> Linear(1). Partial unfreezing: patch embedding + stages 1-2 frozen
   (run without grad), stages 3-4 + head trained. AdamW (encoder lr 2e-5, head lr 1e-3, weight decay 0.01), 1 warm-up
   epoch then cosine over 25 epochs, batch 4, bf16 autocast, BCE. Early stopping on validation BCE (patience 5, at
   least 3 epochs), best epoch restored. Augmentation: random flips (3 axes), translation +-8 voxels, per-channel
   intensity scale 0.9-1.1 and shift +-0.1 inside the brain. Prediction: mean logit over 8 flip TTAs.
E. Arms (run in this order; each = 100 fine-tunes):
     1 brats21:grade4:real      PRIMARY
     2 brats21:grade4:perm      control: identical pipeline, verified labels permuted among T_ver scans of the outer
                                training set (one permutation per outer split, seed 1000r+k); the stacking ridge uses
                                the real labels, so this shows what an uninformative fine-tuned score does to the stack
     3 brats21:all_glioma:real  secondary population
     4 bsf:grade4:real          secondary encoder (BrainSegFounder)
     5 brats21+prev:grade4:real OPTIONAL secondary (change): same pipeline, siamese encoder on the current scan and
                                the patient's previous scan cropped at the same atlas box (MU is SRI24-registered,
                                240x240x155), head on [f_cur, f_cur - f_prev, has_prev] (f_prev = f_cur when no prior
                                scan). Run only if arms 1-4 are finished within the compute budget.
F. Evaluation (CPU). metrics.evaluate_repeated (mean over repeats of the per-repeat pooled-OOF IPCW AUC(120 d), paired
   patient-cluster bootstrap, 1000 draws) with the core ridge baseline recomputed by c3.fit_predict on the same folds
   (must reproduce 0.698 / 0.720) as reference. Reported per population: image-only fine-tuned AUC; core + fine-tuned
   vs core (dAUC, 95% CI); calibration (slope, O/E, Brier) of every arm; permuted-label control (image-only and stack);
   frozen reference = NESTED_D1 OOF predictions of DEEP_FEATURES.md (outputs/results/analyses/deep/<pop>/oof_repeats)
   in the same bootstrap. Diagnostics: best epochs, correlation of the score with log lesion volume and the core logit.
G. PRE-SPECIFIED RULE. Fine-tuning HELPS if, grade 4, arm 1, core + fine-tuned score beats core by dAUC >= 0.03 with the
   paired 95% CI excluding 0. Otherwise it does not. All other arms are secondary (no multiplicity correction). The
   control must give image-only AUC ~0.5 and stack dAUC <= 0; if it does not, the result is flagged as invalid.
   Minimal detectable effect: MDE = 2.8 x SE(dAUC) (80% power, two-sided 5%), SE = CI width / 3.92 from the bootstrap;
   reported with the result (prior expectation from the frozen arms: SE 0.02-0.034 -> MDE ~0.06-0.09).
H. Compute. 4 arms x 100 = 400 fine-tunes (+100 optional). Smoke test (shuffled labels, H100): 0.12 s per training
   step (batch 4) incl. validation, 0.3 s per scan for 8-flip TTA, peak 19 GB per process with the whole grade-4 cohort
   on the GPU (32 GB for the +prev arm), bit-identical predictions on rerun. A full job is ~1.5-2.5 min alone; with 3
   processes per GPU on GPUs 1-3, arms 1-4 take ~2-3.5 h, the optional arm ~1-1.5 h more (2 processes per GPU).

Stages (`python -m prism finetune <command>`):
    cache      crop/resample all cohort scans (+ previous scans) -> outputs/features/finetune_cache/ (CPU, no labels)
    smoke      tiny shuffled-label run on a few scans: memory, speed, determinism (no real labels)
    run        fine-tune all jobs of the given arms on --gpus (--per-gpu processes each); resumable: finished jobs are
               skipped, a job is claimed with an atomic lock file, stale locks are cleared at start
    evaluate   assemble scores, stack, bootstrap -> outputs/results/analyses/finetune/<population>/
    CUDA_VISIBLE_DEVICES is set per worker by `run`; GPU 0 is never used unless listed in --gpus.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from prism.config import LABEL_ET, LABEL_NETC, LABEL_RC, LABEL_SNFH, OUTPUTS, RESULTS, mu_scan_paths

H = 120
CACHE = OUTPUTS / "features" / "finetune_cache"
OUT = Path(os.environ.get("PRISM_FINETUNE_OUT", RESULTS / "analyses" / "finetune"))
SIDE, MARGIN, MIN_VOXELS = 128, 8, 30
HP = dict(batch=4, max_epochs=25, min_epochs=3, patience=5, warmup=1, lr_enc=2e-5, lr_head=1e-3, wd=0.01,
          dropout=0.3, shift=8, scale=0.1, offset=0.1, n_inner=4, val_folds=5)
ARMS = ("brats21:grade4:real", "brats21:grade4:perm", "brats21:all_glioma:real", "bsf:grade4:real",
        "brats21+prev:grade4:real")
N_REPEATS, N_FOLDS = 5, 5


def slug(arm: str) -> str:
    return arm.replace(":", "_").replace("+", "p")


# ---------------------------------------------------------------- cache (CPU, no labels)
def _split(scan_id):
    pid, tp = scan_id.split("_Timepoint_")
    return pid, "Timepoint_" + tp


def _load_norm(scan_id):
    from prism.features.deep import CHANNELS
    p = mu_scan_paths(*_split(scan_id))
    import nibabel as nib
    img = np.stack([np.asarray(nib.load(str(p[c])).dataobj, dtype=np.float32) for c in CHANNELS])
    brain = (img != 0).any(0)
    for c in range(len(img)):
        v = img[c][brain]
        img[c] = np.where(brain, (img[c] - v.mean()) / (v.std() + 1e-6), 0)
    return img, np.rint(np.asarray(nib.load(str(p["mask"])).dataobj)).astype(np.uint8)


def _crop(a, start, side):
    """a (C, X, Y, Z) -> (C, side, side, side), zeros outside the volume."""
    out = np.zeros((a.shape[0], side, side, side), a.dtype)
    src = [slice(max(s, 0), min(s + side, n)) for s, n in zip(start, a.shape[1:])]
    dst = [slice(sl.start - s, sl.stop - s) for sl, s in zip(src, start)]
    out[(slice(None), *dst)] = a[(slice(None), *src)]
    return out


def _resize(a, mode):
    import torch
    import torch.nn.functional as F
    if a.shape[-1] == SIDE:
        return a
    t = torch.from_numpy(np.ascontiguousarray(a, dtype=np.float32))[None]
    kw = {"align_corners": False} if mode == "trilinear" else {}
    return F.interpolate(t, size=(SIDE,) * 3, mode=mode, **kw)[0].numpy()


def cache_scan(job):
    scan_id, prev_id = job
    import torch
    torch.set_num_threads(1)
    img, mask = _load_norm(scan_id)
    lesion = np.isin(mask, (LABEL_ET, LABEL_NETC, LABEL_SNFH))
    roi = lesion | (mask == LABEL_RC)
    w = np.where(roi) if roi.any() else np.where((img != 0).any(0))
    lo, hi = np.array([a.min() for a in w]), np.array([a.max() + 1 for a in w])
    side = int(max(SIDE, (hi - lo).max() + 2 * MARGIN))
    start = np.round((lo + hi) / 2 - side / 2).astype(int)
    pool = lesion if lesion.sum() > MIN_VOXELS else roi if roi.sum() > MIN_VOXELS else np.ones_like(lesion)
    x = _resize(_crop(img, start, side), "trilinear")
    m = _resize(_crop(pool[None].astype(np.float32), start, side), "area")
    np.save(CACHE / f"{scan_id}.npy", np.concatenate([x, m]).astype(np.float16))
    if prev_id is not None:
        pimg, _ = _load_norm(prev_id)
        np.save(CACHE / f"prev_{scan_id}.npy", _resize(_crop(pimg, start, side), "trilinear").astype(np.float16))
    return {"scan_id": scan_id, "prev_scan_id": prev_id, "side": side, "start": start.tolist(),
            "pool_voxels": int(pool.sum()), "pool": "lesion" if pool is lesion else "roi" if pool is roi else "all"}


def previous_scans(scan_ids):
    """Latest complete earlier timepoint of the same patient (MU index), else None."""
    from prism.data.mu import load_index
    idx = load_index()
    idx = idx[idx.complete.astype(bool)].assign(tp=lambda d: d.timepoint.str.split("_").str[1].astype(int))
    out = {}
    for s in scan_ids:
        pid, tp = _split(s)
        prior = idx[(idx.patient_id == pid) & (idx.tp < int(tp.split("_")[1]))]
        out[s] = prior.sort_values("tp").scan_id.iloc[-1] if len(prior) else None
    return out


def build_cache(workers, limit=None):
    from prism.data.mu import load_cohort
    CACHE.mkdir(parents=True, exist_ok=True)
    ids = load_cohort("all_glioma").scan_id.tolist()[:limit]
    prev = previous_scans(ids)
    todo = [(s, prev[s]) for s in ids if not (CACHE / f"{s}.npy").exists()
            or (prev[s] is not None and not (CACHE / f"prev_{s}.npy").exists())]
    print(f"cache: {len(ids)} scans, {len(todo)} to build, {sum(v is not None for v in prev.values())} with a prior scan")
    t = time.time()
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(cache_scan, todo))
    meta_path = CACHE / "meta.csv"
    meta = pd.concat([pd.read_csv(meta_path), pd.DataFrame(rows)]) if meta_path.exists() else pd.DataFrame(rows)
    meta.drop_duplicates("scan_id", keep="last").to_csv(meta_path, index=False)
    print(f"cache built in {time.time() - t:.0f}s; resampled (side>128): {(meta.side > SIDE).sum()}; "
          f"pool: {meta.pool.value_counts().to_dict()}")


# ---------------------------------------------------------------- jobs (splits are label-dependent only through
# stratification of the early-stopping split and the training labels themselves; nothing here scores a model)
def arm_parts(arm):
    enc, pop, lab = arm.split(":")
    return enc.split("+")[0], "+prev" in enc, pop, lab


def load_population(pop):
    from prism.data.mu import load_cohort
    from prism.models.folds import load_folds
    return load_cohort(pop), load_folds()


def fold_ids(cohort, folds, r):
    return cohort.scan_id.map(folds[folds.repeat == r].set_index("scan_id").fold).to_numpy()


def outer_split(cohort, folds, r, k, labels):
    f = fold_ids(cohort, folds, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    return tr[~np.isnan(labels[tr])], te


def inner_folds(cohort, tr_ver, n_inner):
    from sklearn.model_selection import GroupKFold
    return list(GroupKFold(n_splits=n_inner).split(tr_ver, groups=cohort.patient_id.iloc[tr_ver]))


def train_labels(cohort, lab, r, k, tr_ver):
    """Labels used for training: real, or permuted among the outer-training verified scans (control)."""
    y = cohort[f"label_{H}"].to_numpy(float).copy()
    if lab == "perm":
        y[tr_ver] = np.random.default_rng(1000 * r + k).permutation(y[tr_ver])
    elif lab == "shuf":  # runner test only (step 1): labels permuted over the whole cohort, never evaluated
        known = np.where(~np.isnan(y))[0]
        y[known] = np.random.default_rng(999).permutation(y[known])
    return y


def job_spec(arm, r, k, j, cohort, folds):
    """Cohort row indices: fit / val (training), holdout (inner fold j) and test (outer fold); training labels."""
    from sklearn.model_selection import StratifiedGroupKFold
    _, _, _, lab = arm_parts(arm)
    tr_ver, te = outer_split(cohort, folds, r, k, cohort[f"label_{H}"].to_numpy(float))
    if lab == "shuf":
        tr_ver = tr_ver[np.random.default_rng(999).permutation(len(tr_ver))[:len(tr_ver) // 4]]  # quick test
    y = train_labels(cohort, lab, r, k, tr_ver)
    a, b = inner_folds(cohort, tr_ver, HP["n_inner"])[j]
    pool, hold = tr_ver[a], tr_ver[b]
    seed = job_seed(r, k, j)
    sgkf = StratifiedGroupKFold(n_splits=HP["val_folds"], shuffle=True, random_state=seed)
    fit_i, val_i = next(sgkf.split(pool, y[pool].astype(int), cohort.patient_id.iloc[pool]))
    return dict(fit=pool[fit_i], val=pool[val_i], hold=hold, test=te, y=y, seed=seed)


def job_seed(r, k, j):
    return 10000 + 100 * r + 10 * k + j


def all_jobs(arms, limit=None):
    """Jobs in run order (arm, repeat, outer fold, inner fold); `limit` = first N per arm (runner test)."""
    jobs = [[(a, r, k, j) for r in range(N_REPEATS) for k in range(N_FOLDS) for j in range(HP["n_inner"])] for a in arms]
    return [jb for js in jobs for jb in js[:limit]]


def job_path(arm, r, k, j):
    return OUT / "jobs" / slug(arm) / f"r{r}_k{k}_j{j}.npz"


# ---------------------------------------------------------------- network (GPU)
def _torch():
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    return torch, nn, F


def make_net(encoder, change, dropout):
    torch, nn, F = _torch()
    from prism.features.deep import load_encoder

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.vit = load_encoder(encoder, device="cpu").swinViT
            for mod in (self.vit.patch_embed, self.vit.layers1, self.vit.layers2):
                mod.requires_grad_(False)
            dim = 192 + 384 + 768 + 768
            dim = 2 * dim + 1 if change else dim
            self.head = nn.Sequential(nn.LayerNorm(dim), nn.Dropout(dropout), nn.Linear(dim, 1))

        def features(self, x, m):
            v = self.vit
            with torch.no_grad():
                x2 = v.layers2[0](v.layers1[0](v.pos_drop(v.patch_embed(x)).contiguous()).contiguous())
            x3 = v.layers3[0](x2.contiguous())
            x4 = v.layers4[0](x3.contiguous())
            outs = [v.proj_out(t, True) for t in (x2, x3, x4)]
            pooled = []
            for h in outs:
                w = F.adaptive_avg_pool3d(m, h.shape[2:])
                pooled.append((h * w).sum((2, 3, 4)) / w.sum((2, 3, 4)).clamp(min=1e-6))
            return torch.cat(pooled + [outs[-1].mean((2, 3, 4))], 1)

        def forward(self, x, m, prev=None, has_prev=None):
            f = self.features(x, m)
            if change:
                fp = self.features(prev, m)
                hp = has_prev[:, None].to(f.dtype)
                f = torch.cat([f, (f - fp) * hp, hp], 1)
            return self.head(f.float()).squeeze(1)

        def train(self, mode=True):
            super().train(mode)
            for mod in (self.vit.patch_embed, self.vit.layers1, self.vit.layers2):
                mod.eval()
            return self

    return Net()


class GPUData:
    """All cached crops of a population on the GPU (float16): X (n,4,S,S,S), M (n,1,S,S,S), optional P (prev)."""

    def __init__(self, scan_ids, device, change=False):
        torch, _, _ = _torch()
        arr = [np.load(CACHE / f"{s}.npy", mmap_mode="r") for s in scan_ids]
        self.X = torch.stack([torch.from_numpy(np.ascontiguousarray(a[:4])) for a in arr]).to(device)
        self.M = torch.stack([torch.from_numpy(np.ascontiguousarray(a[4:5])) for a in arr]).to(device)
        self.P = self.has = None
        if change:
            paths = [CACHE / f"prev_{s}.npy" for s in scan_ids]
            self.has = torch.tensor([p.exists() for p in paths], device=device)
            self.P = torch.stack([torch.from_numpy(np.load(p)) if p.exists() else self.X[i].cpu()
                                  for i, p in enumerate(paths)]).to(device)


def _shift(t, s, p):
    torch, _, F = _torch()
    t = F.pad(t, (p,) * 6)
    n = t.shape[-1] - 2 * p
    return t[..., p - s[0]:p - s[0] + n, p - s[1]:p - s[1] + n, p - s[2]:p - s[2] + n]


def augment(x, m, prev, g):
    """Per-sample flips, translation, intensity scale/shift (random numbers from the CPU generator g)."""
    torch, _, _ = _torch()
    xs, ms, ps = [], [], []
    for i in range(len(x)):
        fl = [d for d in (1, 2, 3) if torch.rand(1, generator=g).item() < 0.5]
        s = torch.randint(-HP["shift"], HP["shift"] + 1, (3,), generator=g).tolist()
        sc = (1 + HP["scale"] * (2 * torch.rand(4, 1, 1, 1, generator=g) - 1)).to(x.device)
        of = (HP["offset"] * (2 * torch.rand(4, 1, 1, 1, generator=g) - 1)).to(x.device)
        def tr(t, fl=fl, s=s):
            return _shift(t.flip(fl) if fl else t, s, HP["shift"])
        xi = tr(x[i])
        xs.append(torch.where((xi != 0).any(0, keepdim=True), xi * sc + of, xi))
        ms.append(tr(m[i]))
        if prev is not None:
            pi = tr(prev[i])
            ps.append(torch.where((pi != 0).any(0, keepdim=True), pi * sc + of, pi))
    return torch.stack(xs), torch.stack(ms), (torch.stack(ps) if prev is not None else None)


def _batch(data, rows):
    torch, _, _ = _torch()
    ix = torch.as_tensor(rows, device=data.X.device)
    prev = data.P[ix].float() if data.P is not None else None
    has = data.has[ix] if data.has is not None else None
    return data.X[ix].float(), data.M[ix].float(), prev, has


def predict(net, data, rows, tta=True):
    torch, _, _ = _torch()
    from prism.features.deep import FLIPS
    net.eval()
    out = []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        for r in rows:
            x, m, p, h = _batch(data, [r])
            fl = FLIPS if tta else [()]
            acc = []
            for c in range(0, len(fl), 4):  # 4 flips per forward pass (memory)
                fc = fl[c:c + 4]
                xs = torch.cat([x.flip(f) if f else x for f in fc])
                ms = torch.cat([m.flip(f) if f else m for f in fc])
                ps = torch.cat([p.flip(f) if f else p for f in fc]) if p is not None else None
                hs = h.repeat(len(fc)) if h is not None else None
                acc.append(net(xs, ms, ps, hs).float())
            out.append(float(torch.cat(acc).mean()))
    return np.array(out)


def fine_tune(encoder, change, data, fit, val, y, seed, max_epochs=None, log=print):
    """Train on rows `fit` (labels y[fit]), early-stop on BCE of rows `val`; returns the best network and a history."""
    torch, nn, F = _torch()
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed)
    rng = np.random.default_rng(seed)
    max_epochs = max_epochs or HP["max_epochs"]
    net = make_net(encoder, change, HP["dropout"])
    torch.manual_seed(seed)  # load_encoder seeds 0: re-seed, then draw the head init and dropout from the job seed
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
    best, best_state, bad, hist = np.inf, None, 0, []
    for ep in range(max_epochs):
        net.train()
        t0, losses = time.time(), []
        order = fit[rng.permutation(len(fit))]
        for b in range(0, len(order), HP["batch"]):
            rows = order[b:b + HP["batch"]]
            x, m, p, h = _batch(data, rows)
            x, m, p = augment(x, m, p, g)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logit = net(x, m, p, h)
            loss = F.binary_cross_entropy_with_logits(logit.float(), torch.tensor(y[rows], dtype=torch.float32, device="cuda"))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
            losses.append(loss.item())
        vl = float(F.binary_cross_entropy_with_logits(torch.tensor(predict(net, data, val, tta=False), dtype=torch.float32), yv))
        hist.append({"epoch": ep, "train_loss": float(np.mean(losses)), "val_loss": vl, "sec": time.time() - t0})
        log(f"    ep {ep} train {hist[-1]['train_loss']:.4f} val {vl:.4f} {hist[-1]['sec']:.1f}s")
        if vl < best - 1e-4:
            best, bad = vl, 0
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()
                          if not k.startswith(("vit.patch_embed", "vit.layers1", "vit.layers2"))}
        else:
            bad += 1
            if ep + 1 >= HP["min_epochs"] and bad >= HP["patience"]:
                break
    net.load_state_dict(best_state, strict=False)
    return net, hist


def setup_torch():
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch, _, _ = _torch()
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.use_deterministic_algorithms(True, warn_only=True)
    warnings.filterwarnings("ignore")
    return torch


def run_job(arm, r, k, j, cohort, folds, data, log):
    torch = setup_torch()
    encoder, change, _, _ = arm_parts(arm)
    s = job_spec(arm, r, k, j, cohort, folds)
    t = time.time()
    torch.cuda.reset_peak_memory_stats()
    net, hist = fine_tune(encoder, change, data, s["fit"], s["val"], s["y"], s["seed"], log=log)
    rows = np.concatenate([s["hold"], s["test"]])
    logit = predict(net, data, rows)
    best = int(np.argmin([h["val_loss"] for h in hist]))
    path = job_path(arm, r, k, j)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.npz")
    np.savez(tmp, rows=rows, is_test=np.r_[np.zeros(len(s["hold"]), bool), np.ones(len(s["test"]), bool)], logit=logit,
             scan_id=cohort.scan_id.to_numpy()[rows].astype(str),
             info=json.dumps({"best_epoch": best, "epochs": len(hist), "hist": hist, "sec": time.time() - t,
                              "peak_gb": torch.cuda.max_memory_allocated() / 1e9, "n_fit": len(s["fit"]),
                              "n_val": len(s["val"]), "seed": s["seed"]}))
    os.replace(tmp, path)
    return time.time() - t


# ---------------------------------------------------------------- parallel runner with resume
def worker(arms, tag, limit=None):
    """Claim jobs in order (atomic lock files), run, write results. Several workers may share a GPU."""
    lock_dir = OUT / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    loaded = {}
    log = lambda m: print(f"[{tag}] {m}", flush=True)
    for arm, r, k, j in all_jobs(arms, limit):
        if job_path(arm, r, k, j).exists():
            continue
        lock = lock_dir / f"{slug(arm)}_r{r}_k{k}_j{j}.lock"
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            continue
        _, change, pop, _ = arm_parts(arm)
        if (pop, change) not in loaded:
            loaded.clear()
            torch = setup_torch()
            torch.cuda.empty_cache()
            cohort, folds = load_population(pop)
            loaded[(pop, change)] = (cohort, folds, GPUData(cohort.scan_id, "cuda", change))
        cohort, folds, data = loaded[(pop, change)]
        log(f"{arm} r{r} k{k} j{j} start")
        sec = run_job(arm, r, k, j, cohort, folds, data, lambda m: None)
        log(f"{arm} r{r} k{k} j{j} done {sec / 60:.1f} min")
        lock.unlink(missing_ok=True)


def launch(arms, gpus, per_gpu, limit=None):
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    for lock in (OUT / "locks").glob("*.lock") if (OUT / "locks").exists() else []:
        lock.unlink()  # stale claims from an interrupted run; finished jobs are kept
    todo = [jb for jb in all_jobs(arms, limit) if not job_path(*jb).exists()]
    print(f"{len(todo)} of {len(all_jobs(arms, limit))} jobs to run on GPUs {gpus} x {per_gpu}", flush=True)
    procs = []
    for g in gpus:
        for s in range(per_gpu):
            env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(g), "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2",
                   "OPENBLAS_NUM_THREADS": "2", "CUBLAS_WORKSPACE_CONFIG": ":4096:8"}
            logf = open(OUT / "logs" / f"worker_gpu{g}_{s}.log", "a")
            procs.append(subprocess.Popen([sys.executable, "-m", "prism.analyses.finetune_deep", "worker", "--arms", *arms,
                                           "--tag", f"gpu{g}.{s}"] + (["--limit", str(limit)] if limit else []), env=env, stdout=logf, stderr=subprocess.STDOUT))
            time.sleep(20)  # stagger GPU data loading
    codes = [p.wait() for p in procs]
    left = [jb for jb in all_jobs(arms, limit) if not job_path(*jb).exists()]
    print(f"workers exited {codes}; {len(left)} jobs left", flush=True)


# ---------------------------------------------------------------- evaluation (CPU)
def collect(arm, cohort):
    """Per repeat: test logits (mean of inner networks) and per outer split the inner OOF logits on T_ver."""
    n = len(cohort)
    test = np.full((N_REPEATS, n), np.nan)
    oof = {}
    info = []
    for r in range(N_REPEATS):
        for k in range(N_FOLDS):
            acc, cnt, o = np.zeros(n), np.zeros(n), np.full(n, np.nan)
            for j in range(HP["n_inner"]):
                z = np.load(job_path(arm, r, k, j))
                assert (cohort.scan_id.to_numpy()[z["rows"]] == z["scan_id"]).all()
                t = z["is_test"]
                acc[z["rows"][t]] += z["logit"][t]
                cnt[z["rows"][t]] += 1
                o[z["rows"][~t]] = z["logit"][~t]
                info.append({"arm": arm, "repeat": r, "fold": k, "inner": j, **{
                    k_: v for k_, v in json.loads(str(z["info"])).items() if k_ != "hist"}})
            te = cnt > 0
            assert (cnt[te] == HP["n_inner"]).all()
            test[r, te] = acc[te] / cnt[te]
            oof[(r, k)] = o
    return test, oof, pd.DataFrame(info)


def stack_predict(cohort, base, score_oof, score_test, tr_ver, te, seed):
    """Core ridge + z-scored fine-tuned score (inner OOF on T_ver for training, cross-fit mean on test)."""
    from sklearn.base import clone
    from prism.experiments import c3_radiomics as c3
    mu, sd = score_oof[tr_ver].mean(), score_oof[tr_ver].std() + 1e-8
    bp = clone(c3.BASE_PRE).fit(base.iloc[tr_ver])
    Xtr = np.hstack([bp.transform(base.iloc[tr_ver]), ((score_oof[tr_ver] - mu) / sd)[:, None]])
    Xte = np.hstack([bp.transform(base.iloc[te]), ((score_test[te] - mu) / sd)[:, None]])
    return c3._ridge(Xtr, cohort, tr_ver, seed).predict_proba(Xte)[:, 1]


def assemble(pop, arms, cohort=None, base=None):
    """OOF prediction matrices (repeats x scans) per reported model. `cohort`/`base` overridable for tests."""
    from prism.experiments import c3_radiomics as c3
    if cohort is None:
        cohort, folds, base, _, _ = c3.load(pop)
    else:
        folds = load_population(pop)[1]
    labels = cohort[f"label_{H}"].to_numpy(float)
    n = len(cohort)
    ref = "core"
    res = {ref: np.zeros((N_REPEATS, n))}
    infos = []
    for r in range(N_REPEATS):
        f = fold_ids(cohort, folds, r)
        for k in range(N_FOLDS):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            res[ref][r, te] = c3.fit_predict(c3.BASELINES[0], cohort, base, {}, {}, tr, te, seed=r)
    for arm in arms:
        test, oof, info = collect(arm, cohort)
        infos.append(info)
        name = arm.split(":")[0] + ("_perm" if arm.endswith("perm") else "")
        res[f"ft_image:{name}"] = 1 / (1 + np.exp(-test))
        res[f"core+ft:{name}"] = np.zeros((N_REPEATS, n))
        for r in range(N_REPEATS):
            for k in range(N_FOLDS):
                tr_ver, te = outer_split(cohort, folds, r, k, labels)
                res[f"core+ft:{name}"][r, te] = stack_predict(cohort, base, oof[(r, k)], test[r], tr_ver, te, seed=r)
    return cohort, res, pd.concat(infos) if infos else pd.DataFrame()


def frozen_reference(pop, cohort):
    p = RESULTS / "analyses" / "deep" / pop / "oof_repeats.csv.gz"
    if not p.exists():
        return {}
    d = pd.read_csv(p).set_index("scan_id").reindex(cohort.scan_id)
    return {"frozen:NESTED_D1": d[[f"NESTED_D1#r{r}" for r in range(N_REPEATS)]].to_numpy().T}


def evaluate(pop, arms, n_boot):
    from prism.models.metrics import evaluate_repeated, point_metrics
    from prism.features.tabular import groups as feature_groups
    out = OUT / pop
    out.mkdir(parents=True, exist_ok=True)
    arms = [a for a in arms if arm_parts(a)[2] == pop and all(job_path(*jb).exists() for jb in all_jobs([a]))]
    cohort, res, info = assemble(pop, arms)
    res.update(frozen_reference(pop, cohort))
    ev = evaluate_repeated(cohort, res, H, "core", n_boot).rename(columns={"d_auc_ipcw_vs_core": "d_auc_ipcw"})
    ev["mde_80"] = 2.8 * (ev.d_auc_ipcw_hi - ev.d_auc_ipcw_lo) / 3.92
    ev.index.name = "model"
    ev.to_csv(out / "results.csv")
    info.to_csv(out / "jobs.csv", index=False)
    pd.concat([pd.DataFrame(o.T, columns=[f"{k}#r{r}" for r in range(len(o))]) for k, o in res.items()], axis=1
              ).assign(scan_id=cohort.scan_id).to_csv(out / "oof_repeats.csv.gz", index=False)
    vols = feature_groups(cohort, legacy_radiomics=False)["volumes"]
    core_logit = np.log(res["core"].mean(0) / (1 - res["core"].mean(0)))
    diag = [{"model": m, "r_log_lesion_cc": float(np.corrcoef(np.log(o.mean(0) / (1 - o.mean(0))), vols.log_lesion_cc)[0, 1]),
             "r_core_logit": float(np.corrcoef(np.log(o.mean(0) / (1 - o.mean(0))), core_logit)[0, 1])}
            for m, o in res.items() if m.startswith("ft_image")]
    pd.DataFrame(diag).to_csv(out / "diagnostics.csv", index=False)
    return ev, info, pd.DataFrame(diag)


# ---------------------------------------------------------------- smoke test (shuffled labels only)
def smoke(n, epochs, encoders):
    """A few scans, labels = a random permutation (never evaluated against real outcomes): memory, speed,
    determinism (two identical runs), full-size step timing."""
    torch = setup_torch()
    from prism.data.mu import load_cohort
    cohort = load_cohort("grade4")
    ids = [s for s in cohort.scan_id if (CACHE / f"{s}.npy").exists()][:n]
    rng = np.random.default_rng(0)
    y = rng.permutation(np.r_[np.ones(n // 2), np.zeros(n - n // 2)])
    rows = np.arange(n)
    fit, val, test = rows[: n - 8], rows[n - 8: n - 4], rows[n - 4:]
    report = {}
    for enc in encoders:
        for change in (False, True):
            data = GPUData(ids, "cuda", change)
            preds, secs = [], []
            for rep in range(2 if not change else 1):
                torch.cuda.reset_peak_memory_stats()
                t = time.time()
                net, hist = fine_tune(enc, change, data, fit, val, y, seed=123, max_epochs=epochs,
                                      log=lambda m: print(m, flush=True))
                p = predict(net, data, test)
                secs.append(time.time() - t)
                preds.append(p)
                key = f"{enc}{'+prev' if change else ''}"
                step = np.mean([h["sec"] for h in hist[1:]] or [hist[0]["sec"]]) / math.ceil(len(fit) / HP["batch"])
                report[key] = {"peak_gb": torch.cuda.max_memory_allocated() / 1e9, "sec_total": secs,
                               "sec_per_step_incl_val": step, "epochs": len(hist), "test_logits": [list(map(float, q)) for q in preds]}
                del net
            if len(preds) == 2:
                report[key]["max_abs_diff_between_runs"] = float(np.abs(preds[0] - preds[1]).max())
            t = time.time()
            report[key]["sec_tta_predict_per_scan"] = None
            net = make_net(enc, change, HP["dropout"]).cuda()
            predict(net, data, test)
            report[key]["sec_tta_predict_per_scan"] = (time.time() - t) / len(test)
            del data, net
            torch.cuda.empty_cache()
    print(json.dumps(report, indent=1))
    (OUT / "smoke").mkdir(parents=True, exist_ok=True)
    (OUT / "smoke" / "smoke.json").write_text(json.dumps(report, indent=1))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism finetune", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["cache", "smoke", "run", "worker", "evaluate"])
    ap.add_argument("--arms", nargs="+", default=list(ARMS[:4]))
    ap.add_argument("--gpus", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--per-gpu", type=int, default=3, help="processes per GPU (use 2 for the +prev arm)")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int, help="cache: first N scans; run/worker: first N jobs per arm (test)")
    ap.add_argument("--tag", default="w")
    ap.add_argument("--n", type=int, default=24, help="smoke: number of scans")
    ap.add_argument("--epochs", type=int, default=3, help="smoke: epochs")
    ap.add_argument("--encoders", nargs="+", default=["brats21"], help="smoke: encoders")
    ap.add_argument("--population", nargs="+", default=["grade4", "all_glioma"])
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    if a.command == "cache":
        build_cache(a.workers, a.limit)
    elif a.command == "smoke":
        smoke(a.n, a.epochs, a.encoders)
    elif a.command == "run":
        launch(a.arms, a.gpus, a.per_gpu, a.limit)
    elif a.command == "worker":
        worker(a.arms, a.tag, a.limit)
    else:
        show = ["auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "d_auc_ipcw", "d_auc_ipcw_lo", "d_auc_ipcw_hi", "mde_80",
                "cal_slope", "oe_ratio", "brier_ipcw"]
        for pop in a.population:
            ev, info, diag = evaluate(pop, a.arms, a.n_boot)
            print(f"== {pop}\n{ev[[c for c in show if c in ev]].round(3).to_string()}\n{diag.round(3).to_string(index=False)}")
            if len(info):
                print(info.groupby("arm")[["best_epoch", "epochs", "sec", "peak_gb"]].mean().round(2).to_string())


if __name__ == "__main__":
    main()
