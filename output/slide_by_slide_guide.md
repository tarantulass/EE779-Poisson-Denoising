# Slide-by-slide guide (for you, not for the slides)

Read this once top to bottom. Each slide has four parts:
**What is on it** · **What it means in plain words** · **What to say** (about the suggested time) · **If they ask**.

---

## First: the one picture that explains everything (photons and "peak")

Think of each pixel of the camera as a **bucket left out in light rain**. Each raindrop is a **photon**.

* A bright part of the scene = heavy rain on that bucket. A dark part = light rain.
* You leave the buckets out for a short time and then **count the drops** in each one.
  That count is the pixel value y. It is always a whole number: 0, 1, 2, ...
* Even if two buckets get exactly the same rain, one may catch 3 drops and the other 5. That
  randomness is the **noise**. It is called **Poisson noise** because the number of random
  arrivals in a fixed time follows the Poisson distribution.

**The clean image x** is the *average* number of drops each bucket would catch if you repeated the
experiment many times. **The noisy image y** is what you actually counted once. Denoising = guess x from y.

**Peak p** = the average number of drops in the *brightest* bucket.
* Peak 4: the brightest pixel gets about 4 photons on average; darker pixels fewer. Dim but readable.
* Peak 1: the brightest pixel gets about 1 photon. Very dark.
* Peak 0.1: the brightest pixel gets 0.1 photons on average, i.e. it catches a photon only about
  1 time in 10. About **90% of all pixels read 0**. The image looks like a few scattered dots.

So "peak from 0.1 to 4" just means: **we tested at six light levels, from almost total darkness
(0.1) to dim light (4)**. We did not invent this range: the P4IP paper uses exactly these six values,
so using them lets us compare our numbers with theirs.

How we make a test image at peak p (this is what "synthetic" means):
1. Take a normal clean photo (e.g. Cameraman), scale it so its brightest pixel is 1.
2. Multiply by p. Now the brightest pixel's average is p photons → this is x.
3. For every pixel draw a random Poisson count with average x → this is the noisy y.
4. Give y to each method; compare its output with x.

Why the light level matters: with few photons, the randomness is huge compared to the signal.
The rule for Poisson noise is **variance = mean**, so the "signal-to-noise ratio" is √(mean).
At 4 photons SNR = 2; at 0.1 photons SNR ≈ 0.3 (noise bigger than signal).

---

## Slide 1 — Title

**What is on it:** project name, your names, the three parts of the talk.

**Plain words:** "We clean up images taken with very little light. We reproduce a published method
(P4IP), test it on real microscope images, and try two ideas of our own."

**Say (20 s):** Read the three outline lines; they are the structure of the talk.

---

## Slide 2 — Motivation and project goals

**What is on it:** where low-light imaging happens, and five goals.

**Plain words:**
* Microscopy: you use little light because strong light damages or kills living cells.
* Astronomy: faint stars send few photons. Medical PET/CT: low dose protects the patient.
  Night photography: little light, short exposures.
* In all of these, each pixel counts only a handful of photons → very noisy images.

The five goals:
1. Reproduce the paper's results (P4IP vs Anscombe + BM3D vs SPDA).
2. Check on real data (FMD microscope images).
3. Our idea A: replace the "denoiser" inside P4IP with other ones.
4. Our idea B: write denoising as a sparse optimisation problem, solve it with ISTA and FISTA.
5. Compare everything fairly: same images, same noise, separate images for choosing parameters, statistical tests.

**Say (45 s):** "Goals 1–2 reproduce the paper, goals 3–4 are our own contributions, goal 5 is how we
keep the comparison fair."

---

## Slide 3 — Problem statement: Poisson noise

**What is on it:**
* yᵢ ∼ Poisson(xᵢ): the count at pixel i is random with average xᵢ.
* P(yᵢ = k) = e^(−x) xᵏ / k!: the probability of counting exactly k photons.
* E[y] = Var(y) = x: average and variance are equal.
* SNR = √x.
* Peak convention x = p·s.

**Plain words:**
* "Variance = mean" means the noise is **not the same everywhere**: bright pixels have more noise
  in absolute terms, dark pixels less. Normal (Gaussian) denoisers assume the same noise everywhere,
  so they are the wrong tool.
