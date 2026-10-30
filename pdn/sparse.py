"""Direction B1: explicit sparse objective in the Anscombe domain, ISTA vs FISTA
(EE779.odp slides 11, 17, 18).

    z = A(y)                                      (Anscombe, noise ~ N(0, 1))
    F(alpha) = 1/2 ||D alpha - z||^2 + lam * sum_i w_i |alpha_i|
    x_hat = A^{-1}(D alpha_hat)                   (exact unbiased inverse by default)

D is FIXED (synthesis operator of a frame W, D = W^T):
  frame='swt' : undecimated (stationary) wavelet tight frame, pywt.swt2 with
                norm=True. It is Parseval (W^T W = I) and iswt2 is its exact
                adjoint (tests/test_directions.py), so L = ||D||^2 = 1.   (B1-default)
  frame='dwt' : orthonormal DWT, periodization (the A1 basis). The minimiser is the
                one-step solution S(W z, lam) on the penalised bands (B1.0 test).
Approximation (coarse) band, `approx`:
  'fixed'     (default): alpha_0 = (W z)_0 is held fixed and only the detail
              coefficients are optimised, all penalised. Well posed and unbiased in the
              local mean; for the orthonormal DWT it gives exactly the one-step solution
              S(W z, lam) of slide 17, so B1(dwt) and A1.a use the same prior.
  'penalized' : all coefficients penalised (approx band with weight approx_weight).
              Slide 17 as written; in the Anscombe domain the coarse coefficients are
              O(1-10), the same size as lam, so the local mean is shrunk (measured: about
              9 dB PSNR on a tuning image at peaks 0.2-1). Kept as an ablation.
  'free'      : approx band optimised and unpenalised. ILL-POSED on a redundant frame:
              the detail l1 cost can be lowered without bound by moving content into ever
              larger coarse coefficients, so F* need not be attained and FISTA crawls
              (found while testing). Do not use for results.

Solvers: 'ista', 'fista' (Beck & Teboulle 2009), 'one_step' (dwt only), each with
step 1/L, L = 1 or found by backtracking (B1.e). Stopping: relative change of F
below tol, or max_iter. Both solvers use the same F, lam, L, alpha^0 = 0 and stopping
rule, so only the update differs (B1.a).
"""
from __future__ import annotations

import time

import numpy as np
import pywt

from . import anscombe
from .methods import register


class SWTFrame:
    def __init__(self, shape, wavelet="db4", levels=3):
        if any(s % (2 ** levels) for s in shape):
            raise ValueError(f"SWT needs sides divisible by 2^{levels}, got {shape}")
        self.wavelet, self.levels, self.shape = wavelet, levels, shape
        self.pen = np.ones(1 + 3 * levels, bool)
        self.pen[0] = False  # approximation band

    def analysis(self, x):  # W x  -> (1+3J, H, W)
        c = pywt.swt2(x, self.wavelet, level=self.levels, norm=True, trim_approx=True)
        return np.stack([c[0]] + [b for t in c[1:] for b in t])

    def synthesis(self, a):  # W^T a = D a
        cl = [a[0]] + [tuple(a[1 + 3 * i:4 + 3 * i]) for i in range(self.levels)]
        return pywt.iswt2(cl, self.wavelet, norm=True)


class DWTFrame:
    """Orthonormal basis; coefficients as one array via pywt.coeffs_to_array."""

    def __init__(self, shape, wavelet="db4", levels=4):
        if any(s % (2 ** levels) for s in shape):
            raise ValueError(f"orthonormal DWT needs sides divisible by 2^{levels}, got {shape}")
        self.wavelet, self.levels, self.shape = wavelet, levels, shape
        c = pywt.wavedec2(np.zeros(shape), wavelet, mode="periodization", level=levels)
        arr, self.slices = pywt.coeffs_to_array(c)
        self.pen = np.ones(arr.shape, bool)
        self.pen[self.slices[0]] = False

    def analysis(self, x):
        c = pywt.wavedec2(x, self.wavelet, mode="periodization", level=self.levels)
        return pywt.coeffs_to_array(c)[0]

    def synthesis(self, a):
        c = pywt.array_to_coeffs(a, self.slices, output_format="wavedec2")
        return pywt.waverec2(c, self.wavelet, mode="periodization")


def make_frame(shape, frame="swt", wavelet="db4", levels=None):
    if frame == "swt":
        return SWTFrame(shape, wavelet, 3 if levels is None else levels)
    if frame == "dwt":
        return DWTFrame(shape, wavelet, 4 if levels is None else levels)
    raise ValueError(frame)


def soft(a, t):
    return np.sign(a) * np.maximum(np.abs(a) - t, 0.0)


