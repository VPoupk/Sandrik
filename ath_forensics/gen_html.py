"""Render the forensic report (re-framed: wallet-watching / anticipatory distribution)
as a single self-contained styled HTML file with an SVG timeline."""
import json, html, math
from datetime import datetime, timezone
USER="0xf0940b14e8a4be798cd713a6807e95f47b769d9c"
fin=json.load(open('final_table.json'))
win=json.load(open('window21_rows.json'))
dao=json.load(open('dao_origin.json'))
bal=json.load(open('bal_authoritative.json'))
wrows=json.load(open('watch_rows.json'))
chart=json.load(open('watch_chart.json'))
LBL={"0x930b88a592a045c428f3d99f7f3e5f95e3967508":"top arb/MM bot #1",
     "0x8bf44b00436d41fef72474bb0fa0778f7bf956ac":"top arb/MM bot #2",
     "0xea80c98457a0424ef62bc82cadd31b1a7e2cc456":"stealth CoW distributor (DAO-sourced)",
     "0xd8a571774d10eeb5efe07bdd9074c64a0a1e11dd":"DAO genesis recipient",
     "0x91e8b8692baf5ff33333304e5039cd4e75ac122d":"DAO genesis recipient",
     "0xf35c6c74cddbc66d22ef82785e9e144ce7d380b0":"DAO recipient (still holds 64k)",
     "0xd4a3a94791513cbbbfa3d74c6d530e073ef8f6fc":"market whale (one-day dump)",
     "0xd054ba913bf972f2563dff4b26dc383587ae7808":"anticipatory exit (dumped 2d after your unlock)",
     "0x3980daa7eaad0b7e0c53cfc5c2760037270da54d":"contract/router-routed (ambiguous)",
     USER:"YOU"}
BASE7=33
def esc(s): return html.escape(str(s))
def cat(r):
    if r.get('is_user'): return "you"
    if r['cls']=="arb/MM bot": return "bot"
    if dao.get(r['addr'],0)>=80: return "dao"
    return "market"
CATLBL={"you":"YOU","bot":"arb / MM bot","dao":"DAO-allocation seller","market":"market distributor"}
def fmt(n):
    try:n=float(n)
    except:return n
    return f"{n:,.0f}"
def netfmt(n): return "~0" if abs(n)<1 else f"{n:,.0f}"
def short(a): return a[:6]+"…"+a[-4:]
def acct(addr):
    lbl=LBL.get(addr,"")
    a=f'<a href="https://etherscan.io/address/{addr}" target="_blank" title="{addr}"><code>{short(addr)}</code></a>'
    if lbl and lbl!="YOU": a+=f' <span class="lbl">{esc(lbl)}</span>'
    return a
def dstr(ts):
    try: ts=float(ts)
    except: return "-"
    return datetime.fromtimestamp(ts,tz=timezone.utc).strftime("%Y-%m-%d") if ts else "-"

# ---------- sortable seller tables (A=YTD, B=21d) ----------
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
    p=round(float(p)); cls="d0" if p<20 else ("d1" if p<80 else "d2")
    return f'<td class="num {cls}" data-sort="{p}">{p}%</td>'
def seller_table(rows, ytd=True):
    o=['<div class="tw"><table>','<thead><tr>',
       '<th data-t="n">#</th><th>Wallet</th><th>Category</th>',
       '<th class="num" data-t="n">ATH sold</th><th class="num" data-t="n">USD sold¹</th>',
       '<th class="num" data-t="n">Still holds</th><th class="num" data-t="n">Net ATH</th>',
       f'<th class="num" data-t="n">ATH txs<br><small>{"2026" if ytd else "21d"}</small></th>',
       '<th>Activity (what the txs are)</th><th class="num" data-t="n">DAO²</th></tr></thead><tbody>']
    for i,r in enumerate(rows):
        c=cat(r); a=r['addr']
        ath=r['ath_sold'] if ytd else r['ath']; usd=r['usd_sold'] if ytd else r['usd']
        net=r['net']; hold=bal.get(a,0) if ytd else r['hold']; ntx=r['ntx']; d=dao.get(a,0)
        actv=act_ytd(r) if ytd else act_win(r)
        rc=' class="me"' if c=="you" else ''
        o.append(f'<tr{rc}><td class="num" data-sort="{i+1}">{i+1}</td><td class="w">{acct(a)}</td>'
            f'<td><span class="badge {c}">{CATLBL[c]}</span></td>'
            f'<td class="num" data-sort="{ath:.0f}">{fmt(ath)}</td>'
            f'<td class="num money" data-sort="{usd:.0f}">${fmt(usd)}</td>'
            f'<td class="num" data-sort="{hold:.0f}">{fmt(hold)}</td>'
            f'<td class="num" data-sort="{net:.0f}">{netfmt(net)}</td>'
            f'<td class="num" data-sort="{ntx}">{ntx}</td>'
            f'<td class="act">{esc(actv)}</td>{daocell(d)}</tr>')
    o.append('</tbody></table></div>'); return "\n".join(o)

