"""Direction B: explicit sparsity with ISTA / FISTA (slide 11, backup slide 17).

    z = A(y) = 2 sqrt(y + 3/8),    minimise F(alpha) = 1/2 ||D alpha - z||^2 + lam ||alpha||_1
    grad = D^T (D alpha - z),      L = ||D||_2^2
    ISTA : alpha^{k+1} = S(alpha^k - grad(alpha^k)/L, lam/L)
    FISTA: alpha^k = S(q^k - grad(q^k)/L, lam/L),  t_{k+1} = (1 + sqrt(1 + 4 t_k^2))/2,
           q^{k+1} = alpha^k + ((t_k - 1)/t_{k+1}) (alpha^k - alpha^{k-1})
    x_hat = exact unbiased inverse Anscombe of D alpha (slide 4)

D is fixed during sparse coding (slide 11), one of:
    'swt'  : redundant (undecimated) wavelet frame, db4, 4 levels, Parseval so L = 1
    'dict' : the learned wavelet-patch dictionary of A2 placed on overlapping 8x8 patches (stride 4),
             plus one constant atom per patch; L is computed by power iteration
The coarse band (swt) and the constant atoms (dict) carry the local mean of z. They are not
penalised and not optimised: they are fixed to the coarse part of z (D.fixed(z)) and the l1 problem is
solved for the remaining coefficients. Left free with zero weight on a redundant frame they could
cancel noise at no l1 cost and the problem would be ill-posed; penalising them would shrink the
image mean. For an orthonormal wavelet basis (slide 17) this gives exactly alpha* = S(D^T z, lam).

ISTA and FISTA use the same objective, the same lam, the same start alpha^0 = D^T z / L and the same
stopping rule |F_k - F_{k-1}| <= tol F_k (slide 12).

    python -m experiments.direction_b.ista_fista      # convergence curves -> results/ista_fista_convergence.png
"""
import time

import numpy as np
import pywt

from ..common import anscombe, inverse_anscombe_exact


class SWT:
    """Undecimated wavelet frame. coefficients: array (1 + 3J, H, W), band 0 is the coarse band."""

    def __init__(self, shape, wavelet="db4", levels=4):
        self.shape, self.wavelet, self.J = shape, wavelet, levels
        m = 2**levels
        self.padded = (shape[0] + (-shape[0] % m), shape[1] + (-shape[1] % m))
        self.weights = np.ones((1 + 3 * levels, 1, 1)); self.weights[0] = 0
        self.L = 1.0

    def fixed(self, z):  # coarse band of z
        return self.analysis(z)

    def analysis(self, img):  # D^T
        img = np.pad(img, ((0, self.padded[0] - img.shape[0]), (0, self.padded[1] - img.shape[1])))
        c = pywt.swt2(img, self.wavelet, self.J, norm=True, trim_approx=True)
        return np.stack([c[0]] + [b for lev in c[1:] for b in lev])

    def synthesis(self, a):  # D
        c = [a[0]] + [tuple(a[1 + 3 * i: 4 + 3 * i]) for i in range(self.J)]
        return pywt.iswt2(c, self.wavelet, norm=True)[: self.shape[0], : self.shape[1]]


class PatchDictionary:
    """D alpha = sum_j R_j^T [1/8, W_p^T B] alpha_j over overlapping patches (A2's wavelet dictionary)."""

    def __init__(self, shape, stride=4):
        from ..baselines.spda import patch_positions
        from ..direction_a.a2_dictionary import PATCH, W_P, load_dictionary
        B = load_dictionary("wavelet")                              # 63 detail coefficients x 256 atoms
        detail_atoms = np.hstack([np.zeros((B.shape[1], 1)), B.T]) @ W_P  # pixel patch W_p^T [0; b_l]
        constant = np.full((1, PATCH * PATCH), 1.0 / PATCH)          # unit-norm constant atom
        self.atoms = np.vstack([constant, detail_atoms])            # (1 + 256) x 64
        self.P, self.shape = PATCH, shape
        self.rows, self.cols = patch_positions(shape[0], PATCH, stride), patch_positions(shape[1], PATCH, stride)
        self.weights = np.ones(self.atoms.shape[0]); self.weights[0] = 0
        x = np.random.default_rng(0).standard_normal(shape)
        for _ in range(50):  # power iteration for L = ||D||^2
            x = self.synthesis(self.analysis(x)); n = np.linalg.norm(x); x /= n
        self.L = float(n) * 1.01

    def fixed(self, z):
        """Constant-atom coefficients such that their synthesis is the local mean of z."""
        coverage = np.zeros(self.shape)  # number of patches covering each pixel
        for r in self.rows:
            for c in self.cols:
                coverage[r:r + self.P, c:c + self.P] += 1
        a = np.zeros((len(self.rows) * len(self.cols), self.atoms.shape[0]))
        a[:, 0] = self.analysis(z / coverage)[:, 0]
        return a

    def analysis(self, img):
        from numpy.lib.stride_tricks import sliding_window_view
        win = sliding_window_view(img, (self.P, self.P))[np.ix_(self.rows, self.cols)]
        return win.reshape(-1, self.P * self.P) @ self.atoms.T

    def synthesis(self, a):
        patches = (a @ self.atoms).reshape(len(self.rows), len(self.cols), self.P, self.P)
        out = np.zeros(self.shape)
        for i, r in enumerate(self.rows):
            for j, c in enumerate(self.cols):
                out[r:r + self.P, c:c + self.P] += patches[i, j]
        return out


