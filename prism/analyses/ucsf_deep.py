"""UCSF-ALPTDG, Part C: deep networks (docs/results/UCSF_PLAN.md, "Part C", committed 0e7c9fe).

Network, hyperparameters, crop rule, brain z-scoring, augmentation, early stopping, cross-fit design and 8-flip TTA
are those of prism.analyses.finetune_deep / finetune_detection (FINETUNE_DEEP.md, DETECTION_DEEP.md), reused by
import; neither module is changed.

Arms (results: docs/results/UCSF_RESULTS.md, "## Part C"):
    locked_G1, locked_G3  C-locked. MU-trained detection networks applied unchanged to UCSF scan 2. The MU detection
                          runs saved logits only (no weights), so the MU networks are retrained here once on ALL MU
                          grade-4 detection training rows (label_det = 1 or neg_primary) with the MU inner design:
                          GroupKFold(4) by patient, each network early-stopped on a StratifiedGroupKFold(5) 20 %
                          patient split of its other three folds. Ensemble = mean logit of the 4 networks (TTA as MU).
    G1, G4, G3            C-ucsf. Trained on UCSF from the BraTS21 weights. G4 = G1 with permuted labels (validity).
                          G3 = current + (current - scan 1), the MU 8-channel difference network.
    T1                    C-transfer. G1 initialised from the MU-trained G1 network (inner network j <- MU network j).
Training rows (decision, council of 3, recorded before any run): all-glioma scan-2 rows with the primary label
(pos_s2_pm30 vs primary negatives: 48 / 78). Every arm trains on the same rows. Evaluation: grade-4 scan 2 (primary,
29 / 40), WHO GBM scan 2, all-glioma scan 2. Every scan-2 row of the outer test fold is scored.
Cross-fitting: outer 5 folds by patient (one scan-2 row per patient), StratifiedKFold on label (1 / 0 / unlabelled)
x grade 4, seed 20261025 + r; inside, exactly the MU job split (GroupKFold(4), StratifiedGroupKFold(5) early-stop
split seeded with finetune_deep.job_seed(r, k, j)); G4 permutation seed 1000 r + k as MU.

    PYTHONPATH=. .venv/bin/python -m prism.analyses.ucsf_deep cache --workers 10   # CPU, no labels
    ... verify                      # MU preprocessing identity checks (no labels)
    ... smoke                       # timings + equivalence of the fine-tune with finetune_detection.fine_tune
    ... run --per-gpu 3 --repeats 3 # resumable runner on the one visible GPU
    ... evaluate                    # CPU: AUCs, bootstrap, stacking, PDGM sensitivity
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
from pathlib import Path

import numpy as np
import pandas as pd

from prism.analyses import finetune_deep as fd
from prism.analyses import finetune_detection as fdet
from prism.config import LABEL_ET, LABEL_NETC, LABEL_RC, LABEL_SNFH, OUTPUTS, RESULTS

CACHE = fd.CACHE / "ucsf"
SCANS = OUTPUTS / "data" / "ucsf" / "scans.csv"
OUT = Path(os.environ.get("PRISM_UCSF_DEEP_OUT", RESULTS / "analyses" / "ucsf" / "deep"))
HP = fd.HP
N_FOLDS = 5
MAX_REPEATS = 5
SEED = 20261025
PRIMARY_NEG = ("verified_by_later_progression", "no_progression_followed_120")
UCSF_ARMS = {"G1": dict(inp="cur", lab="real", init=None), "G4": dict(inp="cur", lab="perm", init=None),
             "G3": dict(inp="diff", lab="real", init=None), "T1": dict(inp="cur", lab="real", init="MU_G1")}
MU_ARMS = {"MU_G1": dict(inp="cur", src="G1"), "MU_G3": dict(inp="diff", src="G3")}
ARM_ORDER = ("G1", "G4", "G3", "T1")
DIFF_SLOTS = 2


# ---------------------------------------------------------------- preprocessing (identical to finetune_deep)
def load_norm(paths):
    """fd._load_norm for an arbitrary path dict (keys flair, t1c, t1, t2, mask)."""
    import nibabel as nib
    from prism.features.deep import CHANNELS
    img = np.stack([np.asarray(nib.load(str(paths[c])).dataobj, dtype=np.float32) for c in CHANNELS])
    brain = (img != 0).any(0)
    for c in range(len(img)):
        v = img[c][brain]
        img[c] = np.where(brain, (img[c] - v.mean()) / (v.std() + 1e-6), 0)
    return img, np.rint(np.asarray(nib.load(str(paths["mask"])).dataobj)).astype(np.uint8)


def crop_inputs(cur_paths, prev_paths=None):
    """fd.cache_scan's crop rule: returns (cur 5-channel float16 array, prev 4-channel float16 or None, meta)."""
    img, mask = load_norm(cur_paths)
    lesion = np.isin(mask, (LABEL_ET, LABEL_NETC, LABEL_SNFH))
    roi = lesion | (mask == LABEL_RC)
    w = np.where(roi) if roi.any() else np.where((img != 0).any(0))
    lo, hi = np.array([a.min() for a in w]), np.array([a.max() + 1 for a in w])
    side = int(max(fd.SIDE, (hi - lo).max() + 2 * fd.MARGIN))
    start = np.round((lo + hi) / 2 - side / 2).astype(int)
    pool = lesion if lesion.sum() > fd.MIN_VOXELS else roi if roi.sum() > fd.MIN_VOXELS else np.ones_like(lesion)
    x = fd._resize(fd._crop(img, start, side), "trilinear")
    m = fd._resize(fd._crop(pool[None].astype(np.float32), start, side), "area")
    cur = np.concatenate([x, m]).astype(np.float16)
    prev = None
    if prev_paths is not None:
        pimg, _ = load_norm(prev_paths)
        prev = fd._resize(fd._crop(pimg, start, side), "trilinear").astype(np.float16)
    meta = {"side": side, "start": start.tolist(), "pool_voxels": int(pool.sum()),
            "pool": "lesion" if pool is lesion else "roi" if pool is roi else "all"}
    return cur, prev, meta


