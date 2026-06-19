"""Render the forensic report as a single self-contained styled HTML file."""
import json, html
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
def esc(s): return html.escape(str(s))
def cat(r):
    if r.get('is_user'): return "you"
    if r['cls']=="arb/MM bot": return "bot"
    if dao.get(r['addr'],0)>=80: return "dao"
    return "market"
CATLBL={"you":"YOU","bot":"arb / MM bot","dao":"DAO-allocation seller","market":"market distributor"}
def fmt(n): return f"{n:,.0f}"
def netfmt(n): return "~0" if abs(n)<1 else f"{n:,.0f}"
def acct(addr):
    lbl=LBL.get(addr,"")
    short=addr[:6]+"…"+addr[-4:]
    a=f'<a href="https://etherscan.io/address/{addr}" target="_blank" title="{addr}"><code>{short}</code></a>'
    if lbl and lbl!="YOU": a+=f' <span class="lbl">{esc(lbl)}</span>'
    return a
def act_ytd(r):
    if r['cls']=="arb/MM bot": return f"{r['sell_txs']} sells + {r['buy_txs']} buys (continuous V3↔V4 arb)"
    vs=[]
    if r['v3']>0: vs.append(f"V3 {fmt(r['v3'])}")
    if r['v4']>0: vs.append(f"V4 {fmt(r['v4'])}")
    if r['cow']>0: vs.append(f"CoW {fmt(r['cow'])}/{r['cow_fills']}f")
    s=f"{r['sell_txs']} sell-tx ({', '.join(vs)})"
    if r['buy_txs']: s+=f", {r['buy_txs']} buy"
    if r['in_txs']: s+=f", {r['in_txs']} in"
    if r['out_txs']: s+=f", {r['out_txs']} out"
    return s
def act_win(r):
    if r['cls']=="arb/MM bot": return f"{r['stx']} sells + {r['btx']} buys (continuous V3↔V4 arb)"
    vs=[]
    if r['v3']>0: vs.append(f"V3 {fmt(r['v3'])}")
    if r['v4']>0: vs.append(f"V4 {fmt(r['v4'])}")
    if r['cow']>0: vs.append(f"CoW {fmt(r['cow'])}/{r['cowf']}f")
    s=f"{r['stx']} sell-tx ({', '.join(vs)})"
    if r['btx']: s+=f", {r['btx']} buy"
    if r['intx']: s+=f", {r['intx']} in"
    if r['outtx']: s+=f", {r['outtx']} out"
    return s
def daocell(p):
    p=round(p)
    cls="d0" if p<20 else ("d1" if p<80 else "d2")
    return f'<td class="num {cls}" data-sort="{p}">{p}%</td>'

def table(rows, ytd=True):
    out=['<div class="tw"><table>','<thead><tr>',
         '<th data-t="n">#</th><th>Wallet</th><th>Category</th>',
         '<th class="num" data-t="n">ATH sold</th><th class="num" data-t="n">USD sold<sup>1</sup></th>',
         '<th class="num" data-t="n">Still holds</th><th class="num" data-t="n">Net ATH</th>',
         f'<th class="num" data-t="n">ATH txs<br><small>{"2026" if ytd else "21d"}</small></th>',
         '<th>Activity (what the txs are)</th><th class="num" data-t="n">DAO<sup>2</sup></th>',
         '</tr></thead><tbody>']
    for i,r in enumerate(rows):
        c=cat(r); a=r['addr']
        ath=r['ath_sold'] if ytd else r['ath']; usd=r['usd_sold'] if ytd else r['usd']
        net=r['net']; hold=bal.get(a,0) if ytd else r['hold']; ntx=r['ntx']
        d=dao.get(a,0); actv=act_ytd(r) if ytd else act_win(r)
        rowcls=' class="me"' if c=="you" else ''
        out.append(f'<tr{rowcls}>'
            f'<td class="num" data-sort="{i+1}">{i+1}</td>'
            f'<td class="w">{acct(a)}</td>'
            f'<td><span class="badge {c}">{CATLBL[c]}</span></td>'
            f'<td class="num" data-sort="{ath:.0f}">{fmt(ath)}</td>'
            f'<td class="num money" data-sort="{usd:.0f}">${fmt(usd)}</td>'
            f'<td class="num" data-sort="{hold:.0f}">{fmt(hold)}</td>'
            f'<td class="num" data-sort="{net:.0f}">{netfmt(net)}</td>'
            f'<td class="num" data-sort="{ntx}">{ntx}</td>'
            f'<td class="act">{esc(actv)}</td>'
            f'{daocell(d)}</tr>')
    out.append('</tbody></table></div>')
    return "\n".join(out)

