"""Every registered denoiser (including your own plug-ins, if imported via
PDN_PLUGINS=module1,module2) must satisfy the contract in pdn/denoisers.py."""
import importlib
import os

import numpy as np
import pytest

from pdn import denoisers

for m in filter(None, os.environ.get("PDN_PLUGINS", "").split(",")):
    importlib.import_module(m)

FAST = os.environ.get("PDN_FAST_CONTRACT", "1") == "1"


@pytest.mark.parametrize("name", sorted(n for n in denoisers.DENOISERS if not n.startswith("_")))
def test_contract(name):
    if FAST and name == "bm3d":
        r = np.random.default_rng(0).normal(5, 1, (48, 48))
    else:
        r = np.random.default_rng(0).normal(5, 1, (64, 64))
    r[0, 0] = -3.0  # negative inputs occur inside ADMM
    D = denoisers.get(name)
    out1 = D(r.copy(), 1.0)
    out2 = D(r.copy(), 1.0)
    assert out1.shape == r.shape and out1.dtype == np.float64
    assert np.all(np.isfinite(out1))
    # BM3D runs in float32 with threading: allow tiny nondeterminism
    assert np.allclose(out1, out2, rtol=0, atol=1e-3), "denoiser must be deterministic"