# ---------- reactivity table ----------
def assess(r):
    if r['started_after_vis'] and r['react7_pct']>=60 and r['tot']>=20000:
        return ('hot','anticipatory exit — appeared after you loaded & sold right after you')
    if r['react7_pct']>=60:
        return ('warm','elevated: most volume sold just after your sells')
    if r['before3_pct']>=40:
        return ('warm','sold just BEFORE your sells (possible anticipation)')
    if not r['started_after_vis'] and r['first']< chart['visible']:
        return ('cool','independent — was already selling before your wallet was visible')
    return ('cool','independent / own schedule')
def react_table(rows):
    rows=sorted(rows,key=lambda r:(-r['react7_pct'],-r['tot']))
    o=['<div class="tw"><table>','<thead><tr>',
       '<th>Wallet</th><th>Category</th><th class="num" data-t="n">ATH sold</th>',
       '<th class="num" data-t="n">1st sell</th><th>Started after<br>you were visible?</th>',
       '<th class="num" data-t="n">% sold ≤7d<br>after your sell</th>',
       '<th class="num" data-t="n">% sold ≤14d<br>after your unlock</th>',
       '<th class="num" data-t="n">% sold ≤3d<br>before your sell</th>',
       '<th>Assessment</th></tr></thead><tbody>']
    for r in rows:
        a=r['addr']; c='dao' if r['dao']>=80 else 'market'
        lvl,txt=assess(r)
        def hot(v,t): return f'<td class="num {("hi" if v>=t else "")}" data-sort="{v:.0f}">{v:.0f}%</td>'
        o.append(f'<tr><td class="w">{acct(a)}</td>'
            f'<td><span class="badge {c}">{CATLBL[c]}</span></td>'
            f'<td class="num" data-sort="{r["tot"]:.0f}">{fmt(r["tot"])}</td>'
            f'<td class="num" data-sort="{r["first"]}">{dstr(r["first"])}</td>'
            f'<td class="ctr">{"✦ AFTER" if r["started_after_vis"] else "before"}</td>'
            f'{hot(r["react7_pct"],BASE7)}{hot(r["unlock14_pct"],50)}{hot(r["before3_pct"],40)}'
            f'<td class="as {lvl}">{esc(txt)}</td></tr>')
    o.append('</tbody></table></div>')
    return "\n".join(o)

