# A1 notes (test split, 8 images x 3 noise reps; tuned on data/tune, 6x6 grids, round 3)

* **A1 vs Anscombe+BM3D**: A1 wins at peak 0.1 (+1.13 dB, 8/8 images, Holm p 0.047) and loses
  at peak >= 0.5 (-1.1 to -4.1 dB, 0/8). Peak 0.2 is a tie (-0.14 dB, 3/8).
  Cycle spinning widens the low-peak win: A1.g_spin16 +2.05 dB at 0.1 (8/8), +0.48 dB at 0.2
  (7/8, Holm p 0.078, not significant with n = 8).
* **Sub-ablations vs A1** (paired, Holm, claim rule >= 7/8 wins):
  - cycle spinning (g): 4 shifts beats A1 at every peak, by +0.06 to +0.58 dB (8/8 wins, except peak 0.2 at 7/8).
    16 shifts beats A1 at peaks 0.1 to 2 (8/8) but loses at peak 4 (-0.29 dB, 0/8). It also costs 10x the runtime.
  - thresholding the coarse band (b): -1.7 to -4.1 dB at every peak, so the LL band must pass through.
  - levels (d): J2 and J3 are much worse at low peaks (-6.1 / -3.1 dB at 0.1). J3 is better at peaks 2 and 4
    (+0.5 / +0.65 dB, 8/8). J5 is +0.44 dB at 0.1 (6/8, not significant) and worse at 0.5 and 4.
  - wavelet (c): sym8 = db4 (|d| <= 0.13 dB, never significant); Haar is worse by 0.2 to 0.56 dB.
  - hard thresholding (e): +0.16 to +0.21 dB at peaks 1 to 4 (8/8 at 2 and 4); a tie at low peaks.
  - exact prox (A1.a, eta = sigma^2): a tie at peaks 0.2 to 2; -1.55 dB at 0.1 and -0.9 dB at 4.
    The constant-rho schedule doesn't help (A1.a_constrho: -0.76 / -0.88 dB at 0.1 / 4, otherwise within 0.11 dB).
* **A1.a objective** (`results/convergence/a1a.png`): the explicit objective
  sum(x - y log x) + beta ||W_d x||_1 falls by 3 to 5 orders of magnitude relative to its final value.
  It is not monotone at low peaks (up to 8 of 69 steps increase at peak 0.1): ADMM is not a descent method.
* **Caveat, tuning edges**: 35 of 72 tuned (variant, peak) pairs still sit at a grid edge, almost all in rho0.
  rho0 already spans 0.125 to 128 (a factor of 1000), and A1 at peak 0.1 wants rho0 = 128.
  The rho0 surface is flat at these ends. Extending it further is a VM job: add 512 / 0.03125 to
  `experiments/configs/tune_A1.json` and rerun `experiments.tune` and `experiments.run`.
  The numbers above are lower bounds on what a wider grid could give.
* `p4ip_bm3d` has no test results yet (VM job, see GCP.md), so A1 is not yet compared to P4IP-BM3D.
