# Ablation plan for EE779.odp directions A and B

This file turns slides 10–18 of `output/EE779.odp` into a concrete experiment list.
Every experiment changes **one factor** relative to a named **parent**, is tuned with the
**same protocol and budget** as its parent, and is scored on the **same noisy images**.
Experiment IDs (B0.2, A1.c, ...) are used as `label`s in configs and result tables.

The baselines (stage B0) and the harness are implemented. The direction A/B denoisers
and solvers plug into the harness as described in §5.

---

## 0. Protocol (applies to everything)

| Item | Setting | Why |
|---|---|---|
| Test images | `data/test/`: cameraman, house, peppers, starfish, monarch, airplane, parrot, boat (centre 256×256 crop) | 8 images like the paper; cameraman, house, peppers overlap with its Table 1 |
| Tuning images | `data/tune/`: 4 BSD68 images, centre 256×256 crop | Parameters are never chosen on test images |
| Training images | `data/train/`: BSD400 (400 × 180×180) | Dictionary learning only (A2, B1) |
| Noise model | `s = img / max(img)`, `x = p·s`, `y ~ Poisson(x)` | Slide 12 |
| Peaks `p` | 0.1, 0.2, 0.5, 1, 2, 4 | Slide 12 / paper Table 1 |
| Test noise reps | 0, 1, 2 (3 realisations per image and peak) | Seed is a hash of (image, peak, rep) only: every method sees identical `y` |
| Tuning noise reps | 100 (add 101 for final tuning) | Never overlaps test seeds |
| Metric | PSNR = 10 log10(p² / MSE), SSIM on `x̂/p` with range 1, mean signed bias / p | Same scale as the paper; no clipping before scoring |
| Runtime | total wall time and time inside the denoiser, single thread per job | Quality–runtime trade-off is the project question (slide 13) |
| Binning | 3×3 sum, linear upsampling; **separate table**, tuned separately | Slide 12 |

**Statistics and claim rule** (`experiments/analyze.py`). Reps are averaged within each
image, then the 8 images are the paired units. For each peak report the mean ΔPSNR vs
the parent, the 95 % t-interval, wins/8 and the exact Wilcoxon p, then Holm-correct
across the 6 peaks. Call a change an **improvement** only if the interval excludes 0,
Holm p < 0.05 and wins ≥ 7/8. Otherwise write "no detectable difference at this sample
size" and still report the effect size. With 8 images the smallest possible Wilcoxon p is
0.0078, so 6/8 wins can never be significant.

**Tuning protocol** (`experiments/tune.py`). Per peak, a two-stage grid on the tuning
split: stage 1 is 3×3 over the two most sensitive parameters on a log grid (factor 4
apart), stage 2 is 3×3 around the stage-1 winner (factor 2 apart). The tuner flags a
winner on the grid edge; extend the grid and re-run. Each variant gets the same number
of configurations as its parent. If a variant adds a parameter (for example a consensus
weight), also re-tune the parent with the same number of configurations (control
"budget-matched parent"), otherwise extra tuning is confounded with the method.

**Logged per P4IP run** (`results/<exp>/traces/*.json`): ρ_k, σ_k, primal residual
‖x−v‖/(√N·p), change ‖v_k−v_{k−1}‖/(√N·p) and the Poisson NLL at every iteration. Sparse
priors also log the sparsity (§5).

---

## 1. Stage B0 – reproduce the baselines (implemented)

Parent of everything in direction A: **B0.2 P4IP-BM3D**.