# ---------- SVG timeline ----------
def svg_timeline(chart):
    dom0=1767225600; dom1=int(chart['latest'])  # Jan 1 2026 -> latest
    L,R,Tp,rh=210,24,46,30
    W=1120; rows=chart['series']; H=Tp+rh*len(rows)+30
    def x(ts): return L+(float(ts)-dom0)/(dom1-dom0)*(W-L-R)
    s=[f'<svg viewBox="0 0 {W} {H}" width="100%" preserveAspectRatio="xMidYMid meet" font-family="inherit">']
    # reactive bands: 7d after each user sell
    for u in chart['user_sells']:
        x0=x(u['ts']); x1=x(min(u['ts']+7*86400,dom1))
        s.append(f'<rect x="{x0:.1f}" y="{Tp-6}" width="{max(x1-x0,1):.1f}" height="{rh*len(rows)+6}" fill="#1f9d5710"/>')
    # month gridlines
    months=[(1767225600,'Jan'),(1769904000,'Feb'),(1772323200,'Mar'),(1775001600,'Apr'),(1777593600,'May'),(1780272000,'Jun')]
    for mts,ml in months:
        if mts<dom0 or mts>dom1: continue
        xx=x(mts); s.append(f'<line x1="{xx:.1f}" y1="{Tp-10}" x2="{xx:.1f}" y2="{Tp+rh*len(rows)}" stroke="#2a2f3a" stroke-width="1"/>')
        s.append(f'<text x="{xx+3:.1f}" y="{Tp-14}" fill="#9aa3b2" font-size="11">{ml}</text>')
    # unlock markers
    for u in chart['unlocks']:
        xx=x(u['ts']); s.append(f'<line x1="{xx:.1f}" y1="{Tp-10}" x2="{xx:.1f}" y2="{Tp+rh*len(rows)}" stroke="#e0a23d" stroke-width="1.5" stroke-dasharray="4 3"/>')
        s.append(f'<text x="{xx+3:.1f}" y="{Tp+rh*len(rows)+16}" fill="#e0a23d" font-size="10.5">unlock {fmt(u["amt"])}</text>')
    COL={'you':'#34c97a','bot':'#7c8597','dao':'#ff8b76','market':'#5b9dff',None:'#5b9dff'}
    maxath=max((p['ath'] for se in rows for p in se['pts']), default=1)
    for i,se in enumerate(rows):
        y=Tp+i*rh+rh/2
        nm=short(se['addr'])
        tag=' (YOU)' if se['is_user'] else ('' )
        lab=LBL.get(se['addr'],''); labtxt=(lab if (lab and lab!='YOU') else '')
        col=COL.get('you' if se['is_user'] else se['cls'],'#5b9dff')
        s.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="#20242e" stroke-width="1"/>')
        s.append(f'<text x="6" y="{y-2:.1f}" fill="{"#34c97a" if se["is_user"] else "#cfd6e2"}" font-size="11.5" font-weight="{700 if se["is_user"] else 500}">{nm}{tag}</text>')
        if labtxt: s.append(f'<text x="6" y="{y+10:.1f}" fill="#7a8persona" font-size="9">{esc(labtxt[:30])}</text>'.replace('#7a8persona','#788195'))
        for p in se['pts']:
            r=max(2.2,min(12,math.sqrt(p['ath']/maxath)*13))
            o=0.95 if se['is_user'] else 0.7
            s.append(f'<circle cx="{x(p["ts"]):.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{col}" fill-opacity="{o}" stroke="{col}" stroke-width="0.5"><title>{short(se["addr"])} — {dstr(p["ts"])} — {fmt(p["ath"])} ATH</title></circle>')
    s.append(f'<text x="{L}" y="{H-6}" fill="#9aa3b2" font-size="10.5">green bands = 7 days after each of your sells · dashed gold = your vesting unlocks · circle size ∝ ATH sold</text>')
    s.append('</svg>'); return "\n".join(s)

nonbot_after=[r for r in wrows if r['started_after_vis']]
hot=[r for r in wrows if assess(r)[0]=='hot']