def objective(D, a, z, lam):
    return 0.5 * np.sum((D.synthesis(a) - z) ** 2) + lam * np.sum(D.weights * np.abs(a))


def solve(z, D, lam, accelerated, max_iter=2000, tol=1e-6):
    soft = lambda c, th: np.sign(c) * np.maximum(np.abs(c) - th, 0)
    th = lam * D.weights / D.L
    fixed = np.broadcast_to(D.weights == 0, D.analysis(z).shape)
    a = np.where(fixed, D.fixed(z), D.analysis(z) / D.L)       # alpha^0
    q, t = a, 1.0
    F = [objective(D, a, z, lam)]
    for _ in range(max_iter):
        g = q - D.analysis(D.synthesis(q) - z) / D.L
        a_new = np.where(fixed, a, soft(g, th))
        if accelerated:                                         # FISTA
            t_new = (1 + np.sqrt(1 + 4 * t * t)) / 2
            q = a_new + (t - 1) / t_new * (a_new - a)
            t = t_new
        else:                                                   # ISTA
            q = a_new
        a = a_new
        F.append(objective(D, a, z, lam))
        if abs(F[-2] - F[-1]) <= tol * F[-1]:
            break
    return a, F


def sparse_anscombe(y, lam, solver="fista", frame="swt", max_iter=2000, tol=1e-6):
    z = anscombe(y)
    D = SWT(y.shape) if frame == "swt" else PatchDictionary(y.shape)
    t0 = time.time()
    a, F = solve(z, D, lam, accelerated=(solver == "fista"), max_iter=max_iter, tol=tol)
    penalised = D.weights * np.ones_like(a) > 0
    return inverse_anscombe_exact(D.synthesis(a)), {
        "iterations": len(F) - 1, "residuals": F, "solve_time": time.time() - t0,
        "sparsity": float(np.count_nonzero(a[penalised]) / penalised.sum())}


def convergence_plot(peaks=(0.2, 1, 4), image="cameraman", n_star=5000):
    """F(alpha_k) - F* for ISTA and FISTA (same objective, same lam), F* from a long FISTA run."""
    import json
    import os

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from ..common import REPO, image_paths, load_image, noisy_image
    tuned = json.load(open(os.path.join(REPO, "results", "tuned_params.json")))
    path = [p for p in image_paths("test") if image in p][0]
    fig, axes = plt.subplots(2, len(peaks), figsize=(4 * len(peaks), 7), squeeze=False)
    for row, frame in enumerate(("swt", "dict")):
        for col, peak in enumerate(peaks):
            lam = tuned[f"B_fista_{frame}"][str(peak)]["lam"]
            _, y = noisy_image(load_image(path), peak, image)
            z = anscombe(y)
            D = SWT(y.shape) if frame == "swt" else PatchDictionary(y.shape)
            F_star = min(solve(z, D, lam, True, max_iter=n_star, tol=0)[1])
            ax = axes[row, col]
            for acc, name in ((False, "ISTA"), (True, "FISTA")):
                F = np.array(solve(z, D, lam, acc, max_iter=1000, tol=0)[1])
                ax.loglog(np.arange(len(F)) + 1, np.maximum(F - F_star, 1e-12) / F_star, label=name)
            ax.set_title(f"{frame}, peak {peak}, lam {lam:g}")
            ax.set_xlabel("iteration k"); ax.set_ylabel("(F_k - F*) / F*"); ax.grid(alpha=0.3); ax.legend()
    fig.tight_layout()
    out = os.path.join(REPO, "results", "ista_fista_convergence.png")
    fig.savefig(out, dpi=120)
    print("wrote", out)


if __name__ == "__main__":
    convergence_plot()
