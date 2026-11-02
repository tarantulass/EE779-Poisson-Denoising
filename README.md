# EE779-Poisson-Denoising
This is a project on advanced signal processing with emphasis on low lighting condition images and denoising these images with the use of available tools.

Everything follows the proposal deck `output/EE779.odp`. Each method is one short module and
names the slide it implements.

## Structure

```
experiments/
  common.py                 noise model x = p s, y ~ Poisson(x) (slide 2), binning (slide 12),
                            Anscombe + exact unbiased inverse (slide 4), Poisson prox (slides 8, 14),
                            orthonormal wavelet shrinkage (slides 3, 10), PSNR / SSIM
  baselines/
    conventional.py         slide 3: mean, Gaussian, median, Wiener, wavelet thresholding, non-local means
                            (on the Anscombe image), Poisson-TV (TV.txt)
    anscombe_bm3d.py        slides 4-5: Anscombe + BM3D, exact and algebraic inverse
    p4ip.py                 slides 7-8, 15: P4IP (Plug-and-Play ADMM), one or several priors; P4IP + BM3D
    spda.py                 slide 6: SPDA, Poisson sparse coding exp(D alpha) with shared supports
  direction_a/              slide 10: change the P4IP prior
    a1_wavelet.py           A1: P4IP with orthonormal wavelet shrinkage, thresholds per subband
    a2_dictionary.py        A2 (slide 16): learned wavelet-domain patch dictionary vs a pixel dictionary
                            with the same atom count; learned dictionaries in dictionaries/
    a3_consensus.py         A3 (slide 15): BM3D + wavelet consensus prior
  direction_b/
    ista_fista.py           slides 11, 17: ISTA vs FISTA on 1/2||D alpha - z||^2 + lam||alpha||_1,
                            D = redundant wavelet frame or the learned dictionary
  methods.py                the list of all methods compared and their tuning grids
  tune.py                   grid search on data/tune (separate tuning set, slide 12)
  evaluate.py               test runs, tables, paired comparisons, PSNR-vs-peak plot (slide 12)
tests/test_core.py          checks of the slide formulas
data/test, data/tune, data/train   8 test images, 4 tuning images, 400 training images (dictionary learning)
results/                    tuned_params.json, test.csv, test_bin3.csv, summary.md, plots
```

## Methods compared (slide 12)

| Name | Slide | What it is |
|---|---|---|
| `mean_filter`, `gaussian_filter`, `median_filter`, `wiener_filter`, `wavelet_threshold`, `nl_means` | 3 | conventional Gaussian denoisers applied to the Anscombe image (sigma = 1), exact inverse |
| `poisson_tv` | 3 | min sum(x - y log x) + lam TV(x), gradient descent as in TV.txt |
| `anscombe_bm3d` | 4, 5 | Anscombe + BM3D + exact unbiased inverse (baseline) |
| `anscombe_bm3d_algebraic` | 4 | same with the algebraic inverse z^2/4 - 3/8 (shows the bias) |
| `p4ip_bm3d` | 7, 8 | P4IP with BM3D (baseline) |
| `spda` | 6 | SPDA (baseline, "where feasible": simplified, see below) |
| `A1_wavelet`, `A1_subband` | 10 | P4IP with wavelet shrinkage; one threshold / thresholds tuned per level |
| `A2_wavelet_dict`, `A2_pixel_dict` | 10, 16 | P4IP with the learned wavelet-domain dictionary / pixel dictionary (control) |
| `A3_bm3d_wavelet` | 10, 15 | P4IP with BM3D + wavelet consensus |
| `B_ista_swt`, `B_fista_swt`, `B_ista_dict`, `B_fista_dict` | 11, 17 | ISTA vs FISTA, same objective, lam and stopping rule; redundant wavelet or learned dictionary |

Measured for every run: PSNR, SSIM, runtime, coefficient sparsity and the convergence residuals
(P4IP: ||x - v|| per iteration; ISTA/FISTA: F(alpha_k); SPDA: likelihood per round).

## How to run

```bash
pip install -r requirements.txt
python -m pytest -q tests                                  # formula checks
python -m experiments.direction_a.a2_dictionary           # learn the A2 dictionaries (already in the repo)

python -m experiments.tune     --methods all --workers 8   # tune every method on data/tune
python -m experiments.evaluate --methods all --workers 8   # test images, all peaks
python -m experiments.tune     --methods all --bin 3 --workers 8   # binning, reported separately
python -m experiments.evaluate --methods all --bin 3 --workers 8
python -m experiments.evaluate --summary --ref anscombe_bm3d       # results/summary.md, psnr_vs_peak.png
python -m experiments.direction_b.ista_fista               # ISTA vs FISTA convergence curves
```

`--methods` takes any names from the table, e.g. `--methods p4ip_bm3d A3_bm3d_wavelet`. Both
scripts skip work already saved, so they can be stopped and restarted. P4IP with BM3D runs BM3D 70
times per image (about 2-3 minutes per image per core), so the P4IP-BM3D, A2 and A3 runs are
best done on a machine with many cores (on a cloud VM: clone, install, run the commands above
inside `tmux`).

## Choices that the slides leave open

* P4IP (paper Sec. 3.2): rho starts at rho0 and is multiplied by 1.065 every iteration, 70
  iterations, start v = u = 0, output x. lam and rho0 are tuned per peak on data/tune, as the paper
  tuned beta and lambda0 per peak. Grids are written on the peak-normalised scale (see `methods.py`).
* A3: every prior uses the same rho; lam1 and rho0 come from the tuned P4IP-BM3D, and lam2 is tuned.
* SPDA is simplified so that it runs in seconds, not hours: fixed sparsity K instead of the
  bootstrap stopping rule, k-means groups, DCT start dictionary, 3 coding / dictionary-update
  rounds; patch size and K are tuned.
* A2: both dictionaries have 256 atoms and learn on 40,000 clean 8x8 training patches with
  eta = 0.1; the patch mean (coarse coefficient) is kept separately in both. The wavelet dictionary's
  atoms are each restricted to one detail orientation (the "structure" of slide 16).
* Poisson-TV follows TV.txt step by step. Its lam grid is wider than the 0.02-0.3 suggested in
  step 17 (those values barely smooth at low peaks), and the step size tau is tuned with it,
  because a large lam needs a small tau to stay stable.
* Direction B: the coarse band (wavelet) and the constant atoms (dictionary) are fixed to the
  coarse part of z rather than penalised; see the docstring of `ista_fista.py`.

# LLM usage
AI assistant: Claude (Anthropic), used through Claude Code. Commits it co-wrote carry a
`Co-Authored-By: Claude` trailer, so `git log` shows exactly which ones.

1. Summarizing insights and documenting experimental setups: this README and the module
   docstrings were drafted with Claude from our proposal deck (`output/EE779.odp`) and `TV.txt`.
2. Code generation, including the novelty experiments: everything in `experiments/` and `tests/`
   (baselines, directions A and B, tuning and evaluation) was written with Claude, following the
   slides. The research directions come from our proposal.
3. Results: the files under `results/` are produced by running this code; no number is typed in
   by hand.
