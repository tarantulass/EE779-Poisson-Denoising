"""Resumable, parallel experiment runner shared by experiments/run.py and tune.py.

A job is one (method_label, image, peak, rep). Its result row is appended to a
CSV as soon as it finishes, so a run killed half-way (VM preempted, SSH closed)
resumes where it stopped: rows already present are skipped.

Paired design: every method sees the same y for a given (image, peak, rep),
because the noise seed depends only on those three values (pdn/data.py).
"""
from __future__ import annotations

import copy
import csv
import hashlib
import importlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from . import data, methods, metrics

FIELDS = ["label", "method", "image", "peak", "rep", "bin", "psnr", "ssim", "bias",
          "time_total", "time_denoiser", "iters", "params_hash", "params"]


def load_plugins(mods):
    for m in mods or []:
        importlib.import_module(m)


def set_dotted(d: dict, key: str, value):
    """set_dotted(p, 'priors.0.beta', 0.3) -> p['priors'][0]['beta'] = 0.3"""
    parts = key.split(".")
    cur = d
    for p in parts[:-1]:
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    last = parts[-1]
    if isinstance(cur, list):
        cur[int(last)] = value
    else:
        cur[last] = value


def _tuned_sources(tuned):
    """'tuned' is a path, or a list of paths / {"file": path, "map": {old_key: new_key}}.
    A map re-targets keys, e.g. the A1 winner 'priors.0.params.c' -> 'priors.1.params.c'
    when the wavelet is the second prior of the A3 consensus."""
    if not tuned:
        return []
    items = tuned if isinstance(tuned, list) else [tuned]
    out = []
    for it in items:
        f, mp = (it, None) if isinstance(it, str) else (it["file"], it.get("map"))
        with open(os.path.join(data.REPO, f)) as fh:
            best = json.load(fh)["best"]
        if mp is not None:  # map value: one key or a list of keys (copy to several)
            best = {pk: {nk: v for k, v in kv.items() if k in mp
                         for nk in (mp[k] if isinstance(mp[k], list) else [mp[k]])}
                    for pk, kv in best.items()}
        out.append(best)
    return out


def get_dotted(d, key: str):
    cur = d
    for p in key.split("."):
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    return cur


def grid_value(base: dict, key: str, v):
    """Grid entries may be absolute, or '*f' = f times the value in the (tuned) base."""
    if isinstance(v, str) and v.startswith("*"):
        return get_dotted(base, key) * float(v[1:])
    return v


def resolve_params(spec: dict, peak: float) -> dict:
    """spec = {'method':..., 'params': {...}, 'tuned': ... (see _tuned_sources),
    'per_peak': {'0.2': {'rho0': 1, ...}}}. Later sources override earlier ones."""
    p = copy.deepcopy(spec.get("params", {}))
    sources = _tuned_sources(spec.get("tuned"))
    if spec.get("per_peak"):
        sources.append(spec["per_peak"])
    for src in sources:
        key = _peak_key(src, peak)
        for k, v in src.get(key, {}).items():
            set_dotted(p, k, copy.deepcopy(v))
    return p


def tune_variants(tcfg: dict) -> dict:
    """Variants of a tune config: {label: {"overrides": {...}, "grid": {...} | None}}.
    Without "variants" the config is a single variant labelled by its name."""
    vs = tcfg.get("variants") or {tcfg["name"]: {}}
    out = {}
    for label, v in vs.items():
        out[label] = {"overrides": dict(v), "grid": tcfg.get("variant_grids", {}).get(label)}
    return out


def variant_spec(tcfg: dict, label: str, with_own_tuned=True) -> dict:
    """Test-time spec for one tuned variant: base params + overrides, base 'tuned'
    sources, then the variant's own results/tune/<label>.json."""
    p = copy.deepcopy(tcfg.get("params", {}))
    for k, v in tune_variants(tcfg)[label]["overrides"].items():
        set_dotted(p, k, copy.deepcopy(v))
    tuned = tcfg.get("tuned") or []
    tuned = list(tuned) if isinstance(tuned, list) else [tuned]
    if with_own_tuned:
        tuned.append(f"results/tune/{label}.json")
    return {"method": tcfg["method"], "params": p, "tuned": tuned}


