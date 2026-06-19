"""Standalone visual forensic report for the 'potential watcher' wallet 0xd054ba91."""
import json
from datetime import datetime, timezone
W="0xd054ba913bf972f2563dff4b26dc383587ae7808"
def es(a): return f'<a href="https://etherscan.io/address/{a}" target="_blank"><code>{a[:8]}…{a[-4:]}</code></a>'

# ---- verified lifecycle events (token flows) ----
# (date, side, text, kind)  kind: cap|buy|sell|move|recv|fund
EV=[
 ("2026-02-11","in","Funded 0.0498 ETH (gas) from a shared funding service","fund"),
 ("2026-02-12","in","+5,773 USDC working capital","cap"),
 ("2026-02-17","in","+10,122 USDC from Hinkal (privacy protocol)","cap"),
 ("2026-02-19","in","+16,374 USDC from Hinkal (privacy protocol)","cap"),
 ("2026-02-26","buy","Bought 67,580 CFG for 10,000 USDC (CoW)","move"),
 ("2026-03-09","buy","BUY 46,914 ATH for 3,000 USDC (CoW) — $0.064/ATH","buy"),
 ("2026-03-09","buy","Bought 47,365 CFG for 6,769 USDC (CoW)","move"),
 ("2026-03-13","in","+46,004 GTC via Relay bridge","move"),
 ("2026-05-28","sell","Sold 46,004 GTC for 4,037 USDC (CoW) → bridged out","move"),
 ("2026-05-29","sell","SELL all 46,914 ATH for 2,100 USDT (CoW) → bridged out","sell"),
]
# ---- related addresses ----
REL=[
 ("0x25e5e82f5702a27c3466fe68f14abdbbadfca826","Hinkal — privacy / shielding protocol","Source of ~$26.5K working capital","0","Funds deliberately obscured — siblings NOT traceable"),
 ("0x5c7bcd6e7de5423a257d81b442095a1a6ced35c5","ERC1967Proxy (bridge/deposit)","Proceeds exit — 5 transfers out","0","Infrastructure (not a wallet)"),
 ("0x767e4c20f521a829de4ffc40c25176676878147f","Across — SpokePoolPeriphery","Bridge used to move funds","0","Infrastructure"),
 ("0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f","Relay — RelayRouterV3","Source of the 46K GTC (bridge/swap)","0","Infrastructure"),
 ("0xa5a5491bca93dd4c076e4906e79e7673f4a5a142","EOA — shared gas funder (2,842 recipients)","One-time 0.05 ETH gas top-up","0","Service — not a personal link"),
 ("0x9008d19f58aabd9ed0d60971565aa8510560ab41","CoW Protocol — GPv2Settlement","Trade venue for every buy/sell","transient","Venue"),
]

