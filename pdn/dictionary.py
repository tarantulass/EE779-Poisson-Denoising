"""Direction A2: learned dictionary on wavelet-domain patches (EE779.odp slides 10, 16).

Denoiser `wavelet_dict(r, sigma, dict=..., ...)`:
  for every P x P patch R_j r (stride s, last row/column always included):
    m_j = mean(R_j r)                     DC, passed through in every variant
    c_j = T (R_j r - m_j)                 T = W_p (1-level orthonormal Haar) or I
    split c_j into the coded part c_j^K and the passed part c_j^0 (dictionary 'll')
    alpha_j = OMP(B, c_j^K)  with ||c_j^K - B alpha_j||^2 <= n (gamma sigma)^2   (or T atoms)
    patch_j = T^T [B alpha_j ; c_j^0] + m_j
  x = sum_j w_j R_j^T patch_j / sum_j w_j R_j^T 1        (slide 16)

Variants are fixed at dictionary-learning time and stored in the .npz:
  domain='wavelet', ll='pass' : A2-default. B codes the 3(P/2)^2 detail coefficients;
                               the (P/2)^2 LL coefficients (minus DC) pass unchanged.
  domain='pixel'              : A2.0 control. B codes the P^2 mean-removed pixels.
  domain='wavelet', ll='code' : A2.1 null check. B codes all P^2 coefficients.
                               Because W_p is orthonormal and the DC is removed the same
                               way, this is a rotation of A2.0: equal up to learning noise.
Noise: W_p is orthonormal, so coefficient noise has the same sigma as pixels.
(Removing the mean slightly reduces the noise in the coded vector; this is the same
in all three variants.)
"""
from __future__ import annotations

import json
import os

import numpy as np