CSS="""
:root{--bg:#0f1115;--card:#171a21;--card2:#1d212b;--line:#2a2f3a;--tx:#e7eaf0;--mut:#9aa3b2;--acc:#5b9dff;
--green:#34c97a;--greenbg:#11341f;--red:#e0533d;--redbg:#3a1a14;--blue:#3d7bd6;--bluebg:#13243f;--grey:#3a4150;--greybg:#20242e;--am:#ffcf5c;--gold:#e0a23d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1200px;margin:0 auto;padding:32px 22px 80px}
header.hd{border-bottom:1px solid var(--line);padding-bottom:22px}
h1{font-size:27px;margin:0 0 6px;letter-spacing:-.3px}h1 .ath{color:var(--am)}
.sub{color:var(--mut);font-size:13.5px}.sub code{color:var(--tx)}
.meta{display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:12px;font-size:13px;color:var(--mut)}.meta b{color:var(--tx);font-weight:600}
h2{font-size:19px;margin:34px 0 12px}h2 .n{color:var(--acc);font-variant-numeric:tabular-nums;margin-right:8px}
h3{font-size:15px;margin:18px 0 6px}
p{margin:10px 0}a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
code{font:12.5px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:#0c0e12;border:1px solid var(--line);border-radius:5px;padding:1px 5px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0 6px}
.c{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.c .k{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.5px}
.c .v{font-size:20px;font-weight:700;margin-top:4px;font-variant-numeric:tabular-nums}.c .v small{font-size:13px;color:var(--mut);font-weight:500}
.callout{border-radius:12px;padding:16px 18px;margin:16px 0;border:1px solid}
.callout.warn{background:#2a230f;border-color:#e0a23d55}.callout.warn h3{color:#ffcf5c;margin-top:0}
.callout.ok{background:var(--greenbg);border-color:#1f9d5755}.callout.ok h3{color:#5fd699;margin-top:0}
.badge{display:inline-block;font-size:11.5px;font-weight:600;padding:2px 9px;border-radius:20px;white-space:nowrap}
.badge.you{background:var(--greenbg);color:#5fd699;border:1px solid #1f9d5766}
.badge.bot{background:var(--greybg);color:#b6bdca;border:1px solid var(--grey)}
.badge.dao{background:var(--redbg);color:#ff9c87;border:1px solid #e0533d66}
.badge.market{background:var(--bluebg);color:#7db1f0;border:1px solid #3d7bd666}
.legend{display:flex;flex-wrap:wrap;gap:8px 14px;margin:8px 0;font-size:12.5px;color:var(--mut);align-items:center}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:12px;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:920px}
thead th{position:sticky;top:0;background:var(--card2);color:var(--mut);text-align:left;font-weight:600;padding:10px 11px;border-bottom:1px solid var(--line);cursor:pointer;white-space:nowrap;font-size:12px}
thead th.num{text-align:right}
tbody td{padding:9px 11px;border-bottom:1px solid #20242e;vertical-align:top}
tbody tr:hover{background:#161a22}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}td.money{color:#ffd98a}td.ctr{text-align:center}
td.w{white-space:nowrap}td.w .lbl{display:block;color:var(--mut);font-size:11px;margin-top:2px}
td.act{color:#c4ccd8;font-size:12px;min-width:240px}
tr.me{background:#11341f33}tr.me td{border-bottom-color:#1f9d5733}
td.d0{color:var(--mut)}td.d1{color:#ffb45c}td.d2{color:#ff8b76;font-weight:600}
td.hi{color:#ffcf5c;font-weight:700}
td.as{font-size:12px}td.as.hot{color:#ff8b76;font-weight:600}td.as.warm{color:#ffcf5c}td.as.cool{color:var(--mut)}
.chartbox{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 10px;margin:12px 0}
.foot{color:var(--mut);font-size:12.5px}.foot li{margin:4px 0}
hr{border:0;border-top:1px solid var(--line);margin:30px 0}.tag{font-size:11px;color:var(--mut)}
"""
JS="""document.querySelectorAll('table').forEach(t=>{t.querySelectorAll('thead th').forEach((th,ci)=>{th.addEventListener('click',()=>{
const tb=t.tBodies[0],rows=[...tb.rows];const num=th.dataset.t==='n';const asc=!(th.dataset.asc==='1');th.dataset.asc=asc?'1':'0';
rows.sort((a,b)=>{let x=a.cells[ci].dataset.sort??a.cells[ci].innerText,y=b.cells[ci].dataset.sort??b.cells[ci].innerText;
if(num){x=parseFloat(x)||0;y=parseFloat(y)||0;return asc?x-y:y-x}return asc?(''+x).localeCompare(y):(''+y).localeCompare(x)});
rows.forEach(r=>tb.appendChild(r));});});});"""

HTML=f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATH (AthenaDAO) — Wallet-Watching / Anticipatory-Selling Analysis</title>
<style>{CSS}</style></head><body><div class="wrap">

<header class="hd">
<h1><span class="ath">$ATH</span> (AthenaDAO) — Wallet-Watching &amp; Anticipatory-Selling Analysis</h1>
<div class="sub">Subject wallet <code>0xf0940b14e8a4bE798cD713A6807e95f47B769d9C</code> · Token <code>0xa4ffdf32…754739</code> (Ethereum)</div>
<div class="meta"><span>Period <b>2026-01-01 → 2026-06-18</b></span><span>Your wallet became visibly loaded <b>2026-02-20</b></span><span>100% on-chain + CoinGecko marks</span></div>
</header>

