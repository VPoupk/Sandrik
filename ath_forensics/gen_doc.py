"""Assemble the full forensic report markdown (findings + YTD table + 21d table)."""
import json
from datetime import datetime, timezone
USER="0xf0940b14e8a4be798cd713a6807e95f47b769d9c"
fin=json.load(open('final_table.json'))
win=json.load(open('window21_rows.json'))
dao=json.load(open('dao_origin.json'))
bal=json.load(open('bal_authoritative.json'))
LBL={"0x930b88a592a045c428f3d99f7f3e5f95e3967508":"top arb/MM bot #1",
     "0x8bf44b00436d41fef72474bb0fa0778f7bf956ac":"top arb/MM bot #2",
     "0xea80c98457a0424ef62bc82cadd31b1a7e2cc456":"stealth CoW distributor (DAO-sourced)",
     "0xd8a571774d10eeb5efe07bdd9074c64a0a1e11dd":"DAO genesis recipient",
     "0x91e8b8692baf5ff33333304e5039cd4e75ac122d":"DAO genesis recipient",
     "0xf35c6c74cddbc66d22ef82785e9e144ce7d380b0":"DAO recipient (still holds 64k)",
     "0xd4a3a94791513cbbbfa3d74c6d530e073ef8f6fc":"market whale (one-day dump)",
     "0xd054ba913bf972f2563dff4b26dc383587ae7808":"market whale (one CoW dump)",
     USER:"YOU"}
def dt(ts):
    try: ts=float(ts)
    except: return "-"
    return datetime.fromtimestamp(ts,tz=timezone.utc).strftime("%Y-%m-%d") if ts else "-"
def cat(r):
    if r.get('is_user'): return "YOU (DAO contributor allocation)"
    if r['cls']=="arb/MM bot": return "arb/MM bot"
    if dao.get(r['addr'],0)>=80: return "DAO-allocation seller"
    return "market distributor"
def act_ytd(r):
    if r['cls']=="arb/MM bot":
        return f"{r['sell_txs']} sells + {r['buy_txs']} buys (continuous V3<->V4 arb)"
    vs=[]
    if r['v3']>0: vs.append(f"V3 {r['v3']:,.0f}")
    if r['v4']>0: vs.append(f"V4 {r['v4']:,.0f}")
    if r['cow']>0: vs.append(f"CoW {r['cow']:,.0f}/{r['cow_fills']}f")
    s=f"{r['sell_txs']} sell-tx ({', '.join(vs)})"
    if r['buy_txs']: s+=f", {r['buy_txs']} buy"
    if r['in_txs']: s+=f", {r['in_txs']} in"
    if r['out_txs']: s+=f", {r['out_txs']} out"
    return s
def act_win(r):
    if r['cls']=="arb/MM bot":
        return f"{r['stx']} sells + {r['btx']} buys (continuous V3<->V4 arb)"
    vs=[]
    if r['v3']>0: vs.append(f"V3 {r['v3']:,.0f}")
    if r['v4']>0: vs.append(f"V4 {r['v4']:,.0f}")
    if r['cow']>0: vs.append(f"CoW {r['cow']:,.0f}/{r['cowf']}f")
    s=f"{r['stx']} sell-tx ({', '.join(vs)})"
    if r['btx']: s+=f", {r['btx']} buy"
    if r['intx']: s+=f", {r['intx']} in"
    if r['outtx']: s+=f", {r['outtx']} out"
    return s
def name(addr):
    lbl=LBL.get(addr,"")
    return f"`{addr[:10]}...`"+(f" **{lbl}**" if lbl else "")

def ytd_table():
    o=["| # | Wallet | Category | ATH sold | USD sold(1) | Still holds | Net ATH | ATH txs (2026) | Activity (what the txs are) | DAO-origin(2) |",
       "|--:|---|---|--:|--:|--:|--:|--:|---|--:|"]
    for i,r in enumerate(fin):
        o.append(f"| {i+1} | {name(r['addr'])} | {cat(r)} | {r['ath_sold']:,.0f} | ${r['usd_sold']:,.0f} | {bal.get(r['addr'],0):,.0f} | {r['net']:,.0f} | {r['ntx']} | {act_ytd(r)} | {dao.get(r['addr'],0):.0f}% |")
    return "\n".join(o)
def win_table():
    o=["| # | Wallet | Category | ATH sold | USD sold(1) | Still holds | Net ATH | ATH txs (21d) | Activity (what the txs are) | DAO-origin(2) |",
       "|--:|---|---|--:|--:|--:|--:|--:|---|--:|"]
    for i,r in enumerate(win):
        o.append(f"| {i+1} | {name(r['addr'])} | {cat(r)} | {r['ath']:,.0f} | ${r['usd']:,.0f} | {r['hold']:,.0f} | {r['net']:,.0f} | {r['ntx']} | {act_win(r)} | {r['dao']:.0f}% |")
    return "\n".join(o)