CSS="""
:root{--bg:#0f1115;--card:#171a21;--card2:#1d212b;--line:#2a2f3a;--tx:#e7eaf0;--mut:#9aa3b2;--acc:#5b9dff;
--green:#1f9d57;--greenbg:#11341f;--red:#e0533d;--redbg:#3a1a14;--blue:#3d7bd6;--bluebg:#13243f;--grey:#3a4150;--greybg:#20242e;--am:#ffcf5c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:32px 22px 80px}
header.hd{border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:8px}
h1{font-size:27px;margin:0 0 6px;letter-spacing:-.3px}
h1 .ath{color:var(--am)}
.sub{color:var(--mut);font-size:13.5px}
.sub code{color:var(--tx)}
.meta{display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:12px;font-size:13px;color:var(--mut)}
.meta b{color:var(--tx);font-weight:600}
h2{font-size:19px;margin:34px 0 12px;padding-top:6px}
h2 .n{color:var(--acc);font-variant-numeric:tabular-nums;margin-right:8px}
p{margin:10px 0}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
code{font:12.5px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:#0c0e12;border:1px solid var(--line);border-radius:5px;padding:1px 5px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px;margin:18px 0 6px}
.c{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.c .k{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.5px}
.c .v{font-size:21px;font-weight:700;margin-top:4px;font-variant-numeric:tabular-nums}
.c .v small{font-size:13px;color:var(--mut);font-weight:500}
.callout{border-radius:12px;padding:16px 18px;margin:16px 0;border:1px solid}
.callout.ok{background:var(--greenbg);border-color:#1f9d5755}
.callout.warn{background:var(--redbg);border-color:#e0533d55}
.callout h3{margin:0 0 6px;font-size:16px}
.callout.ok h3{color:#5fd699}.callout.warn h3{color:#ff8b76}
.badge{display:inline-block;font-size:11.5px;font-weight:600;padding:2px 9px;border-radius:20px;white-space:nowrap}
.badge.you{background:var(--greenbg);color:#5fd699;border:1px solid #1f9d5766}
.badge.bot{background:var(--greybg);color:#b6bdca;border:1px solid var(--grey)}
.badge.dao{background:var(--redbg);color:#ff9c87;border:1px solid #e0533d66}
.badge.market{background:var(--bluebg);color:#7db1f0;border:1px solid #3d7bd666}
.legend{display:flex;flex-wrap:wrap;gap:8px 14px;margin:6px 0 2px;font-size:12.5px;color:var(--mut);align-items:center}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:12px;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:920px}
thead th{position:sticky;top:0;background:var(--card2);color:var(--mut);text-align:left;font-weight:600;padding:10px 11px;border-bottom:1px solid var(--line);cursor:pointer;white-space:nowrap;font-size:12px}
thead th.num{text-align:right}
thead th small{color:#6b7280}
tbody td{padding:9px 11px;border-bottom:1px solid #20242e;vertical-align:top}
tbody tr:hover{background:#161a22}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.money{color:#ffd98a}
td.w{white-space:nowrap}
td.w .lbl{display:block;color:var(--mut);font-size:11px;margin-top:2px}
td.act{color:#c4ccd8;font-size:12px;min-width:260px}
tr.me{background:#11341f33}
tr.me td{border-bottom-color:#1f9d5733}
td.d0{color:var(--mut)}td.d1{color:#ffb45c}td.d2{color:#ff8b76;font-weight:600}
.foot{color:var(--mut);font-size:12.5px;margin-top:8px}
.foot li{margin:4px 0}
hr{border:0;border-top:1px solid var(--line);margin:30px 0}
.tag{font-size:11px;color:var(--mut)}
"""
JS="""
document.querySelectorAll('table').forEach(t=>{
 t.querySelectorAll('thead th').forEach((th,ci)=>{th.addEventListener('click',()=>{
  const tb=t.tBodies[0],rows=[...tb.rows];const num=th.dataset.t==='n';
  const asc=!(th.dataset.asc==='1');th.dataset.asc=asc?'1':'0';
  rows.sort((a,b)=>{let x=a.cells[ci].dataset.sort??a.cells[ci].innerText,y=b.cells[ci].dataset.sort??b.cells[ci].innerText;
   if(num){x=parseFloat(x)||0;y=parseFloat(y)||0;return asc?x-y:y-x}return asc?(''+x).localeCompare(y):(''+y).localeCompare(x)});
  rows.forEach(r=>tb.appendChild(r));});});});
"""
HTML=f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATH (AthenaDAO) — On-Chain Forensic Analysis</title>
<style>{CSS}</style></head><body><div class="wrap">

