# ATH (AthenaDAO) On-Chain Forensic Analysis — 2026 YTD

Forensic study of selling activity in **ATH** (AthenaDAO / AthenaBIO governance token,
`0xa4ffdf3208f46898ce063e25c1c43056fa754739`, Ethereum) for the period
**Jan 1 2026 → Jun 18 2026** (blocks 24,136,053 → 25,345,825).

Commissioned to investigate suspected front-running of wallet
`0xf0940b14e8a4bE798cD713A6807e95f47B769d9C`, identify all major sellers, their
holdings, token provenance (DAO/team connection), and selling patterns.

## Data sources (100% on-chain + public price oracle)
- **Raw chain data** via public Ethereum JSON-RPC (`publicnode`, `drpc`, `1rpc`, `mevblocker`).
  Every ATH `Transfer` since genesis (deploy block 17,977,841), every Uniswap **V3**
  (ATH/WETH) and **V4** (ATH/BIO) swap, and **CoW Protocol** `Trade` events.
- **Prices**: CoinGecko daily USD marks for ETH, BIO, ATH. USD figures are *realized
  proceeds at sale time* (counter-asset received × its USD rate that day).
- No CEX lists ATH on Ethereum, so all on-chain selling flows through the two Uniswap
  pools (+ CoW, which routes to those pools). Sell totals reconcile to gross venue
  inflow (2,944,143 vs 2,943,757 ATH).

## Key findings
1. **No transaction-level front-running / sandwiching** of the subject wallet. Same-block
   ordering shows zero ATH trades executed *before* the subject in any of its 9 sell
   blocks. The bots that appear around the subject are **arbitrage/MM bots reacting to
   price impact** (e.g. top bot `0x930b88a5`: 0 trades in the hour before the subject's
   sells, but 5× within the hour after).
2. **Thin liquidity is the real cause** of poor fills: ~$59K total liquidity; every large
   sell moves price and creates a V3↔V4 dislocation that ~26 bots instantly arbitrage.
   ATH fell -79% over the period ($0.171 → $0.036).
3. **Parallel insider distribution** is the closest thing to "someone selling alongside
   you": `0xea80c984` (99% DAO-origin) sold 59,970 ATH via **38 stealth CoW fills**
   Jan 4–Mar 31; DAO genesis recipients `0xd8a57177` (57.2K, Mar 26) and `0x91e8b869`
   (32.5K, Mar 27) dumped on consecutive days; `0xf35c6c74` still holds 64K.
4. **41 wallets** sold > $1K. Excluding the subject: 26 arb/MM bots (1.17M ATH / $80K of
   net-zero churn), 4 DAO-allocation insiders (165K / $12.3K), 10 market distributors
   (303K / $26.8K). The subject is the single largest *genuine* (non-bot) seller ($25K).
5. **Genesis**: all 30M minted to `0x4d754910…`, distributed to vesting/treasury contracts
   (`0x5b99e2da` = 12.5M Core/Early-Contributor pool; `0x0b7ffc1f`+`0x71028407` funded the
   subject). Maps to official allocation (Community 10M / Contributors 12M / Service 8M).

## Deliverables
- **`ATH_forensic_report.html`** — styled, self-contained report (sortable tables,
  color-coded categories, Etherscan links). Open in any browser.
- **`ATH_forensic_report.md`** — the full written report: findings, methodology,
  front-running verdict, provenance, plus **Table A** (all wallets that sold >$1k YTD)
  and **Table B** (all wallets that sold >$1k in the trailing 21 days).
- **`ath_sellers_2026.csv`** — machine-readable YTD table: all 41 wallets, ATH sold,
  USD at sale time, current holdings, net, 2026 activity breakdown, provenance, DAO-origin %.
- **`ath_sellers_2026.md`** — YTD table, formatted.
- Result/evidence JSON: `final_table.json`, `dao_origin.json`, `bal_authoritative.json`,
  `cow_sells.json`, `cow_owners.json`, `dao_roots.json`, `frontrun_stats.json`,
  `prices_daily.json`, `blocks.json`, `deploy.json`.

## Reproduce
Pipeline (each step writes JSON consumed by the next; large raw RPC dumps are gitignored
and regenerated on run):
```
python3 build.py        # decode transfers + V3/V4 swaps, attribute sells, block ts
python3 report.py       # holdings, activity, first >$1k table
python3 cow.py          # de-anonymize CoW sells -> real owners + realized USD
python3 final.py        # unified table (direct + CoW) -> final_table.json
python3 provenance.py   # all-time inbound source classification
python3 frontrun.py     # same-block ordering around subject's sells
python3 frontrun2.py    # minute/hour/day co-trading windows
python3 window21.py     # trailing-21-day >$1k seller aggregation -> window21_rows.json
python3 gen_doc.py      # assemble ATH_forensic_report.md (findings + Table A + Table B)
# (rpc.py = JSON-RPC helper; keccak.py = pure-python keccak-256 for event topics)
```

## Caveats
- EOA attribution uses the on-chain token sender with a `tx.origin` fallback for
  contract-routed swaps; CoW orders attributed via `Trade`-event owner.
- USD uses daily price marks (no intraday granularity).
- Behavioral clustering (one entity = several wallets) is *not* asserted beyond direct
  token-flow links; proving common ownership of the bots would require paid attribution
  (Arkham/Nansen).
