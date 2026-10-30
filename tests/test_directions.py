"""Correctness tests for the direction A and B code (no results are claimed here)."""
import numpy as np
import pywt
import pytest

from pdn import dictionary, p4ip, sparse, wavelet

RNG = np.random.default_rng(0)


# ---------------------------------------------------------------- A1 wavelet prior
def test_dwt_periodization_is_orthonormal():
    x = RNG.normal(size=(64, 64))
    c = pywt.wavedec2(x, "db4", mode="periodization", level=4)
    e = sum(np.sum(a ** 2) for a in [c[0]] + [b for t in c[1:] for b in t])
    assert np.isclose(e, np.sum(x ** 2))


def test_a1a_is_exact_prox_of_weighted_l1():
    """eta='sigma2': D(r, s) = argmin_v 1/2||v-r||^2 + s^2 ||W_d v||_1.
    Check the optimality condition in the coefficient domain."""
    r = RNG.normal(5, 2, (64, 64))
    s = 0.9
    t = s ** 2
    v = wavelet.wavelet_soft(r, s, eta="sigma2", levels=3)
    cr = pywt.wavedec2(r, "db4", mode="periodization", level=3)
    cv = pywt.wavedec2(v, "db4", mode="periodization", level=3)
    assert np.allclose(cv[0], cr[0])                      # approximation band untouched
    for br, bv in zip(cr[1:], cv[1:]):
        for a, b in zip(br, bv):
            g = (a - b) / t                                # must be a subgradient of |.| at b
            nz = np.abs(b) > 1e-10  # exact zeros come back as ~1e-15 after re-analysis
            assert np.allclose(g[nz], np.sign(b[nz]))
            assert np.all(np.abs(g[~nz]) <= 1 + 1e-9)


def test_a1_c_sigma_beta_and_c_confounded():
    """Documents why A1-default tunes (c, rho0) with beta fixed: only c*sqrt(beta) matters."""
    r = RNG.normal(5, 2, (64, 64))
    a = wavelet.wavelet_soft(r, np.sqrt(4.0), c=1.5)
    b = wavelet.wavelet_soft(r, np.sqrt(1.0), c=3.0)
    assert np.allclose(a, b)


def test_cycle_spin_and_hard_run():
    r = RNG.normal(5, 2, (64, 64))
    for kw in ({"cycle_spin": 4}, {"threshold": "hard"}, {"threshold_ll": True},
               {"c": [1, 2, 3, 4]}, {"wavelet": "haar"}):
        out = wavelet.wavelet_soft(r, 1.0, **kw)
        assert out.shape == r.shape and np.all(np.isfinite(out))


def test_odd_size_padding():
    r = RNG.normal(5, 2, (86, 86))  # 3x3-binned 256 image
    out = wavelet.wavelet_soft(r, 1.0)
    assert out.shape == r.shape
    assert wavelet._penalty(r, eta="sigma2") is None     # not an exact prox there


def test_p4ip_wavelet_l1_converges_to_minimiser():
    """A1.a with constant rho: ADMM on sum(x - y log x) + beta ||W_d x||_1. The final
    iterate must be (near) optimal: no small positive perturbation lowers the objective
    noticeably, and the objective has settled."""
    s = np.clip(RNG.normal(4, 1.5, (32, 32)), 0.2, None)
    y = RNG.poisson(s).astype(float)
    beta = 0.5
    prm = {"eta": "sigma2", "levels": 2}
    cfg = p4ip.P4IPConfig(priors=[p4ip.Prior("wavelet_soft", beta, params=prm)], rho0=1.0,
                          rho_step=1.0, n_iter=1500, output="x")
    x, info = p4ip.run(y, cfg)
    objs = [t["objective"] for t in info["trace"]]
    assert abs(objs[-1] - objs[-200]) < 1e-6 * abs(objs[-1])

    def obj(z):
        return p4ip.poisson_nll(z, y) + beta * wavelet._penalty(z, **prm)

    f0 = obj(x)
    for _ in range(20):
        d = RNG.normal(size=x.shape) * 1e-3
        z = np.maximum(x + d, 1e-9)
        assert obj(z) >= f0 - 1e-6 * abs(f0)


