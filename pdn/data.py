"""Image loading, Poisson noise simulation, and binning.

Conventions (match Rond, Giryes & Elad, arXiv:1511.02500, and slide 12 of EE779.odp):
  * s is the clean image normalised so that max(s) = 1.
  * x = peak * s is the expected photon count per pixel.
  * y ~ Poisson(x), independently per pixel.
  * Every method sees exactly the same y for a given (image, peak, seed):
    the RNG seed is derived from the image name, the peak and the repetition
    index only, never from the method.
"""
from __future__ import annotations

import hashlib
import os
from glob import glob

import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
SPLITS = ("test", "tune", "train")


def list_images(split: str) -> list[str]:
    if split not in SPLITS:
        raise ValueError(f"split must be one of {SPLITS}")
    return sorted(glob(os.path.join(DATA, split, "*.png")))


def image_name(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def load_clean(path: str) -> np.ndarray:
    """Return s in [0, 1] with max(s) == 1 (float64)."""
    s = np.asarray(Image.open(path).convert("L"), dtype=np.float64)
    m = s.max()
    if m <= 0:
        raise ValueError(f"{path} is all zeros")
    return s / m


def noise_seed(name: str, peak: float, rep: int) -> int:
    """Stable 64-bit seed from (image, peak, repetition). Independent of method,
    Python version and process, so runs on different machines are identical."""
    key = f"{name}|{peak!r}|{rep}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "little")


def simulate(s: np.ndarray, peak: float, name: str, rep: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (x, y): true intensity and Poisson counts."""
    x = peak * s
    rng = np.random.default_rng(noise_seed(name, peak, rep))
    y = rng.poisson(x).astype(np.float64)
    return x, y


# --------------------------------------------------------------------------
# Binning (paper Sec. 3.2): sum counts in b x b blocks, denoise the small image,
# divide by b^2 and upsample with linear interpolation. Reported separately.
# --------------------------------------------------------------------------
def bin_counts(y: np.ndarray, b: int = 3) -> tuple[np.ndarray, tuple[int, int]]:
    H, W = y.shape
    Hp, Wp = -(-H // b) * b, -(-W // b) * b
    if (Hp, Wp) != (H, W):  # symmetric pad so every block has b*b pixels
        y = np.pad(y, ((0, Hp - H), (0, Wp - W)), mode="symmetric")
    yb = y.reshape(Hp // b, b, Wp // b, b).sum(axis=(1, 3))
    return yb, (H, W)


def unbin(xb: np.ndarray, shape: tuple[int, int], b: int = 3) -> np.ndarray:
    """Per-pixel intensity from a binned estimate, bilinear upsampling with
    block centres as sample positions."""
    from scipy.ndimage import map_coordinates

    H, W = shape
    xb = xb / (b * b)
    # pixel i of the full image sits at (i + 0.5)/b - 0.5 in block coordinates
    r = (np.arange(H) + 0.5) / b - 0.5
    c = (np.arange(W) + 0.5) / b - 0.5
    rr, cc = np.meshgrid(r, c, indexing="ij")
    return map_coordinates(xb, [rr, cc], order=1, mode="nearest")