| ID | Change vs parent | Parent | Purpose |
|---|---|---|---|
| B0.0 | ML estimate `x̂ = y` | — | Floor, sanity check |
| B0.1 | Anscombe + BM3D (σ = 1) + **exact unbiased inverse** | — | Paper's "BM3D" column |
| B0.1a | inverse: closed-form approximation | B0.1 | Checks the inverse implementation |
| B0.1b | inverse: asymptotic `z²/4 − 1/8` | B0.1 | Slide 4 claim about bias |
| B0.1c | inverse: algebraic `z²/4 − 3/8` | B0.1 | Slide 4 claim about bias; expect large negative `bias` at p ≤ 0.5 |
| B0.2 | P4IP-BM3D: zero init, ρ_step 1.065, 70 iterations, output x, β and ρ₀ tuned per peak | — | Paper setting (journal version) |
| B0.2a | output v instead of x | B0.2 | Unspecified choice in the arXiv version |
| B0.2b | init v⁰ = Anscombe-BM3D estimate | B0.2 | Paper claims init does not matter |
| B0.2c | rescale scaled dual when ρ changes (`u ← u·ρ_old/ρ_new`) | B0.2 | Standard ADMM vs paper Alg. 1 |
| B0.2d | ρ_step ∈ {1.0, 1.03, 1.1} (re-tune ρ₀) | B0.2 | Paper says increasing ρ helps |
| B0.2e | iterations ∈ {30, 50, 100}; also PSNR vs iteration curve from traces | B0.2 | Equal-runtime comparison |
| B0.2f | BM3D first stage only (`stage: hard`) | B0.2 | Runtime/quality trade-off of the prior |
| B0.3 | 3×3 binning for B0.1 and B0.2 (ρ_step 1.1, 50 iterations, re-tuned) | B0.1/B0.2 | Paper Table 2 |

**Acceptance check before starting A or B.** The absolute numbers will differ from the
paper (different images), but the trend must match Table 1: P4IP beats Anscombe-BM3D at
p = 0.1 and 0.2, and the gap shrinks by p = 4. If it does not, fix tuning first;
every later comparison inherits this baseline.

---

## 2. Direction A1 – orthonormal wavelet shrinkage as the P4IP prior (slide 10)

Denoiser `D(r, σ) = Wᵀ S(W r, η)` registered as e.g. `wavelet_soft`. Everything else
is identical to B0.2 (same Poisson step, ρ schedule, iterations, init, output). Tune β
and ρ₀ exactly as B0.2, plus the threshold constant `c`.

**A1-default:** `db4`, J = 4 levels, periodization (exactly orthonormal), soft
threshold, threshold on detail subbands only, `η = c·σ`, no cycle spinning.

| ID | Single change vs A1-default | What it tests |
|---|---|---|
| A1.a | `η = σ² = β/ρ` (no separate `c`; β is the only weight) instead of `c·σ` | Only `η = β/ρ` makes the denoiser the exact prox of `β‖W v‖₁` (for orthonormal W). Then P4IP is ADMM on an explicit convex objective: log `f(x)+β‖Wx‖₁` per iteration and check it settles (ADMM is not monotone; run A1.a once with constant ρ to confirm convergence, then with the paper schedule). `η ∝ σ` is the usual heuristic denoiser. This is the cleanest "explicit prior vs plug-in" ablation. |
| A1.b | also threshold the approximation (LL) band | Slide 10 "preserve or separately tune the approximation band" |
| A1.c | wavelet ∈ {haar, sym8} (same J) | Sensitivity to filter length/smoothness |
| A1.d | J ∈ {2, 3, 5} | Sensitivity to the coarsest scale |
| A1.e | hard instead of soft threshold | Bias of soft thresholding at low counts |
| A1.f | per-subband constants `c_j` (one per level, J values tuned) | Slide 10 "tune thresholds by subband". Budget: give B0.2 and A1-default the same number of tuning configs (budget-matched control). |
| A1.g | cycle spinning over K ∈ {4, 16} shifts (average of shifted D) | Removes shift variance; no longer an exact prox. Report runtime ×K. |

**Main comparison:** best A1 vs B0.2 on a PSNR–runtime plot at every peak (expect
BM3D higher PSNR and A1 one to two orders of magnitude faster). The project question is
the trade-off, so report the PSNR gap **and** the speed-up, and also compare against
B0.2f (cheaper BM3D) and B0.2e at 30 iterations so the speed comparison is fair.

**Extra measurements for A1:** fraction of non-zero detail coefficients after
thresholding at the final iteration; objective value per iteration (A1.a only).

---

## 3. Direction A2 – learned dictionary on wavelet-domain patches (slides 10, 16)

Denoiser: extract all `P×P` patches of `r` with stride `s`, compute `c_j = W_p R_j r`,
sparse-code each `c_j` in a **frozen** dictionary `B`, reconstruct `W_pᵀ B α_j`, average
the overlaps (slide 16 formula with `w_j = 1`). The dictionary is learned **once** on
`data/train`, never on test images, and saved to disk with its training seed.

