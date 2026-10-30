# Results

Sources: results/baselines

## Average PSNR (dB) over images (reps averaged within image)

| label                    |   0.1 |   0.2 |   0.5 |   1.0 |   2.0 |   4.0 |
|:-------------------------|------:|------:|------:|------:|------:|------:|
| anscombe_bm3d            | 13.89 | 16.00 | 17.97 | 19.49 | 21.41 | 23.30 |
| anscombe_bm3d_algebraic  | 12.11 | 13.07 | 14.12 | 15.53 | 18.01 | 21.10 |
| anscombe_bm3d_asymptotic | -7.34 | -0.80 |  8.49 | 15.52 | 20.43 | 23.12 |
| anscombe_bm3d_closedform | 13.87 | 15.98 | 17.98 | 19.50 | 21.40 | 23.29 |
| ml                       | -7.08 | -4.09 | -0.11 |  2.91 |  5.92 |  8.94 |

## Average SSIM

| label                    |   0.1 |   0.2 |   0.5 |   1.0 |   2.0 |   4.0 |
|:-------------------------|------:|------:|------:|------:|------:|------:|
| anscombe_bm3d            | 0.239 | 0.319 | 0.420 | 0.515 | 0.602 | 0.679 |
| anscombe_bm3d_algebraic  | 0.250 | 0.325 | 0.412 | 0.497 | 0.585 | 0.670 |
| anscombe_bm3d_asymptotic | 0.094 | 0.189 | 0.349 | 0.475 | 0.582 | 0.671 |
| anscombe_bm3d_closedform | 0.235 | 0.318 | 0.420 | 0.516 | 0.602 | 0.679 |
| ml                       | 0.005 | 0.010 | 0.023 | 0.044 | 0.077 | 0.127 |

## Mean runtime per image (s)

| label                    |   0.1 |   0.2 |   0.5 |   1.0 |   2.0 |   4.0 |
|:-------------------------|------:|------:|------:|------:|------:|------:|
| anscombe_bm3d            |   7.1 |   6.9 |   6.9 |   7.0 |   7.1 |   6.9 |
| anscombe_bm3d_algebraic  |   6.8 |   6.9 |   6.9 |   6.9 |   7.1 |   6.9 |
| anscombe_bm3d_asymptotic |   6.9 |   6.9 |   7.0 |   7.0 |   7.2 |   7.1 |
| anscombe_bm3d_closedform |   6.9 |   7.1 |   7.1 |   7.1 |   7.0 |   7.1 |
| ml                       |   0.0 |   0.0 |   0.0 |   0.0 |   0.0 |   0.0 |

## Paired PSNR difference vs `anscombe_bm3d` (positive = better than reference)

