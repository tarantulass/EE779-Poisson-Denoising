"""Anscombe + BM3D (slides 4 and 5).

    1. z = A(y) = 2 sqrt(y + 3/8)
    2. denoise z with BM3D assuming sigma = 1
    3. map back with an inverse Anscombe: 'exact' unbiased inverse (Makitalo & Foi 2011) or the
       'algebraic' inverse z^2/4 - 3/8, which slide 4 says can bias the estimate.

BM3D (Dabov et al. 2007) is the reference implementation in the `bm3d` package: block matching,
3-D transform hard thresholding, aggregation, then the collaborative Wiener stage (slide 5).
"""
import bm3d

from ..common import INVERSE, anscombe


def anscombe_bm3d(y, inverse="exact"):
    z_hat = bm3d.bm3d(anscombe(y), sigma_psd=1.0)
    return INVERSE[inverse](z_hat), {}