def _peak_key(table: dict, peak: float):
    for k in table:
        if abs(float(k) - peak) < 1e-12:
            return k
    return None


def params_hash(params: dict) -> str:
    return hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:10]


def _job(args):
    label, method, params, path, peak, rep, plugins, trace_dir, save_dir = args
    load_plugins(plugins)
    name = data.image_name(path)
    s = data.load_clean(path)
    x, y = data.simulate(s, peak, name, rep)
    x_hat, info = methods.run_method(method, y, peak, params)
    row = {
        "label": label, "method": method, "image": name, "peak": peak, "rep": rep,
        "bin": int(params.get("bin", 0) or 0),
        "psnr": metrics.psnr(x_hat, x, peak), "ssim": metrics.ssim(x_hat, x, peak),
        "bias": metrics.bias(x_hat, x, peak),
        "time_total": info.get("time_total", np.nan), "time_denoiser": info.get("time_denoiser", np.nan),
        "iters": info.get("iters", ""), "params_hash": params_hash(params),
        "params": json.dumps(params, sort_keys=True),
    }
    stem = f"{label}__{name}__p{peak}__r{rep}"
    if trace_dir and info.get("trace"):
        with open(os.path.join(trace_dir, stem + ".json"), "w") as f:
            json.dump(info["trace"], f)
    if save_dir:
        np.savez_compressed(os.path.join(save_dir, stem + ".npz"), x_hat=x_hat.astype(np.float32),
                            y=y.astype(np.uint16))
    return row


def done_keys(csv_path):
    keys = set()
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
        with open(csv_path) as f:
            rd = csv.DictReader(f)
            if rd.fieldnames != FIELDS:
                raise ValueError(f"{csv_path}: header {rd.fieldnames} != expected {FIELDS}; "
                                 "repair or remove the file")
            for r in rd:
                keys.add((r["label"], r["image"], float(r["peak"]), int(r["rep"]), r["params_hash"]))
    return keys


def run_jobs(jobs, csv_path, workers=None, trace_dir=None, save_dir=None, plugins=None, quiet=False):
    """jobs: list of (label, method, params, image_path, peak, rep)."""
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    for d in (trace_dir, save_dir):
        if d:
            os.makedirs(d, exist_ok=True)
    have = done_keys(csv_path)
    todo = [j for j in jobs
            if (j[0], data.image_name(j[3]), float(j[4]), int(j[5]), params_hash(j[2])) not in have]
    if not quiet:
        print(f"{len(jobs) - len(todo)} done, {len(todo)} to run -> {csv_path}", flush=True)
    if not todo:
        return
    # an empty file (e.g. a run killed before its first row) still needs the header
    new = not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0
    workers = workers or os.cpu_count()
    if workers > 1:  # one thread per worker process; set before workers start
        for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
            os.environ.setdefault(v, "1")
    t0 = time.time()
    with open(csv_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        args = [(*j, plugins or [], trace_dir, save_dir) for j in todo]
        if workers == 1:
            it = map(_job, args)
            for i, row in enumerate(it, 1):
                w.writerow(row); f.flush()
                if not quiet:
                    _progress(i, len(todo), t0, row)
        else:
            with ProcessPoolExecutor(max_workers=workers) as ex:
                futs = [ex.submit(_job, a) for a in args]
                for i, fu in enumerate(as_completed(futs), 1):
                    row = fu.result()
                    w.writerow(row); f.flush()
                    if not quiet:
                        _progress(i, len(todo), t0, row)


def _progress(i, n, t0, row):
    el = time.time() - t0
    print(f"[{i}/{n}] {row['label']} {row['image']} p={row['peak']} r={row['rep']} "
          f"PSNR={row['psnr']:.2f} ({row['time_total']:.1f}s)  eta {el / i * (n - i) / 60:.1f} min",
          flush=True)
