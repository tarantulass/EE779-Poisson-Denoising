"""Gaussian denoisers usable as the P4IP prior step.

Contract every denoiser must satisfy (checked by tests/test_denoiser_contract.py):
    D(r: float64 array (H, W), sigma: float > 0, **params) -> float64 array (H, W)
  * r is an intermediate ADMM image in PHOTON-COUNT units (not normalised); it
    can be negative and can exceed the peak.
  * sigma is the Gaussian noise std in the same units as r (sigma^2 = beta/rho).
  * Deterministic: the same (r, sigma, params) returns the same output.
  * No access to the clean image or to y.

Your own priors (direction A) plug in with:

    from pdn.denoisers import register

    @register("wavelet_soft")
    def wavelet_soft(r, sigma, wavelet="db4", levels=4, ...):
        ...

then refer to them by name in an experiment config. Nothing else changes.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

DENOISERS: dict[str, Callable[..., np.ndarray]] = {}


def register(name: str):
    def deco(fn):
        if name in DENOISERS:
            raise KeyError(f"denoiser {name!r} already registered")
        DENOISERS[name] = fn
        return fn

    return deco


def get(name: str) -> Callable[..., np.ndarray]:
    try:
        return DENOISERS[name]
    except KeyError:
        raise KeyError(f"unknown denoiser {name!r}; registered: {sorted(DENOISERS)}") from None


@register("bm3d")
def bm3d_denoise(r: np.ndarray, sigma: float, stage: str = "all") -> np.ndarray:
    """BM3D (Dabov et al. 2007) via the reference `bm3d` package (Makinen et al.).
    stage='all' runs hard thresholding + Wiener; stage='hard' runs only the first
    stage (about 2x faster, used only as an explicit, labelled ablation)."""
    import bm3d

    st = {"all": bm3d.BM3DStages.ALL_STAGES, "hard": bm3d.BM3DStages.HARD_THRESHOLDING}[stage]
    return np.asarray(bm3d.bm3d(r, sigma_psd=float(sigma), stage_arg=st), dtype=np.float64)


@register("identity")
def identity(r: np.ndarray, sigma: float) -> np.ndarray:
    """Harness plumbing check only: P4IP with this prior returns ~the ML estimate y."""
    return r.copy()


@register("gaussian_filter")
def gaussian_filter(r: np.ndarray, sigma: float, width: float = 1.5) -> np.ndarray:
    """Cheap sanity prior for smoke tests (fixed spatial width in pixels, ignores
    sigma); not a proposed method."""
    from scipy.ndimage import gaussian_filter as gf

    return gf(r, sigma=width, mode="reflect")