**A2-default:** P = 8, stride 2, `W_p` = 1-level Haar on the 8×8 patch (orthonormal),
K = 256 atoms, LL (coarse) coefficients excluded from `B` and passed through unchanged,
`B` learned on the 48 detail coefficients from 100 000 random training patches (fixed
seed), sparse coding by error-constrained OMP with `‖c − Bα‖² ≤ n·(γσ)²`, n = number of
coded coefficients, γ tuned (start 1.15). Learner: the same algorithm, iterations and
atom-norm constraint `‖b_l‖ ≤ 1` for every variant (e.g. scikit-learn
`MiniBatchDictionaryLearning`, fixed `random_state`).

| ID | Single change vs A2-default | What it tests |
|---|---|---|
| A2.0 | **pixel-domain** dictionary, same K, same patches, same learner, DC handled the same way | The essential control (slide 16): is the wavelet domain doing anything? |
| A2.1 | wavelet domain, **free** `B` over all 64 coefficients (LL included) | Null check: with an orthonormal `W_p` this is a reparametrisation of A2.0, so it should match A2.0 up to learning noise. A gap here is an optimisation artefact, not a modelling gain. |
| A2.2 | separate dictionaries per orientation (LH, HL, HH), K/3 atoms each | Structured wavelet model |
| A2.3 | K ∈ {64, 128, 512} | Capacity |
| A2.4 | P = 6 (with a matching W_p) | Patch size |
| A2.5 | stride ∈ {1, 4} | Runtime vs quality (stride 1 is ~4× slower) |
| A2.6 | aggregation weights `w_j = 1/(1+‖α_j‖₀)` | Slide 16 `w_j` |
| A2.7 | fixed sparsity T ∈ {2, 4, 8} instead of error-constrained OMP | Stopping rule |
| A2.8 | dictionary trained on Anscombe-domain noisy patches vs clean patches | Whether training should match the intermediate ADMM image |

**Claim structure.** A "wavelet enhancement" holds only if A2-default (or A2.2) beats
**A2.0** under the claim rule. Beating B0.2 is a separate question. Report average
‖α‖₀ per patch at the last iteration, and dictionary learning time separately from
reconstruction time.

---

## 4. Direction A3 – BM3D + wavelet consensus (slide 15)

Two priors, shared ρ schedule, `rho_weight` per prior (implemented in `pdn/p4ip.py`, see
`Prior.rho_weight`). Prior 1 is BM3D, prior 2 is the best A1 configuration. Output x.

| ID | Change | Purpose |
|---|---|---|
| A3-default | BM3D (weight 1) + best A1 (weight w₂), tune β₁, β₂, ρ₀; w₂ ∈ {0.25, 0.5, 1} | The proposed variant |
| A3.c1 | **BM3D + BM3D** (two identical copies, same weights) | Control: separates "a second, different prior" from "changed effective ρ and σ". Required. |
| A3.c2 | B0.2 re-tuned with the same number of configs as A3 | Budget-matched parent |
| A3.c3 | A1 + A1 | Symmetric control for the wavelet side |
| A3.b | with 3×3 binning at p = 0.2 | Direct comparison to paper Table 3 (+0.21 dB there) |

The paired difference A3 − A3.c1 is the actual test of "wavelets complement BM3D".
Runtime is roughly the sum of both denoisers.

---

## 5. Direction B – explicit sparse objective with ISTA/FISTA (slides 11, 17, 18)

Problem: `z = A(y)` (Anscombe), `min_α ½‖Dα − z‖² + λ‖α‖₁`, then `x̂ = A⁻¹_exact(Dα̂)`.
`D` is **fixed** during sparse coding.

**B1-default:** D = undecimated (stationary) wavelet tight frame (db4, J = 3, Parseval so
L = 1), α⁰ = 0, stopping when the relative change in F falls below 1e-6 or after 1000
iterations, λ tuned per peak on the tuning split.

