#!/bin/sh
# Finishes the slow runs (P4IP-BM3D, A2, A3). Resumable: rerun after any interruption.
# Usage (inside tmux on a many-core machine):  sh run_remaining.sh 16
set -e
W=${1:-8}
H="p4ip_bm3d A3_bm3d_wavelet A2_wavelet_dict A2_pixel_dict"
python3 -m experiments.tune     --methods $H --bin 3 --workers $W
python3 -m experiments.evaluate --methods $H --bin 3 --workers $W
python3 -m experiments.tune     --methods $H --workers $W
python3 -m experiments.evaluate --methods $H --workers $W
python3 -m experiments.direction_b.ista_fista
python3 -m experiments.evaluate --summary
