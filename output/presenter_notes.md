# Presenter notes (not for the slides)

## 1. ISTA and FISTA, from scratch

### The problem they solve
Direction B writes denoising as one explicit optimisation problem:

    minimise  F(α) = ½‖Dα − z‖² + λ‖α‖₁

* z = A(y) = 2√(y + 3/8): the Anscombe-transformed noisy image (noise ≈ Gaussian, σ ≈ 1).
* D: a fixed dictionary (columns = atoms). We use (i) a redundant (undecimated) wavelet frame and
  (ii) our learned 8×8 patch dictionary placed on overlapping patches.
* α: the coefficients. The image estimate is Dα, mapped back with the exact inverse Anscombe.
* ½‖Dα − z‖²: "fit the data". λ‖α‖₁: "use few atoms" (sparsity). λ trades one against the other.

F is convex, so every local minimum is the global minimum, but it is not differentiable (the |·| in
‖α‖₁ has a kink at 0), so plain gradient descent does not apply.

### Split F into a smooth part and a simple part
* f(α) = ½‖Dα − z‖² is smooth. Its gradient is ∇f(α) = Dᵀ(Dα − z).
  The gradient changes at most L times as fast as α, with L = ‖D‖₂² (largest eigenvalue of DᵀD).
  So 1/L is a safe step size.
* g(α) = λ‖α‖₁ is not smooth, but its proximal step is trivial: soft thresholding,

      S(c, t) = sign(c) · max(|c| − t, 0)

  "shrink every coefficient towards 0 by t; if it is smaller than t, set it to 0".

### ISTA (Iterative Shrinkage-Thresholding Algorithm)
Repeat:

    αᵏ⁺¹ = S( αᵏ − (1/L) Dᵀ(Dαᵏ − z),  λ/L )

1. Take a gradient step on the data term (move α to explain z better).
2. Soft-threshold (kill small coefficients, shrink the rest).

Why it works: each step minimises a quadratic upper bound of F around αᵏ (that is what the 1/L step
guarantees), so F never increases. Convergence rate: F(αᵏ) − F* ≤ L‖α⁰ − α*‖² / (2k), i.e. O(1/k).
To gain one more digit of accuracy you need about 10× more iterations.

### FISTA (Fast ISTA, Beck and Teboulle 2009)
Same step, but taken from an extrapolated point q instead of the last iterate:

    αᵏ   = S( qᵏ − (1/L) Dᵀ(Dqᵏ − z),  λ/L )
    tₖ₊₁ = (1 + √(1 + 4tₖ²)) / 2,          t₁ = 1
    qᵏ⁺¹ = αᵏ + ((tₖ − 1)/tₖ₊₁) (αᵏ − αᵏ⁻¹)

The last line is momentum: keep moving in the direction you were already moving, by a factor that
grows towards 1. It costs nothing extra per iteration (one multiplication by D and one by Dᵀ, same
as ISTA). Rate: F(αᵏ) − F* ≤ 2L‖α⁰ − α*‖² / (k + 1)², i.e. O(1/k²). That rate is optimal for
first-order methods on this problem class. F is not monotone for FISTA (small ripples are normal;
you can see them in our convergence plot).

### Why both give the same image in our results
F is convex and has one minimum value F*, so both methods aim at the same solution. We use the
same λ, the same start α⁰ = 0 and the same stopping rule |Fₖ − Fₖ₋₁| ≤ 10⁻⁷ Fₖ, so the PSNR is the
same to 0.01 dB. Only the number of iterations differs: FISTA needed 1.3 to 8× fewer (ISTA often
hit the 2000-iteration cap, so the true ratio is larger).

### Why iterate at all? (slide 17 of the proposal)
If D is an orthonormal basis (DᵀD = I), the minimiser is one step: α* = S(Dᵀz, λ). Iteration is
needed only because our dictionaries are redundant (more atoms than pixels): then coefficients
compete and there is no closed form.

### Why Direction B gives "nothing to iterate" without binning
At low peaks the Anscombe image is almost pure noise in the detail bands. With a Parseval frame
each detail coefficient carries noise of standard deviation ≈ 1. The tuned λ (1 to 4) is larger than
almost every detail coefficient, so the minimiser is α = 0 and the estimate is the smooth coarse
part of z. The tuning chose this because any detail it keeps is mostly noise. With 3×3 binning the
counts are 9× larger, the detail coefficients rise above λ, and ISTA/FISTA have real work to do.

## 2. Likely questions and short answers