* The probability of getting 0 photons when the average is 0.1 is e^(−0.1) ≈ 0.905, i.e. 90%.
  That is why the image is mostly zeros at peak 0.1.

**Say (50 s):** "We get one noisy count image y and must estimate the true brightness x. Three things
make it hard: the noise depends on the signal, the data are whole numbers, and at the lowest light
90% of pixels are zero."

**If they ask "why not just average neighbouring pixels?":** you can (that is the mean filter), but it
blurs edges; the methods on the next slides try to remove noise without blurring.

---

## Slide 4 — Existing methods and where they fail (1)

**What is on it:** a table of classic methods and their weaknesses, with our measured numbers.

**Plain words, row by row:**
* **Mean / Gaussian / median / Wiener filters:** replace each pixel by a (weighted) average or the
  median of its neighbours. Simple, but blur edges. The **median** is useless at low light: if most
  neighbours are 0, the median is 0 → our median filter got only 4.98 dB at peak 0.1.
* **Wavelet thresholding / non-local means:** wavelets split the image into coarse and fine detail
  and remove small (noisy) detail; NL-means averages pixels from similar-looking patches. Both are
  designed for Gaussian noise.
* **Poisson-TV:** uses the correct Poisson model but assumes the image is piecewise flat → "staircase"
  look, loses texture.
* **Anscombe transform:** z = 2√(y + 3/8). This formula turns Poisson noise into *approximately*
  Gaussian noise with variance 1, so any Gaussian denoiser can then be used. Afterwards you must
  convert back (the **inverse**). The approximation is only good when counts are not tiny.

**The measured sentence:** "with the same BM3D output, the algebraic inverse loses 1.7 to 3.9 dB."
* The **algebraic inverse** z²/4 − 3/8 just undoes the formula. At low counts it is **biased**
  (systematically too dark/bright) because the average of a square root is not the square root of the average.
* The **exact unbiased inverse** (Mäkitalo and Foi) corrects for that. Same denoiser, only a different
  way back → 1.7 to 3.9 dB better. That is a big difference (1 dB is clearly visible).
* Even with the exact inverse, at peak 0.1 a plain tuned Gaussian blur (16.15 dB) beats Anscombe + BM3D
  (13.82 dB). Meaning: at extreme darkness the Anscombe route breaks down.

**Say (60 s):** "Classic filters assume Gaussian noise. The standard fix, the Anscombe transform, is only
approximate at low light; our own runs show both problems."

---

## Slide 5 — Existing methods and where they fail (2)

**Plain words:**
* **BM3D** (best classic Gaussian denoiser): for each small patch it finds other patches that look
  similar anywhere in the image, stacks them, filters the stack together (similar patches share the
  real structure, the noise differs), and puts them back. **Problem at low light:** patches are
  almost all zeros, so "similar" patches are found wrongly → artefacts. It also needs the Anscombe step.
* **SPDA:** describes each patch as exp(Dα): a few "atoms" from a dictionary D, inside an exponential
  so brightness stays positive. It uses the true Poisson model. **Problem:** very slow (the P4IP paper
  reports about 10 hours per image without binning).
* **The gap (bold line):** we want the correct Poisson model *and* the best denoiser *and* reasonable speed.

**Say (50 s):** "BM3D has the best image model but the wrong noise model; SPDA has the right noise model
but is slow. P4IP is designed to get both."

---

## Slide 6 — Reference method: P4IP

**What is on it:** the optimisation problem and the three ADMM steps.

**Plain words:**
* We want an image x that (a) explains the counts y well and (b) looks like a natural image.
  (a) is f(x) = Σ(xᵢ − yᵢ log xᵢ): the exact Poisson "badness of fit". (b) is λR(x): a penalty for
  unnatural images; λ says how much we care.
* Problem: no simple method solves (a) and (b) together. **ADMM** splits the problem: make two copies
  x and v, force them to agree, and alternate:
  1. **Poisson step (x):** fit the counts, but stay close to the current denoised image. Has a formula (next slide).
  2. **Denoiser step (v):** clean up x with **any Gaussian denoiser** (BM3D). The denoiser is told the
     noise level σ² = λ/ρ.
  3. **Dual step (u):** keeps track of how much x and v still disagree, and pushes them together.
* **ρ** is how strongly x and v are forced to agree. It starts small (denoiser smooths a lot) and is
  multiplied by 1.065 each round, 70 rounds, so by the end x and v agree.
