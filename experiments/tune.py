"""Per-peak grid search on the TUNE split (never the test split).

    python -m experiments.tune experiments/configs/tune_p4ip_bm3d.json [--workers 8]

Config:
  {"name": "p4ip_bm3d", "method": "p4ip", "params": {...base...},
   "peaks": [0.1, 0.2, ...], "reps": [100, 101],          # tune noise seeds
   "grid": {"priors.0.beta": [...], "rho0": [...]},     # shared grid, or
   "grid_per_peak": {"0.1": {...}, ...},                 # peak-specific grid
   "objective": "psnr"}
Writes results/tune/<name>/grid.csv and results/tune/<name>.json with
{"best": {peak: {dotted_key: value}}, "score": {peak: mean objective}}.
The JSON is what a test config points to via "tuned".

Selection rule: highest mean objective over (tune image x tune rep). Ties
(within 0.01 dB) go to the cheaper setting (fewer iterations). Settings at
the edge of the grid are flagged: extend the grid and re-run if so.
"""
from __future__ import annotations

import argparse
import copy
import itertools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from pdn import data, experiment  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--peaks", type=float, nargs="*")
    a = ap.parse_args(argv)
    with open(a.config) as f:
        cfg = json.load(f)
    experiment.load_plugins(cfg.get("plugins"))
    paths = data.list_images("tune")
    reps = cfg.get("reps", [100])
    peaks = a.peaks or cfg["peaks"]
    out_dir = os.path.join(data.REPO, "results", "tune", cfg["name"])
    csv_path = os.path.join(out_dir, "grid.csv")

    jobs, settings = [], {}
    for peak in peaks:
        grid = cfg.get("grid_per_peak", {}).get(str(peak)) or cfg.get("grid_per_peak", {}).get(
            next((k for k in cfg.get("grid_per_peak", {}) if abs(float(k) - peak) < 1e-12), ""),
            None) or cfg["grid"]
        keys = list(grid)
        for combo in itertools.product(*(grid[k] for k in keys)):
            p = copy.deepcopy(cfg.get("params", {}))
            for k, v in zip(keys, combo):
                experiment.set_dotted(p, k, v)
            h = experiment.params_hash(p)
            settings[(peak, h)] = (dict(zip(keys, combo)), grid)
            for path in paths:
                for r in reps:
                    jobs.append((cfg["name"], cfg["method"], p, path, float(peak), int(r)))
    experiment.run_jobs(jobs, csv_path, workers=a.workers, plugins=cfg.get("plugins"))

    df = pd.read_csv(csv_path)
    obj = cfg.get("objective", "psnr")
    best, score, flags = {}, {}, {}
    for peak in peaks:
        d = df[(df.peak - peak).abs() < 1e-12]
        d = d[d.params_hash.isin([h for (pk, h) in settings if pk == peak])]
        g = d.groupby("params_hash").agg(m=(obj, "mean"), n=(obj, "size"), t=("time_total", "mean"))
        g = g[g.n == len(paths) * len(reps)]
        top = g.m.max()
        cand = g[g.m >= top - 0.01].sort_values("t")
        h = cand.index[0]
        chosen, grid = settings[(peak, h)]
        best[str(peak)] = chosen
        score[str(peak)] = float(g.loc[h, "m"])
        edge = [k for k, v in chosen.items()
                if len(grid[k]) > 1 and v in (grid[k][0], grid[k][-1])]
        flags[str(peak)] = edge
        print(f"peak {peak}: {obj}={score[str(peak)]:.3f}  {chosen}"
              + (f"   !! at grid edge: {edge}" if edge else ""))
    with open(os.path.join(data.REPO, "results", "tune", cfg["name"] + ".json"), "w") as f:
        json.dump({"best": best, "score": score, "at_grid_edge": flags,
                   "tune_images": [data.image_name(p) for p in paths], "tune_reps": reps},
                  f, indent=2)


if __name__ == "__main__":
    main()
