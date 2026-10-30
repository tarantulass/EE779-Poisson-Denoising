# Running the experiments on a GCP VM

You do not need to share any credentials. Everything runs on your VM from a clone of
this repo; results are plain CSV/JSON files you copy back or commit.

## 1. Pick the machine

The workload is BM3D on the CPU (no GPU benefit). Jobs are independent, so cores scale
almost linearly. One job uses one core.

* Recommended: `c2d-standard-16` or `n2-standard-16` (16 vCPU, 64 GB). Memory use is
  small (< 500 MB per worker).
* A Spot VM costs roughly a third. The runner is resumable, so a preemption only loses
  the jobs that were in flight. Re-run the same command.
* 50 GB standard persistent disk, Ubuntu 22.04 or 24.04 LTS.

## 2. One-time setup on the VM

```bash
sudo apt-get update && sudo apt-get install -y git python3-venv tmux
git clone https://github.com/tarantulass/EE779-Poisson-Denoising.git
cd EE779-Poisson-Denoising
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q tests            # must print "13 passed" (more once you add plug-ins)
python -m experiments.run experiments/configs/smoke.json --workers 4   # ~1 min end-to-end check
```

For a private repo, use a GitHub fine-grained token with read-only access to this one
repo, or an SSH deploy key. Keep it on the VM only.

## 3. Run inside tmux so a closed SSH session does not stop it

```bash
tmux new -s exp
source .venv/bin/activate
W=$(nproc)

# Stage B0: tuning on the tuning split, then the test split
python -m experiments.tune experiments/configs/tune_p4ip_bm3d.json --workers $W
python -m experiments.tune experiments/configs/tune_p4ip_bm3d_bin3.json --workers $W
#   -> read the printout; if a winner is "at grid edge", widen the grid in the config
#      and re-run the same command (finished jobs are skipped)
python -m experiments.run experiments/configs/baselines.json --workers $W
python -m experiments.run experiments/configs/baselines_bin3.json --workers $W
python -m experiments.analyze results/baselines --ref p4ip_bm3d
python -m experiments.analyze results/baselines_bin3 --ref p4ip_bm3d_bin3
```

Detach with `Ctrl-b d`, reattach with `tmux attach -t exp`. Progress lines show an ETA.

## 4. Get the results back

Either commit them from the VM (`git add results && git commit && git push`), or copy
from your laptop:

```bash
gcloud compute scp --recurse VM_NAME:~/EE779-Poisson-Denoising/results ./results --zone ZONE
```

`results/*/estimates/` holds the denoised images (compressed). Leave it out of git if it
gets large; `.gitignore` already excludes it.

## 5. Stop paying when idle

`gcloud compute instances stop VM_NAME --zone ZONE` when a stage finishes. A stopped VM
only bills for its disk.