| label                    | ref           |   peak | metric   |   n_images |    delta |    ci_lo |    ci_hi |   wins |   p_wilcoxon |   p_holm |
|:-------------------------|:--------------|-------:|:---------|-----------:|---------:|---------:|---------:|-------:|-------------:|---------:|
| anscombe_bm3d_algebraic  | anscombe_bm3d | 0.1000 | psnr     |          8 |  -1.7837 |  -2.1130 |  -1.4544 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_algebraic  | anscombe_bm3d | 0.2000 | psnr     |          8 |  -2.9267 |  -3.3761 |  -2.4773 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_algebraic  | anscombe_bm3d | 0.5000 | psnr     |          8 |  -3.8462 |  -4.4998 |  -3.1927 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_algebraic  | anscombe_bm3d | 1.0000 | psnr     |          8 |  -3.9640 |  -4.5972 |  -3.3308 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_algebraic  | anscombe_bm3d | 2.0000 | psnr     |          8 |  -3.3954 |  -3.9244 |  -2.8664 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_algebraic  | anscombe_bm3d | 4.0000 | psnr     |          8 |  -2.1949 |  -2.5793 |  -1.8105 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_asymptotic | anscombe_bm3d | 0.1000 | psnr     |          8 | -21.2362 | -21.9364 | -20.5360 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_asymptotic | anscombe_bm3d | 0.2000 | psnr     |          8 | -16.7956 | -17.5360 | -16.0553 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_asymptotic | anscombe_bm3d | 0.5000 | psnr     |          8 |  -9.4780 | -10.4722 |  -8.4837 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_asymptotic | anscombe_bm3d | 1.0000 | psnr     |          8 |  -3.9742 |  -4.8907 |  -3.0576 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_asymptotic | anscombe_bm3d | 2.0000 | psnr     |          8 |  -0.9793 |  -1.4080 |  -0.5507 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_asymptotic | anscombe_bm3d | 4.0000 | psnr     |          8 |  -0.1776 |  -0.3210 |  -0.0342 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_closedform | anscombe_bm3d | 0.1000 | psnr     |          8 |  -0.0239 |  -0.0281 |  -0.0197 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_closedform | anscombe_bm3d | 0.2000 | psnr     |          8 |  -0.0206 |  -0.0251 |  -0.0161 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_closedform | anscombe_bm3d | 0.5000 | psnr     |          8 |   0.0135 |   0.0079 |   0.0191 |      8 |       0.0078 |   0.0469 |
| anscombe_bm3d_closedform | anscombe_bm3d | 1.0000 | psnr     |          8 |   0.0088 |   0.0044 |   0.0131 |      7 |       0.0156 |   0.0469 |
| anscombe_bm3d_closedform | anscombe_bm3d | 2.0000 | psnr     |          8 |  -0.0099 |  -0.0144 |  -0.0053 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_closedform | anscombe_bm3d | 4.0000 | psnr     |          8 |  -0.0098 |  -0.0123 |  -0.0072 |      0 |       0.0078 |   0.0469 |
| ml                       | anscombe_bm3d | 0.1000 | psnr     |          8 | -20.9765 | -21.3363 | -20.6167 |      0 |       0.0078 |   0.0469 |
| ml                       | anscombe_bm3d | 0.2000 | psnr     |          8 | -20.0835 | -20.7465 | -19.4206 |      0 |       0.0078 |   0.0469 |
| ml                       | anscombe_bm3d | 0.5000 | psnr     |          8 | -18.0776 | -18.9628 | -17.1923 |      0 |       0.0078 |   0.0469 |
| ml                       | anscombe_bm3d | 1.0000 | psnr     |          8 | -16.5799 | -17.4656 | -15.6942 |      0 |       0.0078 |   0.0469 |
| ml                       | anscombe_bm3d | 2.0000 | psnr     |          8 | -15.4920 | -16.4417 | -14.5423 |      0 |       0.0078 |   0.0469 |
| ml                       | anscombe_bm3d | 4.0000 | psnr     |          8 | -14.3629 | -15.4052 | -13.3206 |      0 |       0.0078 |   0.0469 |

## Paired SSIM difference vs `anscombe_bm3d` (positive = better than reference)

