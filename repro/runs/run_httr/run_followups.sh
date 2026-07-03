#!/bin/bash
# Wait for main sweep (4 temps) to finish, then run beta_eff + no-BP sensitivity.
source /root/miniforge3/etc/profile.d/conda.sh
conda activate omc
export OPENMC_CROSS_SECTIONS=/root/xs/endfb-viii.0-hdf5/cross_sections.xml
cd /root/bench/httr

echo "[followups] waiting for main sweep to complete..."
until [ "$(grep -c ',' runs/main/keff.csv 2>/dev/null)" -ge 5 ]; do sleep 30; done
echo "[followups] main sweep done. launching beta_eff pair @900K (BP on)"
# beta_eff by prompt method: matched full-k and prompt-only runs at 900 K
python run_sweep.py kin 12000 30 140 1 900 0
python run_sweep.py kin 12000 30 140 1 900 1

echo "[followups] no-BP bracket sweep (294/900/1200 K)"
python run_sweep.py nobp 10000 30 120 0 294,900,1200

echo "FOLLOWUPS_DONE"