* **"Plug-and-play"** = the denoiser is a plug-in box. Swap BM3D for something else and nothing else changes.
  That is exactly what our Direction A does.

**Say (60 s):** "P4IP separates the noise model from the image model. The noise model is handled exactly,
and the image model is any denoiser we like."

---

## Slide 7 — P4IP: closed-form Poisson step

**Plain words:** For each pixel separately, the Poisson step asks: which brightness x balances "fit my
count y" against "stay close to the denoised value a"? Setting the derivative to zero gives a quadratic
equation; its positive root is the formula on the slide. If the count is 0, the answer is simply
"a minus a little, but not below zero". So this step costs almost nothing.

**Say (45 s):** "The data step is exact and per pixel, so all the cost is in the denoiser. The paper reported
the best results at the two lowest light levels, in minutes instead of SPDA's hours."

---

## Slide 8 — Experimental protocol and changes from the paper

**Plain words, each row:**
* **Test images:** the paper used 8 images; 3 of them (Cameraman, House, Peppers) are also in our 8.
* **Tuning:** every method has knobs (parameters). We set them using 4 *other* images, never the test
  images, so our results are honest.
* **Noise:** same peaks; we draw the noise once per image with a fixed random seed, so every method
  sees exactly the same noisy image.
* **BM3D:** we use the Python version, the authors used MATLAB. **SPDA:** simplified (full version takes hours).
* **Real data:** we added FMD (the paper had none).
* **Statistics:** we add a paired test (is the improvement consistent across images?), SSIM and runtime.
* **Training images (400):** used only to learn the A2 dictionaries.

**Say (45 s):** "Everything that differs from the paper is listed here, so every gap later can be traced
to one of these rows."

---

## Slide 9 — Replication: average PSNR (paper Table 1)

**What PSNR is:** a score for how close the cleaned image is to the true image, in decibels (dB).
Higher is better. +1 dB is a visible improvement; +3 dB is large.

**How to read the table:** for each method, the paper's number (their 8 images) and ours (our 8 images),
at peaks 0.1, 0.2 and 1.

**Plain words:**
* **Reproduced:** P4IP beats Anscombe + BM3D at the low peaks, just like in the paper (+1.30 dB at peak 0.1).
* **Not reproduced:** in the paper SPDA wins at peak 1; ours does not (our SPDA is simplified).
* Our absolute numbers are lower because our images are harder (more texture). Different images →
  numbers are not directly comparable. That is why the next slide uses the same images.

**Say (60 s):** "The ranking is reproduced; the absolute values need the same images, which is next."

---

## Slide 10 — Replication on the same images

**How to read:** each cell is "paper / ours" for the same image at the same peak.

**Plain words:** On Cameraman, House and Peppers, our P4IP is within 0.31 dB of the paper from peak 0.2
upward. That is very close: the replication worked. At peak 0.1 we are about 1.2 dB lower; at that
light level a single random noise draw changes the result a lot, and we cannot use the paper's exact
random draws; the BM3D code also differs.

**Say (60 s):** "This is the cleanest check: same image, same light level. From 0.2 up we match within a third of a dB."

**If they ask "why lower at 0.1?":** "Fewest photons → most randomness; different noise draws and
different BM3D implementations. Our protocol fixes one draw per image."

---

## Slide 11 — Replication: binning and multiple priors

**Binning in plain words:** add up the photons in each 3×3 block of pixels (9 buckets → 1 big bucket).
The new image is 3× smaller each way but each pixel has 9× more photons, so peak 0.2 behaves like 1.8.
Denoise that, then stretch back to full size. Trade-off: less noise, less resolution.
Helps in extreme darkness, hurts when there is already enough light.

**What the table says:**
* Anscombe + BM3D with binning matches the paper within 0.49 dB → reproduced.
* Our binned P4IP is ~1 dB lower than the paper. Honest reason: when we tuned binned P4IP we used an
  early, too-narrow range for ρ₀ and the best value was at the edge of that range, so it could be better.
* "Multiple priors" in the paper = BM3D plus a second denoiser (+0.2 dB). Ours with binning did not
  gain (same edge-of-range issue); without binning it does (slide 16).

**Say (45 s):** "Binning is reproduced for the baseline; for binned P4IP we state openly that its tuning range was too narrow."

---

