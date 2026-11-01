"""Parameter tuning on the separate tuning images, data/tune (slide 12).

For every method and peak, every parameter set of the method's grid (experiments/methods.py) is
run on the 4 tuning images (one noise realisation each) and the set with the highest mean PSNR is
kept. A warning is printed when the best value of a parameter is the smallest or largest value
tried. Results go to results/tuned_params.json, which evaluate.py reads.

    python -m experiments.tune --methods anscombe_bm3d p4ip_bm3d --workers 2
    python -m experiments.tune --methods all --bin 3        # binned runs are tuned separately
Already tuned (method, peak) pairs are skipped; --force re-tunes them.
"""
import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from .common import PEAKS, image_paths
from .evaluate import RESULTS, run_one
from .methods import METHODS, REFINE, SAME_PARAMS_AS

TUNED = os.path.join(RESULTS, "tuned_params.json")


def mean_psnr(pool, method, candidates, peak, b):
    paths = image_paths("tune")
    jobs = [(method, c, p, peak, 0, b) for c in candidates for p in paths]
    rows = list(pool.map(run_one, *zip(*jobs)))
    return [float(np.mean([r["psnr"] for r in rows[i * len(paths):(i + 1) * len(paths)]]))
            for i in range(len(candidates))]


def at_edge(candidates, best):
    edge = []
    for k, v in best.items():
        values = sorted({c[k] for c in candidates if k in c})
        if len(values) > 2 and v in (values[0], values[-1]):
            edge.append(k)
    return edge


def tune_peak(pool, method, peak, b, tuned):
    key = lambda m: f"{m}@bin{b}" if b else m
    pk = str(float(peak))
    if method in SAME_PARAMS_AS:
        return dict(tuned[key(SAME_PARAMS_AS[method])][pk], note=f"same parameters as {SAME_PARAMS_AS[method]}")
    if method in REFINE:  # coordinate search, one parameter at a time, starting from another method's best
        source, names, factors = REFINE[method]
        best = dict(tuned[key(source)][pk]["params"], **{n: 1.0 for n in names})
        best_score = mean_psnr(pool, method, [best], peak, b)[0]
        for _ in range(2):
            improved = False
            for n in names:
                cands = [dict(best, **{n: best[n] * f}) for f in factors]
                scores = mean_psnr(pool, method, cands, peak, b)
                if max(scores) > best_score:
                    best, best_score, improved = cands[int(np.argmax(scores))], max(scores), True
            if not improved:
                break
        return {"params": best, "tune_psnr": best_score, "at_grid_edge": []}
    others = {m.split("@")[0]: v[pk]["params"] for m, v in tuned.items()
              if pk in v and (m.endswith(f"@bin{b}") if b else "@" not in m)}
    candidates = METHODS[method][2](peak, others)
    scores = mean_psnr(pool, method, candidates, peak, b)
    best = candidates[int(np.argmax(scores))]
    return {"params": best, "tune_psnr": max(scores), "at_grid_edge": at_edge(candidates, best)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", nargs="*", default=["all"])
    ap.add_argument("--peaks", nargs="*", type=float, default=PEAKS)
    ap.add_argument("--bin", type=int, default=0)
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    methods = list(METHODS) if a.methods == ["all"] else a.methods
    os.makedirs(RESULTS, exist_ok=True)
    tuned = json.load(open(TUNED)) if os.path.exists(TUNED) else {}
    with ProcessPoolExecutor(a.workers) as pool:
        for m in methods:
            key = f"{m}@bin{a.bin}" if a.bin else m
            for peak in a.peaks:
                if str(float(peak)) in tuned.get(key, {}) and not a.force:
                    continue
                res = tune_peak(pool, m, peak, a.bin, tuned)
                tuned.setdefault(key, {})[str(float(peak))] = res
                with open(TUNED, "w") as f:
                    json.dump(tuned, f, indent=1)
                warn = f"   !! best at grid edge: {res['at_grid_edge']}" if res.get("at_grid_edge") else ""
                print(f"{key} peak {peak}: {res['params']}  tune PSNR {res.get('tune_psnr', float('nan')):.2f}{warn}",
                      flush=True)


if __name__ == "__main__":
    main()
