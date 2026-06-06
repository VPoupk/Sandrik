#!/bin/bash
# Orchestrates the AKE disposal/proceeds data pipeline.
# Collects data only. Does NOT edit HTML and does NOT run git.
# Resumable: scan_disposals.py picks up from its checkpoint.
cd "$(dirname "$0")" || exit 1
LOG=pipeline.log
say(){ echo "$(date -u +'%Y-%m-%d %H:%M:%S')Z  [run] $*" | tee -a "$LOG"; }

say "================ PIPELINE RUN START ================"
python3 extract_wallets.py   || say "extract_wallets FAILED rc=$?"
python3 fetch_prices.py      || say "fetch_prices FAILED rc=$?"
python3 scan_disposals.py    || say "scan_disposals FAILED rc=$?"
python3 compute_proceeds.py  || say "compute_proceeds FAILED rc=$?"
say "================ PIPELINE RUN DONE  ================"