def _cache_one(sid):
    import torch
    from prism.features.ucsf_imaging import ucsf_paths
    torch.set_num_threads(1)
    scan = f"{sid}_time2"
    cur, prev, meta = crop_inputs(ucsf_paths(sid, 2), ucsf_paths(sid, 1))
    for name, a in ((scan, cur), (f"prev_{scan}", prev)):
        tmp = CACHE / f"{name}.tmp.npy"
        np.save(tmp, a)
        os.replace(tmp, CACHE / f"{name}.npy")
    return {"scan_id": scan, **meta}


def build_cache(workers):
    from prism.features.ucsf_imaging import subjects
    CACHE.mkdir(parents=True, exist_ok=True)
    sids = subjects()
    todo = [s for s in sids if not (CACHE / f"{s}_time2.npy").exists() or not (CACHE / f"prev_{s}_time2.npy").exists()]
    print(f"ucsf cache: {len(sids)} patients (scan 2 + scan 1 at the scan-2 box), {len(todo)} to build", flush=True)
    t = time.time()
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_cache_one, todo))
    mp = CACHE / "meta.csv"
    meta = pd.concat([pd.read_csv(mp), pd.DataFrame(rows)]) if mp.exists() and rows else pd.DataFrame(rows) if rows \
        else pd.read_csv(mp)
    meta.drop_duplicates("scan_id", keep="last").to_csv(mp, index=False)
    print(f"built in {time.time() - t:.0f}s; resampled (side>128): {(meta.side > fd.SIDE).sum()}; "
          f"pool: {meta.pool.value_counts().to_dict()}", flush=True)


def verify(n=3):
    """Run this module's preprocessing on MU scans and compare with the MU caches (must be bit-identical)."""
    from prism.config import mu_scan_paths
    d = fdet.load_detection()
    d = d[d.prev_scan_id.notna()]
    d = d[[(fd.CACHE / f"{s}.npy").exists() and fdet.prev_path(s, p).exists() for s, p in zip(d.scan_id, d.prev_scan_id)]]
    out = []
    for s, p in zip(d.scan_id.iloc[:n], d.prev_scan_id.iloc[:n]):
        cur, prev, meta = crop_inputs(mu_scan_paths(*fd._split(s)), mu_scan_paths(*fd._split(p)))
        ref_c, ref_p = np.load(fd.CACHE / f"{s}.npy"), np.load(fdet.prev_path(s, p))
        out.append({"cur_shape": list(cur.shape), "cur_max_abs_diff": float(np.abs(cur.astype(np.float32) - ref_c).max()),
                    "cur_identical": bool(np.array_equal(cur, ref_c)),
                    "prev_identical": bool(np.array_equal(prev, ref_p)), "side": meta["side"]})
    # UCSF: the cache matches a fresh recomputation, and the scan geometry / channels are as MU
    import nibabel as nib
    from prism.features.ucsf_imaging import subjects, ucsf_paths
    sid = subjects()[0]
    cur, prev, _ = crop_inputs(ucsf_paths(sid, 2), ucsf_paths(sid, 1))
    img = nib.load(str(ucsf_paths(sid, 2)["flair"]))
    ucsf = {"ucsf_cache_identical": bool(np.array_equal(cur, np.load(CACHE / f"{sid}_time2.npy"))
                                         and np.array_equal(prev, np.load(CACHE / f"prev_{sid}_time2.npy"))),
            "ucsf_shape": list(img.shape), "ucsf_zooms": [float(z) for z in img.header.get_zooms()],
            "ucsf_brain_mean_sd_per_channel": [[float(cur[c][cur[c] != 0].astype(np.float32).mean()), float(cur[c][cur[c] != 0].astype(np.float32).std())]
                                               for c in range(4)]}
    rep = {"mu": out, "ucsf": ucsf}
    print(json.dumps(rep, indent=1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "verify_preprocessing.json").write_text(json.dumps(rep, indent=1))
    assert all(o["cur_identical"] and o["prev_identical"] for o in out) and ucsf["ucsf_cache_identical"]


# ---------------------------------------------------------------- UCSF population, folds and data
class UPop:
    """All UCSF scan-2 rows (one per patient). y = training label (pos_s2_pm30 vs primary negatives, NaN otherwise)."""

    def __init__(self):
        d = pd.read_csv(SCANS)
        d = d[d.timepoint == 2].sort_values("scan_id").reset_index(drop=True)
        excl = d.label_excluded_prior_progression.fillna(False).astype(bool)
        pos = d.pos_s2_pm30.fillna(0).astype(bool) & ~excl
        neg = d.neg_class.isin(PRIMARY_NEG) & ~excl & ~pos
        self.frame = d
        self.scan_id = d.scan_id.to_numpy().astype(str)
        self.patient_id = d.subject_id.astype(str)
        assert self.patient_id.is_unique
        self.y = np.where(pos, 1.0, np.where(neg, 0.0, np.nan))
        self.folds = self._folds()

    def _folds(self):
        from sklearn.model_selection import StratifiedKFold
        lab = np.where(np.isnan(self.y), 2, self.y).astype(int)
        strata = lab * 2 + self.frame.grade4.astype(int).to_numpy()
        f = np.zeros((len(self.y), MAX_REPEATS), int)
        for r in range(MAX_REPEATS):
            for k, (_, te) in enumerate(StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED + r).split(strata, strata)):
                f[te, r] = k
        return f


