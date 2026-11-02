"""A3: BM3D + wavelet consensus prior (slide 10, backup slide 15).

    min f(x) + lam1 R1(v1) + lam2 R2(v2)   s.t.  x = v1 = v2
    x+  = Poisson root with rho_eff = rho1 + rho2 and a = [rho1 (v1 - u1) + rho2 (v2 - u2)] / rho_eff
    v1+ = BM3D(x+ + u1; sigma1),  sigma1^2 = lam1 / rho1
    v2+ = W^T S(W (x+ + u2), lam2 / rho2)
    uj+ = uj + x+ - vj+

The two-prior loop is the general case of baselines/p4ip.py (rho1 = rho2 = rho there).
"""
from ..baselines.p4ip import bm3d_prior, p4ip
from .a1_wavelet import wavelet_prior


def p4ip_bm3d_wavelet(y, lam1, lam2, rho0, rho_step=1.065, n_iter=70):
    return p4ip(y, [bm3d_prior(lam1), wavelet_prior(lam2)], rho0, rho_step, n_iter)