| ID | Change | What it tests |
|---|---|---|
| B1.0 | D = orthonormal wavelet (A1-default basis) | **Correctness test:** ISTA and FISTA must converge to the one-step solution `S(Dᵀz, λ)` (slide 17). Unit test, not a result. |
| B1.a | **ISTA vs FISTA**: same F, λ, L, α⁰ and stopping rule | Slide 11. Report F(αᵏ) − F* vs k and vs wall time (F* from 5000 FISTA iterations), iterations to reach F − F* ≤ 1e-3·F* and 1e-4·F*, and final PSNR. Expect the FISTA rate advantage in iterations, not necessarily in PSNR. |
| B1.b | PSNR vs iteration (early stopping) | Whether the converged minimiser is the best estimate |
| B1.c | D = A2's learned dictionary, patch-wise (each patch coded independently, overlaps averaged) | Learned vs analytic frame inside the same objective. L = ‖B‖² from power iteration. |
| B1.d | inverse: algebraic instead of exact | Interaction with the Anscombe bias at low peaks |
| B1.e | L by backtracking instead of ‖D‖² | Slide 17 note |

**Key cross-direction ablation (the likelihood effect).** Compare **B1 with an orthonormal
basis** (the one-step Anscombe-domain solution) against **A1.a** with the same basis
and the same threshold rule (`η = β/ρ`), β and λ each tuned on the tuning split. The prior is identical, so the difference measures
"approximate Gaussian likelihood after Anscombe" vs "exact Poisson likelihood via P4IP" as
a function of peak. Expect the gap to grow as the peak falls.

**Optional B2 (slide 18), exact Poisson + wavelet ℓ1.** `min_{x ≥ ε} Σ(x − y log x) +
β‖Wx‖₁` solved two ways: (i) A1.a (P4IP/ADMM, η = β/ρ) and (ii) proximal gradient
with backtracking on the domain x ≥ ε and an inner solver for the prox of
`β‖W·‖₁ + I{x≥ε}` (e.g. Dykstra or a few ADMM steps). Both solve the same convex
problem, so their objective values must agree to tolerance (cross-check). Then compare
runtime. Disclose ε.

---

## 6. How the new methods plug in

* **Priors (A1, A2, A3):** a function `D(r, sigma, **params) -> array` in your own
  module, decorated with `@pdn.denoisers.register("name")`. List the module under
  `"plugins"` in the config and use `{"denoiser": "name", "beta": ..., "params": {...}}`
  in `priors`. `tests/test_denoiser_contract.py` checks shape, finiteness, negative
  inputs and determinism: `PDN_PLUGINS=yourmodule pytest tests`.
* **Whole methods (B1):** a function `method(y, peak, **params) -> (x_hat, info)`
  decorated with `@pdn.methods.register("name")`. Put iteration logs (objective,
  sparsity) in `info["trace"]` as a list of dicts and the runner saves them.
* **Sparsity logging:** return it via a module-level counter or put it in the trace
  from the method. The analysis treats any extra trace keys as plain data.

## 7. Compute budget (measured here: BM3D on 256×256 ≈ 3.4 s per call per core)

| Run | Jobs | Cost per job | Core-hours |
|---|---|---|---|
| B0.1 test (8 × 6 × 3) | 144 | ~4 s | 0.2 |
| B0.2 tuning (18 configs × 4 img × 1 rep × 6 peaks) | 432 | ~4 min | ~29 |
| B0.2 test | 144 | ~4 min | ~10 |
| each B0.2 sub-ablation (test only, re-tune where stated) | 144 | ~4 min | ~10 (+29 if re-tuned) |
| A1 variants | 144 | seconds | < 1 each |
| A3 (BM3D + wavelet) | 144 | ~4.5 min | ~11 + tuning |

B0 in full (tuning, test, all six sub-ablations, two re-tunes) is about 160 core-hours: roughly 10–12 hours on a 16-vCPU VM.
Run the cheap A1/B1 sweeps first while BM3D jobs queue.

## 8. What goes in the report

1. Table 1 equivalent: mean PSNR per method per peak (+ SSIM), no binning; binned table separately.
2. Paired-difference table for each ablation group with Δ, CI, wins/8, Holm p.
3. PSNR vs runtime scatter at p = 0.2 and p = 1 (one point per method).
4. Convergence: ADMM residuals and PSNR vs iteration (B0.2, A1, A1.a with objective), ISTA vs FISTA F − F*.
5. Visual crops: cameraman and house at p = 0.2 and p = 1 for B0.1, B0.2, best A1, best A2, A3.
6. A parameter table: tuned β, ρ₀ (and c, γ, λ) per peak per method.
7. A limitations paragraph: 8 test images, synthetic Poisson noise, tuning budget, ε in B2.