class UData:
    """UCSF scan-2 crops on the GPU: X (n,4,..), M (n,1,..), P = scan-1 crop at the scan-2 box, has = 1."""

    def __init__(self, pop, device, need_prev=True):
        import torch
        arr = [np.load(CACHE / f"{s}.npy", mmap_mode="r") for s in pop.scan_id]
        self.X = torch.stack([torch.from_numpy(np.ascontiguousarray(a[:4])) for a in arr]).to(device)
        self.M = torch.stack([torch.from_numpy(np.ascontiguousarray(a[4:5])) for a in arr]).to(device)
        self.P = self.has = None
        if need_prev:
            self.P = torch.stack([torch.from_numpy(np.load(CACHE / f"prev_{s}.npy")) for s in pop.scan_id]).to(device)
            self.has = torch.ones(len(pop.scan_id), dtype=torch.bool, device=device)


# ---------------------------------------------------------------- fine-tune (fdet.fine_tune + optional init state)
def fine_tune(inp, data, fit, val, y, seed, init_state=None, max_epochs=None, log=print):
    """finetune_detection.fine_tune, line for line, with an optional starting state for stages 3-4 + head (transfer).
    With init_state=None it is identical to finetune_detection.fine_tune (checked in `smoke`)."""
    torch, nn, F = fd._torch()
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed)
    rng = np.random.default_rng(seed)
    max_epochs = max_epochs or HP["max_epochs"]
    net = fdet.make_net(inp, HP["dropout"])
    torch.manual_seed(seed)
    for mod in net.head:
        if hasattr(mod, "reset_parameters"):
            mod.reset_parameters()
    if init_state is not None:
        missing, unexpected = net.load_state_dict(init_state, strict=False)
        assert not unexpected and all(k.startswith(("vit.patch_embed", "vit.layers1", "vit.layers2")) for k in missing)
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
    return net, hist, best_state


# ---------------------------------------------------------------- jobs
def split_spec(folds_r, k, j, y_all, patient_id, lab, r):
    """MU job split (fdet.job_spec) on given outer folds: tr = labelled outer-training rows; GroupKFold(4) inner;
    StratifiedGroupKFold(5) early-stopping split seeded with fd.job_seed(r, k, j)."""
    from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
    tr, te = np.where(folds_r != k)[0], np.where(folds_r == k)[0]
    tr = tr[~np.isnan(y_all[tr])]
    y = y_all.copy()
    if lab == "perm":
        y[tr] = np.random.default_rng(1000 * r + k).permutation(y[tr])
    a, b = list(GroupKFold(n_splits=HP["n_inner"]).split(tr, groups=patient_id.iloc[tr]))[j]
    pool, hold = tr[a], tr[b]
    seed = fd.job_seed(r, k, j)
    sgkf = StratifiedGroupKFold(n_splits=HP["val_folds"], shuffle=True, random_state=seed)
    fit_i, val_i = next(sgkf.split(pool, y[pool].astype(int), patient_id.iloc[pool]))
    return dict(fit=pool[fit_i], val=pool[val_i], hold=hold, test=te, y=y, seed=seed)


def mu_net_path(arm, j):
    return OUT / "mu_full" / arm / f"net_j{j}.pt"


def mu_job_path(arm, j):
    return OUT / "mu_full" / arm / f"j{j}.npz"


def job_path(arm, r, k, j):
    return OUT / "jobs" / arm / f"r{r}_k{k}_j{j}.npz"


def locked_path(arm):
    return OUT / "locked" / f"{arm}.npz"


def all_jobs(repeats):
    """Run order: MU G1 nets, locked G1, UCSF repeat 0 (G1, G4, G3, T1), MU G3 nets, locked G3, repeats 1.."""
    js = [("mu", "MU_G1", j) for j in range(HP["n_inner"])] + [("locked", "MU_G1")]
    for r in range(repeats):
        js += [("ucsf", a, r, k, j) for a in ARM_ORDER for k in range(N_FOLDS) for j in range(HP["n_inner"])]
        if r == 0:
            js += [("mu", "MU_G3", j) for j in range(HP["n_inner"])] + [("locked", "MU_G3")]
    return js


def out_path(job):
    if job[0] == "mu":
        return mu_job_path(job[1], job[2])
    if job[0] == "locked":
        return locked_path(job[1])
    return job_path(*job[1:])


def deps_ok(job):
    if job[0] == "locked":
        return all(mu_net_path(job[1], j).exists() for j in range(HP["n_inner"]))
    if job[0] == "ucsf" and UCSF_ARMS[job[1]]["init"]:
        return mu_net_path(UCSF_ARMS[job[1]]["init"], job[4]).exists()
    return True


def _save(path, **kw):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.npz")
    np.savez(tmp, **kw)
    os.replace(tmp, path)


