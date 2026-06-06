# AKE disposal / proceeds pipeline

Collects the data needed to price each wallet's AKE disposals at the **price on
the day the tokens were sold (sent out to a CEX/DEX)** — not the Oct-2025 flat
average, and not the day they were received.

## Why this exists
A previous background pipeline auto-applied results to the HTML docs and
auto-committed in a loop. It repeatedly overwrote manual edits and wiped a
comprehensive commit. **This pipeline only collects and saves data. It never
edits the HTML and never runs git.** Applying results to the docs is a separate,
deliberate step.

## Steps (`run_pipeline.sh`)
1. `extract_wallets.py` — in-scope wallets from the 3 HTML docs → `data/wallets.json`
   (+ `data/rows_merged.json`, the merged receive-side scan data).
2. `fetch_prices.py` — keep `data/ake_daily_prices.json` current (CoinGecko if
   reachable; otherwise keep existing real data).
3. `scan_disposals.py` — one combined `topics` OR-filter scan of OUTBOUND AKE
   transfers for all wallets, 50k-block chunks, **resumable** checkpoint at
   `data/disposals_raw.json`.
4. `compute_proceeds.py` — date each outbound transfer by block timestamp, join
   with daily prices → `data/proceeds.json`.

## Honest status
- `data/status.json` — machine-readable progress (stage, % scanned, counts, anomalies).
- `pipeline.log` — human-readable running log.

## Outputs (`data/`)
- `proceeds.json` — per wallet: `recv`, `balance`, `net_sold`, `gross_outbound`,
  `proceeds_by_outbound`, `proceeds_net_sold`, `wavg_price`, `bydate{...}`,
  `dest_top`, `pools`, `flag`.
- Anomalies (round-trips, no outbound found, price clamping) are **flagged, not hidden**.

## Run / resume
    bash pipeline/run_pipeline.sh        # foreground
Re-running resumes the scan from its checkpoint. Safe to interrupt.