| label                    | ref           |   peak | metric   |   n_images |   delta |   ci_lo |   ci_hi |   wins |   p_wilcoxon |   p_holm |
|:-------------------------|:--------------|-------:|:---------|-----------:|--------:|--------:|--------:|-------:|-------------:|---------:|
| anscombe_bm3d_algebraic  | anscombe_bm3d | 0.1000 | ssim     |          8 |  0.0113 |  0.0021 |  0.0204 |      7 |       0.0234 |   0.0703 |
| anscombe_bm3d_algebraic  | anscombe_bm3d | 0.2000 | ssim     |          8 |  0.0061 | -0.0068 |  0.0190 |      5 |       0.3828 |   0.3828 |
| anscombe_bm3d_algebraic  | anscombe_bm3d | 0.5000 | ssim     |          8 | -0.0081 | -0.0203 |  0.0042 |      3 |       0.1484 |   0.2969 |
| anscombe_bm3d_algebraic  | anscombe_bm3d | 1.0000 | ssim     |          8 | -0.0180 | -0.0259 | -0.0101 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_algebraic  | anscombe_bm3d | 2.0000 | ssim     |          8 | -0.0169 | -0.0221 | -0.0116 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_algebraic  | anscombe_bm3d | 4.0000 | ssim     |          8 | -0.0093 | -0.0127 | -0.0060 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_asymptotic | anscombe_bm3d | 0.1000 | ssim     |          8 | -0.1450 | -0.1775 | -0.1125 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_asymptotic | anscombe_bm3d | 0.2000 | ssim     |          8 | -0.1301 | -0.1699 | -0.0904 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_asymptotic | anscombe_bm3d | 0.5000 | ssim     |          8 | -0.0715 | -0.1080 | -0.0349 |      1 |       0.0156 |   0.0625 |
| anscombe_bm3d_asymptotic | anscombe_bm3d | 1.0000 | ssim     |          8 | -0.0404 | -0.0675 | -0.0133 |      2 |       0.0391 |   0.0625 |
| anscombe_bm3d_asymptotic | anscombe_bm3d | 2.0000 | ssim     |          8 | -0.0204 | -0.0380 | -0.0027 |      1 |       0.0234 |   0.0625 |
| anscombe_bm3d_asymptotic | anscombe_bm3d | 4.0000 | ssim     |          8 | -0.0074 | -0.0152 |  0.0005 |      1 |       0.0156 |   0.0625 |
| anscombe_bm3d_closedform | anscombe_bm3d | 0.1000 | ssim     |          8 | -0.0037 | -0.0088 |  0.0014 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_closedform | anscombe_bm3d | 0.2000 | ssim     |          8 | -0.0010 | -0.0019 | -0.0001 |      0 |       0.0078 |   0.0469 |
| anscombe_bm3d_closedform | anscombe_bm3d | 0.5000 | ssim     |          8 |  0.0001 | -0.0001 |  0.0003 |      4 |       0.8438 |   0.8438 |
| anscombe_bm3d_closedform | anscombe_bm3d | 1.0000 | ssim     |          8 |  0.0004 |  0.0000 |  0.0008 |      6 |       0.0547 |   0.1641 |
| anscombe_bm3d_closedform | anscombe_bm3d | 2.0000 | ssim     |          8 | -0.0001 | -0.0004 |  0.0001 |      4 |       0.3125 |   0.6250 |
| anscombe_bm3d_closedform | anscombe_bm3d | 4.0000 | ssim     |          8 | -0.0003 | -0.0004 | -0.0001 |      1 |       0.0234 |   0.0938 |
| ml                       | anscombe_bm3d | 0.1000 | ssim     |          8 | -0.2340 | -0.2636 | -0.2045 |      0 |       0.0078 |   0.0469 |
| ml                       | anscombe_bm3d | 0.2000 | ssim     |          8 | -0.3094 | -0.3420 | -0.2768 |      0 |       0.0078 |   0.0469 |
| ml                       | anscombe_bm3d | 0.5000 | ssim     |          8 | -0.3968 | -0.4293 | -0.3644 |      0 |       0.0078 |   0.0469 |
| ml                       | anscombe_bm3d | 1.0000 | ssim     |          8 | -0.4712 | -0.5007 | -0.4416 |      0 |       0.0078 |   0.0469 |
| ml                       | anscombe_bm3d | 2.0000 | ssim     |          8 | -0.5254 | -0.5618 | -0.4890 |      0 |       0.0078 |   0.0469 |
| ml                       | anscombe_bm3d | 4.0000 | ssim     |          8 | -0.5523 | -0.5873 | -0.5172 |      0 |       0.0078 |   0.0469 |

## Per-image PSNR