def run_mu(arm, j, pop, data, log):
    """One MU 'full' network: all labelled MU grade-4 detection rows, inner fold j held out (MU OOF check)."""
    torch = fd.setup_torch()
    from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
    tr = np.where(~np.isnan(pop.y))[0]
    a, b = list(GroupKFold(n_splits=HP["n_inner"]).split(tr, groups=pop.patient_id.iloc[tr]))[j]
    pool, hold = tr[a], tr[b]
    seed = SEED + j
    fit_i, val_i = next(StratifiedGroupKFold(n_splits=HP["val_folds"], shuffle=True, random_state=seed).split(
        pool, pop.y[pool].astype(int), pop.patient_id.iloc[pool]))
    fit, val = pool[fit_i], pool[val_i]
    pid = pop.patient_id.to_numpy()
    assert not (set(pid[fit]) & set(pid[val])) and not (set(pid[pool]) & set(pid[hold]))
    t = time.time()
    torch.cuda.reset_peak_memory_stats()
    net, hist, state = fine_tune(MU_ARMS[arm]["inp"], data, fit, val, pop.y, seed, log=log)
    logit = fd.predict(net, data, hold)
    p = mu_net_path(arm, j)
    p.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state, p.with_suffix(".tmp"))
    os.replace(p.with_suffix(".tmp"), p)
    _save(mu_job_path(arm, j), rows=hold, logit=logit, scan_id=pop.scan_id[hold],
          info=json.dumps(_info(hist, t, torch, fit, val, seed)))
    return time.time() - t


def _info(hist, t, torch, fit, val, seed):
    return {"best_epoch": int(np.argmin([h["val_loss"] for h in hist])), "epochs": len(hist), "hist": hist,
            "sec": time.time() - t, "peak_gb": torch.cuda.max_memory_allocated() / 1e9, "n_fit": len(fit),
            "n_val": len(val), "seed": seed}


def run_locked(arm, upop, data, log):
    torch = fd.setup_torch()
    t = time.time()
    logits = []
    for j in range(HP["n_inner"]):
        net = fdet.make_net(MU_ARMS[arm]["inp"], HP["dropout"])
        missing, unexpected = net.load_state_dict(torch.load(mu_net_path(arm, j)), strict=False)
        assert not unexpected
        logits.append(fd.predict(net.cuda(), data, np.arange(len(upop.scan_id))))
        del net
    _save(locked_path(arm), logit=np.array(logits), scan_id=upop.scan_id, info=json.dumps({"sec": time.time() - t}))
    return time.time() - t


def run_ucsf(arm, r, k, j, upop, data, log):
    torch = fd.setup_torch()
    a = UCSF_ARMS[arm]
    s = split_spec(upop.folds[:, r], k, j, upop.y, upop.patient_id, a["lab"], r)
    pid = upop.patient_id.to_numpy()
    parts = [set(pid[s[x]]) for x in ("fit", "val", "hold", "test")]
    assert all(not (parts[p] & parts[q]) for p in range(4) for q in range(p + 1, 4)), "patient overlap"
    init = torch.load(mu_net_path(a["init"], j)) if a["init"] else None
    t = time.time()
    torch.cuda.reset_peak_memory_stats()
    net, hist, _ = fine_tune(a["inp"], data, s["fit"], s["val"], s["y"], s["seed"], init_state=init, log=log)
    rows = np.concatenate([s["hold"], s["test"]])
    logit = fd.predict(net, data, rows)
    _save(job_path(arm, r, k, j), rows=rows, is_test=np.r_[np.zeros(len(s["hold"]), bool), np.ones(len(s["test"]), bool)],
          logit=logit, scan_id=upop.scan_id[rows], info=json.dumps(_info(hist, t, torch, s["fit"], s["val"], s["seed"])))
    return time.time() - t