from .denoisers import register

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def haar_1d(P: int) -> np.ndarray:
    if P % 2:
        raise ValueError("P must be even for a 1-level Haar transform")
    H = np.zeros((P, P))
    s = 1 / np.sqrt(2)
    for i in range(P // 2):
        H[i, 2 * i] = H[i, 2 * i + 1] = s          # low-pass
        H[P // 2 + i, 2 * i] = s                     # high-pass
        H[P // 2 + i, 2 * i + 1] = -s
    return H


def patch_transform(P: int, domain: str):
    """Returns (T, ll_mask): T acts on row-major vec(patch) (P^2 x P^2, orthonormal)."""
    if domain == "pixel":
        return np.eye(P * P), np.zeros(P * P, bool)
    if domain != "wavelet":
        raise ValueError(domain)
    H = haar_1d(P)
    T = np.kron(H, H)  # vec(H X H^T) for row-major vec
    i, j = np.divmod(np.arange(P * P), P)
    ll = (i < P // 2) & (j < P // 2)
    return T, ll


def coded_mask(P, domain, ll):
    T, llm = patch_transform(P, domain)
    if domain == "wavelet" and ll == "pass":
        return T, ~llm
    return T, np.ones(P * P, bool)


def positions(n, P, s):
    idx = list(range(0, n - P + 1, s))
    if idx[-1] != n - P:
        idx.append(n - P)
    return np.array(idx)


def extract(r, P, s):
    from numpy.lib.stride_tricks import sliding_window_view

    win = sliding_window_view(r, (P, P))
    ys, xs = positions(r.shape[0], P, s), positions(r.shape[1], P, s)
    pat = win[ys][:, xs].reshape(-1, P * P)
    return pat, ys, xs


_CACHE: dict = {}


def load_dictionary(path):
    full = path if os.path.isabs(path) else os.path.join(REPO, path)
    if full not in _CACHE:
        z = np.load(full, allow_pickle=False)
        meta = json.loads(str(z["meta"]))
        B = z["B"].astype(np.float64)  # (n_coded, K)
        B /= np.maximum(np.linalg.norm(B, axis=0, keepdims=True), 1e-12)  # unit-norm atoms
        _CACHE[full] = (B, meta, B.T @ B)
    return _CACHE[full]


def batch_omp(G, Xy, norms, tol_sq=None, max_atoms=16, chunk=4000):
    """Batched OMP over all patches at once (numpy; equivalent to sklearn's per-patch
    Gram OMP). Stops a patch when ||c - B alpha||^2 <= tol_sq or after max_atoms atoms.
    G = B^T B (K x K), Xy = B^T C (K x M), norms = ||c_j||^2. Returns alpha (K x M)."""
    K, M = Xy.shape
    A = np.zeros((K, M))
    tol = -np.inf if tol_sq is None else float(tol_sq)
    for c0 in range(0, M, chunk):
        sl = slice(c0, min(c0 + chunk, M))
        xy, nr = Xy[:, sl], norms[sl]
        m = xy.shape[1]
        idx = np.zeros((m, max_atoms), dtype=np.int64)
        gam = [None] * m
        active = nr > tol
        res = xy.copy()                       # B^T (c - B alpha)
        for k in range(max_atoms):
            a = np.flatnonzero(active)
            if a.size == 0:
                break
            r = np.abs(res[:, a])
            if k:
                r[idx[a, :k].T, np.arange(a.size)] = 0.0   # never re-pick an atom
            idx[a, k] = np.argmax(r, axis=0)
            S = idx[a, :k + 1]                              # (n, k+1)
            Gs = G[S[:, :, None], S[:, None, :]]            # (n, k+1, k+1)
            b = xy[S, a[:, None]]                           # (n, k+1)
            g = np.linalg.solve(Gs, b[..., None])[..., 0]   # (n, k+1)
            err = nr[a] - np.einsum("ij,ij->i", b, g)
            # update residual correlations for the active patches
            res[:, a] = xy[:, a] - np.einsum("kni,ni->kn", G[:, S], g)
            for t, j in enumerate(a):
                gam[j] = (S[t].copy(), g[t].copy())
            active[a[err <= tol]] = False
        for j, sg in enumerate(gam):
            if sg is not None:
                A[sg[0], c0 + j] = sg[1]
    return A


def sparse_code(B, G, C, tol_sq=None, n_nonzero=None, max_atoms=16):
    """alpha for each column of C (n_coded x M): error-constrained (tol_sq, capped at
    max_atoms) or fixed sparsity (n_nonzero)."""
    norms = np.einsum("ij,ij->j", C, C)
    if n_nonzero is not None:
        return batch_omp(G, B.T @ C, norms, None, int(n_nonzero))
    return batch_omp(G, B.T @ C, norms, tol_sq, int(max_atoms))


@register("wavelet_dict")
def wavelet_dict(r: np.ndarray, sigma: float, dict: str = "models/a2_default.npz",
                 stride: int = 2, gamma: float = 1.15, sparsity: int | None = None,
                 weights: str = "uniform", max_atoms: int = 16) -> np.ndarray:
    """A2 denoiser. sparsity=T switches to fixed-sparsity OMP (A2.7);
    weights='sparsity' uses w_j = 1/(1+||alpha_j||_0) (A2.6).
    max_atoms caps error-constrained OMP (default P^2/4 = 16): late in P4IP sigma is
    small and uncapped OMP used ~30 atoms per patch (53 s per call on 256x256)."""
    r = np.asarray(r, dtype=np.float64)
    B, meta, G = load_dictionary(dict)
    P = int(meta["P"])
    T, cm = coded_mask(P, meta["domain"], meta["ll"])
    pat, ys, xs = extract(r, P, int(stride))
    m = pat.mean(axis=1, keepdims=True)
    C = (pat - m) @ T.T                      # rows: patches, cols: coefficients
    Ck = C[:, cm].T                          # n_coded x M
    n = Ck.shape[0]
    A = sparse_code(B, G, Ck, tol_sq=n * (gamma * sigma) ** 2, n_nonzero=sparsity,
                    max_atoms=max_atoms)
    C_hat = C.copy()
    C_hat[:, cm] = (B @ A).T
    rec = C_hat @ T + m                      # T orthonormal: T^{-1} = T^T
    l0 = np.count_nonzero(A, axis=0)
    if weights == "uniform":
        w = np.ones(len(l0))
    elif weights == "sparsity":
        w = 1.0 / (1.0 + l0)
    else:
        raise ValueError(weights)
    acc = np.zeros_like(r)
    cnt = np.zeros_like(r)
    YY, XX = np.meshgrid(ys, xs, indexing="ij")
    YY, XX = YY.ravel(), XX.ravel()
    rec = rec.reshape(-1, P, P)
    for di in range(P):
        for dj in range(P):
            np.add.at(acc, (YY + di, XX + dj), w * rec[:, di, dj])
            np.add.at(cnt, (YY + di, XX + dj), w)
    wavelet_dict.last_stats = {"mean_l0": float(l0.mean())}
    return acc / cnt


wavelet_dict.last_stats = {}


def learn(train_paths, P=8, K=256, domain="wavelet", ll="pass", n_patches=100_000,
          seed=0, sparsity=8, n_iter=20, scale=255.0, chunk=20_000):
    """Learn B on clean training patches with OMP (fixed sparsity) + MOD updates
    (Engan, Aase & Husoy 1999). Same patches, learner, sparsity and iterations for
    every variant (only domain/ll/P/K change). Atoms are renormalised to unit norm
    after each update; atoms unused in an iteration are re-seeded from random
    training vectors (seeded). Returns (B, meta); meta['rel_err'] traces the fit."""
    import time

    from sklearn.linear_model import orthogonal_mp_gram

    from . import data

    rng = np.random.default_rng(seed)
    imgs = [data.load_clean(p) for p in train_paths]
    per = int(np.ceil(n_patches / len(imgs)))
    rows = []
    for im in imgs:
        H, W = im.shape
        yy = rng.integers(0, H - P + 1, per)
        xx = rng.integers(0, W - P + 1, per)
        rows.append(np.stack([im[a:a + P, b:b + P].ravel() for a, b in zip(yy, xx)]))
    X = np.concatenate(rows)[:n_patches] * scale
    T, cm = coded_mask(P, domain, ll)
    Xc = ((X - X.mean(axis=1, keepdims=True)) @ T.T)[:, cm]
    Xc = Xc[np.linalg.norm(Xc, axis=1) > 1e-6].T          # n_coded x M (flat patches dropped)
    M = Xc.shape[1]
    t0 = time.perf_counter()
    B = Xc[:, rng.choice(M, K, replace=False)].copy()
    B /= np.linalg.norm(B, axis=0, keepdims=True)
    errs = []
    tot = float((Xc ** 2).sum())
    for it in range(n_iter):
        G = B.T @ B
        A = np.zeros((K, M))
        for a in range(0, M, chunk):
            A[:, a:a + chunk] = orthogonal_mp_gram(G, B.T @ Xc[:, a:a + chunk],
                                                   n_nonzero_coefs=sparsity).reshape(K, -1)
        errs.append(float(((Xc - B @ A) ** 2).sum()) / tot)
        AAt = A @ A.T
        B = np.linalg.solve(AAt + 1e-8 * np.eye(K), A @ Xc.T).T   # MOD: X A^T (A A^T)^-1
        nrm = np.linalg.norm(B, axis=0)
        dead = (nrm < 1e-10) | (np.abs(A).sum(axis=1) == 0)
        if dead.any():
            B[:, dead] = Xc[:, rng.choice(M, int(dead.sum()), replace=False)]
            nrm = np.linalg.norm(B, axis=0)
        B /= nrm
    meta = {"P": P, "K": K, "domain": domain, "ll": ll, "n_patches": int(M), "seed": seed,
            "sparsity": sparsity, "n_iter": n_iter, "scale": scale, "n_coded": int(cm.sum()),
            "learn_time_s": time.perf_counter() - t0, "train_images": len(train_paths),
            "learner": "OMP(fixed sparsity)+MOD", "rel_err": errs}
    return B, meta


def save_dictionary(path, B, meta):
    full = path if os.path.isabs(path) else os.path.join(REPO, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    np.savez_compressed(full, B=B.astype(np.float32), meta=json.dumps(meta))