<header class="hd">
<h1><span class="ath">$ATH</span> (AthenaDAO) — On-Chain Forensic Analysis</h1>
<div class="sub">Subject wallet <code>0xf0940b14e8a4bE798cD713A6807e95f47B769d9C</code> &nbsp;·&nbsp; Token <code>0xa4ffdf32…754739</code> (Ethereum)</div>
<div class="meta"><span>Period <b>2026-01-01 → 2026-06-18</b></span><span>Blocks <b>24,136,053 → 25,345,825</b></span><span>Prepared <b>2026-06-18</b></span><span>Source <b>100% on-chain + CoinGecko daily marks</b></span></div>
</header>

<div class="cards">
<div class="c"><div class="k">ATH price</div><div class="v">$0.034 <small>−79% YTD</small></div></div>
<div class="c"><div class="k">Market cap</div><div class="v">~$297K</div></div>
<div class="c"><div class="k">Total DEX liquidity</div><div class="v">~$59K <small>V3+V4</small></div></div>
<div class="c"><div class="k">Distinct sellers (YTD)</div><div class="v">456 <small>41 &gt; $1k</small></div></div>
<div class="c"><div class="k">Your sells (YTD)</div><div class="v">$25,004 <small>453K ATH</small></div></div>
<div class="c"><div class="k">Front-runner found?</div><div class="v" style="color:#5fd699">No</div></div>
</div>

<div class="callout ok">
<h3>Verdict: you are not being front-run</h3>
<p style="margin:4px 0">Across all <b>9 of your sell transactions</b>, <b>zero</b> other ATH trades executed <i>before</i> you in the same block, and there are <b>no sandwiches</b>. The wallets that appear "on top of you" are arbitrage / market-making bots <b>reacting</b> to your price impact — e.g. the top bot <code>0x930b88a5</code> traded <b>0×</b> in the hour before your sells but <b>5×</b> within the hour after. On a ~$59K book every large sell moves price and bots instantly arbitrage the V3↔V4 gap, which feels like front-running but is back-running.</p>
</div>

<h2><span class="n">1</span>Methodology</h2>
<p>Every figure is reconstructed from raw Ethereum logs — no third-party dashboards.</p>
<ul>
<li>Every ATH <code>Transfer</code> since genesis (deploy block 17,977,841; <b>16,907</b> all-time, 4,370 in 2026).</li>
<li>Every Uniswap <b>V3</b> swap (2,315) and <b>V4</b> swap (2,128); V4 signed-int128 amounts validated against receipts.</li>
<li><b>CoW Protocol</b> settlements de-anonymized to the true order owner via <code>Trade</code> events (exposed sellers invisible to pool-only analysis).</li>
<li>ATH has <b>only two Ethereum venues and no CEX listing</b> → all on-chain selling is captured. Detected sells <b>2,944,143 ATH</b> reconcile to gross venue inflow <b>2,943,757 ATH</b>.</li>
<li><b>USD = realized proceeds at sale time</b> (counter-asset received × its daily USD rate).</li>
</ul>

