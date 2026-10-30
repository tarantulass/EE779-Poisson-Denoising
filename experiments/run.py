"""Run an experiment config on the TEST split (or any split named in the config).

    python -m experiments.run experiments/configs/baselines.json [--workers 8]
        [--peaks 0.1 1] [--reps 0] [--images cameraman house] [--only p4ip_bm3d]

"methods_from_tune": [tune configs] adds every variant of those tune configs with
its tuned parameters (results/tune/<label>.json), so test and tuning stay in sync.

Results: results/<config name>/results.csv (+ traces/, + estimates/ if
"save_estimates": true). Re-running the same command resumes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdn import data, experiment  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--peaks", type=float, nargs="*")
    ap.add_argument("--reps", type=int, nargs="*")
    ap.add_argument("--images", nargs="*")
    ap.add_argument("--only", nargs="*", help="method labels to run")
    ap.add_argument("--out", default=None, help="override results directory")
    a = ap.parse_args(argv)

    with open(a.config) as f:
        cfg = json.load(f)
    experiment.load_plugins(cfg.get("plugins"))
    peaks = a.peaks or cfg["peaks"]
    reps = a.reps if a.reps is not None else cfg.get("reps", [0])
    paths = data.list_images(cfg.get("split", "test"))
    if a.images:
        paths = [p for p in paths if data.image_name(p) in a.images]
    if cfg.get("split", "test") == "test" and cfg.get("tuning_on_test"):
        raise SystemExit("refusing: tuning on the test split")

    methods = dict(cfg.get("methods", {}))
    for tf in cfg.get("methods_from_tune", []):   # every tuned variant of a tune config
        with open(os.path.join(data.REPO, tf)) as f:
            tcfg = json.load(f)
        experiment.load_plugins(tcfg.get("plugins"))
        for label in experiment.tune_variants(tcfg):
            methods[label] = experiment.variant_spec(tcfg, label)

    jobs = []
    for label, spec in methods.items():
        if a.only and label not in a.only:
            continue
        for peak in peaks:
            params = experiment.resolve_params(spec, peak)
            for p in paths:
                for r in reps:
                    jobs.append((label, spec["method"], params, p, float(peak), int(r)))

    out = a.out or os.path.join(data.REPO, "results", cfg["name"])
    experiment.run_jobs(
        jobs, os.path.join(out, "results.csv"), workers=a.workers,
        trace_dir=os.path.join(out, "traces") if cfg.get("save_traces", True) else None,
        save_dir=os.path.join(out, "estimates") if cfg.get("save_estimates") else None,
        plugins=cfg.get("plugins"))


if __name__ == "__main__":
    main()
