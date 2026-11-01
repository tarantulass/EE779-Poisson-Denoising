"""Conventional denoising methods (slide 3).

Slide 3: "For Poisson data we must adapt the noise model or first stabilize the variance."
  * mean, Gaussian, median, Wiener, wavelet thresholding and non-local means are Gaussian-noise
    methods, so they run on the Anscombe image z = 2 sqrt(y + 3/8) with sigma = 1 and are mapped
    back with the exact unbiased inverse (slide 4).
  * Poisson-TV keeps the exact Poisson likelihood:
        min_{x >= 0} sum_i (x_i - y_i log x_i) + lam TV(x)
    solved with the gradient-descent procedure written in TV.txt (steps 2-14).

Every function takes the noisy counts y and its parameters and returns (x_hat, info).
"""
import numpy as np
from scipy import ndimage, signal
from skimage.restoration import denoise_nl_means

from ..common import anscombe, inverse_anscombe_exact, wavelet_shrink


def _in_anscombe_domain(y, denoise_z):
    return inverse_anscombe_exact(denoise_z(anscombe(y))), {}


def mean_filter(y, size=3):
    return _in_anscombe_domain(y, lambda z: ndimage.uniform_filter(z, size, mode="reflect"))


def gaussian_filter(y, sigma=1.0):
    return _in_anscombe_domain(y, lambda z: ndimage.gaussian_filter(z, sigma, mode="reflect"))


def median_filter(y, size=3):
    return _in_anscombe_domain(y, lambda z: ndimage.median_filter(z, size, mode="reflect"))


def wiener_filter(y, size=5):
    """Local Wiener filter with the known noise variance 1 of the Anscombe image."""
    return _in_anscombe_domain(y, lambda z: signal.wiener(z, size, noise=1.0))


def wavelet_threshold(y, c=3.0, levels=4):
    """Soft thresholding at c * sigma (sigma = 1) in every detail level, coarse band kept."""
    z_hat, nnz = wavelet_shrink(anscombe(y), [c] * levels)
    return inverse_anscombe_exact(z_hat), {"sparsity": nnz}


def nl_means(y, h=1.0):
    """Non-local means, filtering strength h * sigma (sigma = 1)."""
    return _in_anscombe_domain(
        y, lambda z: denoise_nl_means(z, h=h, sigma=1.0, patch_size=5, patch_distance=6, fast_mode=True))


def poisson_tv(y, lam=0.1, tau=0.01, eps=1e-3, n_iter=500, tol=1e-4, floor=0.01):
    """Poisson-TV by gradient descent, exactly as in TV.txt."""
    x = y + floor                                               # step 2
    residuals = []
    for _ in range(n_iter):
        dh = np.zeros_like(x); dh[:, :-1] = x[:, 1:] - x[:, :-1]  # steps 4, 6
        dv = np.zeros_like(x); dv[:-1, :] = x[1:, :] - x[:-1, :]  # steps 5, 6
        m = np.sqrt(dh**2 + dv**2 + eps**2)                     # step 7
        ph, pv = dh / m, dv / m                                 # step 8
        div = ph.copy(); div[:, 1:] -= ph[:, :-1]              # step 9 (outside the image = 0)
        div += pv; div[1:, :] -= pv[:-1, :]
        g = (1 - y / x) - lam * div                             # steps 10, 11
        x_new = np.maximum(x - tau * g, floor)                  # steps 12, 13
        change = float(np.mean(np.abs(x_new - x)))
        residuals.append(change)
        x = x_new
        if change < tol:                                        # step 14
            break
    return x, {"iterations": len(residuals), "residuals": residuals}
