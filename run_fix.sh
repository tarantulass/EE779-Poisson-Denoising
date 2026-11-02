#!/bin/sh
# Run after run_remaining.sh. Re-tunes the binned P4IP-type methods with the current grids
# (an older, too-narrow P4IP grid was used for them) and re-runs their test images.
set -e
W=${1:-12}
export PYTHONWARNINGS=ignore
H="p4ip_bm3d A3_bm3d_wavelet A2_wavelet_dict A2_pixel_dict"
python3 -m experiments.tune     --methods $H --bin 3 --force --workers $W
python3 -m experiments.evaluate --methods $H --bin 3 --force --workers $W
python3 -m experiments.evaluate --summary
