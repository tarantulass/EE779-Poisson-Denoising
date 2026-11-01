"""Shared pieces used by every method (slides 2, 4, 8, 12, 14 of output/EE779.odp).

    * images and the Poisson noise model         x = peak * s,  y ~ Poisson(x)       (slide 2)
    * binning (reported separately)                                                  (slide 12)
    * Anscombe transform and its inverses                                            (slide 4)
    * the closed-form Poisson proximal step used by P4IP                             (slides 8, 14)
    * PSNR / SSIM                                                                     (slide 12)
"""
import glob
import hashlib
import os

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
from scipy.stats import poisson
from skimage.metrics import structural_similarity

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PEAKS = [0.1, 0.2, 0.5, 1, 2, 4]  # slide 12


# ---------------------------------------------------------------- images and noise (slide 2)
def image_paths(split):
    """split = 'test' (8 images), 'tune' (4 images) or 'train' (400 images, dictionary learning only)."""
    return sorted(glob.glob(os.path.join(REPO, "data", split, "*.png")))


def image_name(path):
    return os.path.splitext(os.path.basename(path))[0]


def load_image(path):
    """Clean image s with max(s) = 1."""
    s = np.asarray(Image.open(path).convert("L"), dtype=np.float64)
    return s / s.max()


def noisy_image(s, peak, name, rep=0):
    """x = peak * s and y ~ Poisson(x). The seed depends only on (image, peak, rep), so every
    method sees exactly the same noisy image (slide 12: same test images and noise seeds)."""
    seed = int.from_bytes(hashlib.sha256(f"{name}|{float(peak)}|{rep}".encode()).digest()[:8], "little")
    x = peak * s
    y = np.random.default_rng(seed).poisson(x).astype(np.float64)
    return x, y


# ---------------------------------------------------------------- binning (slide 12, P4IP paper Sec. 3.2)
def bin_counts(y, b=3):
    """Sum the counts in b x b blocks (the image is padded symmetrically to a multiple of b)."""
    H, W = y.shape
    Hp, Wp = -(-H // b) * b, -(-W // b) * b
    y = np.pad(y, ((0, Hp - H), (0, Wp - W)), mode="symmetric")
    return y.reshape(Hp // b, b, Wp // b, b).sum(axis=(1, 3))


def unbin(xb, shape, b=3):
    """Divide by b^2 and upsample with linear interpolation (block centres are the samples)."""
    r = (np.arange(shape[0]) + 0.5) / b - 0.5
    c = (np.arange(shape[1]) + 0.5) / b - 0.5
    rr, cc = np.meshgrid(r, c, indexing="ij")
    return map_coordinates(xb / b**2, [rr, cc], order=1, mode="nearest")


# ---------------------------------------------------------------- Anscombe (slide 4)
def anscombe(y):
    return 2.0 * np.sqrt(y + 3.0 / 8.0)


def inverse_anscombe_algebraic(z):
    """z^2/4 - 3/8: biased at low counts (slide 4)."""
    return z**2 / 4.0 - 3.0 / 8.0


# Exact unbiased inverse (Makitalo & Foi 2011): the x with E[2 sqrt(y + 3/8) | x] = z.
# E[.] is computed by summing the Poisson pmf on a dense grid of x, then inverted by interpolation.
_X = np.concatenate([np.linspace(0, 1, 2001)[:-1], np.linspace(1, 60, 5901)])
_K = np.arange(200)
_EZ = poisson.pmf(_K[None, :], _X[:, None]) @ anscombe(_K)


def inverse_anscombe_exact(z):
    z = np.asarray(z, dtype=np.float64)
    out = np.interp(z, _EZ, _X)  # z below E[A(y)|x=0] maps to 0
    hi = z > _EZ[-1]  # above x = 60 the Makitalo-Foi closed form is exact to < 1e-6
    a = np.sqrt(1.5)
    zh = z[hi]
    out[hi] = zh**2 / 4 + a / (4 * zh) - 11 / (8 * zh**2) + 5 * a / (8 * zh**3) - 1 / 8
    return out


INVERSE = {"exact": inverse_anscombe_exact, "algebraic": inverse_anscombe_algebraic}


# ---------------------------------------------------------------- Poisson likelihood step (slides 8, 14)
def poisson_prox(a, y, rho):
    """argmin_{x >= 0} x - y log x + (rho/2)(x - a)^2, pixel by pixel.

    Positive root x* = [rho a - 1 + sqrt((rho a - 1)^2 + 4 rho y)] / (2 rho).
    With b = a - 1/rho this is (b + sqrt(b^2 + 4y/rho)) / 2; when b < 0 we use the equivalent
    (2y/rho) / (sqrt(b^2 + 4y/rho) - b), which avoids cancellation (slide 14).
    For y = 0 both give max(b, 0), the boundary solution.
    """
    b = a - 1.0 / rho
    root = np.sqrt(b * b + 4.0 * y / rho)
    with np.errstate(divide="ignore", invalid="ignore"):
        small = np.where(root - b > 0, (2.0 * y / rho) / (root - b), 0.0)
    return np.where(b >= 0, 0.5 * (b + root), small)


def poisson_nll(x, y):
    """f(x) = sum x - y log x (slide 7), with 0 log 0 = 0."""
    with np.errstate(divide="ignore"):
        return float(np.sum(x) - np.sum(np.where(y > 0, y * np.log(x), 0.0)))


# ---------------------------------------------------------------- orthonormal wavelet shrinkage (slides 3, 10, 15)
def wavelet_shrink(r, thresholds, wavelet="db4", hard=False):
    """D(r, eta) = W^T S(W r, eta) with an orthonormal 2-D DWT W (slide 10).

    thresholds: one eta per detail level, finest first, e.g. [eta1, eta2, eta3, eta4] for 4 levels.
    The coarse (approximation) band is kept, as slide 10 suggests.
    Returns (estimate, fraction of nonzero detail coefficients).
    """
    import pywt

    J = len(thresholds)
    H, W = r.shape
    m = 2**J  # periodized DWT needs sides divisible by 2^J: pad symmetrically, crop afterwards
    rp = np.pad(r, ((0, -H % m), (0, -W % m)), mode="symmetric")
    coeffs = pywt.wavedec2(rp, wavelet, mode="periodization", level=J)
    nnz = tot = 0
    for i in range(1, J + 1):  # coeffs[1] is the coarsest detail level, coeffs[J] the finest
        eta = thresholds[J - i]
        bands = []
        for c in coeffs[i]:
            c = np.where(np.abs(c) > eta, c, 0.0) if hard else np.sign(c) * np.maximum(np.abs(c) - eta, 0.0)
            nnz, tot = nnz + np.count_nonzero(c), tot + c.size
            bands.append(c)
        coeffs[i] = tuple(bands)
    out = pywt.waverec2(coeffs, wavelet, mode="periodization")[:H, :W]
    return out, nnz / tot


# ---------------------------------------------------------------- metrics (slide 12)
def psnr(x_hat, x, peak):
    """PSNR on the peak scale, 10 log10(peak^2 / MSE), as in the P4IP and SPDA papers."""
    return float(10 * np.log10(peak**2 / np.mean((x_hat - x) ** 2)))


def ssim(x_hat, x, peak):
    return float(structural_similarity(x_hat / peak, x / peak, data_range=1.0))