**Why does P4IP beat Anscombe + BM3D at low peaks but lose at high peaks?**
At low peaks the Anscombe approximation is poor (variance is not 1, the inverse is biased); P4IP uses
the exact Poisson likelihood in its x-step. At high peaks the Anscombe approximation is accurate, so
Anscombe + BM3D is already near-optimal, and P4IP's 70 ADMM iterations with a fixed schedule add a
small error.

**Why are your absolute numbers lower than the paper's?**
Different test images (ours include textured ones: monarch, parrot, starfish), one noise draw per
image, Python BM3D (bm3d package) instead of the authors' MATLAB code, and a simplified SPDA. On the
three images both studies share (Cameraman, House, Peppers), our P4IP + BM3D is within about 0.3 dB of
the paper from peak 0.2 up.

**Why did the multiple-prior method (A3) help only at peak 0.1?**
At peak 0.1 most pixels are 0, so BM3D's block matching finds wrong "similar" patches and leaves
artefacts. The wavelet prior gives a stable smooth estimate; averaging the two in the consensus step
suppresses BM3D's mistakes. From peak 0.5 up, block matching works, the wavelet prior only adds
blur, and the tuning drives its weight to the smallest value tried.

**Why does a per-level threshold help the wavelet prior?**
The tuned weights are large at the finest level (w1 = 2 to 4) and small at the coarsest
(w4 = 0.25 to 0.5). At low counts the finest scales are mostly noise, the coarse scales carry the
structure. One threshold must compromise; per-level thresholds remove fine-scale noise without
erasing coarse structure.

**Why is the wavelet-patch dictionary not better than the pixel dictionary?**
The 8×8 patch Haar transform is orthonormal, so coding in the wavelet domain spans the same space
as coding in pixels. Our "structure" (each atom restricted to one orientation) removes freedom
rather than adding information, so it can only match or lose. Both are local patch models and lack
BM3D's non-local grouping, which is why both stay below BM3D.

**Why use the exact unbiased inverse Anscombe?**
E[A(y)] is not 2√(x + 3/8) at low counts, so the algebraic inverse z²/4 − 3/8 is biased. The exact
inverse maps E[A(y) | x] back to x (Mäkitalo and Foi). It gains 1.7 to 3.9 dB in our runs.

**What is binning and why does it help?**
Sum each 3×3 block: counts become 9× larger (peak ×9), the Poisson noise is relatively smaller and
the Anscombe approximation holds. Denoise, then interpolate back. It loses resolution, so it helps
at peak 0.1 (Anscombe + BM3D +2.25 dB) and hurts at peak 4 (−1.38 dB).

**How did you choose parameters? Did you tune on the test images?**
No. Every parameter is chosen per peak on 4 separate BSD68 tuning images; the 8 test images are used
only for the final numbers. FMD parameters are transferred from that tuning, not tuned on FMD.

**How do you get Poisson data from FMD?**
FMD noise is Poisson-Gaussian: Var(z) = a·u + b. We fit a and b per image from the raw capture and
the 50-frame average, then y = z/a + b/a² has mean = variance, i.e. it is approximately Poisson, so
the same Poisson methods run unchanged.

**Is the difference significant?**
We use the paired Wilcoxon signed-rank test over the 8 test images (same images, same noise for
both methods). With 8 images the smallest possible p is 0.0078 (all 8 images agree).

**What is ρ in P4IP and why does it grow?**
ρ is the ADMM penalty that ties x (data step) to v (denoiser step). The denoiser sees noise level
σ² = λ/ρ. Starting with small ρ lets the denoiser smooth strongly; multiplying ρ by 1.065 each
iteration makes x and v agree by the end (70 iterations, as in the paper).

**Runtime?**
Anscombe + BM3D: seconds per image. P4IP + BM3D: 70 BM3D calls, a few minutes per image on one core.
SPDA (simplified): about 20 to 30 s. ISTA/FISTA: under a second to tens of seconds.

**What did FMD show?**
On 12 real images (one per microscope and sample type; effective peaks 13 to 86 photons), P4IP + BM3D and
Anscombe + BM3D are level on average (not significant, p = 0.79). P4IP wins all three wide-field images
(+1.6 to +2.1 dB); Anscombe + BM3D wins 8 of 9 confocal and two-photon images. The wide-field captures have
strong Gaussian read noise (fitted b ≈ 90, against ≈ 0 for the others). We did not isolate why P4IP handles
them better; say so if asked. A3 (BM3D + wavelet) is the highest on average (+0.14 dB over P4IP).
Parameters were not tuned on FMD; they were transferred from the synthetic tuning at peak 4.