<div class="cards">
<div class="c"><div class="k">Your wallet "watchable" from</div><div class="v">Feb 20 <small>2026 unlock</small></div></div>
<div class="c"><div class="k">Non-bot selling after vs before</div><div class="v" style="color:#ffcf5c">≈1.9× <small>4.7k→9.2k/day</small></div></div>
<div class="c"><div class="k">Clear anticipatory exits</div><div class="v">1 <small>of 14 non-bot</small></div></div>
<div class="c"><div class="k">Block-level front-run / sandwich</div><div class="v" style="color:#5fd699">None</div></div>
<div class="c"><div class="k">Your sells (YTD)</div><div class="v">$25,004 <small>453K ATH</small></div></div>
</div>

<div class="callout warn">
<h3>Re-framed verdict: partial, confounded evidence of wallet-watching</h3>
<p style="margin:4px 0">Your tokens were locked in vesting until <b>2026-02-20</b>, so your wallet only became a <i>visible, loaded whale</i> on that date (and again at the May 27 unlock). After that point, <b>non-bot selling roughly doubled</b> (≈4,700 → 9,200 ATH/day). That is consistent with other holders de-risking once they could see a large seller — <b>but it is heavily confounded</b> by (a) your own sells adding visible supply/price pressure, and (b) a market falling −79%. At the individual level, <b>only one sizeable holder shows a clean "watching" pattern</b> — <code>0xd054ba91</code>, which had bought 46,914 ATH in March, sat on it, then dumped the entire bag <b>2 days after your May 27 unlock</b>. The other large sellers sold on their own schedules (several were active <i>before</i> your wallet was visible). There is still <b>no block-level front-running / sandwiching</b>.</p>
</div>

<h2><span class="n">1</span>When your wallet became "watchable"</h2>
<p>A wallet-watcher can only react once your address visibly holds sellable ATH. Your receipt history:</p>
<ul>
<li><b>2023-09-06</b> — received 315,553 ATH (original allocation), but <b>moved it into a vesting contract</b> days later and the DEX market <b>did not exist until Dec 2023</b> → no one could "sell ahead of you" then. (Your 7–14-day post-receipt check is therefore empty by construction.)</li>
<li><b>2026-02-20 20:24</b> — vesting claim of <b>333,333 ATH</b> lands in your wallet; you began selling <b>16 minutes later</b>. <i>This</i> is when your wallet became a visible whale.</li>
<li><b>2026-05-27 15:13</b> — second claim of <b>200,000 ATH</b> → a fresh visible "more supply incoming" signal.</li>
</ul>

<h2><span class="n">2</span>Did selling intensify once you were visible?</h2>
<p>Yes, measurably — but read the caveat. Excluding you and the arb/MM bots:</p>
<ul>
<li>Before Feb 20 (51 days): <b>4,702 ATH/day</b> of non-bot selling.</li>
<li>After Feb 20 (118 days): <b>9,155 ATH/day</b> — roughly <b>1.9×</b>.</li>
</ul>
<p class="tag">Caveat: your own sells are the largest single genuine supply this year, and the price fell from $0.171 to $0.036. Both independently push other holders to sell, so the doubling is <b>consistent with</b> wallet-watching but does not prove holders are literally monitoring <code>0xf0940b14</code>.</p>

<h2><span class="n">3</span>Who actually sold in reaction to you</h2>
<p>For every non-bot wallet that sold &gt;$1k, the share of its volume sold shortly <b>after</b> your sells / unlocks (and just <b>before</b> your sells). Baseline for a random seller ≈ <b>{BASE7}%</b> for the "≤7d after" column — values well above that are reactive.</p>
<div class="legend"><b style="color:var(--tx)">Legend:</b><span class="badge dao">DAO-allocation</span><span class="badge market">market</span>
<span style="margin-left:auto" class="tag">✦ AFTER = first sold only after your wallet was visible · click headers to sort</span></div>
{react_table(wrows)}
<div class="callout ok" style="background:#1a1f17;border-color:#3a4150">
<h3 style="color:#ff8b76">The one clean case — <code>0xd054ba913bf972f2563dff4b26dc383587ae7808</code></h3>
<p style="margin:4px 0">Bought <b>46,914 ATH on 2026-03-09</b> (via CoW), held it untouched for 11 weeks, then sold the <b>entire</b> position on <b>2026-05-29 — two days after your 200k vesting unlock</b> and four days after your May 25 sell. 100% of its sell volume sits in your post-sell/post-unlock window. It is a market buyer (not DAO-connected) and this is a single event, so timing alone isn't proof — but it is the textbook "saw the whale reload, rushed the exit" pattern.</p>
</div>