def solve(z, lam, frame, solver="fista", max_iter=1000, tol=1e-6, L=1.0,
          backtracking=False, bt_eta=2.0, approx="fixed", approx_weight=1.0, callback=None):
    """Returns (alpha, trace). trace: list of {iter, F, time, nnz_frac[, L]}.
    callback(k, alpha) -> dict merged into the trace (analysis only)."""
    a0 = np.zeros_like(frame.analysis(z))
    detail = _expand(frame.pen, a0)
    if approx == "fixed":
        wts = np.where(detail, 1.0, 0.0)
        a0 = np.where(detail, 0.0, frame.analysis(z))   # alpha^0: details 0, coarse = (Wz)_0
    elif approx == "penalized":
        wts = np.where(detail, 1.0, float(approx_weight))
    elif approx == "free":
        wts = np.where(detail, 1.0, 0.0)
    else:
        raise ValueError(approx)
    fixed = (~detail) if approx == "fixed" else None
    mask = wts > 0
    n_pen = max(int(mask.sum()), 1)

    def thresh(a, t):
        out = soft(a, t * wts)  # w = 0 -> identity
        if fixed is not None:
            out[fixed] = a0[fixed]
        return out

    def F(a):
        r = frame.synthesis(a) - z
        return 0.5 * float(np.sum(r * r)) + lam * float(np.sum(wts * np.abs(a)))

    def grad(a):
        return frame.analysis(frame.synthesis(a) - z)

    t0 = time.perf_counter()
    if solver == "one_step":
        if not isinstance(frame, DWTFrame):
            raise ValueError("one_step is exact only for an orthonormal basis (frame='dwt')")
        a = thresh(frame.analysis(z), lam)
        return a, [{"iter": 1, "F": F(a), "time": time.perf_counter() - t0}]

    a = a0
    w, tk = a.copy(), 1.0
    Fk = F(a)
    trace = []
    for k in range(1, max_iter + 1):
        base = w if solver == "fista" else a
        g = grad(base)
        if backtracking:  # Beck & Teboulle: increase L until the quadratic bound holds
            r0 = frame.synthesis(base) - z
            f0 = 0.5 * float(np.sum(r0 * r0))
            while True:
                a_new = thresh(base - g / L, lam / L)
                r1 = frame.synthesis(a_new) - z
                d = a_new - base
                if 0.5 * float(np.sum(r1 * r1)) <= f0 + float(np.sum(g * d)) + 0.5 * L * float(np.sum(d * d)) + 1e-12:
                    break
                L *= bt_eta
        else:
            a_new = thresh(base - g / L, lam / L)
        if solver == "fista":
            t_new = 0.5 * (1 + np.sqrt(1 + 4 * tk * tk))
            w = a_new + ((tk - 1) / t_new) * (a_new - a)
            tk = t_new
        elif solver != "ista":
            raise ValueError(solver)
        a = a_new
        F_new = F(a)
        ent = {"iter": k, "F": F_new, "time": time.perf_counter() - t0,
               "nnz_frac": float(np.count_nonzero(a[mask])) / n_pen}
        if backtracking:
            ent["L"] = L
        if callback is not None:
            ent.update(callback(k, a) or {})
        trace.append(ent)
        if tol > 0 and abs(Fk - F_new) <= tol * max(abs(Fk), 1e-300):
            break
        Fk = F_new
    return a, trace


def _expand(pen, a):
    """Boolean mask over coefficient array a (pen is per band for SWT, per entry for DWT)."""
    if pen.shape == a.shape:
        return pen
    return np.broadcast_to(pen[:, None, None], a.shape)


@register("anscombe_l1")
def anscombe_l1(y, peak, lam, frame="swt", wavelet="db4", levels=None, solver="fista",
                max_iter=1000, tol=1e-6, backtracking=False, L0=1.0, inverse="exact",
                approx="fixed", approx_weight=1.0):
    """B1 method. L0 = 1 is exact for both frames (Parseval / orthonormal); with
    backtracking=True it is the starting guess (use L0 < 1 to see it grow)."""
    z = anscombe.forward(y)
    fr = make_frame(y.shape, frame, wavelet, levels)
    a, trace = solve(z, float(lam), fr, solver=solver, max_iter=int(max_iter), tol=float(tol),
                     L=float(L0), backtracking=bool(backtracking),
                     approx=approx, approx_weight=float(approx_weight))
    zd = fr.synthesis(a)
    return anscombe.INVERSES[inverse](zd), {"iters": len(trace), "trace": trace,
                                            "time_denoiser": trace[-1]["time"] if trace else 0.0}
