"""Real data: the FMD fluorescence-microscopy test set (Zhang et al., CVPR 2019).

FMD test_mix: 48 fields of view from confocal, two-photon and wide-field microscopes, 8-bit, with
a raw single capture (`raw/`) and a ground truth that is the average of 50 captures (`gt/`). As in
FMD's own benchmark, the central 256 x 256 crop is used.

The camera noise is Poisson-Gaussian, z = a * Poisson(u / a) + N(0, b) (u = gt), so
    Var(z | u) = a u + b.
a and b are fitted per image by least squares on (u, (z - u)^2) over 32 intensity bins. Then
    y = z / a + b / a^2
has mean = variance = u / a + b / a^2, i.e. it is approximately Poisson (the shifted-Poisson
approximation), so every Poisson method of this study runs on y unchanged. The estimate is mapped
back by u_hat = a * (x_hat - b / a^2). PSNR is on the 8-bit scale, 10 log10(255^2 / MSE), as in FMD.

No parameter is tuned on FMD. Parameters are transferred from the synthetic tuning
(results/tuned_params.json) at the tuned peak nearest to the image's effective peak
p = max(u / a + b / a^2), with the same peak scaling as the tuning grids (experiments/methods.py):
rho0 = r / p, lam = s^2 r, wavelet lam = c sqrt(p) rho0.

    python -m experiments.fmd --data data/fmd/test_mix --workers 2
    python -m experiments.fmd --summary
Results: results/fmd.csv, results/fmd_noise.csv (fitted a, b, effective peak per image).
"""
import argparse
import csv
import glob
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image

from .common import PEAKS, REPO
from .methods import METHODS

RESULTS = os.path.join(REPO, "results")
OUT = os.path.join(RESULTS, "fmd.csv")
FIELDS = ["method", "image", "a", "b", "peak_eff", "peak_used", "psnr", "ssim", "time", "params"]
FMD_METHODS = ["noisy", "gaussian_filter", "anscombe_bm3d", "spda", "A1_subband", "B_fista_dict",
               "p4ip_bm3d", "A3_bm3d_wavelet"]


def load_pair(gt_path, raw_dir, crop=256):
    name = os.path.basename(gt_path)
    u = np.asarray(Image.open(gt_path).convert("L"), dtype=np.float64)
    z = np.asarray(Image.open(os.path.join(raw_dir, name)).convert("L"), dtype=np.float64)
    H, W = u.shape
    r0, c0 = (H - crop) // 2, (W - crop) // 2
    return u[r0:r0 + crop, c0:c0 + crop], z[r0:r0 + crop, c0:c0 + crop]


def fit_noise(u, z, n_bins=32):
    """Least-squares fit of Var(z | u) = a u + b on intensity bins (bins with >= 50 pixels)."""
    edges = np.quantile(u, np.linspace(0, 1, n_bins + 1))
    m, v, w = [], [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (u >= lo) & (u <= hi)
        if sel.sum() >= 50 and hi > lo:
            m.append(u[sel].mean()); v.append(np.mean((z[sel] - u[sel]) ** 2)); w.append(sel.sum())
    A = np.stack([np.array(m), np.ones(len(m))], 1)
    a, b = np.linalg.lstsq(A * np.sqrt(w)[:, None], np.array(v) * np.sqrt(w), rcond=None)[0]
    return max(float(a), 1e-3), max(float(b), 0.0)


def transfer(method, p):
    """Tuned parameters at the nearest tuned peak, rescaled to peak p (see module docstring)."""
    tuned = json.load(open(os.path.join(RESULTS, "tuned_params.json")))
    pk = min(PEAKS, key=lambda q: abs(np.log(q) - np.log(p)))
    prm = dict(tuned[method][str(float(pk))]["params"])
    if "rho0" in prm:
        rho_new = prm["rho0"] * pk / p
        if method == "A3_bm3d_wavelet":
            c = prm["lam2"] / (np.sqrt(pk) * prm["rho0"])
            prm["lam2"] = float(c * np.sqrt(p) * rho_new)
        elif method.startswith("A1_"):
            c = prm["lam"] / (np.sqrt(pk) * prm["rho0"])
            prm["lam"] = float(c * np.sqrt(p) * rho_new)
        prm["rho0"] = float(rho_new)
    return pk, prm


def psnr8(x, gt):
    return float(10 * np.log10(255.0 ** 2 / np.mean((np.clip(x, 0, 255) - gt) ** 2)))


def ssim8(x, gt):
    from skimage.metrics import structural_similarity
    return float(structural_similarity(np.clip(x, 0, 255), gt, data_range=255.0))


def run_one(method, gt_path, raw_dir):
    u, z = load_pair(gt_path, raw_dir)
    a, b = fit_noise(u, z)
    shift = b / a ** 2
    y = np.maximum(z / a + shift, 0)
    p = float((u / a + shift).max())
    t0 = time.time()
    if method == "noisy":
        est, pk, prm = z, "", {}
    else:
        pk, prm = transfer(method, p)
        func, fixed, _ = METHODS[method]
        x_hat, _ = func(y, **fixed, **prm)
        est = a * (x_hat - shift)
    return {"method": method, "image": os.path.basename(gt_path), "a": a, "b": b, "peak_eff": p,
            "peak_used": pk, "psnr": psnr8(est, u), "ssim": ssim8(est, u), "time": time.time() - t0,
            "params": json.dumps(prm)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(REPO, "data", "fmd", "test_mix"))
    ap.add_argument("--methods", nargs="*", default=FMD_METHODS)
    ap.add_argument("--limit", type=int, default=0, help="use only the first N images (0 = all 48)")
    ap.add_argument("--pattern", default="*.png", help="e.g. '*_1.png': one field of view per configuration (12 images)")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.summary:
        return summary()
    gts = sorted(glob.glob(os.path.join(a.data, "gt", a.pattern)))
    if a.limit:
        gts = gts[:a.limit]
    done = set()
    if os.path.exists(OUT):
        done = {(r["method"], r["image"]) for r in csv.DictReader(open(OUT))}
    jobs = [(m, g) for m in a.methods for g in gts if (m, os.path.basename(g)) not in done]
    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as f, ProcessPoolExecutor(a.workers) as pool:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        futs = [pool.submit(run_one, m, g, os.path.join(a.data, "raw")) for m, g in jobs]
        for i, fu in enumerate(futs, 1):
            r = fu.result()
            w.writerow(r); f.flush()
            print(f"[{i}/{len(futs)}] {r['method']} {r['image']}: PSNR {r['psnr']:.2f} dB "
                  f"(peak {r['peak_eff']:.1f}, {r['time']:.1f} s)", flush=True)
    summary()


def summary():
    import pandas as pd
    d = pd.read_csv(OUT)
    t = d.groupby("method").agg(psnr=("psnr", "mean"), ssim=("ssim", "mean"), n=("psnr", "size"),
                                time=("time", "mean"))
    print(t.sort_values("psnr").round(3).to_string())
    noise = d[d.method == "noisy"][["image", "a", "b", "peak_eff"]]
    noise.to_csv(os.path.join(RESULTS, "fmd_noise.csv"), index=False)
    print(noise.describe().round(2).to_string())


if __name__ == "__main__":
    main()
