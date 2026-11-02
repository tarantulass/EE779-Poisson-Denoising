"""A2: learned dictionary for wavelet-domain image patches as the P4IP denoiser (slide 10, backup 16).

Learning (slide 16), on clean training patches (data/train):
    c_j = W_p R_j r          W_p: orthonormal 2-D Haar transform of an 8x8 patch (3 levels)
    min_{B, alpha}  sum_j  1/2 ||c_j - B alpha_j||^2 + eta ||alpha_j||_1,   ||b_l||_2 <= 1
solved by alternating FISTA sparse coding and projected-gradient dictionary steps.

Slide 16: "A free dictionary after an orthonormal wavelet transform is only a reparameterization.
Structure must justify the enhancement. Keep coarse coefficients separate. Learn detail-subband
structure and test it ... against a pixel-domain dictionary with the same atom count."
So two dictionaries are learned, both with 256 atoms:
    'wavelet': the coarse (patch-mean) coefficient is kept separate and not coded; every atom is
               restricted to one detail orientation (horizontal, vertical or diagonal, all scales).
    'pixel':   the same 256 atoms on the mean-removed pixel patch, no restriction (the control).

Denoiser (slide 16):  D(r) = (sum_j w_j R_j^T R_j)^-1 sum_j w_j R_j^T W_p^T B alpha_j, with w_j = 1,
where alpha_j is the l1 sparse code of the noisy patch with penalty sigma (sigma^2 = lam/rho in P4IP).
The dictionary is frozen during P4IP (slide 16).

    python -m experiments.direction_a.a2_dictionary      # learns both dictionaries (a few minutes)
"""
import os

import numpy as np
import pywt

from ..baselines.p4ip import p4ip
from ..baselines.spda import aggregate, extract
from ..common import image_paths, load_image

PATCH = 8
DICT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictionaries")


def haar_matrix(patch=PATCH, levels=3):
    """Rows = orthonormal 2-D Haar basis of a patch, ordered coarse first.
    Also returns the orientation of every row: 0 coarse, 1 horizontal, 2 vertical, 3 diagonal."""
    rows, orient = [], None
    for k in range(patch * patch):
        e = np.zeros(patch * patch); e[k] = 1
        c = pywt.wavedec2(e.reshape(patch, patch), "haar", mode="periodization", level=levels)
        vec, lab = [c[0].ravel()], [np.zeros(c[0].size, int)]
        for detail in c[1:]:
            for o, band in enumerate(detail, start=1):
                vec.append(band.ravel()); lab.append(np.full(band.size, o))
        rows.append(np.concatenate(vec))
        orient = np.concatenate(lab)
    return np.array(rows).T, orient  # W (64 x 64): coefficients = W @ patch


W_P, ORIENT = haar_matrix()


def split(P, domain):
    """Patches (N x 64) -> (coarse part kept separately, part that is sparse coded)."""
    if domain == "wavelet":
        C = P @ W_P.T
        return C[:, :1], C[:, 1:]
    m = P.mean(axis=1, keepdims=True)
    return m, P - m


def merge(coarse, detail, domain):
    if domain == "wavelet":
        return np.hstack([coarse, detail]) @ W_P
    return coarse + detail


def project_atoms(B, domain):
    """Constraint set: ||b|| <= 1, plus the structure of each dictionary."""
    if domain == "wavelet":
        B = B * atom_mask(B.shape[1])
    else:
        B = B - B.mean(axis=0)  # pixel atoms live in the mean-free space, like the wavelet details
    return B / np.maximum(np.linalg.norm(B, axis=0), 1.0)


def atom_mask(n_atoms):
    """Atom l may only use detail coefficients of orientation (l mod 3) + 1."""
    orient = ORIENT[1:]
    return (orient[:, None] == (np.arange(n_atoms) % 3 + 1)[None, :]).astype(float)


def fista_codes(C, B, lam, n_iter=30):
    """Batched FISTA for min 1/2 ||c - B a||^2 + lam ||a||_1 (slide 17), one row of C per patch."""
    L = np.linalg.norm(B, 2) ** 2
    G, BtC = B.T @ B, C @ B
    a = q = np.zeros((C.shape[0], B.shape[1]))
    t = 1.0
    for _ in range(n_iter):
        g = q - (q @ G - BtC) / L
        a_new = np.sign(g) * np.maximum(np.abs(g) - lam / L, 0)
        t_new = (1 + np.sqrt(1 + 4 * t * t)) / 2
        q = a_new + (t - 1) / t_new * (a_new - a)
        a, t = a_new, t_new
    return a


def learn(domain, n_atoms=256, n_patches=40000, eta=0.1, n_rounds=20, seed=0):
    rng = np.random.default_rng(seed)
    paths = image_paths("train")
    per = n_patches // len(paths) + 1
    P = []
    for p in paths:
        s = load_image(p)
        r = rng.integers(0, s.shape[0] - PATCH + 1, per)
        c = rng.integers(0, s.shape[1] - PATCH + 1, per)
        P += [s[i:i + PATCH, j:j + PATCH].ravel() for i, j in zip(r, c)]
    _, C = split(np.array(P[:n_patches]), domain)
    B = project_atoms(C[rng.choice(len(C), n_atoms, replace=False)].T + 1e-3 * rng.standard_normal((C.shape[1], n_atoms)), domain)
    B /= np.linalg.norm(B, axis=0)
    for it in range(n_rounds):
        A = fista_codes(C, B, eta, n_iter=50)
        for _ in range(5):  # projected gradient steps on B
            LB = max(np.linalg.norm(A.T @ A, 2), 1e-12)
            B = project_atoms(B - ((B @ A.T - C.T) @ A) / LB, domain)
        err = np.linalg.norm(C - A @ B.T) / np.linalg.norm(C)
        print(f"{domain} round {it + 1}/{n_rounds}: relative error {err:.3f}, "
              f"mean nonzeros {np.count_nonzero(A) / len(A):.1f}", flush=True)
    os.makedirs(DICT_DIR, exist_ok=True)
    np.save(os.path.join(DICT_DIR, f"{domain}.npy"), B)
    return B


_CACHE = {}


def load_dictionary(domain):
    if domain not in _CACHE:
        _CACHE[domain] = np.load(os.path.join(DICT_DIR, f"{domain}.npy"))
    return _CACHE[domain]


def dictionary_denoise(r, sigma, domain, stride=4):
    B = load_dictionary(domain)
    P, rows, cols = extract(r, PATCH, stride)
    coarse, C = split(P, domain)
    A = fista_codes(C, B, sigma)
    out = aggregate(merge(coarse, A @ B.T, domain), rows, cols, r.shape, PATCH)
    return out, {"sparsity": float(np.count_nonzero(A) / A.size)}


def dictionary_prior(lam, domain):
    return lambda r, rho: dictionary_denoise(r, np.sqrt(lam / rho), domain)


def p4ip_dictionary(y, lam, rho0, domain="wavelet", rho_step=1.065, n_iter=70):
    return p4ip(y, [dictionary_prior(lam, domain)], rho0, rho_step, n_iter)


if __name__ == "__main__":
    for d in ("wavelet", "pixel"):
        learn(d)
