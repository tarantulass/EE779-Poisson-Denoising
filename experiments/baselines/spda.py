"""SPDA: Sparse Poisson Denoising Algorithm (slide 6; Giryes & Elad, IEEE TIP 2014).

Model (slide 6): a clean patch is p_j = exp(D alpha_j) with ||alpha_j||_0 <= K, and for the
noisy count patch q_j the sparse code solves
    min_alpha  1^T exp(D alpha) - q_j^T D alpha     s.t. ||alpha||_0 <= K.

Steps, as on slide 6:
    1. group similar patches (k-means)
    2. greedy pursuit with a support shared by every patch of a group: start from the DC atom,
       add the atom with the largest summed squared gradient over the group, re-fit the
       coefficients of every patch on the support (Newton), until K atoms are used
    3. alternate sparse coding and dictionary updates (gradient steps on the Poisson
       likelihood, atoms renormalised)
    4. aggregate the overlapping patch estimates exp(D alpha_j) by averaging

Simplifications relative to the paper (to keep it runnable in minutes, not hours):
    * square patches (16x16 by default; the size is tuned), stride 2, 100 atoms initialised with a
      separable 2-D DCT;
    * a fixed sparsity K (tuned on the tune split) instead of the paper's bootstrap stopping rule;
    * 3 rounds of sparse coding / dictionary update on the noisy image itself;
    * groups are found by k-means on a lightly smoothed Anscombe image;
    * log-intensities are kept >= log(1e-3 * mean(y)) so all-zero patches stay finite.
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy import ndimage
from sklearn.cluster import MiniBatchKMeans

from ..common import anscombe


def dct_dictionary(patch, n_atoms):
    """Overcomplete separable 2-D DCT; atom 0 is the constant (DC) atom. Unit-norm columns."""
    m = int(np.ceil(np.sqrt(n_atoms)))
    i = np.arange(patch)[:, None]
    d1 = np.cos(np.pi * np.arange(m)[None, :] * (i + 0.5) / m)
    d1[:, 1:] -= d1[:, 1:].mean(axis=0)
    D = np.kron(d1, d1)[:, :n_atoms]
    return D / np.linalg.norm(D, axis=0)


def patch_positions(n, patch, stride):
    pos = list(range(0, n - patch + 1, stride))
    if pos[-1] != n - patch:
        pos.append(n - patch)  # always cover the last rows / columns
    return np.array(pos)


def extract(img, patch, stride):
    rows, cols = patch_positions(img.shape[0], patch, stride), patch_positions(img.shape[1], patch, stride)
    win = sliding_window_view(img, (patch, patch))[np.ix_(rows, cols)]
    return win.reshape(-1, patch * patch), rows, cols


def aggregate(patches, rows, cols, shape, patch):
    acc, cnt = np.zeros(shape), np.zeros(shape)
    k = 0
    for r in rows:
        for c in cols:
            acc[r:r + patch, c:c + patch] += patches[k].reshape(patch, patch)
            cnt[r:r + patch, c:c + patch] += 1
            k += 1
    return acc / cnt


def _objective(Z, Q):
    return np.sum(np.exp(Z) - Q * Z, axis=1)  # per patch


def newton(Q, D, supp, alpha, zmin, steps=5):
    """Fit the coefficients on the support of every patch: min 1^T exp(D_S a) - q^T D_S a."""
    DS = D.T[supp]  # (P, t, n)
    t = supp.shape[1]
    for _ in range(steps):
        Z = np.maximum(np.einsum("ptn,pt->pn", DS, alpha), zmin)
        E = np.exp(Z)
        g = np.einsum("ptn,pn->pt", DS, E - Q)
        H = np.einsum("ptn,pn,psn->pts", DS, E, DS) + 1e-8 * np.eye(t)
        step = np.linalg.solve(H, g[..., None])[..., 0]
        f0 = _objective(Z, Q)
        s = np.ones(len(Q))
        for _ in range(20):  # backtracking, per patch
            new = alpha - s[:, None] * step
            bad = _objective(np.maximum(np.einsum("ptn,pt->pn", DS, new), zmin), Q) > f0
            if not bad.any():
                break
            s[bad] *= 0.5
        alpha = alpha - s[:, None] * step
    return alpha


def sparse_code(Q, D, labels, K, zmin):
    """Greedy pursuit with a support shared inside each group (slide 6)."""
    P, n = Q.shape
    n_groups = labels.max() + 1
    supp = np.zeros((P, 1), dtype=int)  # the DC atom is always used
    group_mean = np.bincount(labels, Q.mean(axis=1), n_groups) / np.bincount(labels, minlength=n_groups)
    alpha = (np.log(np.maximum(group_mean[labels], np.exp(zmin))) * np.sqrt(n))[:, None]
    alpha = newton(Q, D, supp, alpha, zmin)
    for _ in range(1, K):
        Z = np.maximum(np.einsum("ptn,pt->pn", D.T[supp], alpha), zmin)
        G = (np.exp(Z) - Q) @ D  # gradient of every atom, per patch
        score = np.zeros((n_groups, D.shape[1]))
        np.add.at(score, labels, G**2)
        first = np.unique(labels, return_index=True)[1]  # one patch per group gives its support
        used = supp[first]
        np.put_along_axis(score, used, -np.inf, axis=1)
        supp = np.hstack([supp, score.argmax(axis=1)[labels][:, None]])
        alpha = newton(Q, D, supp, np.hstack([alpha, np.zeros((P, 1))]), zmin)
    A = np.zeros((P, D.shape[1]))
    np.put_along_axis(A, supp, alpha, axis=1)
    return A


def update_dictionary(Q, D, A, zmin, steps=5):
    """Gradient steps on sum_j 1^T exp(D a_j) - q_j^T D a_j, then renormalise atoms (DC fixed)."""
    total = lambda D_: float(np.sum(_objective(np.maximum(A @ D_.T, zmin), Q)))
    f = total(D)
    lr = 1.0
    for _ in range(steps):
        G = (np.exp(np.maximum(A @ D.T, zmin)) - Q).T @ A
        G[:, 0] = 0
        while lr > 1e-12:
            D_new = D - lr * G
            f_new = total(D_new)
            if f_new < f:
                D, f = D_new, f_new
                lr *= 2
                break
            lr *= 0.5
    D[:, 1:] /= np.linalg.norm(D[:, 1:], axis=0)
    return D


def spda(y, K=3, patch=16, stride=2, n_atoms=100, group_size=40, n_outer=3, seed=0):
    Q, rows, cols = extract(y, patch, stride)
    zmin = np.log(1e-3 * max(y.mean(), 1e-6))
    feats, _, _ = extract(ndimage.gaussian_filter(anscombe(y), 1.0), patch, stride)
    n_groups = max(1, len(Q) // group_size)
    labels = MiniBatchKMeans(n_groups, random_state=seed, n_init=1, batch_size=4096).fit_predict(feats)
    labels = np.unique(labels, return_inverse=True)[1]  # remove empty groups
    D = dct_dictionary(patch, n_atoms)
    nll = []
    for it in range(n_outer):
        A = sparse_code(Q, D, labels, K, zmin)
        nll.append(float(np.sum(_objective(np.maximum(A @ D.T, zmin), Q))))
        if it < n_outer - 1:
            D = update_dictionary(Q, D, A, zmin)
    x = aggregate(np.exp(np.maximum(A @ D.T, zmin)), rows, cols, y.shape, patch)
    return x, {"sparsity": float(np.count_nonzero(A) / A.size), "residuals": nll}
