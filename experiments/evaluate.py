"""Evaluation on the test images (slide 12).

    x = p s,  y ~ Poisson(x),  p in {0.1, 0.2, 0.5, 1, 2, 4}
    same 8 test images and the same noise seeds for every method, parameters tuned on data/tune
    measurements: PSNR / SSIM, runtime, coefficient sparsity, convergence residuals
    binning (3x3) is a separate run: --bin 3

Run:
    python -m experiments.evaluate --methods anscombe_bm3d p4ip_bm3d spda --workers 2
    python -m experiments.evaluate --methods all --bin 3
    python -m experiments.evaluate --summary --ref anscombe_bm3d
Results: results/test.csv (or results/test_bin3.csv), residual traces in results/traces/,
tables in results/summary.md, plot in results/psnr_vs_peak.png.
"""
import argparse
import csv
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from .common import (PEAKS, REPO, bin_counts, image_name, image_paths, load_image, noisy_image, psnr,
                     ssim, unbin)
from .methods import METHODS

RESULTS = os.path.join(REPO, "results")
FIELDS = ["method", "image", "peak", "rep", "bin", "psnr", "ssim", "time", "iterations", "sparsity",
          "final_residual", "params"]


def run_one(method, params, path, peak, rep=0, b=0, trace_dir=None):
    """Simulate y for (image, peak, rep), run the method (on binned counts if b > 0), score it."""
    func, fixed, _ = METHODS[method]
    name = image_name(path)
    x, y = noisy_image(load_image(path), peak, name, rep)
    t0 = time.time()
    if b:
        xb, info = func(bin_counts(y, b), **fixed, **params)
        x_hat = unbin(xb, y.shape, b)
    else:
        x_hat, info = func(y, **fixed, **params)
    elapsed = time.time() - t0
    res = info.get("residuals", [])
    if trace_dir and res:
        os.makedirs(trace_dir, exist_ok=True)
        with open(os.path.join(trace_dir, f"{method}__{name}__p{peak}__b{b}.json"), "w") as f:
            json.dump({k: v for k, v in info.items() if isinstance(v, list)}, f)
    return {"method": method, "image": name, "peak": peak, "rep": rep, "bin": b,
            "psnr": psnr(x_hat, x, peak), "ssim": ssim(x_hat, x, peak), "time": elapsed,
            "iterations": info.get("iterations", len(res) or ""), "sparsity": info.get("sparsity", ""),
            "final_residual": res[-1] if res else "", "params": json.dumps(params)}


def tuned_params(method, peak, b):
    with open(os.path.join(RESULTS, "tuned_params.json")) as f:
        tuned = json.load(f)
    key = f"{method}@bin{b}" if b else method
    if key not in tuned or str(float(peak)) not in tuned[key]:
        raise KeyError(f"no tuned parameters for {key} at peak {peak}: run experiments.tune first")
    return tuned[key][str(float(peak))]["params"]


def evaluate(methods, peaks, reps, b, workers):
    out = os.path.join(RESULTS, f"test_bin{b}.csv" if b else "test.csv")
    done = set()
    if os.path.exists(out):
        with open(out) as f:
            done = {(r["method"], r["image"], float(r["peak"]), int(r["rep"])) for r in csv.DictReader(f)}
    jobs = [(m, tuned_params(m, p, b), path, p, r, b, os.path.join(RESULTS, "traces"))
            for m in methods for p in peaks for path in image_paths("test") for r in range(reps)
            if (m, image_name(path), float(p), r) not in done]
    print(f"{len(jobs)} runs -> {out}", flush=True)
    new = not os.path.exists(out)
    with open(out, "a", newline="") as f, ProcessPoolExecutor(workers) as pool:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        for i, row in enumerate(pool.map(run_one, *zip(*jobs)) if jobs else [], 1):
            w.writerow(row); f.flush()
            print(f"[{i}/{len(jobs)}] {row['method']} {row['image']} peak {row['peak']}: "
                  f"PSNR {row['psnr']:.2f} dB ({row['time']:.1f} s)", flush=True)


def summary(ref):
    import pandas as pd
    from scipy.stats import wilcoxon
    lines = ["# Results (test split, 8 images; parameters tuned on data/tune)\n"]
    frames = []
    for b in (0, 3):
        path = os.path.join(RESULTS, f"test_bin{b}.csv" if b else "test.csv")
        if not os.path.exists(path):
            continue
        d = pd.read_csv(path)
        d = d.groupby(["method", "image", "peak"], as_index=False).mean(numeric_only=True)  # mean over reps
        frames.append((b, d))
        tag = " with 3x3 binning" if b else " (no binning)"
        for col, title, fmt in (("psnr", "PSNR (dB)", "{:.2f}"), ("ssim", "SSIM", "{:.3f}"),
                                ("time", "runtime per image (s)", "{:.1f}"), ("sparsity", "coefficient sparsity (fraction nonzero)", "{:.3f}")):
            t = d.pivot_table(index="method", columns="peak", values=col, aggfunc="mean")
            if t.dropna(how="all").empty:
                continue
            lines.append(f"\n## Mean {title}{tag}\n")
            lines.append(t.map(lambda v: "" if pd.isna(v) else fmt.format(v)).to_markdown())
        if ref in set(d.method):
            lines.append(f"\n## Paired PSNR difference vs {ref}{tag} (positive = better than {ref})\n")
            rows = []
            for (m, p), g in d.groupby(["method", "peak"]):
                if m == ref:
                    continue
                r = d[(d.method == ref) & (d.peak == p)].set_index("image").psnr
                diff = (g.set_index("image").psnr - r).dropna()
                if len(diff) == 0:
                    continue
                pval = wilcoxon(diff).pvalue if len(diff) > 1 and np.any(diff != 0) else float("nan")
                rows.append({"method": m, "peak": p, "mean diff (dB)": round(diff.mean(), 2),
                             "wins": f"{int((diff > 0).sum())}/{len(diff)}", "Wilcoxon p": round(pval, 4)})
            lines.append(pd.DataFrame(rows).to_markdown(index=False))
    text = "\n".join(lines) + "\n"
    with open(os.path.join(RESULTS, "summary.md"), "w") as f:
        f.write(text)
    print(text)
    _plot(frames)


def _plot(frames):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    if not frames:
        return
    fig, axes = plt.subplots(1, len(frames), figsize=(7 * len(frames), 5), squeeze=False)
    for ax, (b, d) in zip(axes[0], frames):
        for m, g in d.groupby("method"):
            g = g.groupby("peak").psnr.mean()
            ax.plot(g.index, g.values, marker="o", label=m)
        ax.set_xscale("log"); ax.set_xticks(PEAKS); ax.set_xticklabels([str(p) for p in PEAKS])
        ax.set_xlabel("peak (photons)"); ax.set_ylabel("mean PSNR (dB)")
        ax.set_title("3x3 binning" if b else "no binning"); ax.grid(alpha=0.3); ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "psnr_vs_peak.png"), dpi=120)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", nargs="*", default=["all"])
    ap.add_argument("--peaks", nargs="*", type=float, default=PEAKS)
    ap.add_argument("--reps", type=int, default=1, help="noise realisations per image")
    ap.add_argument("--bin", type=int, default=0)
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--ref", default="anscombe_bm3d")
    a = ap.parse_args()
    if a.summary:
        return summary(a.ref)
    methods = list(METHODS) if a.methods == ["all"] else a.methods
    evaluate(methods, a.peaks, a.reps, a.bin, a.workers)


if __name__ == "__main__":
    main()
