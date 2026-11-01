"""Every method compared in the study (slide 12), in one table.

    name: (function, fixed parameters, tuning grid)

A function takes the noisy counts y and its parameters and returns (x_hat, info).
A grid is a function grid(peak, tuned) -> list of parameter dicts, searched on data/tune by
experiments/tune.py; `tuned` holds the parameters already tuned for other methods at this peak.

Scaling used in the grids: intensities scale with the peak, and the Poisson noise std in a bright
pixel is about sqrt(peak). So for P4IP-type methods we grid
    rho0 = r / peak                                  (r: rho0 on the peak-normalised scale)
    sigma0 = s * sqrt(peak), lam = sigma0^2 * rho0   (BM3D / dictionary: first sigma = sqrt(lam/rho0))
    eta0 = c * sqrt(peak),   lam = eta0 * rho0       (wavelet: first threshold = lam/rho0)
"""
import itertools

import numpy as np

from .baselines import conventional
from .baselines.anscombe_bm3d import anscombe_bm3d
from .baselines.p4ip import p4ip_bm3d
from .baselines.spda import spda
from .direction_a.a1_wavelet import p4ip_wavelet
from .direction_a.a2_dictionary import p4ip_dictionary
from .direction_a.a3_consensus import p4ip_bm3d_wavelet
from .direction_b.ista_fista import sparse_anscombe


def product(**axes):
    keys = list(axes)
    return [dict(zip(keys, v)) for v in itertools.product(*axes.values())]


def none(peak, tuned):
    return [{}]


def p4ip_sigma_grid(peak, tuned):
    return [{"lam": (s * np.sqrt(peak)) ** 2 * r / peak, "rho0": r / peak}
            for s in (0.5, 1, 2) for r in (1, 4, 16)]


def wavelet_grid(peak, tuned):
    return [{"lam": c * np.sqrt(peak) * r / peak, "rho0": r / peak}
            for c in (0.25, 0.5, 1, 2, 4) for r in (0.25, 1, 4, 16, 64)]


def consensus_grid(peak, tuned):
    """BM3D weight and rho0 from the tuned P4IP-BM3D; grid the wavelet weight lam2 (slide 15)."""
    b = tuned["p4ip_bm3d"]
    return [{"lam1": b["lam"], "rho0": b["rho0"], "lam2": c * np.sqrt(peak) * b["rho0"]}
            for c in (0.125, 0.25, 0.5, 1, 2)]


def sparse_grid(peak, tuned):
    return product(lam=[0.5, 1, 2, 4, 8, 16, 32])


# Slide 3: conventional methods
CONVENTIONAL = {
    "mean_filter":       (conventional.mean_filter, {}, lambda p, t: product(size=[3, 5, 7, 9, 11])),
    "gaussian_filter":   (conventional.gaussian_filter, {}, lambda p, t: product(sigma=[0.5, 1, 1.5, 2, 3, 4])),
    "median_filter":     (conventional.median_filter, {}, lambda p, t: product(size=[3, 5, 7, 9])),
    "wiener_filter":     (conventional.wiener_filter, {}, lambda p, t: product(size=[3, 5, 7, 9])),
    "wavelet_threshold": (conventional.wavelet_threshold, {}, lambda p, t: product(c=[1, 2, 3, 4, 5])),
    "nl_means":          (conventional.nl_means, {}, lambda p, t: product(h=[0.4, 0.6, 0.8, 1.0, 1.2])),
    "poisson_tv":        (conventional.poisson_tv, {},
                          lambda p, t: product(lam=[0.1, 0.3, 1, 3, 10], tau=[0.001, 0.003, 0.01, 0.03])),
}

# Slide 12: baselines
BASELINES = {
    "anscombe_bm3d":           (anscombe_bm3d, {"inverse": "exact"}, none),
    "anscombe_bm3d_algebraic": (anscombe_bm3d, {"inverse": "algebraic"}, none),  # slide 4 ablation
    "p4ip_bm3d":               (p4ip_bm3d, {}, p4ip_sigma_grid),
    "spda":                    (spda, {}, lambda p, t: product(patch=[8, 16], K=[1, 2, 3, 4])),
}

# Slide 10: direction A, change the P4IP prior
DIRECTION_A = {
    "A1_wavelet":       (p4ip_wavelet, {}, wavelet_grid),
    "A1_subband":       (p4ip_wavelet, {}, None),  # A1's best, then per-level weights (see REFINE)
    "A2_wavelet_dict":  (p4ip_dictionary, {"domain": "wavelet"}, p4ip_sigma_grid),
    "A2_pixel_dict":    (p4ip_dictionary, {"domain": "pixel"}, p4ip_sigma_grid),
    "A3_bm3d_wavelet":  (p4ip_bm3d_wavelet, {}, consensus_grid),
}

# Slide 11: direction B, ISTA / FISTA on the same objective; ISTA reuses FISTA's lam
DIRECTION_B = {
    "B_fista_swt":  (sparse_anscombe, {"solver": "fista", "frame": "swt"}, sparse_grid),
    "B_ista_swt":   (sparse_anscombe, {"solver": "ista", "frame": "swt"}, None),
    "B_fista_dict": (sparse_anscombe, {"solver": "fista", "frame": "dict"}, sparse_grid),
    "B_ista_dict":  (sparse_anscombe, {"solver": "ista", "frame": "dict"}, None),
}

METHODS = {**CONVENTIONAL, **BASELINES, **DIRECTION_A, **DIRECTION_B}

# Methods without their own grid take their parameters from another method.
SAME_PARAMS_AS = {"B_ista_swt": "B_fista_swt", "B_ista_dict": "B_fista_dict"}

# A1_subband: start from A1_wavelet's parameters, then coordinate search over the level weights.
REFINE = {"A1_subband": ("A1_wavelet", ["w1", "w2", "w3", "w4"], [0.5, 2.0])}
