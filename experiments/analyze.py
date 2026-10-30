"""Tables, paired statistics and plots for one or more results.csv files.

    python -m experiments.analyze results/baselines [results/ablation_A1 ...] \
        --ref p4ip_bm3d [--out results/report]

Statistics (paired design, same y for every method):
  * Unit of analysis is the IMAGE. Noise repetitions are averaged within an
    image first, because reps of the same image are not independent evidence
    about generalisation to new images.
  * For each method vs --ref and each peak: mean Delta-PSNR, 95% t-interval over
    images, Wilcoxon signed-rank p (exact, two-sided), wins/n.
  * Holm-Bonferroni correction across peaks within each comparison.
  With 8 images the smallest attainable Wilcoxon p is 2/256 = 0.0078, so a
  difference can only be called significant if it holds on (nearly) all 8.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def holm(p):
    p = np.asarray(p, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    m = len(p)
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def load(dirs):
    dfs = []
    for d in dirs:
        f = d if d.endswith(".csv") else os.path.join(d, "results.csv")
        dfs.append(pd.read_csv(f))
    df = pd.concat(dfs, ignore_index=True)
    dup = df.duplicated(["label", "image", "peak", "rep"], keep="last")
    if dup.any():
        print(f"note: {dup.sum()} duplicate rows (re-runs with changed params); keeping the last")
        df = df[~dup]
    return df


def summary_tables(df):
    per_img = df.groupby(["label", "peak", "image"]).agg(
        psnr=("psnr", "mean"), ssim=("ssim", "mean"), bias=("bias", "mean"),
        time=("time_total", "mean"), reps=("rep", "nunique")).reset_index()
    avg = per_img.groupby(["label", "peak"]).agg(
        psnr=("psnr", "mean"), psnr_sd=("psnr", "std"), ssim=("ssim", "mean"),
        bias=("bias", "mean"), time_s=("time", "mean"), n_images=("image", "nunique"),
        reps=("reps", "min")).reset_index()
    return per_img, avg


def paired(per_img, ref, metric="psnr"):
    rows = []
    base = per_img[per_img.label == ref].set_index(["peak", "image"])[metric]
    for label in sorted(set(per_img.label) - {ref}):
        sub = per_img[per_img.label == label].set_index(["peak", "image"])[metric]
        part = []
        for peak in sorted(set(sub.index.get_level_values(0))):
            common = sub.loc[peak].index.intersection(base.loc[peak].index) if peak in base.index.get_level_values(0) else []
            if len(common) < 2:
                continue
            d = (sub.loc[peak].loc[common] - base.loc[peak].loc[common]).values
            n = len(d)
            mean, se = d.mean(), d.std(ddof=1) / np.sqrt(n)
            h = stats.t.ppf(0.975, n - 1) * se if n > 1 and se > 0 else 0.0
            try:
                pw = stats.wilcoxon(d, method="exact").pvalue if np.any(d != 0) else 1.0
            except ValueError:
                pw = 1.0
            part.append({"label": label, "ref": ref, "peak": peak, "metric": metric, "n_images": n,
                         "delta": mean, "ci_lo": mean - h, "ci_hi": mean + h,
                         "wins": int((d > 0).sum()), "p_wilcoxon": pw})
        if part:
            adj = holm([r["p_wilcoxon"] for r in part])
            for r, a in zip(part, adj):
                r["p_holm"] = a
            rows += part
    return pd.DataFrame(rows)


def to_md(df, floatfmt=".2f"):
    try:
        return df.to_markdown(index=False, floatfmt=floatfmt)
    except ImportError:
        return df.to_string(index=False)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--ref", default="p4ip_bm3d")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    df = load(a.dirs)
    out = a.out or (a.dirs[0] if not a.dirs[0].endswith(".csv") else os.path.dirname(a.dirs[0]))
    os.makedirs(out, exist_ok=True)

    per_img, avg = summary_tables(df)
    per_img.to_csv(os.path.join(out, "per_image.csv"), index=False)
    avg.to_csv(os.path.join(out, "average.csv"), index=False)
    wide = avg.pivot(index="label", columns="peak", values="psnr")
    wide_ssim = avg.pivot(index="label", columns="peak", values="ssim")
    wide_t = avg.pivot(index="label", columns="peak", values="time_s")

    md = ["# Results\n", f"Sources: {', '.join(a.dirs)}\n",
          "## Average PSNR (dB) over images (reps averaged within image)\n",
          to_md(wide.reset_index()), "\n## Average SSIM\n", to_md(wide_ssim.reset_index(), ".3f"),
          "\n## Mean runtime per image (s)\n", to_md(wide_t.reset_index(), ".1f")]
    if a.ref in set(df.label):
        for metric in ("psnr", "ssim"):
            pr = paired(per_img, a.ref, metric)
            if len(pr):
                pr.to_csv(os.path.join(out, f"paired_{metric}_vs_{a.ref}.csv"), index=False)
                md += [f"\n## Paired {metric.upper()} difference vs `{a.ref}` "
                       "(positive = better than reference)\n", to_md(pr, ".4f")]
    md += ["\n## Per-image PSNR\n",
           to_md(per_img.pivot_table(index=["label", "peak"], columns="image", values="psnr").reset_index())]
    with open(os.path.join(out, "summary.md"), "w") as f:
        f.write("\n".join(md) + "\n")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(10, 4))
        for label, g in avg.groupby("label"):
            ax[0].plot(g.peak, g.psnr, marker="o", label=label)
            ax[1].plot(g.peak, g.time_s, marker="o", label=label)
        for x_, yl in zip(ax, ("PSNR (dB)", "runtime per image (s)")):
            x_.set_xscale("log"); x_.set_xlabel("peak photons"); x_.set_ylabel(yl); x_.grid(alpha=.3)
        ax[1].set_yscale("log"); ax[0].legend(fontsize=8)
        fig.tight_layout(); fig.savefig(os.path.join(out, "psnr_runtime_vs_peak.png"), dpi=150)
    except Exception as e:  # plotting is optional
        print("plot skipped:", e)
    print(open(os.path.join(out, "summary.md")).read())


if __name__ == "__main__":
    main()