<h2><span class="n">4</span>Timeline — your sells &amp; unlocks vs. the largest other sellers</h2>
<p class="tag">Each row is a wallet; each circle a sell (size ∝ ATH). Green bands = the 7 days after each of your sells; gold dashed lines = your vesting unlocks. Look for rows whose circles cluster inside the green bands / just right of the gold lines.</p>
<div class="chartbox">{svg_timeline(chart)}</div>

<h2><span class="n">5</span>Provenance &amp; DAO/team connection (unchanged)</h2>
<ul>
<li>All 30M circulating ATH minted to genesis <code>0x4d754910…</code> → vesting/treasury contracts (Community 10M / Core &amp; Early Contributors 12M / Service Providers 8M; 70M unminted).</li>
<li><b>DAO/team-connected sellers:</b> you, <code>0xea80c984</code> (stealth daily CoW drip Jan→Mar, 99% DAO-origin — but it sold <i>before</i> you were visible, so not watching you), <code>0xd8a57177</code> &amp; <code>0x91e8b869</code> (consecutive-day dumps Mar 26–27, in a window when you were NOT selling), <code>0xf35c6c74</code> (still holds 64k).</li>
<li><b>Arb/MM bots</b> source ATH from the pools (hold 0) — mechanical, not watchers. <code>0xd054ba91</code> &amp; <code>0xd4a3a947</code> are market buyers.</li>
</ul>

<h2><span class="n">6</span>Table A — all wallets that sold &gt; $1,000 of ATH (YTD: Jan 1 → Jun 18)</h2>
<p class="tag">{len(fin)} wallets. Besides you: 26 arb/MM bots (1.17M ATH / ~$80K net-zero churn), 4 DAO-allocation insiders (165K / $12.3K), 10 market distributors (303K / $26.8K).</p>
{seller_table(fin, True)}

<h2><span class="n">7</span>Table B — wallets that sold &gt; $1,000 of ATH in the LAST 21 DAYS (May 28 → Jun 18)</h2>
<p class="tag">Only {len(win)} wallets cleared $1k in the trailing 3 weeks; no DAO-allocation wallet among them. The lone non-bot besides you is the anticipatory exit <code>0xd054ba91</code>.</p>
{seller_table(win, False)}

<hr>
<h2><span class="n">8</span>Notes &amp; caveats</h2>
<ul class="foot">
<li>¹ <b>USD sold</b> = realized proceeds at sale time (counter-asset × daily USD rate).</li>
<li>² <b>DAO-origin %</b> = share of all-time inbound ATH traceable (≤4 hops) to genesis/treasury/vesting.</li>
<li><b>"Watchable" baseline:</b> ~33% of the post-Feb-20 timeline lies within 7 days of one of your sells, so a random seller scores ~33% on the "≤7d after" metric; only values well above that indicate reaction.</li>
<li>Reactivity is correlation, not proof of monitoring; your own price impact + the −79% market are competing explanations.</li>
<li>EOA attribution via on-chain token sender with <code>tx.origin</code> fallback; CoW via <code>Trade</code>-event owner. Contract/router-routed sellers (e.g. <code>0x3980daa7</code>) can show inflated reactivity as an artifact and are flagged.</li>
</ul>
<p class="tag">Machine-readable data: ath_sellers_2026.csv · pipeline: README.md · this report: ATH_forensic_report.html</p>

</div><script>{JS}</script></body></html>"""
open('ATH_forensic_report.html','w').write(HTML)
print("wrote ATH_forensic_report.html", len(HTML),"bytes; series:",len(chart['series']),"react rows:",len(wrows))