<h2><span class="n">2</span>The real competing sellers — parallel insider distribution</h2>
<p>What you're sensing is <b>other DAO-allocation holders distributing</b>, not a predatory bot:</p>
<ul>
<li><b><code>0xea80c984</code> — 99% DAO-origin, the stealth seller.</b> 59,970 ATH via <b>38 small CoW fills, near-daily Jan 4 → Mar 31</b>, avg ≈ $0.099/ATH (sold early, near the top). Trail: genesis → <code>0x5b99e2da</code> (12.5M contributor pool) → hub <code>0x0e449816</code> → this wallet.</li>
<li><b><code>0xd8a57177</code> (57,220, Mar 26)</b> and <b><code>0x91e8b869</code> (32,535, Mar 27)</b> — both 100% DAO genesis recipients, dumping on consecutive days (looks coordinated).</li>
<li><b><code>0xf35c6c74</code></b> — DAO recipient; sold 15,761 but <b>still holds 64,011 ATH</b> (largest known overhang outside the treasury).</li>
</ul>

<h2><span class="n">3</span>Provenance &amp; DAO / team connection</h2>
<p>All 30M circulating ATH was minted to genesis <code>0x4d754910…</code>, then routed to vesting/treasury contracts — matching the official allocation (Community 10M / <b>Core &amp; Early Contributors 12M, 24-mo vesting</b> / Service Providers 8M; 70M unminted treasury).</p>
<ul>
<li><b>DAO/team-connected sellers:</b> you, <code>0xea80c984</code>, <code>0xd8a57177</code>, <code>0x91e8b869</code>, <code>0xf35c6c74</code>.</li>
<li><b>You</b> received 848,886 ATH from DAO distribution contracts <code>0x71028407</code> + <code>0x0b7ffc1f</code>, sold ≈483K (393K direct + 90K via CoW), hold 50,000 — the single largest <i>genuine</i> (non-bot) seller of ATH in 2026.</li>
<li><b>Arb/MM bots are not DAO-connected</b> (they buy from the pools and resell, hold 0). <b>Market distributors</b> bought/bridged in.</li>
</ul>

<div class="legend"><b style="color:var(--tx)">Legend:</b>
<span class="badge you">YOU</span><span class="badge dao">DAO-allocation seller</span><span class="badge market">market distributor</span><span class="badge bot">arb / MM bot</span>
<span style="margin-left:auto" class="tag">click any column header to sort · click a wallet to open Etherscan</span></div>

<h2><span class="n">4</span>Table A — all wallets that sold &gt; $1,000 of ATH (YTD: Jan 1 → Jun 18)</h2>
<p class="tag">{len(fin)} wallets. Besides you: 26 arb/MM bots (1.17M ATH / ~$80K net-zero churn), 4 DAO-allocation insiders (165K / $12.3K), 10 market distributors (303K / $26.8K).</p>
{table(fin, True)}

<h2><span class="n">5</span>Table B — wallets that sold &gt; $1,000 of ATH in the LAST 21 DAYS (May 28 → Jun 18)</h2>
<p class="tag">Only <b>{len(win)} wallets</b> cleared $1K in the trailing 3 weeks. <b>No DAO-allocation wallet sold &gt;$1K in this window</b> — insider distribution has gone quiet. You are the only sustained genuine seller; the lone other non-bot was a single CoW dump.</p>
{table(win, False)}

<hr>
<h2><span class="n">6</span>Notes &amp; caveats</h2>
<ul class="foot">
<li><sup>1</sup> <b>USD sold</b> = realized proceeds at sale time (counter-asset × daily USD rate). Daily marks; intraday swings not captured.</li>
<li><sup>2</sup> <b>DAO-origin %</b> = share of the wallet's all-time inbound ATH traceable (≤4 hops) to genesis/treasury/vesting.</li>
<li><b>Net ATH</b> = sells − on-chain buys; arb/MM bots net ≈ 0 (buy and sell equal amounts, hold nothing).</li>
<li>EOA attribution uses the on-chain token sender with a <code>tx.origin</code> fallback for contract-routed swaps; CoW via <code>Trade</code>-event owner.</li>
<li>Behavioral wallet-clustering (one entity / several addresses) is not asserted beyond direct token-flow links; proving common ownership of the bot cluster needs paid attribution (Arkham/Nansen).</li>
</ul>
<p class="tag">Machine-readable data: ath_sellers_2026.csv · reproduction pipeline: README.md</p>

</div><script>{JS}</script></body></html>"""
open('ATH_forensic_report.html','w').write(HTML)
print("wrote ATH_forensic_report.html", len(HTML),"bytes")