def worker(repeats, tag):
    lock_dir = OUT / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    log = lambda m: print(f"[{tag}] {time.strftime('%H:%M:%S')} {m}", flush=True)
    loaded = {}
    while True:
        did, waiting = False, False
        for job in all_jobs(repeats):
            if out_path(job).exists():
                continue
            if not deps_ok(job):
                waiting = True
                continue
            is_diff = (MU_ARMS if job[0] in ("mu", "locked") else UCSF_ARMS)[job[1]]["inp"] == "diff"
            slot = None
            if is_diff:  # memory: at most DIFF_SLOTS difference-input processes on the GPU at once
                for i in range(DIFF_SLOTS):
                    try:
                        os.close(os.open(lock_dir / f"diffslot_{i}.slot", os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                        slot = lock_dir / f"diffslot_{i}.slot"
                        break
                    except FileExistsError:
                        pass
                if slot is None:
                    waiting = True
                    continue
            lock = lock_dir / ("_".join(map(str, job)) + ".lock")
            try:
                os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            except FileExistsError:
                if slot:
                    slot.unlink(missing_ok=True)
                continue
            if job[0] == "mu":
                key = ("mu", MU_ARMS[job[1]]["inp"] != "cur")
            elif job[0] == "locked":
                key = ("ucsf", MU_ARMS[job[1]]["inp"] != "cur")
            else:
                key = ("ucsf", UCSF_ARMS[job[1]]["inp"] != "cur")
            if key not in loaded:
                import gc
                loaded.clear()
                pop = data = None  # drop the previous GPU dataset before loading the next one
                gc.collect()
                torch = fd.setup_torch()
                torch.cuda.empty_cache()
                if job[0] == "mu":
                    pop = fdet.population(MU_ARMS[job[1]]["src"])
                    loaded[key] = (pop, fdet.DetData(pop, "cuda", key[1]))
                else:
                    pop = UPop()
                    loaded[key] = (pop, UData(pop, "cuda", key[1]))
            pop, data = loaded[key]
            log(f"{job} start")
            try:
                fn = {"mu": run_mu, "locked": run_locked, "ucsf": run_ucsf}[job[0]]
                sec = fn(*job[1:], pop, data, lambda m: None)
            except Exception as e:
                log(f"{job} FAILED {type(e).__name__}: {str(e)[:300]}")
                lock.unlink(missing_ok=True)
                if slot:
                    slot.unlink(missing_ok=True)
                if "out of memory" not in str(e).lower():
                    raise
                import gc
                gc.collect()
                fd._torch()[0].cuda.empty_cache()
                time.sleep(60)  # deterministic job: retried later
                did = True
                break
            log(f"{job} done {sec / 60:.1f} min")
            lock.unlink(missing_ok=True)
            if slot:
                slot.unlink(missing_ok=True)
            did = True
            break  # rescan from the top (priority order, dependencies)
        if not did:
            if waiting:
                time.sleep(30)
                continue
            return


def launch(repeats, per_gpu):
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    for lock in (OUT / "locks").glob("*.lock") if (OUT / "locks").exists() else []:
        lock.unlink()
    todo = [j for j in all_jobs(repeats) if not out_path(j).exists()]
    print(f"{time.strftime('%H:%M:%S')} {len(todo)} of {len(all_jobs(repeats))} jobs to run x {per_gpu} processes", flush=True)
    procs = []
    for s in range(per_gpu):
        env = {**os.environ, "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2",
               "CUBLAS_WORKSPACE_CONFIG": ":4096:8", "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}
        logf = open(OUT / "logs" / f"worker_{s}.log", "a")
        procs.append(subprocess.Popen([sys.executable, "-m", "prism.analyses.ucsf_deep", "worker", "--repeats",
                                       str(repeats), "--tag", f"w{s}"], env=env, stdout=logf, stderr=subprocess.STDOUT))
        time.sleep(20)
    codes = [p.wait() for p in procs]
    left = [j for j in all_jobs(repeats) if not out_path(j).exists()]
    print(f"{time.strftime('%H:%M:%S')} workers exited {codes}; {len(left)} jobs left", flush=True)


# ---------------------------------------------------------------- smoke (shuffled labels only)
def smoke(n=24, epochs=3):
    """Timing / memory on UCSF crops, and fine_tune(init_state=None) == fdet.fine_tune (bit-identical logits).
    Labels are a random permutation, never evaluated."""
    torch = fd.setup_torch()
    upop = UPop()
    ids = np.arange(n)

    class Sub:
        pass
    sub = Sub()
    sub.scan_id = upop.scan_id[ids]
    data = UData(sub, "cuda", True)
    y = np.random.default_rng(0).permutation(np.r_[np.ones(n // 2), np.zeros(n - n // 2)])
    rows = np.arange(n)
    fit, val, test = rows[: n - 8], rows[n - 8: n - 4], rows[n - 4:]
    rep = {}
    for inp in ("cur", "diff"):
        torch.cuda.reset_peak_memory_stats()
        t = time.time()
        net, hist, _ = fine_tune(inp, data, fit, val, y, 123, max_epochs=epochs, log=lambda m: None)
        a = fd.predict(net, data, test)
        sec = time.time() - t
        del net
        net, _ = fdet.fine_tune(inp, data, fit, val, y, 123, max_epochs=epochs, log=lambda m: None)
        b = fd.predict(net, data, test)
        step = np.mean([h["sec"] for h in hist[1:]]) / math.ceil(len(fit) / HP["batch"])
        t2 = time.time()
        fd.predict(net, data, test)
        rep[inp] = {"max_abs_diff_vs_finetune_detection": float(np.abs(a - b).max()), "sec_total": sec,
                    "sec_per_step": step, "sec_tta_per_scan": (time.time() - t2) / len(test),
                    "peak_gb": torch.cuda.max_memory_allocated() / 1e9}
        del net
        torch.cuda.empty_cache()
    print(json.dumps(rep, indent=1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "smoke.json").write_text(json.dumps(rep, indent=1))


# ---------------------------------------------------------------- evaluation (CPU)
def complete_repeats(arm):
    n = 0
    for r in range(MAX_REPEATS):
        if all(job_path(arm, r, k, j).exists() for k in range(N_FOLDS) for j in range(HP["n_inner"])):
            n += 1
        else:
            break
    return n


def collect(arm, upop, R):
    """(R x n) mean test logit of the 4 inner networks; {(r, k): inner-OOF logits}; job info."""
    n = len(upop.scan_id)
    T = np.full((R, n), np.nan)
    oof, info = {}, []
    for r in range(R):
        for k in range(N_FOLDS):
            acc, cnt, o = np.zeros(n), np.zeros(n), np.full(n, np.nan)
            for j in range(HP["n_inner"]):
                z = np.load(job_path(arm, r, k, j))
                assert (upop.scan_id[z["rows"]] == z["scan_id"]).all()
                t = z["is_test"]
                acc[z["rows"][t]] += z["logit"][t]
                cnt[z["rows"][t]] += 1
                o[z["rows"][~t]] = z["logit"][~t]
                inf = json.loads(str(z["info"]))
                info.append({"arm": arm, "repeat": r, "fold": k, "inner": j,
                             **{a: b for a, b in inf.items() if a != "hist"},
                             "best_val_loss": min(h["val_loss"] for h in inf["hist"]),
                             "first_val_loss": inf["hist"][0]["val_loss"],
                             "final_train_loss": inf["hist"][-1]["train_loss"]})
            te = cnt > 0
            assert (cnt[te] == HP["n_inner"]).all() and (upop.folds[te, r] == k).all()
            T[r, te] = acc[te] / cnt[te]
            oof[(r, k)] = o
    assert np.isfinite(T).all()
    return T, oof, pd.DataFrame(info)


def boot(y, scores: dict, groups, n_boot=1000, seed=SEED, pairs=()):
    """Mean over repeats of the AUC per score (R x n), patient-cluster bootstrap; paired deltas on the same draws."""
    from sklearn.metrics import roc_auc_score
    auc = lambda S, idx: float(np.mean([roc_auc_score(y[idx], s[idx]) for s in S]))
    allidx = np.arange(len(y))
    point = {k: auc(np.atleast_2d(S), allidx) for k, S in scores.items()}
    rng = np.random.default_rng(seed)
    by = {g: np.where(groups == g)[0] for g in np.unique(groups)}
    pats = np.array(list(by))
    draws = {k: [] for k in scores}
    for _ in range(n_boot):
        idx = np.concatenate([by[p] for p in rng.choice(pats, len(pats))])
        if len(np.unique(y[idx])) < 2:
            continue
        for k, S in scores.items():
            draws[k].append(auc(np.atleast_2d(S), idx))
    draws = {k: np.array(v) for k, v in draws.items()}
    rows = [{"model": k, "auc": point[k], "lo": np.percentile(draws[k], 2.5), "hi": np.percentile(draws[k], 97.5)}
            for k in scores]
    for a, b in pairs:
        dd = draws[a] - draws[b]
        rows.append({"model": f"{a} - {b}", "auc": point[a] - point[b], "lo": np.percentile(dd, 2.5),
                     "hi": np.percentile(dd, 97.5)})
    return rows


def eval_sets(upop):
    """Evaluation rows (scan 2) x label variants. Labels: primary (pos_s2_pm30 vs primary negatives) and the plan's
    sensitivity labels, scored with the networks trained on the primary label."""
    d = upop.frame
    excl = d.label_excluded_prior_progression.fillna(False).astype(bool).to_numpy()
    pops = {"grade4": d.grade4.astype(bool).to_numpy(), "gbm_who": d.gbm_who.astype(bool).to_numpy(),
            "all_glioma": np.ones(len(d), bool)}
    negp = d.neg_class.isin(PRIMARY_NEG).to_numpy() & ~excl
    negv = d.neg_class.eq("verified_by_later_progression").to_numpy() & ~excl
    labels = {"primary": (d.pos_s2_pm30.fillna(0).astype(bool).to_numpy() & ~excl, negp),
              "verified_neg": (d.pos_s2_pm30.fillna(0).astype(bool).to_numpy() & ~excl, negv),
              "pos_s2_between": (d.pos_s2_between.fillna(0).astype(bool).to_numpy() & ~excl, negp),
              "et_increased_REFERENCE": (d.et_increased.fillna(False).astype(bool).to_numpy(),
                                         ~d.et_increased.fillna(False).astype(bool).to_numpy() & d.et_change.notna().to_numpy())}
    pdgm = d.in_pdgm.fillna(False).astype(bool).to_numpy()
    out = {}
    for pn, pm in pops.items():
        for ln, (pos, neg) in labels.items():
            for excl_pdgm in (False, True):
                if excl_pdgm and ln != "primary":
                    continue
                sel = pm & (pos | neg) & (~pdgm if excl_pdgm else True)
                out[(pn, ln, "excl_pdgm" if excl_pdgm else "all")] = (sel, pos)
    return out


def base_designs(upop):
    """Stacking bases with Part B's definitions (prism.analyses.ucsf_internal.design, scan 2, with_prev=True):
    B0 = clinical (age at scan 1, sex, IDH, MGMT; unknown markers -> 0) and B-Tl = the UCSF timeline arm."""
    from prism.analyses import ucsf_internal as ui
    s = ui.scans().set_index("scan_id").loc[upop.scan_id].reset_index()
    assert (s.scan_id.to_numpy() == upop.scan_id).all()
    X = ui.design(s, True)
    return {"B0": X["B0"].reset_index(drop=True), "B-Tl": X["B-Tl"].reset_index(drop=True)}


def stack_scores(upop, base, T, oof, R):
    """Base ridge vs base + z-scored deep score, both trained on the same labelled outer-training rows (all-glioma
    scan 2) with fd.stack_predict / c3 verified ridge; returns (R x n) predictions for base and stack."""
    from sklearn.base import clone
    from prism.experiments import c3_radiomics as c3
    cohort = pd.DataFrame({"patient_id": upop.patient_id.to_numpy(), f"label_{fd.H}": upop.y})
    n = len(upop.y)
    B, S = np.full((R, n), np.nan), np.full((R, n), np.nan)
    for r in range(R):
        for k in range(N_FOLDS):
            f = upop.folds[:, r]
            tr, te = np.where((f != k) & ~np.isnan(upop.y))[0], np.where(f == k)[0]
            o = oof[(r, k)]
            assert np.isfinite(o[tr]).all()
            bp = clone(c3.BASE_PRE).fit(base.iloc[tr])
            B[r, te] = c3._ridge(bp.transform(base.iloc[tr]), cohort, tr, r).predict_proba(bp.transform(base.iloc[te]))[:, 1]
            S[r, te] = fd.stack_predict(cohort, base, o, T[r], tr, te, seed=r)
    return B, S


def evaluate(n_boot):
    upop = UPop()
    out = OUT / "evaluation"
    out.mkdir(parents=True, exist_ok=True)
    groups = upop.patient_id.to_numpy()
    scores, infos = {}, []
    for arm in ("MU_G1", "MU_G3"):
        if locked_path(arm).exists():
            z = np.load(locked_path(arm))
            assert (z["scan_id"] == upop.scan_id).all()
            scores[f"locked_{arm[3:]}"] = z["logit"].mean(0)[None]
    R = min([complete_repeats(a) for a in ARM_ORDER if complete_repeats(a) > 0] or [0])
    oofs = {}
    for arm in ARM_ORDER:
        if complete_repeats(arm) >= max(R, 1):
            T, oof, info = collect(arm, upop, R)
            scores[arm], oofs[arm] = T, oof
            infos.append(info)
    print(f"arms: {list(scores)}; repeats used for the C-ucsf arms: {R}")
    feats = pd.read_csv(OUTPUTS / "data" / "ucsf" / "imaging_features.csv").set_index("scan_id").reindex(upop.scan_id)
    deep_arms = list(scores)
    # EXPLORATORY reference (not in the plan): log ET volume alone at scan 2, same rows and bootstrap draws
    scores["REF_log_et_cc"] = feats.log_et_cc.to_numpy(float)[None]
    pairs = [(a, "G4") for a in ("G1", "G3", "T1") if a in scores and "G4" in scores]
    pairs += [("T1", "G1")] if {"T1", "G1"} <= set(scores) else []
    pairs += [(a, "REF_log_et_cc") for a in deep_arms]
    rows = []
    for (pn, ln, sub), (sel, pos) in eval_sets(upop).items():
        y = pos[sel].astype(int)
        if y.sum() < 3 or (1 - y).sum() < 3:
            continue
        res = boot(y, {k: v[:, sel] for k, v in scores.items()}, groups[sel], n_boot, SEED, pairs)
        for x in res:
            rows.append({"population": pn, "label": ln, "subset": sub, "n_pos": int(y.sum()), "n_neg": int((1 - y).sum()), **x})
    res = pd.DataFrame(rows)
    res.to_csv(out / "image_only_auc.csv", index=False)
    if infos:
        info = pd.concat(infos)
        info.to_csv(out / "jobs.csv", index=False)
    mu_info = []
    for arm in MU_ARMS:
        for j in range(HP["n_inner"]):
            if mu_job_path(arm, j).exists():
                z = np.load(mu_job_path(arm, j))
                inf = json.loads(str(z["info"]))
                mu_info.append({"arm": arm, "inner": j, **{a: b for a, b in inf.items() if a != "hist"}})
    if mu_info:
        pd.DataFrame(mu_info).to_csv(out / "mu_full_jobs.csv", index=False)
        mu_oof = []
        from sklearn.metrics import roc_auc_score
        for arm in MU_ARMS:
            if all(mu_job_path(arm, j).exists() for j in range(HP["n_inner"])):
                pop = fdet.population(MU_ARMS[arm]["src"])
                o = np.full(len(pop.y), np.nan)
                for j in range(HP["n_inner"]):
                    z = np.load(mu_job_path(arm, j))
                    o[z["rows"]] = z["logit"]
                m = ~np.isnan(pop.y)
                mu_oof.append({"arm": arm, "mu_inner_oof_auc": roc_auc_score(pop.y[m], o[m]), "n": int(m.sum())})
        pd.DataFrame(mu_oof).to_csv(out / "mu_full_oof_auc.csv", index=False)
        print(pd.DataFrame(mu_oof).round(3).to_string(index=False))
    # stacking (C-ucsf arms only: they have inner OOF scores on the training rows)
    base = base_designs(upop)
    Rs = max(R, 1)
    for a in [k for k in scores if k.startswith("locked_")]:  # fixed score: its training-side value is the score
        v = scores[a][0]
        oofs[a] = {(r, k): v for r in range(Rs) for k in range(N_FOLDS)}
    stackT = {a: (np.repeat(scores[a], Rs, 0) if a.startswith("locked_") else scores[a]) for a in oofs}
    srows = []
    for bname, X in base.items():
        for arm in oofs:
            Bp, Sp = stack_scores(upop, X, stackT[arm], oofs[arm], Rs if arm.startswith("locked_") else R)
            for (pn, ln, sub), (sel, pos) in eval_sets(upop).items():
                if ln != "primary":
                    continue
                y = pos[sel].astype(int)
                res_s = boot(y, {bname: Bp[:, sel], f"{bname}+{arm}": Sp[:, sel]}, groups[sel], n_boot, SEED,
                             [(f"{bname}+{arm}", bname)])
                for x in res_s:
                    srows.append({"base": bname, "arm": arm, "population": pn, "subset": sub, "n_pos": int(y.sum()),
                                  "n_neg": int((1 - y).sum()), **x})
    st = pd.DataFrame(srows)
    st.to_csv(out / "stacking.csv", index=False)
    show = res[(res.label == "primary")]
    print(show.round(3).to_string(index=False))
    if len(st):
        print(st[st.model.str.contains(" - ")].round(3).to_string(index=False))
    # aggregate score diagnostics: correlation with log lesion / ET volume (scan 2)
    diag = []
    for k, S in scores.items():
        s = S.mean(0)
        diag.append({"model": k, **{f"r_{c}": float(np.corrcoef(s, feats[c].to_numpy(float))[0, 1])
                                    for c in ("log_lesion_cc", "log_et_cc") if c in feats}})
    pd.DataFrame(diag).to_csv(out / "diagnostics.csv", index=False)
    print(pd.DataFrame(diag).round(3).to_string(index=False))
    (out / "meta.json").write_text(json.dumps({"repeats": R, "arms": list(scores), "base_arms": list(base),
                                               "n_boot": n_boot, "seed": SEED}))



# ---------------------------------------------------------------- EXPLORATORY (added after the repeat-0 results)
def untrained(n_rep=1):
    """EXPLORATORY control: the BraTS21 encoder with the head initialised exactly as each job's fine-tune starts
    (job seed), no training at all; predicts the outer-test rows of repeat r (TTA as MU). GPU."""
    torch = fd.setup_torch()
    upop = UPop()
    data = UData(upop, "cuda", False)
    out = OUT / "jobs" / "G0_untrained"
    out.mkdir(parents=True, exist_ok=True)
    for r in range(n_rep):
        for k in range(N_FOLDS):
            for j in range(HP["n_inner"]):
                path = job_path("G0_untrained", r, k, j)
                if path.exists():
                    continue
                s = split_spec(upop.folds[:, r], k, j, upop.y, upop.patient_id, "real", r)
                torch.manual_seed(s["seed"])
                net = fdet.make_net("cur", HP["dropout"])
                torch.manual_seed(s["seed"])
                for mod in net.head:
                    if hasattr(mod, "reset_parameters"):
                        mod.reset_parameters()
                rows = np.concatenate([s["hold"], s["test"]])
                logit = fd.predict(net.cuda(), data, rows)
                _save(path, rows=rows, is_test=np.r_[np.zeros(len(s["hold"]), bool), np.ones(len(s["test"]), bool)],
                      logit=logit, scan_id=upop.scan_id[rows], info=json.dumps({"best_epoch": -1, "epochs": 0, "hist": [{"val_loss": np.nan, "train_loss": np.nan}],
                                                                                 "sec": 0, "peak_gb": 0, "n_fit": 0, "n_val": 0, "seed": s["seed"]}))
                del net
                print(f"untrained r{r} k{k} j{j}", flush=True)


def explore():
    """EXPLORATORY diagnostics: per-network test AUC and correlation with log ET volume, within-fold AUC, AUC of the
    ensemble score's residual after a linear fit on log ET volume (scan 2), per arm and repeat."""
    from sklearn.metrics import roc_auc_score
    upop = UPop()
    lab = ~np.isnan(upop.y)
    g4 = upop.frame.grade4.astype(bool).to_numpy()
    f = pd.read_csv(OUTPUTS / "data" / "ucsf" / "imaging_features.csv").set_index("scan_id").reindex(upop.scan_id)
    et = f.log_et_cc.to_numpy(float)
    rows_out = []
    arms = [a for a in (*ARM_ORDER, "G0_untrained") if complete_repeats(a) > 0]
    for arm in arms:
        R = complete_repeats(arm)
        T, _, _ = collect(arm, upop, R)
        for r in range(R):
            net_auc, net_r = [], []
            for k in range(N_FOLDS):
                for j in range(HP["n_inner"]):
                    z = np.load(job_path(arm, r, k, j))
                    t = z["is_test"]
                    rw = z["rows"][t]
                    m = lab[rw]
                    net_auc.append(roc_auc_score(upop.y[rw][m], z["logit"][t][m]))
                    net_r.append(np.corrcoef(z["logit"][t], et[rw])[0, 1])
            sc = T[r]
            X = np.c_[np.ones(len(sc)), et]
            res = sc - X @ np.linalg.lstsq(X, sc, rcond=None)[0]
            wf = [roc_auc_score(upop.y[(upop.folds[:, r] == k) & lab], sc[(upop.folds[:, r] == k) & lab])
                  for k in range(N_FOLDS)]
            rows_out.append({"arm": arm, "repeat": r, "nets_auc_gt_0.5": int((np.array(net_auc) > 0.5).sum()),
                             "n_nets": len(net_auc), "net_auc_median": float(np.median(net_auc)),
                             "net_r_logET_min": float(np.min(net_r)), "net_r_logET_median": float(np.median(net_r)),
                             "nets_r_logET_negative": int((np.array(net_r) < 0).sum()),
                             "within_fold_auc_mean_all": float(np.mean(wf)),
                             "residual_after_logET_auc_all": roc_auc_score(upop.y[lab], res[lab]),
                             "residual_after_logET_auc_grade4": roc_auc_score(upop.y[lab & g4], res[lab & g4]),
                             "r_score_logET": float(np.corrcoef(sc, et)[0, 1])})
    d = pd.DataFrame(rows_out)
    (OUT / "evaluation").mkdir(parents=True, exist_ok=True)
    d.to_csv(OUT / "evaluation" / "exploratory_diagnostics.csv", index=False)
    print(d.round(3).to_string(index=False))

def main(argv=None):
    ap = argparse.ArgumentParser(prog="ucsf_deep", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["cache", "verify", "smoke", "run", "worker", "evaluate", "explore", "untrained"])
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--per-gpu", type=int, default=3)
    ap.add_argument("--tag", default="w")
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    if a.command == "cache":
        build_cache(a.workers)
    elif a.command == "verify":
        verify()
    elif a.command == "smoke":
        smoke()
    elif a.command == "run":
        launch(a.repeats, a.per_gpu)
    elif a.command == "worker":
        worker(a.repeats, a.tag)
    elif a.command == "explore":
        explore()
    elif a.command == "untrained":
        untrained(a.repeats)
    else:
        evaluate(a.n_boot)


if __name__ == "__main__":
    main()
