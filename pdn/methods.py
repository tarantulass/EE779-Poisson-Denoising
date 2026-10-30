"""Full Poisson denoising methods: y (counts) -> x_hat (intensity, counts).

Each method has signature  method(y, peak, **params) -> (x_hat, info).
`peak` is used ONLY to look up peak-dependent parameters, exactly as the P4IP
paper tunes per peak; it is never used to rescale the estimate.

All methods accept bin=0|b: sum counts in b x b blocks, run, divide by b^2 and
upsample bilinearly (paper Sec. 3.2). Binned results are reported separately.
"""
from __future__ import annotations

import time

import numpy as np

from . import anscombe, data, denoisers, p4ip

METHODS = {}


def register(name):
    def deco(fn):
        METHODS[name] = fn
        return fn

    return deco


def run_method(name: str, y: np.ndarray, peak: float, params: dict):
    params = dict(params)
    b = int(params.pop("bin", 0) or 0)
    fn = METHODS[name]
    t0 = time.perf_counter()
    if b > 1:
        yb, shape = data.bin_counts(y, b)
        xb, info = fn(yb, peak * b * b, **params)
        x_hat = data.unbin(xb, shape, b)
    else:
        x_hat, info = fn(y, peak, **params)
    info["time_total"] = time.perf_counter() - t0
    return x_hat, info


@register("ml")
def ml(y, peak):
    """Maximum-likelihood estimate x_hat = y. Lower reference only."""
    return y.astype(np.float64), {}


@register("anscombe")
def anscombe_gauss(y, peak, denoiser="bm3d", inverse="exact", sigma=1.0, denoiser_params=None):
    """Anscombe transform -> Gaussian denoiser at sigma=1 -> inverse.
    inverse in {'exact','closed_form','asymptotic','algebraic'}."""
    z = anscombe.forward(y)
    D = denoisers.get(denoiser)
    zd = D(z, float(sigma), **(denoiser_params or {}))
    return anscombe.INVERSES[inverse](zd), {}


@register("p4ip")
def p4ip_method(y, peak, priors, rho0, rho_step=1.0, n_iter=50, init="zero",
                rescale_dual=False, output="v", tol=0.0, init_params=None):
    """priors: list of dicts {denoiser, beta, rho_weight?, params?}.
    init='anscombe' warm-starts v from Anscombe+<denoiser> (an ablation; the
    paper initialises with zeros)."""
    if init == "anscombe":
        init, _ = anscombe_gauss(y, peak, **(init_params or {}))
    cfg = p4ip.P4IPConfig(
        priors=[p4ip.Prior(**p) for p in priors], rho0=float(rho0), rho_step=float(rho_step),
        n_iter=int(n_iter), init=init, rescale_dual=bool(rescale_dual), output=output,
        tol=float(tol))
    return p4ip.run(y, cfg, peak_hint=peak)
