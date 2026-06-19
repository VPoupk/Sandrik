"""Assemble the full forensic report markdown (findings + YTD table + 21d table)."""
import json
from datetime import datetime, timezone
USER="0xf0940b14e8a4be798cd713a6807e95f47b769d9c"
fin=json.load(open('final_table.json'))
win=json.load(open('window21_rows.json'))
dao=json.load(open('dao_origin.json'))
bal=json.load(open('bal_authoritative.json'))
wrows=json.load(open('watch_rows.json'))
def dstr(ts):
    from datetime import datetime, timezone
    try: ts=float(ts)
    except: return "-"
    return datetime.fromtimestamp(ts,tz=timezone.utc).strftime("%Y-%m-%d") if ts else "-"
def react_md():
    rows=sorted(wrows,key=lambda r:(-r['react7_pct'],-r['tot']))
    o=["| Wallet | Category | ATH sold | 1st sell | Started after you visible? | % ≤7d after your sell | % ≤14d after your unlock | Assessment |",
       "|---|---|--:|--:|:--:|--:|--:|---|"]
    for r in rows:
        a=r['addr']; c="DAO-allocation" if r['dao']>=80 else "market"
        if r['started_after_vis'] and r['react7_pct']>=60 and r['tot']>=20000: asv="**anticipatory exit**"
        elif r['react7_pct']>=60: asv="elevated post-sell selling"
        elif r['before3_pct']>=40: asv="sold just before your sells"
        elif not r['started_after_vis']: asv="independent (active before you were visible)"
        else: asv="independent / own schedule"
        st="✦ AFTER" if r['started_after_vis'] else "before"
        o.append(f"| `{a[:10]}…` | {c} | {r['tot']:,.0f} | {dstr(r['first'])} | {st} | {r['react7_pct']:.0f}% | {r['unlock14_pct']:.0f}% | {asv} |")
    return "\n".join(o)
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

DOC=f"""# ATH (AthenaDAO) - Wallet-Watching & Anticipatory-Selling Analysis

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

{react_md()}

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