# ---------------------------------------------------------------- A2 dictionary prior
def test_patch_haar_orthonormal():
    for P in (6, 8):
        T, ll = dictionary.patch_transform(P, "wavelet")
        assert np.allclose(T @ T.T, np.eye(P * P))
        assert ll.sum() == (P // 2) ** 2


def _save(tmp_path, name, B, P, domain, ll):
    path = str(tmp_path / f"{name}.npz")
    dictionary.save_dictionary(path, B, {"P": P, "K": B.shape[1], "domain": domain, "ll": ll})
    return path


def test_complete_dictionary_at_zero_noise_returns_input(tmp_path):
    P = 8
    path = _save(tmp_path, "eye", np.eye(48), P, "wavelet", "pass")
    r = RNG.normal(5, 2, (40, 40))
    out = dictionary.wavelet_dict(r, 1e-6, dict=path, stride=3, max_atoms=48)
    assert np.allclose(out, r, atol=1e-6)


def test_a2_1_free_wavelet_dict_equals_rotated_pixel_dict(tmp_path):
    """The A2.1 null check is exact in the coder: B_w = T B_pix gives the same output."""
    P, K = 8, 96
    Bp = RNG.normal(size=(64, K)); Bp /= np.linalg.norm(Bp, axis=0)
    T, _ = dictionary.patch_transform(P, "wavelet")
    pa = _save(tmp_path, "pix", Bp, P, "pixel", "code")
    pb = _save(tmp_path, "wav", T @ Bp, P, "wavelet", "code")
    dictionary._CACHE.clear()
    r = RNG.normal(5, 2, (32, 32))
    a = dictionary.wavelet_dict(r, 0.8, dict=pa, stride=2)
    b = dictionary.wavelet_dict(r, 0.8, dict=pb, stride=2)
    assert np.allclose(a, b, atol=1e-4)  # float32 storage of B


def test_dictionary_variants_run(tmp_path):
    B = RNG.normal(size=(48, 64)); B /= np.linalg.norm(B, axis=0)
    path = _save(tmp_path, "d", B, 8, "wavelet", "pass")
    r = RNG.normal(5, 2, (32, 32))
    for kw in ({"sparsity": 2}, {"weights": "sparsity"}, {"stride": 1}):
        out = dictionary.wavelet_dict(r, 1.0, dict=path, **kw)
        assert out.shape == r.shape and np.all(np.isfinite(out))
    assert dictionary.wavelet_dict.last_stats["mean_l0"] >= 0


# ---------------------------------------------------------------- B1 ISTA / FISTA
def test_swt_is_parseval_and_iswt_is_adjoint():
    fr = sparse.SWTFrame((64, 64), "db4", 3)
    x = RNG.normal(size=(64, 64))
    a = fr.analysis(x)
    assert np.isclose(np.sum(a ** 2), np.sum(x ** 2))
    c = RNG.normal(size=a.shape)
    assert np.isclose(np.sum(a * c), np.sum(x * fr.synthesis(c)))
    assert np.allclose(fr.synthesis(a), x)


@pytest.mark.parametrize("solver", ["ista", "fista"])
def test_b1_0_orthonormal_converges_to_one_step(solver):
    z = RNG.normal(3, 1, (64, 64))
    fr = sparse.DWTFrame((64, 64), "db4", 3)
    a1, _ = sparse.solve(z, 0.7, fr, solver="one_step")
    a2, tr = sparse.solve(z, 0.7, fr, solver=solver, max_iter=500, tol=0)
    assert np.allclose(a1, a2, atol=1e-8)


def test_fista_not_slower_than_ista_and_backtracking_same_minimiser():
    z = RNG.normal(3, 1, (64, 64))
    fr = sparse.SWTFrame((64, 64), "db4", 2)
    _, ti = sparse.solve(z, 0.5, fr, solver="ista", max_iter=50, tol=0)
    _, tf = sparse.solve(z, 0.5, fr, solver="fista", max_iter=50, tol=0)
    a_star, ts = sparse.solve(z, 0.5, fr, solver="fista", max_iter=3000, tol=0)
    Fs = ts[-1]["F"]
    assert tf[-1]["F"] - Fs <= ti[-1]["F"] - Fs + 1e-9
    _, tb = sparse.solve(z, 0.5, fr, solver="fista", max_iter=3000, tol=0, L=0.1, backtracking=True)
    assert abs(tb[-1]["F"] - Fs) < 1e-6 * Fs  # same minimiser (fixed coarse band: well posed)
    assert tb[-1]["L"] > 0.5  # grew from 0.1 to near the true L = 1


def test_fixed_coarse_band_keeps_local_mean():
    """approx='fixed' must not shrink the coarse band (the failure of 'penalized')."""
    z = RNG.normal(3, 1, (64, 64))
    fr = sparse.SWTFrame((64, 64), "db4", 3)
    a, _ = sparse.solve(z, 1.0, fr, solver="fista", max_iter=300, tol=1e-8)
    assert np.allclose(a[0], fr.analysis(z)[0])
    assert abs(fr.synthesis(a).mean() - z.mean()) < 0.05


def test_batch_omp_matches_sklearn():
    from sklearn.linear_model import orthogonal_mp_gram
    B = RNG.normal(size=(48, 128)); B /= np.linalg.norm(B, axis=0)
    C = RNG.normal(size=(48, 500))
    G, nr = B.T @ B, (C ** 2).sum(0)
    tol = 0.3 * nr.mean()
    a = dictionary.batch_omp(G, B.T @ C, nr, tol, 48, chunk=128)
    b = orthogonal_mp_gram(G, B.T @ C, tol=tol, norms_squared=nr)
    assert np.allclose(a, b, atol=1e-10)
    a = dictionary.batch_omp(G, B.T @ C, nr, None, 5)
    b = orthogonal_mp_gram(G, B.T @ C, n_nonzero_coefs=5)
    assert np.allclose(a, b, atol=1e-10)
    a = dictionary.batch_omp(G, B.T @ C, nr, 1e-12, 3)   # cap binds
    assert np.all(np.count_nonzero(a, axis=0) <= 3)
