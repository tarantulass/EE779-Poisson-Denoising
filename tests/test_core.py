"""Checks of the formulas on the slides.   python -m pytest -q tests"""
import numpy as np
import pywt
from scipy.stats import poisson

from experiments.common import (anscombe, bin_counts, inverse_anscombe_exact, poisson_prox, unbin,
                                wavelet_shrink)
from experiments.direction_b.ista_fista import SWT, objective, solve


def test_poisson_prox_is_the_minimiser():  # slides 8, 14
    rng = np.random.default_rng(0)
    a = rng.normal(0, 2, 200); y = rng.poisson(1.0, 200).astype(float); rho = 0.7
    x = poisson_prox(a, y, rho)
    grid = np.linspace(1e-9, 15, 300001)
    for ai, yi, xi in zip(a[:20], y[:20], x[:20]):
        phi = grid - yi * np.log(grid) + rho / 2 * (grid - ai) ** 2
        assert abs(xi - grid[np.argmin(phi)]) < 1e-3
    assert np.all(x[y == 0] == np.maximum(a[y == 0] - 1 / rho, 0))


def test_exact_inverse_anscombe_is_unbiased():  # slide 4
    k = np.arange(400)
    for x in [0.05, 0.3, 1.0, 4.0, 20.0]:
        ez = np.sum(poisson.pmf(k, x) * anscombe(k))
        assert abs(inverse_anscombe_exact(np.array([ez]))[0] - x) < 1e-4


def test_wavelet_shrink():  # slide 10
    r = np.random.default_rng(1).normal(size=(64, 64))
    assert np.allclose(wavelet_shrink(r, [0, 0, 0, 0])[0], r)  # orthonormal: zero threshold = identity
    big = wavelet_shrink(r, [1e9] * 4)[0]  # all details removed: only the coarse band is left
    assert np.allclose(big.mean(), r.mean())


def test_binning_keeps_a_constant_image():  # slide 12
    y = np.full((256, 256), 0.3)
    assert np.allclose(unbin(bin_counts(y, 3), y.shape, 3), 0.3)


class OrthonormalDWT:
    """D = W^T for an orthonormal DWT: slide 17 says the solution is one soft-threshold step."""
    def __init__(self, shape):
        self.slices = None; self.L = 1.0; self.shape = shape
        a, self.slices = pywt.coeffs_to_array(pywt.wavedec2(np.zeros(shape), "db4", "periodization", 3))
        self.weights = np.ones_like(a); self.weights[self.slices[0]] = 0

    def fixed(self, z):
        return self.analysis(z)

    def analysis(self, img):
        return pywt.coeffs_to_array(pywt.wavedec2(img, "db4", "periodization", 3))[0]

    def synthesis(self, a):
        return pywt.waverec2(pywt.array_to_coeffs(a, self.slices, "wavedec2"), "db4", "periodization")


def test_ista_fista_orthonormal_special_case():  # slide 17
    z = np.random.default_rng(2).normal(2, 1, (64, 64))
    D, lam = OrthonormalDWT(z.shape), 0.7
    c = D.analysis(z)
    one_step = np.sign(c) * np.maximum(np.abs(c) - lam * D.weights, 0)
    for acc in (False, True):
        a, _ = solve(z, D, lam, accelerated=acc, tol=1e-12)
        assert np.allclose(a, one_step, atol=1e-8)


def test_ista_and_fista_reach_the_same_objective():  # slide 11, redundant frame
    z = anscombe(np.random.default_rng(3).poisson(2.0, (64, 64)).astype(float))
    D = SWT(z.shape)
    assert np.allclose(D.synthesis(D.analysis(z)), z)  # Parseval frame
    Fi = solve(z, D, 0.5, False, max_iter=5000, tol=1e-10)[1]
    Ff = solve(z, D, 0.5, True, max_iter=5000, tol=1e-10)[1]
    assert abs(Fi[-1] - Ff[-1]) < 1e-4 * Ff[-1]
    assert len(Ff) < len(Fi)  # FISTA needs fewer iterations


def test_patch_haar_and_split_merge():  # slide 16
    from experiments.direction_a.a2_dictionary import W_P, merge, split
    assert np.allclose(W_P @ W_P.T, np.eye(64))
    P = np.random.default_rng(4).random((10, 64))
    for d in ("wavelet", "pixel"):
        assert np.allclose(merge(*split(P, d), d), P)