DOC=f"""# ATH (AthenaDAO) - On-Chain Forensic Analysis

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

## 2. Headline finding - are you being front-run?
**No.** There is no transaction-level front-running and no sandwich bot targeting you.
- Across all **9 of your sell transactions**, **zero** other ATH trades executed *before* you in the same block; **zero** sandwiches.
- The wallets that appear "on top of you" are **arbitrage / market-making bots reacting to your price impact.** Proof: the #1 bot `0x930b88a5` traded **0 times in the hour *before*** your sells but **5x within the hour *after*** (17x within 6h after) - that is back-running/arbitrage, not prediction.

**Why it feels like front-running:** ATH liquidity is only **~$59K** (V3 $32K + V4 $27K). Every large sell you place visibly moves price and creates a V3<->V4 dislocation that ~26 bots instantly arbitrage. The price fell **-79% over the period ($0.171 -> $0.036)**, so you (and everyone) sold into a downtrend with heavy slippage.

## 3. The real "competing sellers" - parallel insider distribution
What you're sensing is **other DAO-allocation holders distributing**, not a predatory bot:
- **`0xea80c984` - 99% DAO-origin, the stealth seller.** Sold **59,970 ATH via 38 small CoW fills, near-daily Jan 4 -> Mar 31**, avg ~$0.099/ATH (distributed *early, near the top*). Token trail: genesis -> `0x5b99e2da` (12.5M Core/Early-Contributor pool) -> hub `0x0e449816` -> this wallet. Invisible on Etherscan's normal views because it routed through CoW.
- **`0xd8a57177` (57,220 ATH, Mar 26)** and **`0x91e8b869` (32,535 ATH, Mar 27)** - both **100% DAO genesis recipients**, dumping on **consecutive days** (looks coordinated).
- **`0xf35c6c74`** - DAO recipient; sold 15,761 but **still holds 64,011 ATH** (largest known future overhang outside the treasury).
- These ran on their **own schedules and mostly finished by early Q2** - none reactively shadows your specific trades.

## 4. Provenance & DAO/team connection
All 30M circulating ATH was minted to genesis **`0x4d754910...`**, then distributed to vesting/treasury contracts - consistent with the official allocation (Community 10M / **Core & Early Contributors 12M, 24-mo vesting** / Service Providers 8M incl. Molecule-bio.xyz 6.9M; 70M unminted treasury).
- **DAO/team-connected sellers:** **you**, `0xea80c984`, `0xd8a57177`, `0x91e8b869`, `0xf35c6c74` (all trace to genesis/vesting).
- **You** received **848,886 ATH** from DAO distribution contracts `0x71028407` + `0x0b7ffc1f`, sold ~483K (393K direct + 90K via CoW), and hold 50,000 - you are the **single largest *genuine* (non-bot) seller of ATH in 2026**.
- **Arb/MM bots are NOT DAO-connected** - they source ATH by buying from the pools and reselling (hold 0).
- **Market distributors** (`0xd4a3a947`, `0xd054ba91`, etc.) bought on the DEX or bridged in, then sold - no DAO link.

---

## 5. TABLE A - All wallets that sold > $1,000 of ATH (YTD: Jan 1 -> Jun 18, 2026)
{len(fin)} wallets. Among the 40 besides you: **26 arb/MM bots** (1.17M ATH / ~$80K of net-zero churn, hold nothing), **4 DAO-allocation insiders** (165K ATH / $12.3K), **10 market distributors** (303K ATH / $26.8K).

{ytd_table()}

---

## 6. TABLE B - Wallets that sold > $1,000 of ATH in the LAST 21 DAYS (May 28 -> Jun 18, 2026)
Only **{len(win)} wallets** cleared $1K in the trailing 3 weeks. The insider/DAO distribution has gone quiet - **no DAO-allocation wallet sold >$1K in this window** (the stealth seller stopped end-March; the genesis recipients dumped in March). The only persistent presence is the two arb/MM bots, still churning through today.

{win_table()}

**Read-through:** Over the last 21 days you are essentially the *only* sustained genuine seller; the sole other non-bot was `0xd054ba91` (a single 46,914-ATH CoW dump on May 29). The two bots (`0x930b88a5`, `0x8bf44b00`) remain the constant counterparties - reacting to flow, not anticipating yours.

---

## 7. Notes & caveats
- (1) **USD sold** = realized proceeds at sale time (counter-asset received x its daily USD rate). Daily marks; intraday swings not captured.
- (2) **DAO-origin %** = share of the wallet's all-time inbound ATH that traces back (<=4 hops) to the genesis/treasury/vesting contracts.
- **Net ATH** = sells - on-chain buys. Arb/MM bots net ~ 0 (they buy and sell equal amounts and hold nothing).
- EOA attribution uses the on-chain token sender with a `tx.origin` fallback for contract-routed swaps; CoW orders attributed via the `Trade`-event owner.
- Behavioral wallet-clustering (one entity behind several addresses) is **not asserted** beyond direct token-flow links; proving common ownership of the bot cluster would require paid attribution (Arkham/Nansen).

*Full machine-readable data: `ath_sellers_2026.csv`. Reproduction pipeline & evidence JSONs: see `README.md`.*
"""
open('ATH_forensic_report.md','w').write(DOC)
print("wrote ATH_forensic_report.md", len(DOC),"bytes")
print("YTD rows:",len(fin),"| 21d rows:",len(win))
