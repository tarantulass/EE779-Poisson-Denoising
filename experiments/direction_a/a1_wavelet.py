"""A1: orthonormal wavelet shrinkage as the P4IP denoiser (slide 10).

    D(r, eta) = W^T S(W r, eta),   S(c, eta) = sign(c) max(|c| - eta, 0)

P4IP's Poisson x-step is kept unchanged (baselines/p4ip.py); only the v-step changes. For the
unweighted l1 wavelet penalty lam ||W_d v||_1 the exact proximal step has eta = lam / rho
(slide 10 notes), so this P4IP solves a real convex MAP problem.
"Tune thresholds by wavelet subband": level l gets eta_l = w_l * lam / rho. A1 uses w_l = 1 for
every level; A1_subband tunes the weights w_l on the tune split. The coarse band is not
thresholded (slide 10 notes).
"""
from ..baselines.p4ip import p4ip
from ..common import wavelet_shrink


def wavelet_prior(lam, level_weights=(1, 1, 1, 1), wavelet="db4"):
    def prior(r, rho):
        v, nnz = wavelet_shrink(r, [w * lam / rho for w in level_weights], wavelet)
        return v, {"sparsity": nnz}
    return prior


def p4ip_wavelet(y, lam, rho0, w1=1.0, w2=1.0, w3=1.0, w4=1.0, rho_step=1.065, n_iter=70):
    """w1 is the finest level, w4 the coarsest detail level."""
    return p4ip(y, [wavelet_prior(lam, (w1, w2, w3, w4))], rho0, rho_step, n_iter)