## Slide 12 — Real data: FMD fluorescence microscopy

**What FMD is:** a public dataset of real microscope images (3 microscope types: confocal, two-photon,
wide-field). For each scene they took 50 pictures; the **average of 50** is almost noise-free and serves
as the "true" image. A **single picture** is the noisy input.

**Why we needed a conversion:** real cameras add a second noise on top of photon noise (electronic
"read noise", Gaussian). So real noise variance = a·(brightness) + b. We estimated a and b for each image
from the single picture vs the average, then converted: y = z/a + b/a². After this, the data behave like
Poisson counts (variance = mean), so our methods run unchanged. "Effective peak 13 to 86 photons" means
these real images are brighter than our synthetic ones (0.1 to 4).

**Table (PSNR on 24 images where all methods ran):**
* Noisy input 26.76 → best methods ~32.6 dB (≈ +6 dB, a big improvement).
* A3 32.61, Anscombe + BM3D 32.60, P4IP 32.50: essentially a tie.

**Plain words:**
* Overall P4IP and Anscombe + BM3D are level (difference −0.10 dB, p = 0.59 → not significant).
* But it depends on the microscope: P4IP wins all 6 wide-field images (+1.6 to +2.1 dB); Anscombe +
  BM3D wins 17 of 18 confocal/two-photon images.
* Wide-field images have strong read noise. We did **not** prove why P4IP does better there; say so.
* This fits the synthetic results: at 10+ photons the Anscombe approximation works, so P4IP has no general edge.
* We did not re-tune anything for FMD; parameters were carried over.

**Say (60 s):** "On real microscope data the methods are level on average, and the winner depends on the microscope."

---

## Slide 13 — Proposed direction A

**Plain words:** P4IP lets us swap the denoiser. We tried three replacements:
* **A1 – wavelet shrinkage:** split the image into coarse and fine layers (wavelet transform), set small
  values to zero (they are mostly noise), shrink the rest, rebuild. "Per-level" = a different strength
  for each layer.
* **A2 – learned dictionary:** learn 256 typical 8×8 patch shapes ("atoms") from 400 training images;
  rebuild each noisy patch from a few atoms. Two versions: atoms learned on wavelet coefficients (our idea)
  vs atoms on raw pixels (the control, to check whether the wavelet idea helps).
* **A3 – multiple priors:** run BM3D *and* wavelet shrinkage every round and average them; how much the
  wavelet part counts (λ₂) is tuned.
* **Hypothesis:** wavelets help BM3D exactly where BM3D is weak: the lowest light.

**Say (45 s).**

---

## Slide 14 — A1 results

**Plain words:**
* Per-level thresholds beat one threshold by up to 1.41 dB. Why: the tuning chose strong removal at the
  finest layer (mostly noise at low light) and weak removal at the coarse layer (where the real shapes
  are). One single threshold must compromise.
* A1 beats Anscombe + BM3D at peak 0.1 (+1.23 dB) but loses from 0.5 up. Why: wavelets look at one
  neighbourhood at a time; BM3D also uses similar patches from *elsewhere* in the image ("non-local").
  When there is enough light to find those patches, BM3D recovers texture that wavelets erase.

**Say (60 s).**

---

## Slide 15 — A2 results

**Plain words:**
* The wavelet-domain dictionary is not better than the pixel dictionary (−0.16 to −0.25 dB).
  Why: the patch wavelet transform is just a rotation of the same 64-number space (orthonormal) → it
  cannot add information. Forcing each atom to one orientation only removes freedom.
* Both are below P4IP + BM3D: they only look at single patches, BM3D groups similar patches across the image.
* Unbinned test runs of A2 were skipped (25 min per image); tuning images show the same order.

**Say (50 s):** "A negative result with a clear mathematical reason."

---

## Slide 16 — A3 results (multiple priors)

**Plain words:**
* At peak 0.1, BM3D + wavelet beats BM3D alone by +0.66 dB on the test images, on **all 8 images**
  (Wilcoxon p = 0.0078, the strongest possible with 8 images).
* Why: at 0.1 photons, patches are almost all zeros, BM3D groups wrong patches and leaves blotches;
  the wavelet estimate is smooth and stable; averaging the two cancels BM3D's mistakes.
* From 0.2 up A3 is slightly worse (0.03 to 0.20 dB): BM3D is already reliable, the wavelet only adds a
  little blur; tuning picked the smallest wavelet weight but not zero.

