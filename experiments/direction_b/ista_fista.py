"""Direction B: explicit sparsity with ISTA / FISTA (slide 11, backup slide 17).

    z = A(y) = 2 sqrt(y + 3/8),    minimise F(alpha) = 1/2 ||D alpha - z||^2 + lam ||alpha||_1
    grad = D^T (D alpha - z),      L = ||D||_2^2
    ISTA : alpha^{k+1} = S(alpha^k - grad(alpha^k)/L, lam/L)
    FISTA: alpha^k = S(q^k - grad(q^k)/L, lam/L),  t_{k+1} = (1 + sqrt(1 + 4 t_k^2))/2,
           q^{k+1} = alpha^k + ((t_k - 1)/t_{k+1}) (alpha^k - alpha^{k-1})
    x_hat = exact unbiased inverse Anscombe of D alpha (slide 4)

D is fixed during sparse coding (slide 11), one of:
    'swt'  : redundant (undecimated) wavelet frame, db4, 4 levels, Parseval so L = 1
    'dict' : the learned wavelet-patch dictionary of A2 placed on overlapping 8x8 patches (stride 4);
             L is computed by power iteration
The local mean is handled outside the l1 problem: z = low + r, where low is the coarse wavelet band
of z (swt) or the average of the 8x8 patch means (dict, exact for flat regions), and the slide's
objective is solved for r with the detail atoms only. Coding the mean with free (unpenalised)
atoms on a redundant frame makes the problem ill-posed; penalising it shrinks the image mean.
For an orthonormal wavelet basis this gives exactly the one-step solution of slide 17.

ISTA and FISTA use the same objective, the same lam, the same start alpha^0 = 0 and the same
stopping rule |F_k - F_{k-1}| <= tol F_k (slide 12).

    python -m experiments.direction_b.ista_fista      # convergence curves -> results/ista_fista_convergence.png
"""
import time

import numpy as np
import pywt

from ..common import anscombe, inverse_anscombe_exact


class SWT:
    """Undecimated wavelet frame, detail bands only: coefficients are an array (3J, H, W)."""

    def __init__(self, shape, wavelet="db4", levels=4):
        self.shape, self.wavelet, self.J = shape, wavelet, levels
        m = 2**levels
        self.padded = (shape[0] + (-shape[0] % m), shape[1] + (-shape[1] % m))
        self.L = 1.0

    def _swt(self, img):
        img = np.pad(img, ((0, self.padded[0] - img.shape[0]), (0, self.padded[1] - img.shape[1])))
        return pywt.swt2(img, self.wavelet, self.J, norm=True, trim_approx=True)

    def _iswt(self, coarse, details):
        c = [coarse] + [tuple(details[3 * i: 3 * i + 3]) for i in range(self.J)]
        return pywt.iswt2(c, self.wavelet, norm=True)[: self.shape[0], : self.shape[1]]

    def lowpass(self, z):  # synthesis of the coarse band of z alone
        c = self._swt(z)
        return self._iswt(c[0], np.zeros((3 * self.J,) + c[0].shape))

    def analysis(self, img):  # D^T
        return np.stack([b for lev in self._swt(img)[1:] for b in lev])

    def synthesis(self, a):  # D
        return self._iswt(np.zeros(a.shape[1:]), a)


