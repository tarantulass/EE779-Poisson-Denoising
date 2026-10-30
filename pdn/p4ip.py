"""P4IP: Plug-and-Play ADMM for Poisson denoising (Rond, Giryes & Elad 2015).

Notation follows EE779.odp (slides 7, 8, 14, 15): rho is the ADMM penalty
(the paper's lambda), beta is the prior weight (the paper's beta), and the
denoiser is called with sigma^2 = beta / rho.

    x^{k+1} = argmin_{x>=0} sum_i (x_i - y_i log x_i) + (rho_eff/2)||x - a||^2
              a = sum_j rho_j (v_j - u_j) / rho_eff,  rho_eff = sum_j rho_j
    v_j^{k+1} = D_j(x^{k+1} + u_j, sqrt(beta_j / rho_j))
    u_j^{k+1} = u_j + x^{k+1} - v_j^{k+1}
    rho_j <- rho_j * rho_step                      (paper: increasing penalty)

With one prior this is exactly Algorithm 1 of the paper (H = I). With two
priors it is the M-P4IP / consensus split of slide 15.

Choices the paper leaves open are explicit arguments so they can be ablated:
  init        'zero' (paper) | 'y' | an array (e.g. an Anscombe-BM3D estimate)
  rescale_dual  False (paper Alg. 1) | True (Boyd et al.: u *= rho_old/rho_new,
                which keeps the unscaled dual constant when rho changes)
  output      'v' (denoiser output, default) | 'x' (likelihood step output)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from . import denoisers


def poisson_prox(a: np.ndarray, y: np.ndarray, rho: float) -> np.ndarray:
    """argmin_{x>=0} x - y log x + (rho/2)(x - a)^2, elementwise, closed form.

    Positive root of rho x^2 + (1 - rho a) x - y = 0. With b = a - 1/rho:
      b >= 0: x = (b + sqrt(b^2 + 4y/rho)) / 2
      b <  0: x = (2y/rho) / (sqrt(b^2 + 4y/rho) - b)   (no cancellation)
    For y = 0 this gives max(b, 0), the boundary solution.
    """
    b = a - 1.0 / rho
    disc = np.sqrt(b * b + 4.0 * y / rho)
    out = np.empty_like(b)
    pos = b >= 0
    out[pos] = 0.5 * (b[pos] + disc[pos])
    neg = ~pos
    denom = disc[neg] - b[neg]  # > 0 whenever b < 0
    out[neg] = (2.0 * y[neg] / rho) / denom
    return out


def poisson_nll(x: np.ndarray, y: np.ndarray) -> float:
    """sum x - y log x with 0 log 0 = 0 (inf if y > 0 at x = 0)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(y > 0, y * np.log(x), 0.0)
    return float(np.sum(x) - np.sum(t))


@dataclass
class Prior:
    denoiser: str
    beta: float
    rho_weight: float = 1.0  # rho_j = rho_weight * rho (shared schedule)
    params: dict = field(default_factory=dict)


@dataclass
class P4IPConfig:
    priors: list[Prior]
    rho0: float
    rho_step: float = 1.0
    n_iter: int = 50
    init: object = "zero"
    rescale_dual: bool = False
    output: str = "v"
    tol: float = 0.0  # stop early if ||v - v_prev||/sqrt(N) / peak < tol; 0 = fixed iterations


def run(y: np.ndarray, cfg: P4IPConfig, peak_hint: float | None = None, log: bool = True,
        callback=None):
    """Returns (x_hat, info). info['trace'] has one dict per iteration.
    callback(k, x, v_list) -> dict | None is merged into that iteration's trace
    entry (e.g. PSNR vs iteration in analysis scripts; never used by methods)."""
    J = len(cfg.priors)
    N = y.size
    D = [denoisers.get(p.denoiser) for p in cfg.priors]

    if isinstance(cfg.init, np.ndarray):
        v0 = cfg.init.astype(np.float64)
    elif cfg.init == "zero":
        v0 = np.zeros_like(y)
    elif cfg.init == "y":
        v0 = y.astype(np.float64).copy()
    else:
        raise ValueError(cfg.init)
    v = [v0.copy() for _ in range(J)]
    u = [np.zeros_like(y) for _ in range(J)]
    rho = cfg.rho0
    scale = peak_hint if peak_hint else max(float(y.mean()), 1e-12)

    trace = []
    t_den = 0.0
    t0 = time.perf_counter()
    x = None
    for k in range(cfg.n_iter):
        rhos = [p.rho_weight * rho for p in cfg.priors]
        rho_eff = sum(rhos)
        a = sum(r_j * (v[j] - u[j]) for j, r_j in enumerate(rhos)) / rho_eff
        x = poisson_prox(a, y, rho_eff)

        v_prev = [vj.copy() for vj in v]
        sig = []
        for j, p in enumerate(cfg.priors):
            s_j = float(np.sqrt(p.beta / rhos[j]))
            sig.append(s_j)
            td = time.perf_counter()
            v[j] = D[j](x + u[j], s_j, **p.params)
            t_den += time.perf_counter() - td
            u[j] = u[j] + x - v[j]

        if log:
            primal = max(float(np.linalg.norm(x - v[j])) for j in range(J)) / np.sqrt(N)
            change = max(float(np.linalg.norm(v[j] - v_prev[j])) for j in range(J)) / np.sqrt(N)
            nll = poisson_nll(np.maximum(x, 0), y)
            entry = {
                "iter": k + 1, "rho": rho, "sigma": sig[0] if J == 1 else sig,
                "primal_res": primal / scale, "v_change": change / scale, "nll": nll,
            }
            for j in range(J):  # e.g. sparsity of a wavelet prior
                st = getattr(D[j], "last_stats", None)
                if st:
                    entry.update({(f"p{j}_{kk}" if J > 1 else kk): vv for kk, vv in st.items()})
            # explicit objective f(x) + sum_j beta_j g_j(x), only when every prior is
            # the exact prox of a known g_j (e.g. A1.a); otherwise not logged
            pens = [getattr(D[j], "penalty", None) for j in range(J)]
            if all(pens):
                vals = [pens[j](x, **cfg.priors[j].params) for j in range(J)]
                if all(vv is not None for vv in vals):
                    entry["objective"] = nll + sum(p.beta * vv for p, vv in zip(cfg.priors, vals))
            trace.append(entry)
        if callback is not None:
            extra = callback(k + 1, x, v)
            if extra and log:
                trace[-1].update(extra)

        rho_new = rho * cfg.rho_step
        if cfg.rescale_dual and rho_new != rho:
            u = [uj * (rho / rho_new) for uj in u]
        rho = rho_new

        if cfg.tol > 0 and k > 0:
            change = max(float(np.linalg.norm(v[j] - v_prev[j])) for j in range(J)) / np.sqrt(N)
            if change / scale < cfg.tol:
                break

    if cfg.output == "v":
        x_hat = sum(v) / J
    elif cfg.output == "x":
        x_hat = x
    else:
        raise ValueError(cfg.output)
    info = {"iters": k + 1, "time_total": time.perf_counter() - t0, "time_denoiser": t_den,
            "trace": trace}
    return x_hat, info