**Say (60 s):** "Our main positive result: the second prior helps exactly where we predicted."

---

## Slide 17 — Direction B: ISTA vs FISTA

**Plain words:**
* Write denoising as: find coefficients α so that Dα (a combination of dictionary atoms) is close to the
  Anscombe image z, using as few atoms as possible. ½‖Dα − z‖² = closeness, λ‖α‖₁ = "few atoms".
* **ISTA:** repeat: step towards a better fit, then shrink small coefficients to zero ("soft thresholding").
* **FISTA:** the same, plus **momentum** (keep moving in the direction you were already going, like a
  rolling ball). Same cost per step, far fewer steps.
* Table (with binning): same PSNR for both, FISTA needs 1.3 to 8× fewer iterations (ISTA often stopped at
  the 2000-iteration limit, so the real speed-up is bigger). Same result because the problem has only one
  minimum (convex).
* The picture on the right: error vs iteration; the FISTA line drops much faster.
* Without binning, the best λ removes all detail at peaks up to 1: at that light the detail is only noise.

**Say (70 s).** Full explanation in `presenter_notes.md`, section 1.

---

## Slide 18 — All methods: PSNR vs peak

**How to read:** x-axis = light level, y-axis = PSNR. Each line is one method.

**Plain words:** at the dark end (left) P4IP-type methods and smoothing lead; at the bright end (right)
Anscombe + BM3D leads. The lines cross between peak 1 and 2: that is where the Anscombe approximation
becomes good enough.

**Say (40 s).**

---

## Slide 19 — Major findings

Six sentences, each backed by an earlier slide:
1. Replication works (slides 9–10). 2. Exact inverse matters (slide 4). 3. Multiple priors help at
0.1 (slide 16). 4. Per-level wavelets help, wavelet dictionaries don't (14–15). 5. FISTA is faster,
same result (17). 6. Best method depends on light level; real data confirms it (12, 18).

**Say (60 s).**

---

## Slide 20 — Limitations and future directions

**Limitations:** one noise draw per image; 8 test images; simplified SPDA; Python BM3D; some parameters
at the edge of their search range; FMD slow methods on a subset, not re-tuned.

**Future:** choose the prior weight from the light level automatically; neural-network denoisers inside
P4IP; a version of P4IP with the exact Poisson + Gaussian noise for microscopes.

**Say (40 s):** "We state limitations openly; each future step follows from a finding."

---

## Slide 21 — Thank you

Questions, code link, AI-use statement, references. Then take questions.

## Slides 22–28 — Backup (only if asked)

* 22–23: full PSNR tables, without and with binning (bold = best per light level).
* 24–25: paired comparisons vs Anscombe + BM3D. Each cell: mean difference, then (images better / 8).
  * = significant (p < 0.05).
* 26: what binning gains or loses for each method.
* 27: SSIM (structure similarity, 0 to 1, higher better) and runtime.
* 28: example images, cameraman at peak 1.

---

## Words you may be asked to define (one line each)

* **Photon count:** number of light particles a pixel caught.
* **Peak:** average photon count of the brightest pixel; our light level.
* **PSNR:** 10·log₁₀(peak² / mean squared error), higher = closer to the truth.
* **SSIM:** similarity of structure (edges, texture), 0 to 1.
* **Prior:** what we assume natural images look like (smooth, sparse, repeating patches).
* **Denoiser:** a function that takes a noisy image and returns a cleaner one.
* **ADMM:** a way to solve a hard problem by alternating two easy ones.
* **ρ (rho):** how strongly ADMM forces the two copies to agree.
* **Anscombe transform:** square-root formula that makes Poisson noise look Gaussian.
* **Wavelet:** splits an image into coarse shapes and fine details at several scales.
* **Dictionary / atoms:** a set of typical patch shapes; patches are rebuilt from a few of them.
* **Sparse:** most coefficients are zero.
* **Soft thresholding:** set small values to zero, shrink the others.
* **Convex:** a bowl-shaped problem with a single lowest point.
* **Wilcoxon signed-rank test:** checks if one method beats another consistently across images.
* **Binning:** add up 3×3 pixel blocks; more photons per pixel, less resolution.
* **Tuning set:** images used only to choose parameters; never the test images.
