# ATH (AthenaDAO) - Wallet-Watching & Anticipatory-Selling Analysis

**Subject wallet:** `0xf0940b14e8a4bE798cD713A6807e95f47B769d9C`
**Token:** ATH - AthenaDAO / AthenaBIO governance token - `0xa4ffdf3208f46898ce063e25c1c43056fa754739` (Ethereum, 18 dec)
**Period:** 2026-01-01 -> 2026-06-18 (blocks 24,136,053 -> 25,345,825)
**Prepared:** 2026-06-18 - 100% on-chain data + CoinGecko daily price marks

---

## 1. Methodology (what "actual data, fully reviewed" means here)
Every figure below is reconstructed from raw Ethereum logs - no third-party dashboards.
- Pulled **every ATH `Transfer`** since genesis (deploy block 17,977,841; 16,907 transfers all-time, 4,370 in 2026).
- Pulled **every Uniswap V3** (ATH/WETH) swap (2,315) and **V4** (ATH/BIO) swap (2,128); V4 amounts decoded as signed int128 and **validated against transaction receipts**.
- **De-anonymized CoW Protocol** settlements (44 txs) to the true order owner via `Trade` events - this exposed sellers invisible to pool-only analysis.
- ATH has **only two Ethereum venues and no CEX listing**, so all on-chain selling is captured. Detected sells (**2,944,143 ATH**) reconcile to gross venue inflow (**2,943,757 ATH**) - essentially exact.
- **USD = realized proceeds at the moment of sale** (WETH/BIO/CoW-buy-token received x that asset's USD rate on the sale date).

## 2. Re-framed question: is anyone *watching your wallet* and selling in anticipation?
This is **not** about same-block MEV (for the record there is none: across your 9 sell txs, zero other ATH trades ran before you in-block, no sandwiches). The question is whether holders see your loaded wallet and dump ahead of expected pressure. Verdict: **partial, confounded evidence.**

**When your wallet became "watchable":** your tokens sat in a vesting contract until **2026-02-20**, when a **333,333 ATH** claim hit your wallet (you sold 16 min later); a second **200,000 ATH** claim hit **2026-05-27**. Your *original* 2023 receipt predates the DEX market (pool created Dec 2023), so the "7-14 days after first receipt" check is empty by construction - nobody could sell ahead of you then.

**Aggregate selling roughly doubled once you were visible.** Excluding you and the arb/MM bots, non-bot selling ran **4,702 ATH/day before Feb 20** vs **9,155 ATH/day after** (~1.9x). That is consistent with holders de-risking around a visible whale - **but confounded** by (a) your own sells being the single largest genuine supply this year and (b) the price falling -79% ($0.171 -> $0.036). Both independently trigger others to sell, so this is correlation, not proof of monitoring.

## 3. Who actually sold in reaction to you
For each non-bot >$1k seller: share of volume sold shortly **after** your sells/unlocks. A random seller scores ~**33%** on "<=7d after" (that share of the post-Feb-20 timeline sits within 7 days of one of your sells), so only values well above 33% are reactive.

| Wallet | Category | ATH sold | 1st sell | Started after you visible? | % ≤7d after your sell | % ≤14d after your unlock | Assessment |
|---|---|--:|--:|:--:|--:|--:|---|
| `0xd054ba91…` | market | 46,914 | 2026-05-29 | ✦ AFTER | 100% | 100% | **anticipatory exit** |
| `0x3980daa7…` | market | 32,762 | 2026-01-31 | before | 97% | 92% | elevated post-sell selling |
| `0x664eeb03…` | market | 11,358 | 2026-01-03 | before | 30% | 26% | independent (active before you were visible) |
| `0xea80c984…` | DAO-allocation | 59,970 | 2026-01-04 | before | 16% | 16% | independent (active before you were visible) |
| `0xd4a3a947…` | market | 106,036 | 2026-05-06 | ✦ AFTER | 0% | 0% | independent / own schedule |
| `0xd8a57177…` | DAO-allocation | 57,220 | 2026-03-26 | ✦ AFTER | 0% | 0% | independent / own schedule |
| `0x91e8b869…` | DAO-allocation | 32,535 | 2026-03-27 | ✦ AFTER | 0% | 0% | independent / own schedule |
| `0x43309757…` | market | 25,614 | 2026-01-05 | before | 0% | 0% | independent (active before you were visible) |
| `0x97162365…` | market | 22,540 | 2026-01-20 | before | 0% | 0% | independent (active before you were visible) |
| `0xa31c8c9a…` | market | 20,514 | 2026-05-04 | ✦ AFTER | 0% | 0% | independent / own schedule |
| `0x663bd8fd…` | market | 16,803 | 2026-05-09 | ✦ AFTER | 0% | 0% | sold just before your sells |
| `0xf35c6c74…` | DAO-allocation | 15,761 | 2026-02-02 | before | 0% | 31% | independent (active before you were visible) |
| `0x65a8f07b…` | market | 14,968 | 2026-01-11 | before | 0% | 0% | independent (active before you were visible) |
| `0xaf061c2d…` | market | 5,800 | 2026-01-04 | before | 0% | 0% | independent (active before you were visible) |

**The one clean case - `0xd054ba913bf972f2563dff4b26dc383587ae7808`:** bought **46,914 ATH on Mar 9** (via CoW), held it 11 weeks, then sold the **entire** bag on **May 29 - two days after your 200k unlock** and four days after your May 25 sell. 100% of its volume sits in your post-sell/post-unlock window. Market buyer (not DAO), single event - suggestive, not conclusive, but the textbook "saw the whale reload, rushed the exit" pattern.

The other large sellers were **independent**: the stealth DAO distributor `0xea80c984` sold daily **before** you were visible (started Jan 4); `0xd8a57177`/`0x91e8b869` dumped Mar 26-27 in a window when you were **not** selling; `0xd4a3a947` dumped into the May 6 price bounce. None of these shadow your trades.

## 4. Provenance & DAO/team connection
All 30M circulating ATH was minted to genesis **`0x4d754910...`**, then distributed to vesting/treasury contracts - consistent with the official allocation (Community 10M / **Core & Early Contributors 12M, 24-mo vesting** / Service Providers 8M incl. Molecule-bio.xyz 6.9M; 70M unminted treasury). The "competing sellers" you sense are mostly **other DAO-allocation holders distributing on their own schedules**:
- **`0xea80c984` - 99% DAO-origin.** 59,970 ATH via 38 CoW fills, near-daily Jan 4 -> Mar 31 (started *before* you were visible). Trail: genesis -> `0x5b99e2da` (12.5M Core/Early-Contributor pool) -> hub `0x0e449816` -> this wallet.
- **`0xd8a57177` (57,220, Mar 26)** and **`0x91e8b869` (32,535, Mar 27)** - 100% DAO genesis recipients, consecutive-day dumps in a window when you were not selling.
- **`0xf35c6c74`** - DAO recipient; sold 15,761 but **still holds 64,011 ATH** (largest known overhang outside the treasury).
- **You** received **848,886 ATH** from DAO distribution contracts `0x71028407` + `0x0b7ffc1f`, sold ~483K (393K direct + 90K via CoW), hold 50,000 - the **single largest *genuine* (non-bot) seller of ATH in 2026**.
- **Arb/MM bots are NOT DAO-connected** (buy from pools, resell, hold 0). **Market buyers** `0xd4a3a947` and the anticipatory-exit `0xd054ba91` bought/bridged in - no DAO link.

---

## 5. TABLE A - All wallets that sold > $1,000 of ATH (YTD: Jan 1 -> Jun 18, 2026)
41 wallets. Among the 40 besides you: **26 arb/MM bots** (1.17M ATH / ~$80K of net-zero churn, hold nothing), **4 DAO-allocation insiders** (165K ATH / $12.3K), **10 market distributors** (303K ATH / $26.8K).

| # | Wallet | Category | ATH sold | USD sold(1) | Still holds | Net ATH | ATH txs (2026) | Activity (what the txs are) | DAO-origin(2) |
|--:|---|---|--:|--:|--:|--:|--:|---|--:|
| 1 | `0xf0940b14...` **YOU** | YOU (DAO contributor allocation) | 453,333 | $25,004 | 50,000 | 453,333 | 13 | 11 sell-tx (V3 292,916, V4 100,417, CoW 60,000/2f), 2 in | 100% |
| 2 | `0x930b88a5...` **top arb/MM bot #1** | arb/MM bot | 314,861 | $20,512 | 0 | -0 | 261 | 261 sells + 261 buys (continuous V3<->V4 arb) | 0% |
| 3 | `0x8bf44b00...` **top arb/MM bot #2** | arb/MM bot | 195,899 | $12,399 | 0 | -0 | 151 | 151 sells + 151 buys (continuous V3<->V4 arb) | 0% |
| 4 | `0xd4a3a947...` **market whale (one-day dump)** | market distributor | 106,036 | $8,591 | 0 | 106,036 | 5 | 2 sell-tx (V3 79,527, V4 26,509), 3 in, 2 out | 0% |
| 5 | `0xea80c984...` **stealth CoW distributor (DAO-sourced)** | DAO-allocation seller | 59,970 | $5,963 | 0 | 59,970 | 42 | 38 sell-tx (CoW 59,970/38f), 4 in | 99% |
| 6 | `0xf07b4d27...` | arb/MM bot | 63,269 | $4,787 | 0 | 0 | 65 | 65 sells + 65 buys (continuous V3<->V4 arb) | 0% |
| 7 | `0x43309757...` | market distributor | 25,614 | $4,296 | 0 | 25,614 | 1 | 1 sell-tx (V3 17,418, V4 8,197) | 0% |
| 8 | `0x834d10ce...` | arb/MM bot | 55,544 | $3,640 | 0 | 0 | 62 | 62 sells + 62 buys (continuous V3<->V4 arb) | 0% |
| 9 | `0xd8a57177...` **DAO genesis recipient** | DAO-allocation seller | 57,220 | $3,425 | 3,132 | 57,220 | 1 | 1 sell-tx (V3 45,776, V4 11,444), 1 out | 100% |
| 10 | `0x00000000...` | arb/MM bot | 53,602 | $3,304 | 0 | 0 | 96 | 96 sells + 96 buys (continuous V3<->V4 arb) | 0% |
| 11 | `0xfc9928f6...` | arb/MM bot | 35,502 | $2,730 | 0 | 0 | 39 | 39 sells + 39 buys (continuous V3<->V4 arb) | 0% |
| 12 | `0xbbafac01...` | arb/MM bot | 21,759 | $2,710 | 0 | 0 | 84 | 84 sells + 84 buys (continuous V3<->V4 arb) | 0% |
| 13 | `0x97162365...` | market distributor | 22,540 | $2,631 | 0 | 22,540 | 2 | 2 sell-tx (CoW 22,540/2f) | 0% |
| 14 | `0x0bde5998...` | arb/MM bot | 33,209 | $2,408 | 0 | 0 | 40 | 40 sells + 40 buys (continuous V3<->V4 arb) | 0% |
| 15 | `0xd7e1236c...` | arb/MM bot | 33,785 | $2,408 | 0 | 0 | 30 | 30 sells + 30 buys (continuous V3<->V4 arb) | 0% |
| 16 | `0x3980daa7...` | market distributor | 32,762 | $2,144 | 0 | 30,000 | 3 | 3 sell-tx (V3 25,793, V4 6,969), 2 buy | 0% |
| 17 | `0xd054ba91...` **market whale (one CoW dump)** | market distributor | 46,914 | $2,100 | 0 | 46,914 | 1 | 1 sell-tx (CoW 46,914/1f) | 0% |
| 18 | `0x7bd7cae2...` | arb/MM bot | 41,923 | $2,026 | 0 | 0 | 11 | 11 sells + 11 buys (continuous V3<->V4 arb) | 0% |
| 19 | `0xb3588dd7...` | arb/MM bot | 17,637 | $1,996 | 0 | 0 | 8 | 8 sells + 8 buys (continuous V3<->V4 arb) | 0% |
| 20 | `0xa31c8c9a...` | market distributor | 20,514 | $1,923 | 0 | -0 | 2 | 1 sell-tx (V3 17,232, V4 3,282), 1 buy, 1 in, 1 out | 0% |
| 21 | `0x99a5b028...` | arb/MM bot | 33,203 | $1,887 | 0 | 0 | 30 | 30 sells + 30 buys (continuous V3<->V4 arb) | 0% |
| 22 | `0x65a8f07b...` | market distributor | 14,968 | $1,832 | 0 | 14,968 | 5 | 2 sell-tx (V3 14,968), 2 in, 3 out | 0% |
| 23 | `0x004b3821...` | arb/MM bot | 28,385 | $1,826 | 0 | 0 | 47 | 47 sells + 47 buys (continuous V3<->V4 arb) | 0% |
| 24 | `0x91e8b869...` **DAO genesis recipient** | DAO-allocation seller | 32,535 | $1,769 | 0 | 32,535 | 1 | 1 sell-tx (V3 27,654, V4 4,880), 1 out | 100% |
| 25 | `0xcc66f4f1...` | arb/MM bot | 22,641 | $1,604 | 0 | 0 | 70 | 70 sells + 70 buys (continuous V3<->V4 arb) | 0% |
| 26 | `0x4f54f1e9...` | arb/MM bot | 25,392 | $1,596 | 0 | 0 | 31 | 31 sells + 31 buys (continuous V3<->V4 arb) | 0% |
| 27 | `0xe2228e89...` | arb/MM bot | 10,902 | $1,550 | 0 | 0 | 48 | 48 sells + 48 buys (continuous V3<->V4 arb) | 0% |
| 28 | `0x00000000...` | arb/MM bot | 11,831 | $1,495 | 0 | 0 | 34 | 34 sells + 34 buys (continuous V3<->V4 arb) | 0% |
| 29 | `0x8b560646...` | arb/MM bot | 23,798 | $1,488 | 0 | 0 | 37 | 37 sells + 37 buys (continuous V3<->V4 arb) | 0% |
| 30 | `0x61c0293d...` | arb/MM bot | 22,218 | $1,429 | 0 | 0 | 8 | 8 sells + 8 buys (continuous V3<->V4 arb) | 0% |
| 31 | `0x1053ec0d...` | arb/MM bot | 23,432 | $1,378 | 0 | 0 | 24 | 24 sells + 24 buys (continuous V3<->V4 arb) | 0% |
| 32 | `0xfa7b1534...` | arb/MM bot | 18,927 | $1,335 | 0 | 0 | 40 | 40 sells + 40 buys (continuous V3<->V4 arb) | 0% |
| 33 | `0x00000000...` | arb/MM bot | 17,122 | $1,320 | 0 | -0 | 11 | 11 sells + 11 buys (continuous V3<->V4 arb) | 0% |
| 34 | `0x315d2ee4...` | arb/MM bot | 19,291 | $1,276 | 0 | 0 | 7 | 7 sells + 7 buys (continuous V3<->V4 arb) | 0% |
| 35 | `0x00000000...` | arb/MM bot | 17,067 | $1,235 | 0 | 0 | 29 | 29 sells + 29 buys (continuous V3<->V4 arb) | 0% |
| 36 | `0x664eeb03...` | market distributor | 11,358 | $1,169 | 0 | 9,440 | 7 | 7 sell-tx (V3 11,358), 2 buy | 0% |
| 37 | `0xf35c6c74...` **DAO recipient (still holds 64k)** | DAO-allocation seller | 15,761 | $1,109 | 64,011 | 15,761 | 13 | 8 sell-tx (V3 13,531, V4 2,230), 3 in, 10 out | 100% |
| 38 | `0x663bd8fd...` | market distributor | 16,803 | $1,099 | 0 | 16,803 | 4 | 2 sell-tx (V3 14,394, V4 2,409), 2 in, 2 out | 0% |
| 39 | `0xdf8adfe1...` | arb/MM bot | 15,621 | $1,093 | 0 | 0 | 21 | 21 sells + 21 buys (continuous V3<->V4 arb) | 0% |
| 40 | `0x5f444704...` | arb/MM bot | 15,938 | $1,028 | 0 | 0 | 17 | 17 sells + 17 buys (continuous V3<->V4 arb) | 0% |
| 41 | `0xaf061c2d...` | market distributor | 5,800 | $1,008 | 0 | 5,800 | 1 | 1 sell-tx (V3 5,800) | 0% |

---

## 6. TABLE B - Wallets that sold > $1,000 of ATH in the LAST 21 DAYS (May 28 -> Jun 18, 2026)
Only **4 wallets** cleared $1K in the trailing 3 weeks. The insider/DAO distribution has gone quiet - **no DAO-allocation wallet sold >$1K in this window** (the stealth seller stopped end-March; the genesis recipients dumped in March). The only persistent presence is the two arb/MM bots, still churning through today.

| # | Wallet | Category | ATH sold | USD sold(1) | Still holds | Net ATH | ATH txs (21d) | Activity (what the txs are) | DAO-origin(2) |
|--:|---|---|--:|--:|--:|--:|--:|---|--:|
| 1 | `0xf0940b14...` **YOU** | YOU (DAO contributor allocation) | 150,000 | $5,643 | 50,000 | 150,000 | 3 | 3 sell-tx (V3 105,000, V4 45,000) | 100% |
| 2 | `0x930b88a5...` **top arb/MM bot #1** | arb/MM bot | 62,500 | $2,340 | 0 | 0 | 40 | 40 sells + 40 buys (continuous V3<->V4 arb) | 0% |
| 3 | `0xd054ba91...` **market whale (one CoW dump)** | market distributor | 46,914 | $2,100 | 0 | 46,914 | 1 | 1 sell-tx (CoW 46,914/1f) | 0% |
| 4 | `0x8bf44b00...` **top arb/MM bot #2** | arb/MM bot | 43,712 | $1,551 | 0 | 0 | 25 | 25 sells + 25 buys (continuous V3<->V4 arb) | 0% |

**Read-through:** Over the last 21 days you are essentially the *only* sustained genuine seller; the sole other non-bot was `0xd054ba91` (a single 46,914-ATH CoW dump on May 29). The two bots (`0x930b88a5`, `0x8bf44b00`) remain the constant counterparties - reacting to flow, not anticipating yours.

---

## 7. Notes & caveats
- (1) **USD sold** = realized proceeds at sale time (counter-asset received x its daily USD rate). Daily marks; intraday swings not captured.
- (2) **DAO-origin %** = share of the wallet's all-time inbound ATH that traces back (<=4 hops) to the genesis/treasury/vesting contracts.
- **Net ATH** = sells - on-chain buys. Arb/MM bots net ~ 0 (they buy and sell equal amounts and hold nothing).
- EOA attribution uses the on-chain token sender with a `tx.origin` fallback for contract-routed swaps; CoW orders attributed via the `Trade`-event owner.
- Behavioral wallet-clustering (one entity behind several addresses) is **not asserted** beyond direct token-flow links; proving common ownership of the bot cluster would require paid attribution (Arkham/Nansen).

*Full machine-readable data: `ath_sellers_2026.csv`. Reproduction pipeline & evidence JSONs: see `README.md`.*