| label                    |   peak |   airplane |   boat |   cameraman |   house |   monarch |   parrot |   peppers |   starfish |
|:-------------------------|-------:|-----------:|-------:|------------:|--------:|----------:|---------:|----------:|-----------:|
| anscombe_bm3d            |   0.10 |      12.28 |  14.66 |       14.03 |   14.01 |     13.53 |    14.21 |     14.23 |      14.21 |
| anscombe_bm3d            |   0.20 |      14.66 |  16.59 |       16.31 |   16.75 |     15.17 |    15.81 |     16.35 |      16.33 |
| anscombe_bm3d            |   0.50 |      16.63 |  18.57 |       18.25 |   19.45 |     16.76 |    17.66 |     18.36 |      18.09 |
| anscombe_bm3d            |   1.00 |      18.30 |  19.99 |       19.76 |   21.09 |     18.29 |    19.80 |     19.54 |      19.15 |
| anscombe_bm3d            |   2.00 |      19.71 |  21.41 |       21.84 |   23.34 |     20.65 |    21.90 |     21.98 |      20.45 |
| anscombe_bm3d            |   4.00 |      21.55 |  23.15 |       23.88 |   25.35 |     22.70 |    23.61 |     24.19 |      21.97 |
| anscombe_bm3d_algebraic  |   0.10 |       9.73 |  12.92 |       12.58 |   11.89 |     12.21 |    12.64 |     12.55 |      12.36 |
| anscombe_bm3d_algebraic  |   0.20 |      10.85 |  13.79 |       13.51 |   13.12 |     12.95 |    13.33 |     13.57 |      13.45 |
| anscombe_bm3d_algebraic  |   0.50 |      11.94 |  14.87 |       14.53 |   14.23 |     13.96 |    14.51 |     14.78 |      14.18 |
| anscombe_bm3d_algebraic  |   1.00 |      13.69 |  16.19 |       15.86 |   15.59 |     15.24 |    16.24 |     15.97 |      15.43 |
| anscombe_bm3d_algebraic  |   2.00 |      16.62 |  18.28 |       18.30 |   18.52 |     17.65 |    18.75 |     18.37 |      17.63 |
| anscombe_bm3d_algebraic  |   4.00 |      19.90 |  21.02 |       21.63 |   22.21 |     20.61 |    21.51 |     21.73 |      20.22 |
| anscombe_bm3d_asymptotic |   0.10 |      -7.04 |  -7.41 |       -7.42 |   -7.26 |     -7.42 |    -7.45 |     -7.38 |      -7.37 |
| anscombe_bm3d_asymptotic |   0.20 |      -0.25 |  -0.92 |       -0.91 |   -0.65 |     -0.92 |    -0.98 |     -0.87 |      -0.88 |
| anscombe_bm3d_asymptotic |   0.50 |       9.77 |   8.21 |        8.22 |    9.04 |      8.07 |     7.97 |      8.25 |       8.42 |
| anscombe_bm3d_asymptotic |   1.00 |      16.69 |  15.21 |       15.10 |   17.00 |     14.90 |    14.73 |     15.24 |      15.27 |
| anscombe_bm3d_asymptotic |   2.00 |      19.57 |  20.34 |       20.33 |   22.65 |     19.96 |    20.12 |     20.84 |      19.64 |
| anscombe_bm3d_asymptotic |   4.00 |      21.54 |  23.01 |       23.42 |   25.30 |     22.64 |    23.19 |     23.97 |      21.89 |
| anscombe_bm3d_closedform |   0.10 |      12.25 |  14.63 |       14.00 |   13.99 |     13.52 |    14.18 |     14.21 |      14.18 |
| anscombe_bm3d_closedform |   0.20 |      14.64 |  16.57 |       16.29 |   16.72 |     15.16 |    15.80 |     16.33 |      16.31 |
| anscombe_bm3d_closedform |   0.50 |      16.65 |  18.58 |       18.26 |   19.47 |     16.77 |    17.67 |     18.36 |      18.11 |
| anscombe_bm3d_closedform |   1.00 |      18.29 |  20.00 |       19.78 |   21.10 |     18.30 |    19.82 |     19.55 |      19.15 |
| anscombe_bm3d_closedform |   2.00 |      19.71 |  21.40 |       21.82 |   23.33 |     20.63 |    21.90 |     21.96 |      20.44 |
| anscombe_bm3d_closedform |   4.00 |      21.54 |  23.14 |       23.87 |   25.34 |     22.69 |    23.60 |     24.18 |      21.97 |
| ml                       |   0.10 |      -8.86 |  -6.64 |       -6.71 |   -7.58 |     -6.69 |    -6.42 |     -6.82 |      -6.93 |
| ml                       |   0.20 |      -5.92 |  -3.63 |       -3.69 |   -4.62 |     -3.68 |    -3.33 |     -3.81 |      -4.01 |
| ml                       |   0.50 |      -1.91 |   0.33 |        0.30 |   -0.61 |      0.30 |     0.61 |      0.10 |       0.03 |
| ml                       |   1.00 |       1.10 |   3.35 |        3.27 |    2.41 |      3.33 |     3.59 |      3.17 |       3.06 |
| ml                       |   2.00 |       4.10 |   6.39 |        6.30 |    5.38 |      6.35 |     6.63 |      6.16 |       6.03 |
| ml                       |   4.00 |       7.13 |   9.39 |        9.34 |    8.40 |      9.34 |     9.65 |      9.17 |       9.08 |