class PatchDictionary:
    """D alpha = sum_j R_j^T W_p^T B alpha_j over overlapping 8x8 patches (A2's wavelet dictionary)."""

    def __init__(self, shape, stride=4):
        from ..baselines.spda import patch_positions
        from ..direction_a.a2_dictionary import PATCH, W_P, load_dictionary
        B = load_dictionary("wavelet")                                   # 63 detail coefficients x 256 atoms
        self.atoms = np.hstack([np.zeros((B.shape[1], 1)), B.T]) @ W_P  # pixel patches W_p^T [0; b_l]
        self.P, self.shape = PATCH, shape
        self.rows, self.cols = patch_positions(shape[0], PATCH, stride), patch_positions(shape[1], PATCH, stride)
        x = np.random.default_rng(0).standard_normal(shape)
        for _ in range(50):  # power iteration for L = ||D||^2
            x = self.synthesis(self.analysis(x)); n = np.linalg.norm(x); x /= n
        self.L = float(n) * 1.01

    def _patches(self, img):
        from numpy.lib.stride_tricks import sliding_window_view
        win = sliding_window_view(img, (self.P, self.P))[np.ix_(self.rows, self.cols)]
        return win.reshape(-1, self.P * self.P)

    def _overlap_add(self, patches):
        patches = patches.reshape(len(self.rows), len(self.cols), self.P, self.P)
        out = np.zeros(self.shape)
        for i, r in enumerate(self.rows):
            for j, c in enumerate(self.cols):
                out[r:r + self.P, c:c + self.P] += patches[i, j]
        return out

    def lowpass(self, z):  # average over the covering patches of each patch's mean
        means = self._patches(z).mean(axis=1, keepdims=True) * np.ones((1, self.P * self.P))
        return self._overlap_add(means) / self._overlap_add(np.ones_like(means))

    def analysis(self, img):
        return self._patches(img) @ self.atoms.T

    def synthesis(self, a):
        return self._overlap_add(a @ self.atoms)


def objective(D, a, r, lam):
    return 0.5 * np.sum((D.synthesis(a) - r) ** 2) + lam * np.sum(np.abs(a))


def solve(r, D, lam, accelerated, max_iter=2000, tol=1e-7):
    soft = lambda c, th: np.sign(c) * np.maximum(np.abs(c) - th, 0)
    a = np.zeros_like(D.analysis(r))                            # alpha^0 = 0
    q, t = a, 1.0
    F = [objective(D, a, r, lam)]
    for _ in range(max_iter):
        a_new = soft(q - D.analysis(D.synthesis(q) - r) / D.L, lam / D.L)
        if accelerated:                                         # FISTA
            t_new = (1 + np.sqrt(1 + 4 * t * t)) / 2
            q = a_new + (t - 1) / t_new * (a_new - a)
            t = t_new
        else:                                                   # ISTA
            q = a_new
        a = a_new
        F.append(objective(D, a, r, lam))
        if abs(F[-2] - F[-1]) <= tol * F[-1]:
            break
    return a, F


def make_operator(frame, shape):
    return SWT(shape) if frame == "swt" else PatchDictionary(shape)


def sparse_anscombe(y, lam, solver="fista", frame="swt", max_iter=2000, tol=1e-7):
    z = anscombe(y)
    D = make_operator(frame, y.shape)
    low = D.lowpass(z)
    t0 = time.time()
    a, F = solve(z - low, D, lam, accelerated=(solver == "fista"), max_iter=max_iter, tol=tol)
    return inverse_anscombe_exact(low + D.synthesis(a)), {
        "iterations": len(F) - 1, "residuals": F, "solve_time": time.time() - t0,
        "sparsity": float(np.count_nonzero(a) / a.size)}


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
            D = make_operator(frame, y.shape)
            r = z - D.lowpass(z)
            F_star = min(solve(r, D, lam, True, max_iter=n_star, tol=0)[1])
            ax = axes[row, col]
            for acc, name in ((False, "ISTA"), (True, "FISTA")):
                F = np.array(solve(r, D, lam, acc, max_iter=1000, tol=0)[1])
                ax.loglog(np.arange(len(F)) + 1, np.maximum(F - F_star, 1e-12) / F_star, label=name)
            ax.set_title(f"{frame}, peak {peak}, lam {lam:g}")
            ax.set_xlabel("iteration k"); ax.set_ylabel("(F_k - F*) / F*"); ax.grid(alpha=0.3); ax.legend()
    fig.tight_layout()
    out = os.path.join(REPO, "results", "ista_fista_convergence.png")
    fig.savefig(out, dpi=120)
    print("wrote", out)


if __name__ == "__main__":
    convergence_plot()
