# EE779-Poisson-Denoising
This is a project on advanced signal processing with emphasis on low lighting condition images and denoising these images with the use of available tools.

# Directions A and B

Implemented as specified in `ABLATION_PLAN.md` (§9 maps every experiment ID to its code and
configs, and lists the few items not implemented yet). Results: `results/directions_*`.

# Baseline

Two baselines from the proposal (`output/EE779.odp`, slides 4–8, 12):

* **Anscombe + BM3D** with the exact unbiased inverse (Mäkitalo & Foi 2011), computed
  numerically from the Poisson pmf; closed-form, asymptotic and algebraic inverses for comparison.
* **P4IP-BM3D** (Rond, Giryes & Elad): ADMM with the closed-form Poisson step (numerically
  stable root, slide 14), BM3D at σ² = β/ρ, increasing ρ (ρ_step 1.065, 70 iterations,
  output x, zero init, as in the journal version). Multiple priors (slide 15) are supported.

## Layout

| Path | Contents |
|---|---|
| `data/test`, `data/tune`, `data/train` | 8 test images (Set12 subset, 256×256), 4 tuning images (BSD68 crops), 400 training images (BSD400). Disjoint. |
| `pdn/` | noise simulation and binning, metrics, Anscombe, denoiser registry, P4IP, methods, experiment runner; direction A: `wavelet.py` (A1), `dictionary.py` (A2); direction B: `sparse.py` (B1 ISTA/FISTA) |
| `experiments/` | `tune.py` (grid search on the tuning split), `run.py` (test split), `analyze.py` (tables, paired stats, plots), `learn_dictionary.py` (A2), `convergence.py` (B1.a/B1.b, A1.a), `configs/` |
| `models/` | A2 dictionaries learned on `data/train` (with their learning settings) |
| `tests/` | unit tests: Poisson prox vs numerical minimiser, exact inverse unbiasedness, P4IP converging to a closed-form MAP solution, consensus split, denoiser contract, A1.a exact prox and convergence, A2 null-check equivalence, SWT Parseval/adjoint, B1.0 ISTA/FISTA = one-step solution |
| `ABLATION_PLAN.md` | the experiment list for directions A and B, protocol and claim rules |
| `GCP.md` | how to run everything on a VM |

## Quick start

```bash
pip install -r requirements.txt
python -m pytest -q tests
python -m experiments.run experiments/configs/smoke.json
python -m experiments.tune experiments/configs/tune_p4ip_bm3d.json
python -m experiments.run experiments/configs/baselines.json
python -m experiments.analyze results/baselines --ref p4ip_bm3d
```

New priors plug in through `pdn.denoisers.register` and new methods through
`pdn.methods.register`; see `ABLATION_PLAN.md` §6.

# LLM usage
AI assistant: Claude (Anthropic), used through Claude Code. Commits it co-wrote carry a
`Co-Authored-By: Claude` trailer, so `git log` shows exactly which ones.

1. Summarizing insights and documenting experimental setups: `ABLATION_PLAN.md`, `GCP.md`
   and the Baseline/Layout sections of this README were drafted with Claude.
2. Code generation, including the novelty experiments: the harness (`pdn/`, `experiments/`,
   `tests/`), the baselines, and the direction A and B implementations were written with
   Claude: `pdn/wavelet.py` (A1), `pdn/dictionary.py` and `experiments/learn_dictionary.py`
   (A2), the consensus configs (A3), `pdn/sparse.py` (B1), and their configs and tests. The
   research directions come from the proposal (`output/EE779.odp`).
3. Baseline results' regeneration: the result files under `results/` were produced by
   running this code (in the Claude session or on our own VM); no numbers were typed in by hand.