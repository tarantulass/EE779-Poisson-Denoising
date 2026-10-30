# EE779-Poisson-Denoising
This is a project on advanced signal processing with emphasis on low lighting condition images and denoising these images with the use of available tools.

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
| `pdn/` | noise simulation and binning, metrics, Anscombe, denoiser registry, P4IP, methods, experiment runner |
| `experiments/` | `tune.py` (grid search on the tuning split), `run.py` (test split), `analyze.py` (tables, paired stats, plots), `configs/` |
| `tests/` | unit tests: Poisson prox vs numerical minimiser, exact inverse unbiasedness, P4IP converging to a closed-form MAP solution, consensus split, denoiser contract |
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
1. Only for summarizing any useful insights or documenting experimental setups
2. Not used for code generation of any novelty experiments
3. Baseline results' regeneration - llm usage is mentioned as follows: