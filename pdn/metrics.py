"""Quality metrics on the peak-normalised scale.

PSNR = 10 log10(peak^2 / MSE(x_hat, x)), identical to PSNR of x_hat/peak against s
with data range 1. This is the convention of the P4IP and SPDA papers, so the
numbers are on the same scale as their Table 1 (different images, though).
Estimates are NOT clipped before scoring; clipping is a post-processing choice
and would change the ranking of biased estimators.
"""
from __future__ import annotations

import numpy as np
from skimage.metrics import structural_similarity


def psnr(x_hat: np.ndarray, x: np.ndarray, peak: float) -> float:
    mse = float(np.mean((x_hat - x) ** 2))
    return float("inf") if mse == 0 else 10.0 * np.log10(peak**2 / mse)


def ssim(x_hat: np.ndarray, x: np.ndarray, peak: float) -> float:
    return float(structural_similarity(x_hat / peak, x / peak, data_range=1.0))


def bias(x_hat: np.ndarray, x: np.ndarray, peak: float) -> float:
    """Mean signed error in units of the peak; detects inverse-transform bias."""
    return float(np.mean(x_hat - x) / peak)
