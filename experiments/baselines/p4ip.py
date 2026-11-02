"""P4IP: Plug-and-Play ADMM for Poisson denoising (slides 7, 8, 14, 15; Rond, Giryes & Elad).

Slide 7, one prior:
    x^{k+1} = argmin_{x>=0} f(x) + (rho/2)||x - v^k + u^k||^2      closed form, slide 8
    v^{k+1} = D(x^{k+1} + u^k, sigma),  sigma^2 = lam / rho          the plugged-in denoiser
    u^{k+1} = u^k + x^{k+1} - v^{k+1}

Slide 15, several priors (consensus x = v_1 = v_2 = ...): every prior j has its own v_j, u_j and
rho_j, and the x-step uses the same Poisson root with
    rho_eff = sum_j rho_j,   a = sum_j rho_j (v_j - u_j) / rho_eff.
Here every prior uses the same rho (rho_j = rho); each prior's own lam_j sets its strength.

As in the paper (Sec. 3.2), rho starts at rho0 and is multiplied by rho_step after every iteration,
and a fixed number of iterations is run. Start: v = u = 0. Output: x of the last iteration.

A prior is a function prior(r, rho) -> (v, stats); it knows its own lam.
"""
import bm3d
import numpy as np

from ..common import poisson_prox


def p4ip(y, priors, rho0, rho_step=1.065, n_iter=70):
    J = len(priors)
    v = [np.zeros_like(y) for _ in range(J)]
    u = [np.zeros_like(y) for _ in range(J)]
    rho = rho0
    x_prev = np.zeros_like(y)
    residuals, changes, stats = [], [], {}
    for _ in range(n_iter):
        a = sum(vj - uj for vj, uj in zip(v, u)) / J        # rho_j = rho for all j
        x = poisson_prox(a, y, J * rho)                     # rho_eff = J * rho
        for j, prior in enumerate(priors):
            v[j], stats = prior(x + u[j], rho)
            u[j] = u[j] + x - v[j]
        # convergence residuals (slide 12): primal ||x - v|| and change of x, per pixel
        residuals.append(float(np.sqrt(np.mean(sum((x - vj) ** 2 for vj in v) / J))))
        changes.append(float(np.sqrt(np.mean((x - x_prev) ** 2))))
        x_prev = x
        rho *= rho_step
    info = {"residuals": residuals, "changes": changes}
    info.update(stats)  # e.g. the sparsity of the last denoiser call
    return x, info


def bm3d_prior(lam):
    """v = BM3D(r, sigma) with sigma^2 = lam / rho (slide 7)."""
    return lambda r, rho: (bm3d.bm3d(r, sigma_psd=np.sqrt(lam / rho)), {})


def p4ip_bm3d(y, lam, rho0, rho_step=1.065, n_iter=70):
    return p4ip(y, [bm3d_prior(lam)], rho0, rho_step, n_iter)
