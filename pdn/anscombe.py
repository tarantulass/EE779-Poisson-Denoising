"""Anscombe transform and its inverses (Makitalo & Foi, IEEE TIP 2011).

The *exact unbiased* inverse maps a denoised value D to the x for which
E[2 sqrt(y + 3/8) | x] = D, y ~ Poisson(x). We compute that expectation
numerically by summing the Poisson pmf (no closed-form approximation), tabulate
it on a dense grid, and invert by monotone interpolation. Beyond the table the
Makitalo-Foi closed-form approximation is used; there it agrees with the exact
value to < 1e-6.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import poisson

D0 = 2.0 * np.sqrt(3.0 / 8.0)  # E[A(y)] at x = 0


def forward(y: np.ndarray) -> np.ndarray:
    return 2.0 * np.sqrt(y + 3.0 / 8.0)


def inverse_algebraic(z: np.ndarray) -> np.ndarray:
    return z**2 / 4.0 - 3.0 / 8.0


def inverse_asymptotic(z: np.ndarray) -> np.ndarray:
    return z**2 / 4.0 - 1.0 / 8.0


def inverse_closed_form(z: np.ndarray) -> np.ndarray:
    """Makitalo & Foi closed-form approximation of the exact unbiased inverse."""
    z = np.maximum(z, 1e-12)
    a = np.sqrt(1.5)
    return z**2 / 4 + a / (4 * z) - 11 / (8 * z**2) + 5 * a / (8 * z**3) - 1 / 8


def _expected_anscombe(x: np.ndarray) -> np.ndarray:
    kmax = int(np.ceil(x.max() + 12 * np.sqrt(x.max() + 1) + 40))
    k = np.arange(kmax + 1)
    a = 2.0 * np.sqrt(k + 3.0 / 8.0)
    pmf = poisson.pmf(k[None, :], x[:, None])  # (n_x, kmax+1)
    return pmf @ a


_X_TAB = np.concatenate([np.linspace(0, 1, 2001)[:-1], np.linspace(1, 60, 5901)])
_D_TAB = _expected_anscombe(_X_TAB)
assert np.all(np.diff(_D_TAB) > 0), "E[A(y)|x] must be strictly increasing"


def inverse_exact_unbiased(z: np.ndarray) -> np.ndarray:
    z = np.asarray(z, dtype=np.float64)
    out = np.interp(z, _D_TAB, _X_TAB)  # values below D0 map to x = 0
    hi = z > _D_TAB[-1]
    if np.any(hi):
        out[hi] = inverse_closed_form(z[hi])
    return out


INVERSES = {
    "exact": inverse_exact_unbiased,
    "closed_form": inverse_closed_form,
    "asymptotic": inverse_asymptotic,
    "algebraic": inverse_algebraic,
}
