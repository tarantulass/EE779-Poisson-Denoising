import numpy as np
import pytest
from scipy.optimize import minimize_scalar

from pdn import anscombe, data, denoisers, methods, p4ip


def test_poisson_prox_matches_numerical_minimiser():
    rng = np.random.default_rng(0)
    a = rng.uniform(-3, 5, 400)
    y = rng.poisson(1.5, 400).astype(float)
    for rho in (0.05, 0.5, 5.0, 500.0):
        x = p4ip.poisson_prox(a, y, rho)
        assert np.all(x >= 0)
        for ai, yi, xi in zip(a[:60], y[:60], x[:60]):
            f = lambda t: t - (yi * np.log(t) if yi > 0 else 0) + rho / 2 * (t - ai) ** 2
            r = minimize_scalar(f, bounds=(1e-14, 50), method="bounded", options={"xatol": 1e-12})
            ref = r.x if (yi > 0 or ai - 1 / rho > 0) else 0.0
            assert abs(xi - ref) < 1e-5 * max(1, ref)


def test_poisson_prox_no_cancellation_large_rho_negative_b():
    # b << 0, small y: naive (b + sqrt(b^2+4y/rho))/2 loses all digits
    x = p4ip.poisson_prox(np.array([-1e4]), np.array([1.0]), 1e6)
    b = -1e4 - 1e-6
    exact = 1.0 / (1e6 * -b)  # leading order of the positive root
    assert x[0] > 0 and abs(x[0] - exact) / exact < 1e-6


def test_exact_unbiased_inverse_is_unbiased():
    xs = np.array([0.05, 0.2, 1.0, 3.0, 10.0, 40.0])
    D = anscombe._expected_anscombe(xs)
    assert np.allclose(anscombe.inverse_exact_unbiased(D), xs, rtol=1e-4, atol=1e-4)
    assert anscombe.inverse_exact_unbiased(np.array([0.5]))[0] == 0.0  # below E[A|0]


def test_noise_is_deterministic_and_method_independent():
    s = data.load_clean(data.list_images("test")[0])
    _, y1 = data.simulate(s, 0.2, "a", 0)
    _, y2 = data.simulate(s, 0.2, "a", 0)
    _, y3 = data.simulate(s, 0.2, "a", 1)
    assert np.array_equal(y1, y2) and not np.array_equal(y1, y3)


def test_noise_statistics():
    s = np.full((300, 300), 1.0)
    x, y = data.simulate(s, 0.2, "flat", 0)
    assert abs(y.mean() - 0.2) < 0.01 and abs(y.var() - 0.2) < 0.01


def test_binning_conserves_counts_and_unbin_constant():
    y = np.random.default_rng(1).poisson(0.3, (256, 256)).astype(float)
    yb, shape = data.bin_counts(y, 3)
    assert yb.shape == (86, 86)
    assert data.unbin(np.full((86, 86), 9.0), shape, 3) == pytest.approx(np.ones((256, 256)))


def test_split_disjoint():
    names = {s: {data.image_name(p) for p in data.list_images(s)} for s in data.SPLITS}
    assert len(names["test"]) == 8 and len(names["tune"]) == 4 and len(names["train"]) == 400
    assert not (names["test"] & names["tune"]) and not (names["test"] & names["train"])


def test_p4ip_identity_prior_returns_ml_estimate():
    y = np.random.default_rng(2).poisson(2.0, (32, 32)).astype(float)
    x, info = methods.run_method("p4ip", y, 2.0, {
        "priors": [{"denoiser": "identity", "beta": 1.0}], "rho0": 1.0, "n_iter": 300})
    assert np.allclose(x, y, atol=1e-3)


@pytest.fixture(scope="module")
def ridge():
    # exact prox of R(v)=||v||^2/2 with weight beta at sigma^2=beta/rho
    if "_ridge_test" not in denoisers.DENOISERS:
        denoisers.register("_ridge_test")(lambda r, sigma: r / (1.0 + sigma**2))
    return "_ridge_test"


def test_p4ip_converges_to_explicit_map_solution(ridge):
    """Checks the sigma^2 = beta/rho convention and the whole ADMM loop against
    argmin sum(x - y log x) + beta/2 ||x||^2, solved per pixel in closed form."""
    y = np.random.default_rng(3).poisson(3.0, (16, 16)).astype(float)
    beta = 0.4
    x_map = (-1 + np.sqrt(1 + 4 * beta * y)) / (2 * beta)
    for rescale in (False, True):
        x, _ = methods.run_method("p4ip", y, 3.0, {
            "priors": [{"denoiser": ridge, "beta": beta}], "rho0": 1.0, "n_iter": 400,
            "rescale_dual": rescale, "output": "x"})
        assert np.allclose(x, x_map, atol=1e-6)


def test_two_prior_split_equals_single_prior_with_summed_weight(ridge):
    """Consensus split (slide 15) with two identical ridge priors of weight b/2
    must reach the same MAP point as one prior of weight b."""
    y = np.random.default_rng(4).poisson(3.0, (16, 16)).astype(float)
    beta = 0.4
    x_map = (-1 + np.sqrt(1 + 4 * beta * y)) / (2 * beta)
    x, _ = methods.run_method("p4ip", y, 3.0, {
        "priors": [{"denoiser": ridge, "beta": beta / 2}, {"denoiser": ridge, "beta": beta / 2}],
        "rho0": 1.0, "n_iter": 600, "output": "x"})
    assert np.allclose(x, x_map, atol=1e-5)
