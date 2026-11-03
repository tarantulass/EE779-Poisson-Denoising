#!/bin/sh
# Run after run_remaining.sh. Re-tunes the P4IP-type methods where their best parameter was at the
# edge of the earlier, narrower grids, and re-runs those test images.
set -e
W=${1:-12}
export PYTHONWARNINGS=ignore
H="p4ip_bm3d A3_bm3d_wavelet A2_wavelet_dict A2_pixel_dict"
# 3x3 binned: all peaks (an older P4IP grid was used here)
python3 -m experiments.tune     --methods $H --bin 3 --force --workers $W
python3 -m experiments.evaluate --methods $H --bin 3 --force --workers $W
# no binning: the low peaks, where the largest value tried was chosen
python3 -m experiments.tune     --methods p4ip_bm3d A3_bm3d_wavelet --peaks 0.1 0.2 --force --workers $W
python3 -m experiments.evaluate --methods p4ip_bm3d A3_bm3d_wavelet --peaks 0.1 0.2 --force --workers $W
python3 -m experiments.tune     --methods A2_wavelet_dict --peaks 0.1 0.2 0.5 --force --workers $W
python3 -m experiments.evaluate --methods A2_wavelet_dict --peaks 0.1 0.2 0.5 --force --workers $W
python3 -m experiments.evaluate --summary
