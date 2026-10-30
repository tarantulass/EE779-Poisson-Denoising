"""Convergence studies (analysis only; the clean image is used for PSNR curves here,
never inside a method).

    python -m experiments.convergence b1 [--images cameraman house] [--peaks 0.2 1]
        B1.a  ISTA vs FISTA: F(alpha_k) - F* vs iteration and wall time, with
              F* = min over 5000 FISTA iterations; iterations to reach
              F - F* <= 1e-3 F* and 1e-4 F*.
        B1.b  PSNR vs iteration (is the converged minimiser the best estimate?)
        lam per peak from results/tune/B1.json, or --lams; same F, lam, L = 1, alpha^0, rule.
    python -m experiments.convergence a1
        A1.a  explicit objective sum(x - y log x) + beta ||W_d x||_1 per P4IP iteration,
              from results/directions_A1/traces (paper schedule and constant rho).

Writes results/convergence/{b1_curves.csv, b1_summary.csv, b1.png, a1a.png}.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from pdn import anscombe, data, experiment, metrics, sparse  # noqa: E402

OUT = os.path.join(data.REPO, "results", "convergence")


def b1(images, peaks, n_iter, n_star, lams=None, rep=0):
    with open(os.path.join(data.REPO, "experiments/configs/tune_B1.json")) as f:
        tcfg = json.load(f)
    spec = experiment.variant_spec(tcfg, "B1")
    rows, summ = [], []
    paths = {data.image_name(p): p for p in data.list_images("test")}
    for name in images:
        s = data.load_clean(paths[name])
        for peak, lam_in in [(pk, lm) for pk in peaks for lm in (lams or [None])]:
            prm = experiment.resolve_params(spec, peak)
            if lam_in is not None:
                prm["lam"] = lam_in
            x, y = data.simulate(s, peak, name, rep)
            z = anscombe.forward(y)
            fr = sparse.make_frame(y.shape, prm["frame"], prm["wavelet"], prm["levels"])
            _, ts = sparse.solve(z, prm["lam"], fr, solver="fista", max_iter=n_star, tol=0)
            F_star = min(t["F"] for t in ts)
            for solver in ("ista", "fista"):
                def cb(k, a):
                    xh = anscombe.INVERSES[prm["inverse"]](fr.synthesis(a))
                    return {"psnr": metrics.psnr(xh, x, peak)}
                _, tr = sparse.solve(z, prm["lam"], fr, solver=solver, max_iter=n_iter, tol=0,
                                     callback=cb)
                gap = np.array([t["F"] - F_star for t in tr])
                for t, g in zip(tr, gap):
                    rows.append({"image": name, "peak": peak, "lam": prm["lam"], "solver": solver, "iter": t["iter"],
                                 "F": t["F"], "gap": g, "rel_gap": g / abs(F_star),
                                 "time": t["time"], "psnr": t["psnr"]})
                hit = {e: next((t["iter"] for t, g in zip(tr, gap) if g <= e * abs(F_star)), None)
                       for e in (1e-3, 1e-4)}
                best = max(tr, key=lambda t: t["psnr"])
                summ.append({"image": name, "peak": peak, "solver": solver, "lam": prm["lam"],
                             "F_star": F_star, "iters_to_1e-3": hit[1e-3], "iters_to_1e-4": hit[1e-4],
                             "psnr_final": tr[-1]["psnr"], "psnr_best": best["psnr"],
                             "iter_best": best["iter"], "time_per_iter": tr[-1]["time"] / len(tr)})
                print(summ[-1], flush=True)
    os.makedirs(OUT, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "b1_curves.csv"), index=False)
    pd.DataFrame(summ).to_csv(os.path.join(OUT, "b1_summary.csv"), index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    keys = sorted(set(zip(df.image, df.peak, df.lam)))
    fig, ax = plt.subplots(len(keys), 3, figsize=(13, 3.2 * len(keys)), squeeze=False)
    for i, (im, pk, lm) in enumerate(keys):
        for sv, g in df[(df.image == im) & (df.peak == pk) & (df.lam == lm)].groupby("solver"):
            ax[i, 0].loglog(g.iter, np.maximum(g.rel_gap, 1e-16), label=sv)
            ax[i, 1].loglog(g.time, np.maximum(g.rel_gap, 1e-16), label=sv)
            ax[i, 2].semilogx(g.iter, g.psnr, label=sv)
        ax[i, 0].set_ylabel(f"{im}, p={pk}, lam={lm}\n(F-F*)/F*")
        for a_, xl in zip(ax[i], ("iteration", "wall time (s)", "iteration")):
            a_.set_xlabel(xl); a_.grid(alpha=.3); a_.legend(fontsize=8)
        ax[i, 2].set_ylabel("PSNR (dB)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "b1.png"), dpi=130)


def a1():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    found = False
    for i, lab in enumerate(("A1.a", "A1.a_constrho")):
        for f in sorted(glob.glob(os.path.join(data.REPO, "results/directions_A1/traces",
                                               f"{lab}__cameraman__p*__r0.json"))):
            tr = json.load(open(f))
            if "objective" not in tr[0]:
                continue
            found = True
            ob = np.array([t["objective"] for t in tr])
            pk = f.split("__p")[1].split("__")[0]
            ax[i].plot(np.arange(1, len(ob)), (ob[:-1] - ob[-1]) / abs(ob[-1]), label=f"p={pk}")
        ax[i].set_yscale("log"); ax[i].set_title(f"{lab} (cameraman): (obj_k - obj_final)/|obj_final|")
        ax[i].set_xlabel("P4IP iteration"); ax[i].grid(alpha=.3); ax[i].legend(fontsize=8)
    if not found:
        print("no A1.a traces yet: run experiments/configs/directions_A1.json first")
        return
    os.makedirs(OUT, exist_ok=True)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "a1a.png"), dpi=130)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["b1", "a1"])
    ap.add_argument("--images", nargs="*", default=["cameraman", "house"])
    ap.add_argument("--peaks", type=float, nargs="*", default=[0.2, 1.0])
    ap.add_argument("--n-iter", type=int, default=1000)
    ap.add_argument("--n-star", type=int, default=5000)
    ap.add_argument("--lams", type=float, nargs="*", default=None,
                    help="lam values (default: tuned B1 lam). At the tuned lam the SWT solution can "
                         "have all details zero after one step, which makes ISTA vs FISTA trivial.")
    a = ap.parse_args(argv)
    if a.what == "b1":
        b1(a.images, a.peaks, a.n_iter, a.n_star, a.lams)
    else:
        a1()


if __name__ == "__main__":
    main()
