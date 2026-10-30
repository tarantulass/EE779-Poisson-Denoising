"""Learn the A2 dictionaries once on data/train (never on test or tune images).

    python -m experiments.learn_dictionary            # all presets
    python -m experiments.learn_dictionary a2_default a2_pixel

Every preset uses the same 100 000 training patch locations (seed 0), the same
learner and the same iterations; only the listed factor changes.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdn import data, dictionary  # noqa: E402

PRESETS = {
    "a2_default": dict(P=8, K=256, domain="wavelet", ll="pass"),   # A2-default
    "a2_pixel": dict(P=8, K=256, domain="pixel", ll="code"),       # A2.0 control
    "a2_free": dict(P=8, K=256, domain="wavelet", ll="code"),      # A2.1 null check
    "a2_k64": dict(P=8, K=64, domain="wavelet", ll="pass"),        # A2.3
    "a2_k128": dict(P=8, K=128, domain="wavelet", ll="pass"),
    "a2_k512": dict(P=8, K=512, domain="wavelet", ll="pass"),
    "a2_p6": dict(P=6, K=256, domain="wavelet", ll="pass"),        # A2.4
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=list(PRESETS))
    ap.add_argument("--n-patches", type=int, default=100_000)
    ap.add_argument("--n-iter", type=int, default=20)
    a = ap.parse_args(argv)
    paths = data.list_images("train")
    for name in a.names:
        out = f"models/{name}.npz"
        if os.path.exists(os.path.join(dictionary.REPO, out)):
            print(f"{out} exists, skipping (delete it to re-learn)")
            continue
        B, meta = dictionary.learn(paths, n_patches=a.n_patches, n_iter=a.n_iter,
                                   **PRESETS[name])
        dictionary.save_dictionary(out, B, meta)
        print(f"{out}: {B.shape}, {meta['learn_time_s']:.0f} s", flush=True)


if __name__ == "__main__":
    main()