# ---- SVG timeline (Feb 1 -> Jun 18) ----
import math
def ts(d): return datetime.strptime(d,"%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
dom0=ts("2026-02-01"); dom1=ts("2026-06-18")
W_px=1080;L=150;R=24;T=44;rh=64
def x(t): return L+(t-dom0)/(dom1-dom0)*(W_px-L-R)
your_unlocks=[("2026-02-20","333,333"),("2026-05-27","200,000")]
your_sells=["2026-02-20","2026-02-22","2026-02-23","2026-04-15","2026-05-20","2026-05-25","2026-06-01","2026-06-14","2026-06-15"]
H=T+rh*2+40
svg=[f'<svg viewBox="0 0 {W_px} {H}" width="100%" preserveAspectRatio="xMidYMid meet" font-family="inherit">']
# month ticks
for d,lab in [("2026-02-01","Feb"),("2026-03-01","Mar"),("2026-04-01","Apr"),("2026-05-01","May"),("2026-06-01","Jun")]:
    xx=x(ts(d)); svg.append(f'<line x1="{xx:.1f}" y1="{T-12}" x2="{xx:.1f}" y2="{T+rh*2}" stroke="#2a2f3a"/><text x="{xx+3:.1f}" y="{T-16}" fill="#9aa3b2" font-size="11">{lab}</text>')
# unlock lines
for d,amt in your_unlocks:
    xx=x(ts(d)); svg.append(f'<line x1="{xx:.1f}" y1="{T-12}" x2="{xx:.1f}" y2="{T+rh*2}" stroke="#e0a23d" stroke-width="1.5" stroke-dasharray="4 3"/><text x="{xx+3:.1f}" y="{T+rh*2+14}" fill="#e0a23d" font-size="10">your unlock {amt}</text>')
# row labels
svg.append(f'<text x="6" y="{T+rh*0+8}" fill="#ff8b76" font-size="12" font-weight="700">0xd054…7808</text><text x="6" y="{T+rh*0+24}" fill="#9aa3b2" font-size="10">the watcher candidate</text>')
svg.append(f'<text x="6" y="{T+rh*1+8}" fill="#34c97a" font-size="12" font-weight="700">YOU 0xf094</text><text x="6" y="{T+rh*1+24}" fill="#9aa3b2" font-size="10">unlocks &amp; sells</text>')
y0=T+rh*0+10; y1=T+rh*1+10
svg.append(f'<line x1="{L}" y1="{y0:.1f}" x2="{W_px-R}" y2="{y0:.1f}" stroke="#20242e"/><line x1="{L}" y1="{y1:.1f}" x2="{W_px-R}" y2="{y1:.1f}" stroke="#20242e"/>')
# wallet ATH events (big), other trades (small grey)
for d,side,txt,kind in EV:
    xx=x(ts(d))
    if kind=="buy" and "ATH" in txt:
        svg.append(f'<circle cx="{xx:.1f}" cy="{y0:.1f}" r="9" fill="#34c97a"><title>{txt}</title></circle><text x="{xx:.1f}" y="{y0-14:.1f}" fill="#34c97a" font-size="10.5" text-anchor="middle">BUY ATH $3,000</text>')
    elif kind=="sell" and "ATH" in txt:
        svg.append(f'<circle cx="{xx:.1f}" cy="{y0:.1f}" r="9" fill="#e0533d"><title>{txt}</title></circle><text x="{xx:.1f}" y="{y0-14:.1f}" fill="#ff8b76" font-size="10.5" text-anchor="middle">SELL ATH $2,100</text>')
    else:
        svg.append(f'<circle cx="{xx:.1f}" cy="{y0:.1f}" r="4" fill="#5b6ersonhold" fill-opacity="0.7"><title>{d}: {txt}</title></circle>'.replace("#5b6ersonhold","#788195"))
# your sells
for d in your_sells:
    xx=x(ts(d)); svg.append(f'<circle cx="{xx:.1f}" cy="{y1:.1f}" r="5" fill="#34c97a" fill-opacity="0.85"><title>your sell {d}</title></circle>')
# annotation arrow: May27 unlock -> May29 wallet sell
xu=x(ts("2026-05-27")); xs=x(ts("2026-05-29"))
svg.append(f'<path d="M{xu:.1f},{T+rh*2+22} Q{(xu+xs)/2:.1f},{T+rh*2+34} {xs:.1f},{y0+12:.1f}" fill="none" stroke="#ff8b76" stroke-width="1.2" stroke-dasharray="3 2"/>')
svg.append(f'<text x="{(xu+xs)/2:.1f}" y="{T+rh*2+34}" fill="#ff8b76" font-size="10" text-anchor="middle">dumped ATH 2 days after your unlock</text>')
svg.append(f'<text x="{L}" y="{H-6}" fill="#9aa3b2" font-size="10">green=buy · red=sell · grey=other-token trades · gold dashed=your vesting unlocks</text>')
svg.append("</svg>"); SVG="\n".join(svg)

def relrows():
    o=[]
    for a,what,rel,ath,link in REL:
        o.append(f"<tr><td class='w'>{es(a)}</td><td>{what}</td><td>{rel}</td><td class='num'>{ath}</td><td class='mut'>{link}</td></tr>")
    return "\n".join(o)
def evrows():
    o=[]
    col={"fund":"#788195","cap":"#7db1f0","move":"#9aa3b2","buy":"#34c97a","sell":"#e0533d","in":"#9aa3b2"}
    for d,side,txt,kind in EV:
        c=col.get(kind,"#9aa3b2"); strong="font-weight:700" if "ATH" in txt else ""
        o.append(f"<tr><td class='num'>{d}</td><td style='color:{c};{strong}'>{txt}</td></tr>")
    return "\n".join(o)

CSS="""
:root{--bg:#0f1115;--card:#171a21;--line:#2a2f3a;--tx:#e7eaf0;--mut:#9aa3b2;--acc:#5b9dff;--green:#34c97a;--red:#e0533d;--gold:#e0a23d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1140px;margin:0 auto;padding:32px 22px 70px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:30px 0 10px}h2 .n{color:var(--acc);margin-right:8px}
.sub{color:var(--mut);font-size:13px}.sub code{color:var(--tx)}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
code{font:12.5px ui-monospace,Menlo,Consolas,monospace;background:#0c0e12;border:1px solid var(--line);border-radius:5px;padding:1px 5px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:16px 0}
.c{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.c .k{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.5px}.c .v{font-size:20px;font-weight:700;margin-top:4px}
.c .v small{font-size:12px;color:var(--mut);font-weight:500}
.callout{border-radius:12px;padding:16px 18px;margin:14px 0;border:1px solid;background:#2a230f;border-color:#e0a23d55}
.callout h3{margin:0 0 6px;color:#ffcf5c}
.chartbox{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 10px;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0}
th{text-align:left;color:var(--mut);font-size:12px;border-bottom:1px solid var(--line);padding:8px 10px}
td{padding:8px 10px;border-bottom:1px solid #20242e;vertical-align:top}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}td.w{white-space:nowrap}td.mut{color:var(--mut);font-size:12px}
.flow{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:14px 0;font-size:12.5px}
.box{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:8px 11px}
.box b{display:block}.box span{color:var(--mut);font-size:11px}
.arrow{color:var(--mut)}
.pill{display:inline-block;border-radius:20px;padding:1px 9px;font-size:11.5px;font-weight:600}
.pill.red{background:#3a1a14;color:#ff8b76;border:1px solid #e0533d66}
.foot{color:var(--mut);font-size:12.5px}.foot li{margin:4px 0}
"""
HTML=f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Wallet forensic — 0xd054…7808 (potential watcher)</title><style>{CSS}</style></head><body><div class=wrap>
<h1>Wallet deep-dive — <span style="color:#ff8b76">0xd054…7808</span> <span class="pill red">potential watcher</span></h1>
<div class=sub>{es(W)} · subject context: $ATH (AthenaDAO) seller flagged for dumping 2 days after your May-27 vesting unlock</div>

<div class=cards>
<div class=c><div class=k>ATH held now</div><div class=v>0 <small>fully exited</small></div></div>
<div class=c><div class=k>ATH round-trip P&amp;L</div><div class=v style="color:#ff8b76">−$900 <small>−30%</small></div></div>
<div class=c><div class=k>Bought / Sold ATH</div><div class=v>46,914 <small>$3,000 → $2,100</small></div></div>
<div class=c><div class=k>Hold period</div><div class=v>81 days <small>Mar 9 → May 29</small></div></div>
<div class=c><div class=k>Other holdings</div><div class=v>114,945 CFG <small>+0.05 ETH</small></div></div>
<div class=c><div class=k>Related wallets w/ ATH</div><div class=v style="color:#5fd699">0 found</div></div>
</div>

<div class=callout>
<h3>Verdict: a generalist trader that round-tripped ATH at a loss — not a provable insider/sibling cluster</h3>
<p style="margin:4px 0">This wallet bought 46,914 ATH for <b>$3,000</b> on Mar 9, held it for 11 weeks, and dumped the entire bag for <b>$2,100</b> on May 29 — <b>two days after your 200K unlock</b> and one day after liquidating an unrelated 46K GTC position. The timing is consistent with reacting to renewed ATH supply pressure, but it <b>lost ~30%</b> on the trade and exited two positions back-to-back, which looks more like portfolio de-risking than a savvy, informed front-run. It currently holds <b>no ATH</b>. Crucially, its working capital came out of <b>Hinkal, a privacy/shielding protocol</b>, so any sibling wallets are <b>deliberately un-traceable on-chain</b> — and nothing in its reachable graph holds ATH.</p>
</div>

<h2><span class=n>1</span>ATH lifecycle vs. your activity</h2>
<div class=chartbox>{SVG}</div>

<h2><span class=n>2</span>Money flow (how it got, and got rid of, its ATH)</h2>
<div class=flow>
<div class=box><b>Hinkal (privacy)</b><span>~$26.5K USDC in</span></div><span class=arrow>→</span>
<div class=box><b>0xd054…7808</b><span>this wallet</span></div><span class=arrow>→</span>
<div class=box><b>CoW Protocol</b><span>buy 46,914 ATH<br>for $3,000 (Mar 9)</span></div><span class=arrow>↓ held 81d</span>
<div class=box><b>CoW Protocol</b><span>sell 46,914 ATH<br>for $2,100 (May 29)</span></div><span class=arrow>→</span>
<div class=box><b>bridge / proxy out</b><span>proceeds exit</span></div>
</div>
<table><thead><tr><th>Date</th><th>Event</th></tr></thead><tbody>{evrows()}</tbody></table>
<p class=foot>It never transferred ATH to any wallet — ATH only entered/left via CoW swaps, so there is no direct ATH link to any other address.</p>

<h2><span class=n>3</span>Connected / related addresses — do any hold more ATH?</h2>
<table><thead><tr><th>Address</th><th>What it is</th><th>Relationship to 0xd054</th><th class=num>ATH</th><th>Link strength</th></tr></thead>
<tbody>{relrows()}</tbody></table>
<p class=foot><b>Conclusion:</b> every reachable counterparty is shared infrastructure (Hinkal, CoW, Across, Relay, a gas-funding service) — none is a personal sibling wallet, and <b>none holds ATH</b>. Because funding routed through Hinkal’s shielded pool, on-chain clustering cannot surface sibling wallets even if they exist; confirming or excluding them would require off-chain / paid attribution (Arkham, Nansen, exchange KYC).</p>

<h2><span class=n>4</span>Bottom line</h2>
<ul class=foot>
<li><b>Holdings:</b> 0 ATH (fully exited), 114,945 CFG (~$25K), 0.05 ETH. It is done with ATH.</li>
<li><b>Behaviour:</b> privacy-funded generalist DeFi trader (CFG, GTC, ATH; $3–30K positions), bridges proceeds out.</li>
<li><b>On the “watcher” thesis:</b> timing (T+2 days after your unlock) is suggestive, but the −30% loss and the simultaneous GTC exit point to ordinary de-risking, not an informed insider. Weak, unproven.</li>
<li><b>Related wallets:</b> none found holding ATH; the privacy setup blocks sibling discovery on-chain.</li>
</ul>
<p class=foot>All data on-chain (Ethereum), via JSON-RPC + Blockscout + CoW Trade events, {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.</p>
</div></body></html>"""
open('wallet_0xd054_report.html','w').write(HTML)
print("wrote wallet_0xd054_report.html",len(HTML),"bytes")
