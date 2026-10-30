"""Direction A1: orthonormal wavelet shrinkage as the P4IP prior (EE779.odp slide 10).

    D(r, sigma) = W^T S(W r, eta)

W is a J-level 2-D DWT with periodization, which is exactly orthonormal when
both image sides are divisible by 2^J (true for the 256x256 test images). For
other sizes (e.g. 3x3-binned images) the image is padded symmetrically to the
next multiple of 2^J and cropped back; then D is a good denoiser but no longer
the exact prox, and `penalty` returns None.

Threshold rules (`eta`):
  'c_sigma' : eta = c * sigma   (A1-default; heuristic denoiser)
              c can be a scalar or a list of J values, coarsest level first (A1.f)
  'sigma2'  : eta = sigma^2 = beta/rho (A1.a). With soft thresholding of all
              thresholded bands this is exactly prox_{(beta/rho)||W_T .||_1},
              so P4IP is ADMM on   sum(x - y log x) + beta * ||W_T x||_1,
              W_T = the thresholded bands (details only unless threshold_ll).

Each call stores its sparsity in `wavelet_soft.last_stats`, which pdn/p4ip.py
copies into the iteration trace.
"""
from __future__ import annotations

import numpy as np
import pywt

from .denoisers import register


def _pad_to(r, m):
    H, W = r.shape
    ph, pw = (-H) % m, (-W) % m
    if ph == 0 and pw == 0:
        return r, False
    return np.pad(r, ((0, ph), (0, pw)), mode="symmetric"), True


def _thresholds(sigma, J, eta, c):
    if eta == "sigma2":
        return [float(sigma) ** 2] * J, float(sigma) ** 2
    if eta != "c_sigma":
        raise ValueError(f"eta must be 'c_sigma' or 'sigma2', got {eta!r}")
    cs = list(c) if isinstance(c, (list, tuple)) else [float(c)] * J
    if len(cs) != J:
        raise ValueError(f"need {J} per-level constants (coarsest first), got {len(cs)}")
    return [ci * float(sigma) for ci in cs], cs[0] * float(sigma)


def _shrink(a, t, kind):
    if kind == "soft":
        return np.sign(a) * np.maximum(np.abs(a) - t, 0.0)
    if kind == "hard":
        return a * (np.abs(a) > t)
    raise ValueError(kind)


def _denoise_once(r, sigma, wavelet, levels, threshold, eta, c, threshold_ll):
    coeffs = pywt.wavedec2(r, wavelet, mode="periodization", level=levels)
    ts, t_ll = _thresholds(sigma, levels, eta, c)
    nnz = tot = 0
    out = [coeffs[0]]
    if threshold_ll:
        out[0] = _shrink(coeffs[0], t_ll, threshold)
        nnz += np.count_nonzero(out[0]); tot += out[0].size
    for lev, bands in enumerate(coeffs[1:]):  # lev 0 = coarsest detail level
        nb = tuple(_shrink(b, ts[lev], threshold) for b in bands)
        nnz += sum(np.count_nonzero(b) for b in nb); tot += sum(b.size for b in nb)
        out.append(nb)
    return pywt.waverec2(out, wavelet, mode="periodization"), nnz / max(tot, 1)


@register("wavelet_soft")
def wavelet_soft(r: np.ndarray, sigma: float, wavelet: str = "db4", levels: int = 4,
                 threshold: str = "soft", eta: str = "c_sigma", c=3.0,
                 threshold_ll: bool = False, cycle_spin: int = 1) -> np.ndarray:
    """A1 denoiser. cycle_spin K in {1, 4, 16}: average over sqrt(K) x sqrt(K)
    circular shifts (A1.g; not a prox any more)."""
    r = np.asarray(r, dtype=np.float64)
    H, W = r.shape
    rp, padded = _pad_to(r, 2 ** levels)
    k = int(round(np.sqrt(cycle_spin)))
    if k * k != cycle_spin:
        raise ValueError("cycle_spin must be a perfect square (1, 4, 16, ...)")
    acc = np.zeros_like(rp)
    fr = []
    for dy in range(k):
        for dx in range(k):
            s = np.roll(rp, (dy, dx), axis=(0, 1))
            d, f = _denoise_once(s, sigma, wavelet, levels, threshold, eta, c, threshold_ll)
            acc += np.roll(d, (-dy, -dx), axis=(0, 1))
            fr.append(f)
    wavelet_soft.last_stats = {"nnz_frac": float(np.mean(fr))}
    return acc[:H, :W] / (k * k)


wavelet_soft.last_stats = {}


def _penalty(x, sigma=None, wavelet="db4", levels=4, threshold="soft", eta="c_sigma",
             c=3.0, threshold_ll=False, cycle_spin=1):
    """||W_T x||_1 when D is the exact prox of it (A1.a), else None."""
    if eta != "sigma2" or threshold != "soft" or cycle_spin != 1 or any(
            s % (2 ** levels) for s in x.shape):
        return None
    coeffs = pywt.wavedec2(x, wavelet, mode="periodization", level=levels)
    val = sum(np.abs(b).sum() for bands in coeffs[1:] for b in bands)
    if threshold_ll:
        val += np.abs(coeffs[0]).sum()
    return float(val)


wavelet_soft.penalty = _penalty
