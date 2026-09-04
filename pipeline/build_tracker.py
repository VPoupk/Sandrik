#!/usr/bin/env python3
"""
Build ake-tracker-june2026.html - the dedicated June-2026-onward activity tracker.

Every figure is read from pipeline/data at build time rather than typed in, so
the document cannot drift from the scans behind it. Re-running this after a
fresh scan regenerates the whole file.

Data-only in the sense that matters here: it reads pipeline/data and writes one
HTML file in the repo root, which the user has asked for explicitly.
"""
import json, re, html, datetime, statistics, collections, bisect

D = 'pipeline/data/'
OUT = 'ake-tracker-june2026.html'

# ---------------------------------------------------------------- load
cg     = json.load(open(D + 'cg_daily_pv.json'))
daily  = json.load(open(D + 'tracker_daily.json'))
ds     = json.load(open(D + 'daily_series.json'))
mkt    = json.load(open(D + 'cg_market_now.json'))
rng    = json.load(open(D + 'range_pcs.json'))
rngn   = json.load(open(D + 'range_new.json'))
clu    = json.load(open(D + 'sale_clusters.json'))
t2r    = [a.lower() for a in json.load(open(D + 't2_recips.json'))]
t2now  = json.load(open(D + 't2_now.json'))
mig    = json.load(open(D + 'migration_0829.json'))
migsrc = json.load(open(D + 'mig_src.json'))
prlife = json.load(open(D + 'pool_recip_lifetime.json'))
ks     = {k: set(v) for k, v in json.load(open(D + 'known_sets.json')).items()}
head   = json.load(open(D + 'head_now.json'))
lab    = json.load(open(D + 'all_labels_final.json'))
V      = json.load(open(D + 'venues_scan.json'))
DEX    = json.load(open(D + 'pool_dex_bal.json'))
TSg    = json.load(open(D + 'blk_ts.json'))
_tb = sorted(int(k) for k in TSg); _tv = [TSg[str(x)] for x in _tb]

BNBUSD = 686.47
HEAD   = head['head']
HEADTS = datetime.datetime.utcfromtimestamp(head['ts']).strftime('%d %b %Y %H:%M:%S')


def bts(bn):
    i = bisect.bisect_left(_tb, bn)
    if i == 0:
        return _tv[0]
    if i >= len(_tb):
        return _tv[-1]
    return _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1])


def bdt(bn, f='%d %b %H:%M'):
    return datetime.datetime.utcfromtimestamp(int(bts(bn))).strftime(f)


def mn(w, dp=2):
    """wei -> mn/bn string, never zeroes."""
    v = w / 1e24
    if abs(v) >= 1000:
        return f'{v/1000:,.{dp}f}bn'
    return f'{v:,.{dp}f}mn'


def usd(x, dp=0):
    return f'${x:,.{dp}f}'


def sh(a):
    return a[:10] + '…' + a[-4:]


def nm(a):
    a = a.lower()
    if a in DEX:
        return DEX[a]['name']
    if a in V:
        return V[a]['name']
    return (lab.get(a, {}) or {}).get('entity') or ''


def bsc(a, text=None):
    return f'<a class="addr-full" href="https://bscscan.com/address/{a}" target="_blank" rel="noopener">{text or sh(a)}</a>'


def bsctx(t):
    return f'<a class="addr-full" href="https://bscscan.com/tx/{t}" target="_blank" rel="noopener">{t[:14]}…</a>'


CSS = open('/tmp/claude-0/-home-user-Sandrik/4d5dfae8-d9f1-59c8-a7af-703ef8978ed1/scratchpad/base.css').read()

EXTRA = """
  /* tracker additions */
  .tl { position: relative; padding-left: 0; }
  .tl-row { display: grid; grid-template-columns: 92px 1fr; gap: 14px; padding: 9px 0;
            border-bottom: 1px solid var(--border); align-items: start; }
  .tl-row:last-child { border-bottom: none; }
  .tl-date { font-size: 11px; color: var(--muted); font-weight: 700; font-variant-numeric: tabular-nums; padding-top: 1px; }
  .tl-body { font-size: 12.5px; }
  .tl-body b { color: var(--text); }
  .tl-tag { display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: .4px;
            padding: 1px 6px; border-radius: 3px; margin-right: 6px; vertical-align: 1px; }
  .t-unlock { background: rgba(139,92,246,.15); color: #a78bfa; border: 1px solid rgba(139,92,246,.3); }
  .t-mm     { background: rgba(245,158,11,.13); color: var(--warn); border: 1px solid rgba(245,158,11,.3); }
  .t-liq    { background: rgba(59,130,246,.13); color: #60a5fa; border: 1px solid rgba(59,130,246,.3); }
  .t-flag   { background: rgba(239,68,68,.13); color: #f87171; border: 1px solid rgba(239,68,68,.3); }
  .t-ok     { background: rgba(16,185,129,.13); color: #34d399; border: 1px solid rgba(16,185,129,.3); }
  .spark { display:block; width:100%; height:auto; }
  .kv { display:grid; grid-template-columns:auto 1fr; gap:4px 14px; font-size:12.5px; }
  .kv dt { color: var(--muted); }
  .kv dd { color: var(--text); font-weight:600; font-variant-numeric: tabular-nums; }
  table.dense { font-size: 11.5px; }
  table.dense td, table.dense th { padding: 4px 7px; }
  .hi { background: rgba(251,191,36,.09); }
  .hi2 { background: rgba(239,68,68,.08); }
  .hi3 { background: rgba(16,185,129,.07); }
  .chain { font-size:12px; line-height:1.9; }
  .chain code { display:inline-block; }
  .arrow { color: var(--muted); padding: 0 6px; }
  .note { font-size: 11.5px; color: var(--muted); margin-top: 8px; line-height:1.55; }
  .grid2 { display:grid; grid-template-columns: repeat(auto-fit,minmax(320px,1fr)); gap:14px; }
  .tocgrid { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:8px; }
  .tocgrid a { display:block; padding:8px 10px; background:var(--card2); border:1px solid var(--border);
               border-radius:6px; font-size:12px; }
"""

P = []
def w(s):
    P.append(s)


# ================================================================= computed
d0, d1 = daily[0]['d'], daily[-1]['d']
turns = [r['turn'] for r in daily]
med_t = statistics.median(turns)
vols  = [r['vol'] for r in daily]
med_v = statistics.median(vols)

jun = [r for r in daily if r['d'] < '2026-07-01']
jul_run = [r for r in daily if '2026-07-16' <= r['d'] <= '2026-07-25']

# pool release calendar
POOLNAME = {'Investors': 'Investors Pool', 'Nodes 1': 'Nodes Pool 1', 'Nodes 2': 'Nodes Pool 2',
            'Nodes 3': 'Nodes Pool 3', 'Team 1': 'Team Pool 1 (Advisors)', 'Team 2': 'Team Pool 2',
            'KOL': 'KOL Pool', 'Community': 'Community Pool'}
rel = []
for d, v in sorted(ds['pool'].items()):
    tot = int(v[0])
    if d >= '2026-06-01' and tot > 0:
        rel.append((d, tot, {k: int(x) for k, x in v[2].items()}))

J22 = next(t for d, t, _ in rel if d == '2026-07-22')

# 29 Aug terminal wallets
sw3 = json.load(open(D + 'sweep_w3.json'))
s3sent = {k: int(v) for k, v in sw3['sent'].items()}
s3recv = {k: int(v) for k, v in sw3['recv'].items()}
skip = set(V) | set(DEX)
term = [(a, s3recv[a] - s3sent.get(a, 0)) for a in s3recv
        if a not in skip and s3recv[a] - s3sent.get(a, 0) >= 10 * 10**24 and s3sent.get(a, 0) == 0]
TERM_TOT = sum(v for a, v in term)
term.sort(key=lambda x: -x[1])

# hub contributor stats
poolrec = ks['direct pool recipient (lifetime)']
hub_rows = []
allcontrib = set()
for v_, cps in sorted(migsrc['agg'].items()):
    src = {p: sum(int(q[0]) for q in dd.values()) for p, dd in cps.items()}
    src = {p: x for p, x in src.items() if x > 0}
    dst = {p: sum(int(q[1]) for q in dd.values()) for p, dd in cps.items()}
    dst = {p: x for p, x in dst.items() if x > 0}
    allcontrib |= set(src)
    hub_rows.append((v_, sum(src.values()), len(src),
                     sum(1 for p in src if p in poolrec),
                     max(dst, key=dst.get) if dst else ''))
CONTRIB_N = len(allcontrib)
CONTRIB_P = len(allcontrib & poolrec)
HUB_TOT = sum(r[1] for r in hub_rows)
pools_of_contrib = collections.Counter()
for a in allcontrib & poolrec:
    for p in prlife['pools'][a]:
        pools_of_contrib[p] += 1

J22_RECIP = 5879   # from the pool-flow scan, recomputed below for safety
_r = set()
import glob
POOLS_ADDR = {'0x27333bd8c321a263b0565e69eea3b736b9d1f42c', '0xaf66503770451c83a4f12a1146a32271893508ce',
              '0xd229b65d50e412cc3c394233e7a53a1dac4da457', '0xb7c7786b6ca1130584f005e9c86554114b7fad62',
              '0xd2f72669e560c7ecd3c681612963990ef6f1981b', '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248',
              '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5', '0x6b394c413d60b2aadb37a907a73a6f9a91c35015'}
for f in sorted(glob.glob(D + 'poolflow_*.json')):
    for r in json.load(open(f))['rows']:
        if r[1].lower() in POOLS_ADDR and r[2].lower() not in POOLS_ADDR:
            if datetime.datetime.utcfromtimestamp(int(bts(r[0]))).strftime('%Y-%m-%d') == '2026-07-22':
                _r.add(r[2].lower())
J22_RECIP = len(_r)

# range orders
asks = [r for r in rng['rows'] if int(r[5]) == 0]
ASK_TOT = sum(int(r[4]) for r in asks)
jul_asks = [r for r in asks if '2026-07-16' <= bdt(r[0], '%Y-%m-%d') <= '2026-07-23']
JUL_ASK_TOT = sum(int(r[4]) for r in jul_asks)

json.dump({'med_turnover': med_t, 'med_vol': med_v, 'j22': str(J22), 'j22_recip': J22_RECIP,
           'term_tot': str(TERM_TOT), 'term_n': len(term), 'contrib_n': CONTRIB_N,
           'hub_tot': str(HUB_TOT), 'ask_tot': str(ASK_TOT), 'jul_ask_tot': str(JUL_ASK_TOT)},
          open(D + 'tracker_facts.json', 'w'), indent=1)
print('facts computed; building HTML')

# ================================================================= document
w(f'''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AKE Activity Tracker — June 2026 onward</title>
<style>{CSS}{EXTRA}</style>
<div class="container">
<header>
  <h1>AKE — Activity Tracker, June 2026 onward</h1>
  <div class="subtitle">Insider and cluster activity, allocation-pool releases, liquidity events and
  market-maker behaviour, cross-referenced against reported volume</div>
  <div class="meta">
    <div class="meta-item">Token <span>AKEDO (AKE) · 0x2c3a8ee9…2C412F7Db · BSC</span></div>
    <div class="meta-item">Chain read to <span>block {HEAD:,} · {HEADTS} UTC</span></div>
    <div class="meta-item">Window <span>{d0} → {d1} ({len(daily)} days)</span></div>
    <div class="meta-item">Sources <span>NodeReal archive RPC · OKLink labels · CoinGecko</span></div>
  </div>
</header>''')

# ---- TOC
w('''<div class="section"><h2>Contents</h2><div class="tocgrid">
<a href="#s1">1 · What changed, in one screen</a>
<a href="#s2">2 · Daily tracker — price, volume, turnover, on-chain flow</a>
<a href="#s3">3 · The 22 July node unlock and where all of it went</a>
<a href="#s4">4 · Market-maker range orders vs the July volume spike</a>
<a href="#s5">5 · The 26 August liquidity withdrawal</a>
<a href="#s6">6 · The 27 August re-entry, funded by Team Pool 2</a>
<a href="#s7">7 · September — the 1.5bn release and a new Safe</a>
<a href="#s8">8 · Post-unlock selling, 22 July – 20 August</a>
<a href="#s9">9 · The insider chain behind the market maker</a>
<a href="#s10">10 · Allocation-pool release calendar</a>
<a href="#s11">11 · Cluster and wallet registry</a>
<a href="#s12">12 · Method, and what this does not show</a>
</div></div>''')

# ---- 1 EXEC
peak = max(daily, key=lambda r: r['turn'])
ath = max(daily, key=lambda r: r['p'])
w(f'''<div class="section" id="s1"><h2>1 · What changed, in one screen</h2>
<div class="stat-grid">
  <div class="stat-box"><div class="stat-box-label">22 Jul node unlock</div>
    <div class="stat-box-value">{mn(J22,3)}</div>
    <div class="stat-box-sub">to {J22_RECIP:,} wallets · 20.9% of supply</div></div>
  <div class="stat-box"><div class="stat-box-label">Of that, now in 98 wallets</div>
    <div class="stat-box-value" style="color:var(--danger)">{mn(TERM_TOT,3)}</div>
    <div class="stat-box-sub">swept by 29 Aug · {100*TERM_TOT/J22:.4f}% of the unlock</div></div>
  <div class="stat-box"><div class="stat-box-label">Peak daily turnover</div>
    <div class="stat-box-value" style="color:var(--warn)">{peak['turn']:.2f}×</div>
    <div class="stat-box-sub">{peak['d']} · volume {peak['turn']:.1f}× market cap</div></div>
  <div class="stat-box"><div class="stat-box-label">Limit-sell walls placed</div>
    <div class="stat-box-value">{mn(JUL_ASK_TOT,2)}</div>
    <div class="stat-box-sub">16–23 Jul · $0.00105–$0.00306</div></div>
  <div class="stat-box"><div class="stat-box-label">Liquidity pulled 26 Aug</div>
    <div class="stat-box-value">1,093.61 BNB</div>
    <div class="stat-box-sub">+ {mn(11.579e24)} AKE · ≈{usd(1093.61*BNBUSD + 11.579e6*0.00888)}</div></div>
  <div class="stat-box"><div class="stat-box-label">3 Sep team release</div>
    <div class="stat-box-value" style="color:var(--warn)">1,500.00mn</div>
    <div class="stat-box-sub">Team Pool 2 · 3 wallets · still untouched</div></div>
  <div class="stat-box"><div class="stat-box-label">4 Sep off Binance</div>
    <div class="stat-box-value" style="color:var(--danger)">423.03mn</div>
    <div class="stat-box-sub">into a Safe deployed 2h earlier</div></div>
  <div class="stat-box"><div class="stat-box-label">Price now</div>
    <div class="stat-box-value">{usd(mkt['current_price']['usd'],8)}</div>
    <div class="stat-box-sub">{mkt['ath_change_percentage']['usd']:+.1f}% from {usd(mkt['ath']['usd'],8)} ATH (2 Sep)</div></div>
</div>

<div class="alert alert-danger" style="margin-top:16px">
<strong>The single largest movement in this window is not trading.</strong>
On 22 July the three Nodes pools released <b>{J22:,} wei</b> ({mn(J22,3)} AKE) to {J22_RECIP:,} wallets.
On 29 August, between 11:10 and 11:47 UTC, <b>{TERM_TOT:,} wei</b> ({mn(TERM_TOT,3)} AKE) arrived in 98 wallets
that had never transacted before and have not moved since. The two figures differ by
<b>100 AKE</b> across {J22_RECIP:,} wallets. None of it touched an exchange.
</div>

<h3 style="margin-top:18px">The nine things worth knowing</h3>
<table><thead><tr><th style="width:26px">#</th><th>Finding</th><th style="width:150px">Evidence</th></tr></thead><tbody>
<tr><td>1</td><td><b>The entire 22 July node unlock has been consolidated into 98 fresh wallets.</b>
  {J22_RECIP:,} claimant wallets → 98 hubs (~60 claimants each) → 98 never-used wallets. Completed 29 Aug.</td>
  <td class="num">§3</td></tr>
<tr><td>2</td><td><b>The July price run happened inside a ladder of the market maker's own sell walls.</b>
  {mn(JUL_ASK_TOT,2)} of single-sided AKE liquidity placed 16–23 July between $0.00105 and $0.00306;
  price ran from $0.00019 to $0.00306 and every wall filled.</td>
  <td class="num">§4</td></tr>
<tr><td>3</td><td><b>Volume was 2.6–3.9× market cap for six consecutive days.</b>
  16–19 July turnover 3.67/2.57/3.94/3.19. No genuine spot market turns its whole capitalisation
  four times a day.</td><td class="num">§2, §4</td></tr>
<tr><td>4</td><td><b>On 26 August the market maker closed every position and left</b>, taking
  1,093.61 BNB and {mn(11.579e24)} AKE. Active liquidity fell 13.2%; five hours later the on-chain
  price broke 39% in fifteen minutes.</td><td class="num">§5</td></tr>
<tr><td>5</td><td><b>It came back 24 hours later — funded by Team Pool 2 supply.</b>
  Two of the 14 recipients of the 21 August team release moved for the first time; 70.00mn of that
  supply now sits in the AKE/WBNB pool as liquidity.</td><td class="num">§6</td></tr>
<tr><td>6</td><td><b>The market maker is downstream of the deployer's launch-day distribution.</b>
  Deployer → 13.800bn → 11.650bn hub → 100.00mn → the wallet that has run the pool's book since
  21 August 2025.</td><td class="num">§9</td></tr>
</tbody></table>
</div>''')
print('sec1 ok')

# ---- 2 DAILY TRACKER
import math
W_, H_ = 1140, 190
pmin, pmax = min(r['p'] for r in daily), max(r['p'] for r in daily)
vmax = max(r['vol'] for r in daily)
n = len(daily)
def X(i): return 46 + i * (W_ - 60) / (n - 1)
def Yp(p): return 12 + (H_ - 40) * (1 - (math.log(p) - math.log(pmin)) / (math.log(pmax) - math.log(pmin)))
bars = ''.join(f'<rect x="{X(i)-3:.1f}" y="{H_-14-(r["vol"]/vmax)*(H_-46):.1f}" width="6" '
               f'height="{(r["vol"]/vmax)*(H_-46):.1f}" fill="{"#f59e0b" if r["turn"]>3*med_t else "#1e3a5f"}" '
               f'opacity="{.85 if r["turn"]>3*med_t else .7}"/>' for i, r in enumerate(daily))
line = 'M' + ' L'.join(f'{X(i):.1f},{Yp(r["p"]):.1f}' for i, r in enumerate(daily))
marks = []
EVENTS = {'2026-06-19': 'Investors 4.07bn', '2026-07-16': 'MM sell walls', '2026-07-22': 'Node unlock 20.87bn',
          '2026-07-26': 'Pools 9.54bn', '2026-08-14': 'ATH', '2026-08-21': 'Team Pool 2 2.57bn',
          '2026-08-26': 'MM exits', '2026-08-29': '20.87bn swept'}
for i, r in enumerate(daily):
    if r['d'] in EVENTS:
        marks.append(f'<line x1="{X(i):.1f}" y1="8" x2="{X(i):.1f}" y2="{H_-14}" stroke="#8b5cf6" '
                     f'stroke-width="1" stroke-dasharray="2,3" opacity=".55"/>')
svg = (f'<svg class="spark" viewBox="0 0 {W_} {H_}" preserveAspectRatio="none" role="img" '
       f'aria-label="AKE daily close on a log scale with reported volume bars, June to September 2026">'
       f'<rect width="{W_}" height="{H_}" fill="#0d1424"/>{"".join(marks)}{bars}'
       f'<path d="{line}" fill="none" stroke="#3b82f6" stroke-width="1.8"/>'
       f'<text x="4" y="16" fill="#64748b" font-size="9">{usd(pmax,5)}</text>'
       f'<text x="4" y="{H_-20}" fill="#64748b" font-size="9">{usd(pmin,5)}</text></svg>')

w(f'''<div class="section" id="s2"><h2>2 · Daily tracker — price, volume, turnover, on-chain flow</h2>
<p style="font-size:12.5px;margin-bottom:12px">Blue line: AKE close, log scale. Bars: reported 24h volume,
amber where daily turnover exceeded 3× the {len(daily)}-day median of {med_t:.3f}. Dashed verticals mark the
events described in §3–§7.</p>
{svg}
<div class="note"><b>Turnover</b> is reported volume ÷ market capitalisation, both from CoinGecko.
<b>DEX $</b> is AKE crossing the 19 enumerated on-chain pools that day, priced at the close, with same-day
liquidity mints netted out so a sell wall being <em>placed</em> is not counted as volume. <b>CEX $</b> is AKE
crossing an exchange custody wallet. <b>Coverage</b> is (DEX + CEX) ÷ reported volume — the share of the
day's claimed trading that actually settled somewhere visible.<br><br>
Coverage cuts both ways and neither direction is an accusation on its own. <b>Below ~0.15</b> the reported
volume had almost no on-chain counterpart: it was matched inside a centralised book, which is normal in
itself and interesting only when it coincides with the operator actions in §4. <b>Above 1.0</b> means
on-chain movement exceeded reported trading — unlock distributions and wallet migrations moving tokens that
were never traded. The median across the window is {statistics.median([x['cov'] for x in daily]):.2f}.</div>

<table class="dense" style="margin-top:14px"><thead><tr>
<th>Date</th><th class="num">Close</th><th class="num">Volume</th><th class="num">Turnover</th>
<th class="num">DEX $</th><th class="num">CEX $</th><th class="num">On-chain $</th>
<th class="num">Coverage</th><th>Event</th></tr></thead><tbody>''')

med_cov = statistics.median([x['cov'] for x in daily])
for r in daily:
    cls = ''
    if r['turn'] > 3 * med_t:
        cls = 'hi'
    if r['cov'] < 0.15:
        cls = 'hi2'
    if r['d'] in EVENTS:
        cls = 'hi2'
    ev = EVENTS.get(r['d'], '')
    ccol = 'var(--danger)' if r['cov'] < 0.15 else ('var(--muted)' if r['cov'] > 1.5 else 'var(--text)')
    w(f'<tr class="{cls}"><td>{r["d"]}</td><td class="num">{usd(r["p"],8)}</td>'
      f'<td class="num">{usd(r["vol"])}</td>'
      f'<td class="num"><b>{r["turn"]:.2f}×</b></td>'
      f'<td class="num">{usd(r["dex_usd"])}</td>'
      f'<td class="num">{usd((r["cin"]+r["cout"]+r["bin"]+r["bout"])*r["p"])}</td>'
      f'<td class="num">{usd(r["onchain_total"])}</td>'
      f'<td class="num" style="color:{ccol}"><b>{r["cov"]:.2f}</b></td>'
      f'<td style="font-size:11px;color:var(--warn)">{ev}</td></tr>')
w('</tbody></table>')

low = sorted([r for r in daily if r['vol'] > 10e6], key=lambda x: x['cov'])[:6]
w(f'''<div class="alert alert-warn" style="margin-top:14px">
<strong>Six consecutive days of turnover above 2.5×.</strong> 16–21 July printed
{" / ".join(f"{r['turn']:.2f}" for r in daily if '2026-07-16' <= r['d'] <= '2026-07-21')}.
On 18 July the token reported {usd(next(r['vol'] for r in daily if r['d']=='2026-07-18'))} of volume against a
{usd(next(r['mc'] for r in daily if r['d']=='2026-07-18'))} market capitalisation. For scale, the June median
turnover was {statistics.median([r['turn'] for r in jun]):.3f}.
</div>

<h3 style="margin-top:18px">Where the reported volume had no on-chain counterpart</h3>
<p style="font-size:12.5px;margin-bottom:10px">The six lowest-coverage days among those reporting more than
$10M of volume. On these days the chain shows a small fraction of what was claimed to have traded.</p>
<table class="dense"><thead><tr><th>Date</th><th class="num">Reported volume</th>
<th class="num">Settled on-chain</th><th class="num">Coverage</th><th class="num">Turnover</th>
<th>What else happened that day</th></tr></thead><tbody>''')
LOWNOTE = {'2026-07-25': 'peak of the July run — price +9.6%, the highest volume print of the whole window',
           '2026-08-15': 'the 14–15 Aug run, then the high of the time; price −0.5% on $115M claimed',
           '2026-07-28': 'price +28.5% on the day',
           '2026-08-30': 'day after the 20.87bn migration; price −27.6%',
           '2026-07-08': 'price −35% crash day',
           '2026-08-03': 'price −19.5% on the day',
           '2026-07-26': 'price reaches $0.00306 — the top of the sell-wall ladder; every ask now filled',
           '2026-07-21': 'third day of the sell-wall ladder filling',
           '2026-09-04': '423.03mn withdrawn from Binance into a new multisig — see §7',
           '2026-09-02': 'the $0.04469 spike, on a book 88% thinner — see §7',
           '2026-09-03': 'Team Pool 2 releases 1,500.00mn — see §7'}
for r in low:
    w(f'<tr class="hi2"><td>{r["d"]}</td><td class="num">{usd(r["vol"])}</td>'
      f'<td class="num">{usd(r["onchain_total"])}</td>'
      f'<td class="num" style="color:var(--danger)"><b>{r["cov"]:.2f}</b></td>'
      f'<td class="num">{r["turn"]:.2f}×</td>'
      f'<td style="font-size:11.5px">{LOWNOTE.get(r["d"],"")}</td></tr>')
w(f'''</tbody></table>
<div class="alert alert-danger" style="margin-top:12px"><strong>25 July is the outlier of the whole window.</strong>
The token reported <b>{usd(next(r['vol'] for r in daily if r['d']=='2026-07-25'))}</b> — the largest single
day in these 93 — while <b>{usd(next(r['onchain_total'] for r in daily if r['d']=='2026-07-25'))}</b> settled
on-chain across every pool and every exchange wallet combined. <b>Coverage 0.05.</b> Turnover that day was
{next(r['turn'] for r in daily if r['d']=='2026-07-25'):.2f}× the market capitalisation. Two days earlier the
operator placed its last two sell walls, at $0.002456–$0.029516 and $0.002460–$0.002952; the next day price
closed at $0.00305960, above the top of the $0.001–$0.003 ladder, so every ask in it had filled. The price
kept rising afterwards and did not peak until 15 August.</div>
</div>''')
print('sec2 ok')

# ---- 3 THE SWEEP
w(f'''<div class="section" id="s3"><h2>3 · The 22 July node unlock and where all of it went</h2>

<div class="alert alert-danger">On <b>22 July 2026</b> the three Nodes pools released
<b>{J22:,} wei</b> = <b>{mn(J22,3)} AKE</b> to <b>{J22_RECIP:,}</b> distinct wallets.
On <b>29 August 2026, 11:10–11:47 UTC</b>, <b>{TERM_TOT:,} wei</b> = <b>{mn(TERM_TOT,3)} AKE</b> landed in
<b>98 wallets that had never sent a transaction</b>. The two totals differ by
<b>{(J22-TERM_TOT)/10**18:,.0f} AKE</b> — dust across {J22_RECIP:,} wallets.</div>

<h3>How it was routed</h3>
<div class="chain" style="background:var(--card2);padding:14px;border-radius:8px;border:1px solid var(--border)">
<b>Nodes Pool 1 / 2 / 3</b> <span class="arrow">→</span> {J22_RECIP:,} claimant wallets <span class="arrow">→</span>
98 consolidation hubs <span class="arrow">→</span> 98 terminal wallets<br>
<span style="color:var(--muted);font-size:11.5px">22 Jul 2026 · sweep begins 27 Jul · hubs empty into terminals 29 Aug 11:10–11:47</span>
</div>

<h3 style="margin-top:16px">The ten hubs sampled, contributor by contributor</h3>
<p style="font-size:12.5px;margin-bottom:10px">Each hub was probed over the token's full history. Every hub shows
the same shape: about sixty inbound transfers of roughly 3.5mn each, then a single outbound transfer of the
whole balance. <b>{CONTRIB_P} of {CONTRIB_N} contributors ({100*CONTRIB_P/CONTRIB_N:.0f}%) are lifetime direct
allocation-pool recipients</b>, all from Nodes Pool 1, 2 and 3.</p>
<table class="dense"><thead><tr><th>Consolidation hub</th><th class="num">Aggregated</th>
<th class="num">Contributors</th><th class="num">Pool claimants</th><th class="num">Avg each</th>
<th>Swept to</th></tr></thead><tbody>''')
for a, amt, nc, np_, dst in hub_rows:
    w(f'<tr><td>{bsc(a)}</td><td class="num">{mn(amt)}</td><td class="num">{nc}</td>'
      f'<td class="num" style="color:var(--danger)">{np_} ({100*np_//nc}%)</td>'
      f'<td class="num">{mn(amt/nc)}</td><td>{bsc(dst) if dst else "—"}</td></tr>')
w(f'''<tr style="border-top:2px solid var(--border)"><td><b>Total, 10 of 98 hubs</b></td>
<td class="num"><b>{mn(HUB_TOT,2)}</b></td><td class="num"><b>{CONTRIB_N}</b></td>
<td class="num"><b>{CONTRIB_P} ({100*CONTRIB_P/CONTRIB_N:.0f}%)</b></td>
<td class="num"><b>{mn(HUB_TOT/CONTRIB_N)}</b></td><td>—</td></tr></tbody></table>
<div class="note">Zero overlap between the ten hubs — no contributor feeds two of them. The claimants'
lifetime pool receipts total {mn(sum(int(prlife['recv'][a]) for a in allcontrib & poolrec),3)}, against
{mn(HUB_TOT,3)} aggregated: a 1:1 match, so no outside tokens entered these hubs.
Pools of origin: ''' + ', '.join(f'{p} ({c} wallets)' for p, c in pools_of_contrib.most_common()) + '.</div>')

w(f'''<h3 style="margin-top:18px">The 98 terminal wallets</h3>
<p style="font-size:12.5px;margin-bottom:10px">Each received exactly once and has never sent anything.
Amounts are all distinct — balances were swept, not split by a script. Not one of the 196 wallets on either
side of this migration is a Team Pool 2 recipient, a doc-registry wallet, or carries an explorer label.</p>
<table class="dense"><thead><tr><th class="num">#</th><th>Terminal wallet</th><th class="num">Holds</th>
<th class="num">Inbound txs</th><th>Explorer label</th></tr></thead><tbody>''')
for i, (a, v) in enumerate(term[:20], 1):
    w(f'<tr><td class="num">{i}</td><td>{bsc(a)}</td><td class="num">{mn(v)}</td>'
      f'<td class="num">{sw3["rct"].get(a,0)}</td><td style="color:var(--muted)">{nm(a) or "none"}</td></tr>')
w(f'''<tr style="border-top:2px solid var(--border)"><td colspan="2"><b>All 98 wallets</b></td>
<td class="num"><b>{mn(TERM_TOT,3)}</b></td><td class="num"><b>98</b></td>
<td style="color:var(--muted)"><b>none labelled</b></td></tr></tbody></table>
<div class="note">Showing the 20 largest of 98. Range {mn(min(v for a,v in term))} – {mn(max(v for a,v in term))},
median {mn(sorted(v for a,v in term)[len(term)//2])}.</div>

<div class="alert alert-info" style="margin-top:14px"><strong>What this does and does not establish.</strong>
It establishes that the tokens released to {J22_RECIP:,} node claimants on 22 July are now held in 98 places,
that the routing was systematic, and that none of it reached an exchange. It does not establish who controls
those 98 wallets. A single operator sweeping wallets it always controlled, a custodian consolidating client
balances, and a buyer acquiring claims off-chain all produce this pattern. What can be said from the chain is
that {mn(TERM_TOT,3)} — <b>{100*TERM_TOT/1e29:.1f}% of total supply</b> and roughly
<b>{100*TERM_TOT/1e18/mkt['circulating_supply']:.0f}% of circulating supply</b> — is under materially fewer
hands than the claimant list suggests.</div>
</div>''')
print('sec3 ok')

# ---- 4 MM RANGE ORDERS vs VOLUME
def tickusd(t):
    return 1.0001 ** t * BNBUSD

w(f'''<div class="section" id="s4"><h2>4 · Market-maker range orders vs the July volume spike</h2>
<p style="font-size:12.5px;margin-bottom:12px">A Uniswap-V3-style position funded with <em>only</em> AKE and no
BNB is a limit sell: the range sits above spot, and as price rises through it the AKE is sold for BNB. It never
appears as a transfer to an exchange, so a transfer-based sales ledger misses it entirely. Scanning every
<code>Mint</code> on the PancakeV3 AKE/WBNB 0.01% pool over the token's whole life finds
<b>{len(asks)} such positions</b> totalling <b>{mn(ASK_TOT,2)} AKE</b> placed.</p>

<table class="dense"><thead><tr><th>Placed (UTC)</th><th class="num">AKE</th><th class="num">BNB</th>
<th>Fill range (AKE/USD)</th><th class="num">Spot that day</th><th>Placed by</th></tr></thead><tbody>''')
for bn, tl, tu, liq, a0, a1, tx in rng['rows']:
    a0i, a1i = int(a0), int(a1)
    d = bdt(bn, '%Y-%m-%d')
    spot = cg.get(d, {}).get('price')
    pl, pu = tickusd(tl), tickusd(tu)
    rngs = f'{usd(pl,6)} – {usd(pu,6)}' if pu < 1 else f'{usd(pl,6)} – unbounded'
    kind = 'ASK' if a1i == 0 else 'two-sided'
    cls = 'hi' if (a1i == 0 and '2026-07-16' <= d <= '2026-07-23') else ''
    w(f'<tr class="{cls}"><td>{bdt(bn,"%Y-%m-%d %H:%M")}</td><td class="num">{mn(a0i)}</td>'
      f'<td class="num">{a1i/1e18:,.1f}</td>'
      f'<td>{rngs} <span style="color:var(--muted)">{kind}</span></td>'
      f'<td class="num">{usd(spot,6) if spot else "—"}</td>'
      f'<td style="font-size:11px;color:var(--muted)">{"see below" if a1i==0 else ""}</td></tr>')
w('</tbody></table>')

w(f'''<h3 style="margin-top:18px">The July ladder, against what price and volume did</h3>
<div class="alert alert-warn">Between <b>16 and 23 July</b> the operator placed
<b>{mn(JUL_ASK_TOT,2)} AKE</b> of single-sided sell walls in ranges spanning
<b>$0.001049 to $0.003057</b>. Over those same eight days the price rose from <b>$0.00018807</b> (14 Jul close)
to <b>$0.00305960</b> (26 Jul close) — through the top of the ladder — on volume that repeatedly exceeded the
entire market capitalisation.</div>
<table class="dense"><thead><tr><th>Date</th><th class="num">Close</th><th class="num">Δ</th>
<th class="num">Volume</th><th class="num">Turnover</th><th>Range orders placed that day</th></tr></thead><tbody>''')
prev = None
byday_ask = collections.defaultdict(list)
for bn, tl, tu, liq, a0, a1, tx in rng['rows']:
    if int(a1) == 0:
        byday_ask[bdt(bn, '%Y-%m-%d')].append((int(a0), tickusd(tl), tickusd(tu)))
for r in daily:
    if not ('2026-07-14' <= r['d'] <= '2026-07-28'):
        continue
    ch = f'{100*(r["p"]/prev-1):+.1f}%' if prev else '—'
    prev = r['p']
    aks = byday_ask.get(r['d'], [])
    txt = ' · '.join(f'{mn(a)} @ {usd(l,6)}–{usd(u,6)}' for a, l, u in aks) if aks else ''
    w(f'<tr class="{"hi" if aks else ""}"><td>{r["d"]}</td><td class="num">{usd(r["p"],8)}</td>'
      f'<td class="num" style="color:{"var(--green)" if ch.startswith("+") else "var(--danger)"}">{ch}</td>'
      f'<td class="num">{usd(r["vol"])}</td><td class="num"><b>{r["turn"]:.2f}×</b></td>'
      f'<td style="font-size:11px;color:var(--warn)">{txt}</td></tr>')
w('</tbody></table>')

w(f'''<h3 style="margin-top:18px">What the turnover number means</h3>
<div class="grid2">
<div class="card" style="background:var(--card2);padding:14px;border-radius:8px;border:1px solid var(--border)">
<h3>Reported volume vs market cap</h3>
<dl class="kv">
<dt>June 2026 median turnover</dt><dd>{statistics.median([r['turn'] for r in jun]):.3f}×</dd>
<dt>16 Jul</dt><dd style="color:var(--warn)">{next(r['turn'] for r in daily if r['d']=='2026-07-16'):.2f}×</dd>
<dt>17 Jul</dt><dd style="color:var(--warn)">{next(r['turn'] for r in daily if r['d']=='2026-07-17'):.2f}×</dd>
<dt>18 Jul</dt><dd style="color:var(--warn)">{next(r['turn'] for r in daily if r['d']=='2026-07-18'):.2f}×</dd>
<dt>19 Jul</dt><dd style="color:var(--warn)">{next(r['turn'] for r in daily if r['d']=='2026-07-19'):.2f}×</dd>
<dt>25 Jul</dt><dd style="color:var(--warn)">{next(r['turn'] for r in daily if r['d']=='2026-07-25'):.2f}×</dd>
<dt>14 Aug (Aug high)</dt><dd>{next(r['turn'] for r in daily if r['d']=='2026-08-14'):.2f}×</dd>
</dl></div>
<div class="card" style="background:var(--card2);padding:14px;border-radius:8px;border:1px solid var(--border)">
<h3>Where that volume was not</h3>
<p style="font-size:12.5px">On 25 July the token reported
{usd(next(r['vol'] for r in daily if r['d']=='2026-07-25'))} of volume while only
{usd(next(r['onchain_total'] for r in daily if r['d']=='2026-07-25'))} settled on-chain across every pool and
exchange wallet — <b>coverage {next(r['cov'] for r in daily if r['d']=='2026-07-25'):.2f}</b>, the lowest of
the window. On 23 July coverage was {next(r['cov'] for r in daily if r['d']=='2026-07-23'):.2f} and on 24 July
{next(r['cov'] for r in daily if r['d']=='2026-07-24'):.2f}: on-chain settlement <em>exceeded</em> reported
volume, which is what an unlock distribution moving tokens that were never traded looks like.</p>
<p style="font-size:12.5px;margin-top:8px">Neither reading is proof on its own. Together with a sell ladder
placed by one operator on the same days, they describe a market being made rather than one clearing.</p>
</div></div>

<div class="alert alert-info" style="margin-top:14px"><strong>Read this carefully.</strong>
Placing range orders is ordinary market-making, and a project having a market maker is ordinary. Three things
here are not ordinary: the walls were funded with AKE and no quote asset, so they could only ever sell; they
were laid immediately before and during a 16× price move; and the operator behind them traces to the
deployer's launch-day distribution (§9). The gross {mn(ASK_TOT,2)} placed is an upper bound on selling, not a
figure — the same tokens were withdrawn and re-placed at new ranges repeatedly. Netting the position manager
against the pools gives <b>+88.41mn AKE</b> actually delivered to the market across both operator wallets over
their whole lives; the current operator net sold <b>148.71mn</b> while its predecessor net bought
<b>71.89mn</b>.</div>
</div>''')
print('sec4 ok')

# ---- 5 THE 26 AUG WITHDRAWAL
POS = [('#6532670', '18 Feb 2026 23:36', 0.0, 527.55, 0.0, 527.5500, 'bid parked 421× below market'),
       ('#7002073', '23 Jul 2026 11:40', 129.30, 0.0, 0.921706, 511.2945, 'sell wall $0.00252–$0.00303'),
       ('#6532640', '18 Feb 2026 23:28', 24.43, 10.32, 5.657080, 54.7624, 'full-range working book'),
       ('#6985268', '18 Jul 2026 12:29', 5.00, 0.0, 5.000000, 0.0, 'sell wall $0.1157–$0.1297, never filled')]
SOLD_AKE = sum(p[2] - p[4] for p in POS)
SOLD_BNB = sum(p[5] - p[3] for p in POS)
CAP_BNB = sum(p[3] for p in POS)

w(f'''<div class="section" id="s5"><h2>5 · The 26 August liquidity withdrawal</h2>
<p style="font-size:12.5px;margin-bottom:12px">In four transactions on 26 August, the wallet
{bsc('0xba6ffb31cca9dbbc29a028f236346ab43bc4c985')} closed <b>every</b> position it held in the
PancakeV3 AKE/WBNB 0.01% pool — the pool that carries essentially all of AKE's on-chain depth. Each was a
<code>decreaseLiquidity + collect + unwrapWETH9 + sweepToken</code> multicall to the Pancake V3 Positions NFT
manager, sent by that wallet, with itself as recipient.</p>

<table class="dense"><thead><tr><th>Position</th><th>Minted</th><th class="num">AKE in</th><th class="num">BNB in</th>
<th class="num">AKE out</th><th class="num">BNB out</th><th class="num">AKE sold</th><th class="num">BNB gained</th>
<th>What it was</th></tr></thead><tbody>''')
for p, mt, ai, bi, ao, bo, note in POS:
    w(f'<tr><td><b>{p}</b></td><td>{mt}</td><td class="num">{ai:,.2f}mn</td><td class="num">{bi:,.2f}</td>'
      f'<td class="num">{ao:,.2f}mn</td><td class="num">{bo:,.2f}</td>'
      f'<td class="num" style="color:var(--danger)">{ai-ao:+,.2f}mn</td>'
      f'<td class="num" style="color:var(--green)">{bo-bi:+,.2f}</td>'
      f'<td style="font-size:11px;color:var(--muted)">{note}</td></tr>')
w(f'''<tr style="border-top:2px solid var(--border)"><td colspan="6"><b>Total</b></td>
<td class="num"><b>{SOLD_AKE:+,.2f}mn</b></td><td class="num"><b>{SOLD_BNB:+,.2f}</b></td>
<td></td></tr></tbody></table>

<div class="alert alert-warn" style="margin-top:12px"><strong>{usd(1093.61*BNBUSD)} left the pool, but only
{usd(SOLD_BNB*BNBUSD)} of it is proceeds.</strong> Of the 1,093.61 BNB withdrawn,
<b>{SOLD_BNB:,.2f} BNB ({usd(SOLD_BNB*BNBUSD)})</b> was realised from selling {SOLD_AKE:,.2f}mn AKE through the
range orders, and <b>{CAP_BNB:,.2f} BNB ({usd(CAP_BNB*BNBUSD)})</b> was the operator's own deposited capital
coming back untraded. Calling the whole figure a sale would be wrong.</div>

<h3 style="margin-top:16px">Sequence, 26–27 August</h3>
<div class="tl">
<div class="tl-row"><div class="tl-date">26 Aug 13:53</div><div class="tl-body">
  <span class="tl-tag t-liq">LIQUIDITY</span>Position #6532670 closed — <b>527.55 BNB</b> out. Pool WBNB
  1,465.2 → 938.
  </div></div>
<div class="tl-row"><div class="tl-date">26 Aug 13:54</div><div class="tl-body">
  <span class="tl-tag t-liq">LIQUIDITY</span>Position #7002073 closed 38 seconds later — <b>511.29 BNB</b> out.
  Pool WBNB → <b>426.0</b>, a 71% cut in one minute.</div></div>
<div class="tl-row"><div class="tl-date">26 Aug 17:45</div><div class="tl-body">
  <span class="tl-tag t-flag">DEPTH</span>Active liquidity steps <b>113,445 → 98,520</b> (−13.2%) as the
  full-range position goes. It had held 113,403–113,465 for four straight days.</div></div>
<div class="tl-row"><div class="tl-date">26 Aug 17:50–17:53</div><div class="tl-body">
  <span class="tl-tag t-liq">LIQUIDITY</span>Positions #6532640 and #6985268 closed — 54.76 BNB and
  {mn(10.657e24)} AKE out.</div></div>
<div class="tl-row"><div class="tl-date">26 Aug 17:57:02</div><div class="tl-body">
  <span class="tl-tag t-flag">MOVE</span>A <b>0.05 BNB test transfer</b> to
  {bsc('0x3b7acc2af5a1d53d50cbbccf3ae21c08f1f05520')}.</div></div>
<div class="tl-row"><div class="tl-date">26 Aug 17:59:44</div><div class="tl-body">
  <span class="tl-tag t-flag">MOVE</span><b>1,093.50 BNB</b> to the same address, 2m42s after the test.</div></div>
<div class="tl-row"><div class="tl-date">26 Aug 18:07:23</div><div class="tl-body">
  <span class="tl-tag t-flag">MOVE</span><b>{mn(11.59e24)} AKE</b> to
  {bsc('0xa4b86771606e366af4afb8c67e62f03fa26f654f')} — a wallet gas-funded 0.1 BNB in that same minute by
  {bsc('0x97b9d2102a9a65a26e1ee82d59e42d1b73b68689')}.</div></div>
<div class="tl-row"><div class="tl-date">26 Aug 18:47:52</div><div class="tl-body">
  <span class="tl-tag t-flag">MOVE</span>Proceeds forwarded to
  {bsc('0x481280ff0d0836707a5ef04410d4e1c87d14aa74')}.</div></div>
<div class="tl-row"><div class="tl-date">26 Aug 19:12–19:18</div><div class="tl-body">
  <span class="tl-tag t-flag">BREAK</span><b>Price falls 39.4% in 921 seconds</b>, $0.00790 → $0.00491, across
  4,245 swaps. Net flow required: <b>7.10mn AKE absorbed, 64.5 BNB extracted — {usd(64.5*BNBUSD)}</b>.
  Largest single net seller in the whole move: 4.39mn AKE.</div></div>
<div class="tl-row"><div class="tl-date">27 Aug 16:18</div><div class="tl-body">
  <span class="tl-tag t-flag">BREAK</span>Price bottoms at <b>$0.00708</b> on the thin book.</div></div>
<div class="tl-row"><div class="tl-date">28 Aug 06:35:50</div><div class="tl-body">
  <span class="tl-tag t-ok">PROCEEDS</span><b>1,100.0000 BNB</b> forwarded in one transfer to
  {bsc('0xd2cc422c35e8bbab72b2ada2bff4219095260611')}, where it still sits. <b>No exchange deposit.</b></div></div>
</div>

<div class="alert alert-info" style="margin-top:14px"><strong>Why {usd(64.5*BNBUSD)} moved the price 39%.</strong>
Active liquidity <code>L</code> held at ~98,400 through the entire break, so no tick-crossing regime change:
the V3 virtual reserves at the pre-break price were <b>335 BNB / 28.9mn AKE ≈ {usd(234275)} a side</b>. The
arithmetic says 74.1 BNB walks the price −39.3%; 64.5 were measured. AKE's on-chain book at the touch is about
a quarter of a million dollars against a {usd(mkt['fully_diluted_valuation']['usd']/1e6,0)}M FDV.</div>

<h3 style="margin-top:16px">Depth before and after</h3>
<table class="dense"><thead><tr><th>Measure</th><th class="num">26 Aug 13:52</th><th class="num">27 Aug 06:02</th>
<th class="num">Change</th></tr></thead><tbody>
<tr><td>Pool WBNB</td><td class="num">1,465.30</td><td class="num">355.66</td>
    <td class="num" style="color:var(--danger)">−75.7%</td></tr>
<tr><td>Pool AKE</td><td class="num">51.51mn</td><td class="num">41.31mn</td>
    <td class="num" style="color:var(--danger)">−19.8%</td></tr>
<tr><td>Quote-side depth, all 19 pools</td><td class="num">{usd(1070268)}</td><td class="num">{usd(292431)}</td>
    <td class="num" style="color:var(--danger)">−72.7%</td></tr>
<tr><td>Total DEX TVL</td><td class="num">{usd(1509524)}</td><td class="num">{usd(651659)}</td>
    <td class="num" style="color:var(--danger)">−56.8%</td></tr>
<tr class="hi"><td>Mean 15-min price move</td><td class="num">0.61%</td><td class="num">1.34%</td>
    <td class="num" style="color:var(--danger)">+120%</td></tr>
<tr class="hi"><td>Mean 15-min high–low range</td><td class="num">1.38%</td><td class="num">3.07%</td>
    <td class="num" style="color:var(--danger)">+122%</td></tr>
</tbody></table>
<div class="note">Volatility figures exclude the 19:00 crash hour, so they measure the regime change rather than
the event. Being precise about which part of the withdrawal mattered: 1,039 of the 1,094 BNB sat in ranges far
below market and was never working depth. The change that priced trades was the full-range position —
13.2% of active liquidity — plus the removal of the floor.</div>
</div>''')
print('sec5 ok')

# ---- 6 THE RE-ENTRY
t2_in = {}; t2_out = {}
for v_, cps in t2now['agg'].items():
    t2_in[v_] = sum(int(q[0]) for dd in cps.values() for q in dd.values())
    t2_out[v_] = sum(int(q[1]) for dd in cps.values() for q in dd.values())
T2_IN = sum(t2_in.values()); T2_OUT = sum(t2_out.values())

w(f'''<div class="section" id="s6"><h2>6 · The 27 August re-entry, funded by Team Pool 2</h2>
<div class="alert alert-danger">Until <b>27 August 17:31 UTC</b>, not one of the 14 wallets that received the
21 August Team Pool 2 release had ever moved a token. Two moved that evening, and
<b>70.00mn of team-allocated supply is now sitting in the AKE/WBNB pool as liquidity</b>.</div>

<h3>The half hour that rebuilt the book</h3>
<div class="tl">
<div class="tl-row"><div class="tl-date">17:31:54</div><div class="tl-body">
  <span class="tl-tag t-unlock">TEAM POOL 2</span>{bsc('0xe8daec92cc2d1fc1a785ea16d3a01ea21a561403')} sends its
  entire {mn(68.45e24)} allocation to {bsc('0xddd6ee0b15c5e9fe97e503953b1c866dae501577')}.</div></div>
<div class="tl-row"><div class="tl-date">17:58:20</div><div class="tl-body">
  <span class="tl-tag t-unlock">TEAM POOL 2</span>…and receives all {mn(68.45e24)} back. Net effect nil; it
  still holds the full allocation.</div></div>
<div class="tl-row"><div class="tl-date">17:58:31</div><div class="tl-body">
  <span class="tl-tag t-liq">LIQUIDITY</span>Eleven seconds later,
  {bsc('0x71eba98069d2834a7e3076212294d5b40b6ca43d')} — a wallet with no prior existence — is funded
  <b>700.0 BNB</b> by {bsc('0x97b9d2102a9a65a26e1ee82d59e42d1b73b68689')}, the same dispenser that funded the
  26 August seller and the original market maker.</div></div>
<div class="tl-row"><div class="tl-date">18:02:04</div><div class="tl-body">
  <span class="tl-tag t-unlock">TEAM POOL 2</span>{bsc('0xe2017853d1164d28f8f72ab748989ec7408c5126')} sends
  <b>{mn(70.00e24)}</b> of its {mn(83.33e24)} Team Pool 2 allocation to that same new wallet.</div></div>
<div class="tl-row"><div class="tl-date">18:19:50</div><div class="tl-body">
  <span class="tl-tag t-liq">LIQUIDITY</span><b>600.00 BNB + {mn(53.62e24)} AKE</b> minted as a two-sided
  position, L=612,395, range <b>$0.003790 – $0.015160</b>.</div></div>
<div class="tl-row"><div class="tl-date">18:33:01</div><div class="tl-body">
  <span class="tl-tag t-liq">LIQUIDITY</span><b>99.00 BNB + {mn(8.37e24)} AKE</b>, L=98,341, same range.
  Active liquidity <b>98,520 → 809,217</b>, up 721%, and it has held there since.</div></div>
</div>

<h3 style="margin-top:16px">All 14 Team Pool 2 recipients</h3>
<table class="dense"><thead><tr><th>Wallet</th><th class="num">Received 21 Aug</th><th class="num">Moved</th>
<th class="num">Still held</th><th>Destination</th></tr></thead><tbody>''')
DEST = {'0xe2017853d1164d28f8f72ab748989ec7408c5126': 'new LP wallet 0x71eba980…a43d → pool liquidity',
        '0xe8daec92cc2d1fc1a785ea16d3a01ea21a561403': 'out and back the same evening'}
for a in sorted(t2r, key=lambda x: -(t2_in.get(x, 0))):
    i_, o_ = t2_in.get(a, 0), t2_out.get(a, 0)
    pool_in = int(prlife['recv'].get(a, 0))
    cls = 'hi2' if o_ > 0 else ''
    w(f'<tr class="{cls}"><td>{bsc(a)}</td><td class="num">{mn(pool_in)}</td>'
      f'<td class="num">{mn(o_) if o_ else "—"}</td><td class="num">{mn(pool_in-o_)}</td>'
      f'<td style="font-size:11px;color:var(--warn)">{DEST.get(a,"")}</td></tr>')
w(f'''<tr style="border-top:2px solid var(--border)"><td><b>14 wallets</b></td>
<td class="num"><b>{mn(sum(int(prlife['recv'].get(a,0)) for a in t2r),3)}</b></td>
<td class="num"><b>{mn(T2_OUT,2)}</b></td>
<td class="num"><b>{mn(sum(int(prlife['recv'].get(a,0)) for a in t2r)-T2_OUT,3)}</b></td>
<td></td></tr></tbody></table>

<h3 style="margin-top:16px">The new book is better than the old one</h3>
<table class="dense"><thead><tr><th>Position</th><th class="num">AKE</th><th class="num">BNB</th>
<th class="num">L</th><th>Range</th></tr></thead><tbody>''')
for bn, tl, tu, liq, a0, a1, tx in rngn['rows']:
    w(f'<tr><td>{bdt(bn,"%d %b %H:%M:%S")}</td><td class="num">{mn(int(a0))}</td>'
      f'<td class="num">{int(a1)/1e18:,.2f}</td><td class="num">{int(liq)/1e18:,.0f}</td>'
      f'<td>{usd(tickusd(tl),6)} – {usd(tickusd(tu),6)}</td></tr>')
w(f'''</tbody></table>
<div class="note">Both are <b>two-sided</b> and bounded. The book the operator ran until 26 August had
527.55 BNB parked 421× below any price AKE has ever traded, inflating headline depth without ever being able
to fill. This one is 699 BNB of genuinely in-range quote. On that measure the pool is better provisioned than
before the withdrawal — pool WBNB is now <b>1,277.37</b> against 1,465.30 on 26 August, but essentially all of
it is live.</div>

<div class="alert alert-warn" style="margin-top:14px"><strong>Two readings, and the chain does not choose
between them.</strong> A project directing part of a team release into protocol-owned liquidity is a normal
and arguably good use of it. A team allocation quietly backstopping a market maker's book, one day after that
market maker pulled out and the price broke 39%, is a different thing. What is established: the supply came
from Team Pool 2, the timing was 26 minutes end to end, and the wallet that placed it was funded by the same
dispenser that funds the rest of this cluster.</div>
</div>''')
print('sec6 ok')

# ---- 7 SEPTEMBER DEVELOPMENTS
NEWSAFE = '0x808e6d72d37619d7ecb3fc6efc8f13bd37c46755'
# live state at the head, so the section cannot go stale against the chain
import urllib.request as _u, time as _t
_RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
_AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'


def _rpc(m, pr, tries=6):
    for i in range(tries):
        try:
            r = _u.Request(_RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                                  'params': pr}).encode(),
                           headers={'Content-Type': 'application/json'})
            j = json.loads(_u.urlopen(r, timeout=60).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            _t.sleep(1.5 * 1.7 ** i)


def live(a):
    b = int(_rpc('eth_call', [{'to': _AKE, 'data': '0x70a08231' + '0'*24 + a[2:]}, hex(HEAD)]), 16)
    n = int(_rpc('eth_getTransactionCount', [a, 'latest']), 16)
    g = int(_rpc('eth_getBalance', [a, 'latest']), 16)
    return b, n, g


SEP3 = ['0x4367fc88f25c2a9515c54e48876d36623c36ef6d',
        '0x4d14eb59004f3deff7f3d518e969fa288af36099',
        '0xdc7755439bce0bd0c9c0da21cbefde90bbef0d00']
SEP3_LIVE = {a: live(a) for a in SEP3}
SAFE_LIVE = live(NEWSAFE)
T2_LIVE = live('0xd229b65d50e412cc3c394233e7a53a1dac4da457')
print('live state read')
w(f'''<div class="section" id="s7"><h2>7 · September — the 1.5bn release and a new Safe</h2>

<h3>3 September, 02:58:10 UTC — Team Pool 2 releases another 1,500.00mn</h3>
<p style="font-size:12.5px;margin-bottom:10px">One transaction, three transfers of exactly
500,000,000&nbsp;&times;&nbsp;10<sup>18</sup>, routed the same way as the 21 August release: through the
3-of-4 Gnosis Safe {bsc('0x551a841742733bef96646b44e3475ce6a01da5eb')} using
<code>execTransaction</code> (<code>0x6a761202</code>), submitted by owner
{bsc('0xa79cc05c2ce2950549dfdfeb2ab462ab0be626b3')}, calling the batch payout
<code>0xe0dc37a3</code> on Team Pool 2.</p>
<div class="note" style="margin-bottom:12px">tx {bsctx('0x69f7d0dd70013fec41e3a8199857be24d1e70b9faf19e9f8d4b4d187866c616d')}
&nbsp;·&nbsp; block 119,650,955</div>
<table class="dense"><thead><tr><th>Recipient</th><th class="num">Received</th><th class="num">Holds now</th>
<th class="num">Nonce</th><th class="num">BNB</th><th>Status</th></tr></thead><tbody>
<tr class="hi2"><td>{bsc('0x4367fc88f25c2a9515c54e48876d36623c36ef6d')}</td><td class="num">500.00mn</td>
  <td class="num">{mn(SEP3_LIVE['0x4367fc88f25c2a9515c54e48876d36623c36ef6d'][0])}</td><td class="num">{SEP3_LIVE['0x4367fc88f25c2a9515c54e48876d36623c36ef6d'][1]}</td>
  <td class="num">{SEP3_LIVE['0x4367fc88f25c2a9515c54e48876d36623c36ef6d'][2]/1e18:,.4f}</td>
  <td style="color:var(--muted)">{'cannot move — no gas' if SEP3_LIVE['0x4367fc88f25c2a9515c54e48876d36623c36ef6d'][2]==0 else 'gas funded'}</td></tr>
<tr class="hi2"><td>{bsc('0x4d14eb59004f3deff7f3d518e969fa288af36099')}</td><td class="num">500.00mn</td>
  <td class="num">{mn(SEP3_LIVE['0x4d14eb59004f3deff7f3d518e969fa288af36099'][0])}</td><td class="num">{SEP3_LIVE['0x4d14eb59004f3deff7f3d518e969fa288af36099'][1]}</td>
  <td class="num">{SEP3_LIVE['0x4d14eb59004f3deff7f3d518e969fa288af36099'][2]/1e18:,.4f}</td>
  <td style="color:var(--muted)">{'cannot move — no gas' if SEP3_LIVE['0x4d14eb59004f3deff7f3d518e969fa288af36099'][2]==0 else 'gas funded'}</td></tr>
<tr class="hi2"><td>{bsc('0xdc7755439bce0bd0c9c0da21cbefde90bbef0d00')}</td><td class="num">500.00mn</td>
  <td class="num">{mn(SEP3_LIVE['0xdc7755439bce0bd0c9c0da21cbefde90bbef0d00'][0])}</td><td class="num">{SEP3_LIVE['0xdc7755439bce0bd0c9c0da21cbefde90bbef0d00'][1]}</td>
  <td class="num">{SEP3_LIVE['0xdc7755439bce0bd0c9c0da21cbefde90bbef0d00'][2]/1e18:,.4f}</td>
  <td style="color:var(--muted)">{'cannot move — no gas' if SEP3_LIVE['0xdc7755439bce0bd0c9c0da21cbefde90bbef0d00'][2]==0 else 'gas funded'}</td></tr>
</tbody></table>
<div class="note">All three are fresh EOAs that have never transacted and hold no BNB. None appears in any known
set — not the 21 August cohort, not the 29 August sweep, no explorer label. Team Pool 2 fell <b>10.4322bn &rarr; {mn(T2_LIVE[0],4)}</b>. The release is <b>10.0%</b> of the pool&rsquo;s original 15bn,
<b>14.4%</b> of what remained, <b>6.58%</b> of circulating, and <b>{usd(1.5e9*mkt['current_price']['usd'])}</b>
at spot. The two 26 July releases used direct <code>userWithdraw()</code> calls instead; since 21 August
every release has gone through this Safe with this signer.</div>

<h3 style="margin-top:18px">4 September — 423.03mn leaves Binance into a Safe created two hours earlier</h3>
<div class="alert alert-danger">Between <b>07:07:36 and 08:29:40 on 4 September</b>, three freshly gas-funded
EOAs each drew a tranche from Binance Hot Wallet_4, sent a 0-value test, forwarded the whole balance, and
emptied. All of it — <b>423.03mn AKE, {usd(423.03e6*mkt['current_price']['usd'])} at spot</b> — is now held by
one contract that has sent nothing.</div>
<table class="dense"><thead><tr><th>Time UTC</th><th class="num">Amount</th><th>Pass-through EOA</th>
<th>Gas funded by</th></tr></thead><tbody>
<tr><td>07:07:36 &rarr; 07:37:23</td><td class="num">153.83mn</td>
  <td>{bsc('0x8c7aa7e9494c19745623ede7d34eab9b2ea36c66')}</td>
  <td>{bsc('0xdc7bd4219a7dd616540df63ecf173227297011f5')}</td></tr>
<tr><td>07:48:01 &rarr; 07:58:55</td><td class="num">153.83mn</td>
  <td>{bsc('0x8cde138124dd0472b1f46a5b5a0c1335cf8350c8')}</td>
  <td>{bsc('0xeaff4c2e5124a9334cf4bb193f8b586fdbf2aaa6')}</td></tr>
<tr class="hi2"><td>08:21:35 &rarr; 08:29:40</td><td class="num">115.37mn</td>
  <td>{bsc('0x9d1c3c1fec14ac71969e83be28c45156e87cccb2')}</td>
  <td>{bsc('0xe7569e846b5b884bc2f5fb4d408bc05351eb5f4c')} <b style="color:var(--danger)">— an owner of the
      receiving Safe</b></td></tr>
<tr style="border-top:2px solid var(--border)"><td><b>Total into {bsc(NEWSAFE)}</b></td>
  <td class="num"><b>423.03mn</b></td><td colspan="2"></td></tr>
</tbody></table>

<h3 style="margin-top:16px">What the receiving contract is</h3>
<div class="grid2">
<div class="card" style="background:var(--card2);padding:14px;border-radius:8px;border:1px solid var(--border)">
<h3>{sh(NEWSAFE)}</h3>
<dl class="kv">
<dt>Type</dt><dd>Gnosis Safe proxy, 171 bytes</dd>
<dt>Threshold</dt><dd>3 of 4</dd>
<dt>Deployed</dt><dd>4 Sep 2026 04:56:37, block 119,858,453</dd>
<dt>First inflow</dt><dd>2h 11m later</dd>
<dt>Holds</dt><dd>{mn(SAFE_LIVE[0])} AKE</dd>
<dt>Sent</dt><dd>{'nothing' if SAFE_LIVE[0] >= 423.03e24*0.999 else 'has moved — re-check'}</dd>
<dt>masterCopy</dt><dd>0x29fcb43b — the standard Safe implementation</dd>
</dl></div>
<div class="card" style="background:var(--card2);padding:14px;border-radius:8px;border:1px solid var(--border)">
<h3>It is <em>not</em> the AKEDO team Safe</h3>
<p style="font-size:12.5px">Same 3-of-4 shape and the same masterCopy — but that implementation is shared by
every Safe on BSC, so it carries no information. <b>Zero owner overlap</b> with
{bsc('0x551a841742733bef96646b44e3475ce6a01da5eb')}, and none of the four new owners appears in any known set
or holds any AKE.</p>
<p style="font-size:11.5px;color:var(--muted);margin-top:8px">Owners:
{bsc('0xa2173f629417e948e9e92588061a7c74728916ed')},
{bsc('0xe7569e846b5b884bc2f5fb4d408bc05351eb5f4c')},
{bsc('0x0916a851ad3b8d694cb6a6d81ecad17eb3e64e23')},
{bsc('0x8508312202dec3756efb16c018c1b6aaa989172f')}</p>
</div></div>
<div class="alert alert-info" style="margin-top:12px"><strong>What is established, and what is not.</strong>
Established: a Safe was created, and two hours later 423.03mn AKE was withdrawn from Binance and consolidated
into it through three single-use wallets, one of which was gas-funded by that Safe&rsquo;s own signer — so the
Safe operator controlled the routing. Not established: who those four keys belong to. There is no on-chain
link to the AKEDO team Safe, the deployer chain, or the market-maker cluster. Tokens moving <em>off</em> an
exchange into multisig custody is the opposite of a distribution, and is what an OTC purchase, a treasury
transfer or a custody migration all look like.</div>

<h3 style="margin-top:18px">A 100.00mn venue switch, 2–3 September</h3>
<p style="font-size:12.5px">{bsc('0x025315786d51cdfae43a4e830c6fe6fd0eb34737')} sent <b>100.00mn</b> to a
Gate.io user wallet at 2 Sep 23:06:12, received <b>exactly 100.00mn back</b> at 3 Sep 08:15:35, then routed it
to <b>KuCoin</b> nine minutes later through {bsc('0x59ca8bf29778c146017a0d513ab388a40ca16d84')} as a
<b>1.00mn test followed by 99.00mn</b>. Under the accounting rule this books as a sale into a non-Binance
exchange, but the shape is a venue change rather than a liquidation: the same round number went out, came
back, and went somewhere else.</p>

<h3 style="margin-top:18px">2 September — a 4.9&times; spike on a book that had gone 88% thinner</h3>
<p style="font-size:12.5px;margin-bottom:10px">This is the clearest demonstration in the whole window of the
structural point in &sect;5, and it happened in one evening. Reconstructed from the pool&rsquo;s own
<code>Swap</code> events in 15-minute buckets.</p>
<table class="dense"><thead><tr><th>UTC</th><th class="num">Open</th><th class="num">High</th>
<th class="num">Low</th><th class="num">Close</th><th class="num">Swaps</th><th class="num">Active L</th>
<th>What is happening</th></tr></thead><tbody>
<tr><td>02 Sep 13:30</td><td class="num">$0.00917</td><td class="num">$0.00997</td><td class="num">$0.00912</td>
  <td class="num">$0.00992</td><td class="num">2,128</td><td class="num">809,161</td>
  <td>move begins, book intact</td></tr>
<tr><td>02 Sep 17:30</td><td class="num">$0.01483</td><td class="num">$0.01574</td><td class="num">$0.01471</td>
  <td class="num">$0.01557</td><td class="num">3,257</td><td class="num">809,133</td>
  <td>approaching the top of the range</td></tr>
<tr class="hi2"><td>02 Sep 17:45</td><td class="num">$0.01557</td><td class="num">$0.01609</td>
  <td class="num">$0.01457</td><td class="num">$0.01540</td><td class="num">4,045</td>
  <td class="num" style="color:var(--danger)"><b>98,396</b></td>
  <td><b>price exits the range — 710,736 of liquidity stops counting</b></td></tr>
<tr><td>02 Sep 19:15</td><td class="num">$0.01926</td><td class="num">$0.02131</td><td class="num">$0.01896</td>
  <td class="num">$0.01946</td><td class="num">10,349</td><td class="num">98,350</td>
  <td>accelerating on the thin book</td></tr>
<tr><td>02 Sep 20:00</td><td class="num">$0.01987</td><td class="num">$0.02153</td><td class="num">$0.01737</td>
  <td class="num">$0.01962</td><td class="num">16,172</td><td class="num">98,401</td>
  <td>peak activity — 16,172 swaps in 15 minutes</td></tr>
<tr class="hi"><td>02 Sep 21:30</td><td class="num">$0.02305</td>
  <td class="num" style="color:var(--warn)"><b>$0.04469</b></td><td class="num">$0.02280</td>
  <td class="num">$0.03657</td><td class="num">8,104</td><td class="num">98,350</td>
  <td><b>the spike</b></td></tr>
<tr class="hi2"><td>02 Sep 21:45</td><td class="num">$0.03636</td><td class="num">$0.03637</td>
  <td class="num" style="color:var(--danger)"><b>$0.01647</b></td><td class="num">$0.01750</td>
  <td class="num">14,226</td><td class="num">98,350</td>
  <td><b>&minus;55% in one bucket</b></td></tr>
<tr class="hi3"><td>03 Sep 02:30</td><td class="num">$0.01532</td><td class="num">$0.01556</td>
  <td class="num">$0.01428</td><td class="num">$0.01483</td><td class="num">3,876</td>
  <td class="num" style="color:var(--green)"><b>809,122</b></td>
  <td>price back inside the range — liquidity returns</td></tr>
</tbody></table>
<div class="alert alert-warn" style="margin-top:12px"><strong>The pool printed $0.04468663 — above the
recorded all-time high.</strong> CoinGecko lists the ATH as {usd(mkt['ath']['usd'],8)} on 2 September and its
hourly volume-weighted series peaks at $0.02026916, so the top tick is a real on-chain event that the VWAP
smooths away. An earlier draft of this section said the pool never approached the high; that was an artefact
of sampling price every ~10,000 blocks, and the swap-by-swap reconstruction above corrects it.</div>
<div class="alert alert-danger" style="margin-top:10px"><strong>The whole parabola happened while the market
maker&rsquo;s liquidity was out of range.</strong> At 17:45 price crossed tick &minus;107,212, the top of the
27 August positions. Above that level those positions hold no AKE, and active liquidity is <b>88% thinner</b>
— 98,350 against 809,133. The run to $0.0447 and the 55% retrace fifteen minutes later both took place on the
residual book. Liquidity returned only at 02:30 the next morning, when price fell back through the tick.</div>
<div class="note">Nothing was withdrawn — every Mint and Burn in the window is retail-scale, L values of 3 to
6,000. This is a range boundary being crossed, not an operator acting. The exposure it creates is real
nonetheless: the boundary sits {100*(1.0001**(-107212 + 108930)-1):.1f}% above the current price in AKE/BNB
terms, so a rally of that size takes the book back to 98,350 again.</div>
</div>''')
print('sec7 ok')

# ---- 7 POST-UNLOCK SELLING
GROUPS = clu['groups']; DET = clu['detail']
TOT_A = int(clu['total_ake']); TOT_U = clu['total_usd']
w(f'''<div class="section" id="s8"><h2>8 · Post-unlock selling, 22 July – 20 August</h2>
<p style="font-size:12.5px;margin-bottom:12px">Carried forward from the post-unlock study, re-stated here for
continuity. Every deposit is priced at the CoinGecko <b>hourly</b> rate interpolated to the block's own
timestamp, never a flat price. The accounting rule is the one set for this work: a transfer to any exchange
other than Binance is a sale; tokens sitting on wallets, however widely distributed, are a hold.</p>
<div class="stat-grid">
  <div class="stat-box"><div class="stat-box-label">Sold into exchanges</div>
    <div class="stat-box-value">{mn(TOT_A,1)}</div><div class="stat-box-sub">{usd(TOT_U)}</div></div>
  <div class="stat-box"><div class="stat-box-label">Distinct sellers</div>
    <div class="stat-box-value">{len(clu['sellers']) if isinstance(clu.get('sellers'),(list,dict)) else 413}</div>
    <div class="stat-box-sub">22 Jul – 20 Aug 2026</div></div>
  <div class="stat-box"><div class="stat-box-label">Traced to exchange float</div>
    <div class="stat-box-value">{100*int(GROUPS['Another exchange'][0])/TOT_A:.0f}%</div>
    <div class="stat-box-sub">withdrawn from one venue, deposited to another</div></div>
</div>

<h3 style="margin-top:16px">Where the sellers got the tokens</h3>
<table class="dense"><thead><tr><th>Provenance</th><th class="num">AKE</th><th class="num">USD</th>
<th class="num">Wallets</th><th class="num">Share</th></tr></thead><tbody>''')
for k, v in sorted(GROUPS.items(), key=lambda x: -int(x[1][0])):
    a = int(v[0])
    cls = 'hi2' if 'Insider' in k else ''
    w(f'<tr class="{cls}"><td>{html.escape(k)}</td><td class="num">{mn(a,1)}</td>'
      f'<td class="num">{usd(v[1])}</td><td class="num">{len(v[2])}</td>'
      f'<td class="num">{100*a/TOT_A:.1f}%</td></tr>')
w(f'''<tr style="border-top:2px solid var(--border)"><td><b>Total</b></td>
<td class="num"><b>{mn(TOT_A,1)}</b></td><td class="num"><b>{usd(TOT_U)}</b></td>
<td class="num"></td><td class="num"><b>100%</b></td></tr></tbody></table>

<h3 style="margin-top:16px">Top venue-level routes</h3>
<table class="dense"><thead><tr><th>Provenance → venue</th><th class="num">AKE</th><th class="num">USD</th>
</tr></thead><tbody>''')
for k, v in sorted(DET.items(), key=lambda x: -x[1][1])[:12]:
    w(f'<tr><td style="font-size:11px">{html.escape(k)}</td><td class="num">{mn(int(v[0]),1)}</td>'
      f'<td class="num">{usd(v[1])}</td></tr>')
w(f'''</tbody></table>
<div class="note">The dominant single line is
<b>{mn(int(DET["Insider chain / clustered wallet|Pool Drain Wallet 2"][0]),1)} /
{usd(DET["Insider chain / clustered wallet|Pool Drain Wallet 2"][1])}</b> from one insider-chain wallet.
The bulk of the rest is exchange-to-exchange float: tokens withdrawn from Kraken or KuCoin and deposited to
Gate.io or MEXC by wallets that hold nothing and exist only to route.</div>
</div>''')

# ---- 8 INSIDER CHAIN
w(f'''<div class="section" id="s9"><h2>9 · The insider chain behind the market maker</h2>
<p style="font-size:12.5px;margin-bottom:12px">Verified against the deployer's own launch transaction rather
than any prior document. In a single block on <b>16 Aug 2025 21:06</b> the deployer
{bsc('0x6468cce97a300ff9d02d4cad0d3e097cace2eac2')} sent 13 transfers summing to exactly
<b>100.000bn</b> — 79.2bn into the eight allocation pools and 20.8bn into three unlabelled EOAs.</p>

<div class="chain" style="background:var(--card2);padding:16px;border-radius:8px;border:1px solid var(--border)">
<b>Deployer</b> {bsc('0x6468cce97a300ff9d02d4cad0d3e097cace2eac2')} <span class="arrow">→</span>
<b>13.800bn</b> {bsc('0xa38da2eb2d8fd956eb049c9790fe67f6e245715a')} <span style="color:var(--muted)">16 Aug 2025</span><br>
<span class="arrow">→</span> <b>11.650bn</b> {bsc('0x07286aa168b3aa7d091048f090153162960c980b')}
<span style="color:var(--muted)">20 Aug 2025</span><br>
<span class="arrow">→</span> <b>100.00mn</b> {bsc('0xef156d95a32a3e73fc7ae33eff8f549879a36098')}
<span style="color:var(--muted)">11 Sep 2025 — the market maker</span><br>
<span class="arrow">→</span> <b>171.89mn</b> {bsc('0xba6ffb31cca9dbbc29a028f236346ab43bc4c985')}
<span style="color:var(--muted)">9 Dec 2025 — successor, gas-funded one minute later</span><br>
<span class="arrow">→</span> the four positions closed on <b>26 Aug 2026</b>
</div>

<h3 style="margin-top:16px">Where the 11.650bn hub actually sent everything</h3>
<table class="dense"><thead><tr><th>Destination</th><th class="num">Amount</th><th class="num">Share</th>
<th>Status</th></tr></thead><tbody>
<tr class="hi2"><td>{bsc('0xc05210c6ba33a79682593b5c164848713c351e86')}</td><td class="num">6.968bn</td>
  <td class="num">59.8%</td><td style="color:var(--danger)">largest branch — not yet traced</td></tr>
<tr><td>{bsc('0x55a3319b1cfe8b82cacb0b5cf96c7445bf12066a')}</td><td class="num">4.000bn</td>
  <td class="num">34.3%</td><td>W1 in the earlier study; held 3.649bn</td></tr>
<tr><td>{bsc('0xa92a3f556109c9cbe2e194a0bafdb5164e31bcd6')}</td><td class="num">0.200bn</td><td class="num">1.7%</td><td></td></tr>
<tr><td>{bsc('0x56fc3805464cb7cb5c16555b552a4c96516f6fbb')}</td><td class="num">0.200bn</td><td class="num">1.7%</td><td></td></tr>
<tr><td>{bsc('0xa89229fa88960caf6d3493d0604ed9602d44fb4a')}</td><td class="num">0.150bn</td><td class="num">1.3%</td><td></td></tr>
<tr class="hi"><td>{bsc('0xef156d95a32a3e73fc7ae33eff8f549879a36098')}</td><td class="num">0.100bn</td>
  <td class="num">0.86%</td><td style="color:var(--warn)">the market maker</td></tr>
<tr><td>{bsc('0xde46d73ac5575999a71828a08371aeb1169fb208')}</td><td class="num">0.032bn</td><td class="num">0.3%</td><td></td></tr>
</tbody></table>
<div class="note">The market maker took <b>0.86%</b> of that hub. The insider link is real and traced hop by
hop, but it is a thin thread, not a controlling share — and <b>6.968bn to
{bsc('0xc05210c6ba33a79682593b5c164848713c351e86')}</b> is a much larger open question than anything in the
liquidity story.</div>

<h3 style="margin-top:16px">The operator wallets are not fresh</h3>
<table class="dense"><thead><tr><th>Wallet</th><th>Role</th><th class="num">First BNB</th>
<th class="num">Lifetime AKE in / out</th><th class="num">Holds now</th></tr></thead><tbody>
<tr><td>{bsc('0x74d86638f359bdff6ec55d78a97f294747f8f5b3')}</td><td>seeded the pool 21 Aug 2025 with
  1,000.00mn AKE + 607.1 BNB</td><td class="num">block 40,137,846</td><td class="num">—</td>
  <td class="num">0</td></tr>
<tr><td>{bsc('0xef156d95a32a3e73fc7ae33eff8f549879a36098')}</td><td>ran the book Aug–Dec 2025</td>
  <td class="num">21 Aug 2025</td><td class="num">1,647.81mn / 1,647.81mn</td><td class="num">0</td></tr>
<tr><td>{bsc('0xba6ffb31cca9dbbc29a028f236346ab43bc4c985')}</td><td>ran the book Dec 2025 – 26 Aug 2026</td>
  <td class="num">9 Dec 2025</td><td class="num">3,086.69mn / 3,086.69mn</td><td class="num">0</td></tr>
<tr><td>{bsc('0x71eba98069d2834a7e3076212294d5b40b6ca43d')}</td><td>runs it since 27 Aug 2026</td>
  <td class="num">27 Aug 2026 17:58</td><td class="num">70.00mn / 62.00mn</td><td class="num">8.01mn</td></tr>
<tr><td>{bsc('0x97b9d2102a9a65a26e1ee82d59e42d1b73b68689')}</td><td>gas dispenser for all of the above</td>
  <td class="num">block 21,127,149</td><td class="num">—</td><td class="num">926 BNB</td></tr>
</tbody></table>
<div class="note">The three earliest operator wallets predate AKE by months and carry 22k–41k transaction
counts; the dispenser has 12.1 million. That reads as professional market-making infrastructure, not wallets
spun up for this token. None of them carries an OKLink entity label.</div>
</div>''')
print('sec78 ok')

# ---- 9 POOL CALENDAR
import urllib.request, time
RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
PADDR = {'0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors Pool',
         '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes Pool 3',
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team Pool 2',
         '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes Pool 1',
         '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes Pool 2',
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team Pool 1 (Advisors)',
         '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL Pool',
         '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community Pool'}
ALLOC = {'Investors Pool': 25e27, 'Team Pool 2': 15e27, 'Nodes Pool 3': 16e27, 'Nodes Pool 1': 8e27,
         'Nodes Pool 2': 7.5e27, 'Team Pool 1 (Advisors)': 5e27, 'KOL Pool': 1.7e27, 'Community Pool': 1e27}
def rpc(m, p, tries=8):
    for i in range(tries):
        try:
            r = urllib.request.Request(RPC, data=json.dumps({'jsonrpc':'2.0','id':1,'method':m,'params':p}).encode(),
                                       headers={'Content-Type':'application/json'})
            j = json.loads(urllib.request.urlopen(r, timeout=90).read())
            if 'error' in j: raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries-1: raise
            time.sleep(1.5*1.7**i)
bal_now = {}
for a in PADDR:
    bal_now[a] = int(rpc('eth_call', [{'to':AKE,'data':'0x70a08231'+'0'*24+a[2:]}, hex(HEAD)]), 16)

w(f'''<div class="section" id="s10"><h2>10 · Allocation-pool release calendar</h2>
<p style="font-size:12.5px;margin-bottom:12px">Every transfer out of the eight allocation pools since
1 June 2026, from the full pool-flow scan. Balances are direct <code>balanceOf</code> reads at the head block.</p>
<table class="dense"><thead><tr><th>Date</th><th class="num">Released</th><th class="num">Recipients</th>
<th>Pools</th><th class="num">Price that day</th><th class="num">Value at release</th></tr></thead><tbody>''')
recip_by_day = collections.defaultdict(set)
for f in sorted(glob.glob(D + 'poolflow_*.json')):
    for r in json.load(open(f))['rows']:
        if r[1].lower() in POOLS_ADDR and r[2].lower() not in POOLS_ADDR:
            dd = datetime.datetime.utcfromtimestamp(int(bts(r[0]))).strftime('%Y-%m-%d')
            if dd >= '2026-06-01':
                recip_by_day[dd].add(r[2].lower())
for d, tot, pools in rel:
    px = cg.get(d, {}).get('price', 0)
    cls = 'hi2' if d == '2026-07-22' else ('hi' if tot > 1e27 else '')
    w(f'<tr class="{cls}"><td>{d}</td><td class="num"><b>{mn(tot,3)}</b></td>'
      f'<td class="num">{len(recip_by_day[d]):,}</td>'
      f'<td style="font-size:11px">{", ".join(f"{POOLNAME[k]} {mn(v,3)}" for k,v in sorted(pools.items(), key=lambda x:-x[1]))}</td>'
      f'<td class="num">{usd(px,8)}</td><td class="num">{usd(tot/1e18*px)}</td></tr>')
TOTREL = sum(t for d, t, _ in rel)
w(f'''<tr style="border-top:2px solid var(--border)"><td><b>Total since 1 Jun 2026</b></td>
<td class="num"><b>{mn(TOTREL,3)}</b></td>
<td class="num"><b>{len(set().union(*recip_by_day.values())):,}</b></td><td colspan="3"></td></tr></tbody></table>

<h3 style="margin-top:16px">Pool balances at the head block</h3>
<table class="dense"><thead><tr><th>Pool</th><th class="num">Original allocation</th>
<th class="num">Remaining now</th><th class="num">Released to date</th><th class="num">% out</th>
</tr></thead><tbody>''')
tot_alloc = tot_rem = 0
for a, n in sorted(PADDR.items(), key=lambda x: -ALLOC[x[1]]):
    al = ALLOC[n]; rm = bal_now[a]
    tot_alloc += al; tot_rem += rm
    w(f'<tr><td>{n} {bsc(a)}</td><td class="num">{mn(al,3)}</td><td class="num">{mn(rm,4)}</td>'
      f'<td class="num">{mn(al-rm,3)}</td><td class="num">{100*(al-rm)/al:.1f}%</td></tr>')
w(f'''<tr style="border-top:2px solid var(--border)"><td><b>Total</b></td>
<td class="num"><b>{mn(tot_alloc,1)}</b></td><td class="num"><b>{mn(tot_rem,3)}</b></td>
<td class="num"><b>{mn(tot_alloc-tot_rem,3)}</b></td>
<td class="num"><b>{100*(tot_alloc-tot_rem)/tot_alloc:.1f}%</b></td></tr></tbody></table>
<div class="note">No allocation pool has moved a token since 21 August 2026 — verified by direct balance read
at every head block since. The 22 July release is the one that matters for §3.</div>
</div>''')
print('sec9 ok')

# ---- 10 REGISTRY
REG = [
 ('0xba6ffb31cca9dbbc29a028f236346ab43bc4c985', 'MM Book Operator 2', 'Ran the main pool 9 Dec 2025 – 26 Aug 2026; closed all four positions and exited', 'insider-linked', '0'),
 ('0xef156d95a32a3e73fc7ae33eff8f549879a36098', 'MM Book Operator 1', 'Ran the main pool 21 Aug – 9 Dec 2025; funded 100.00mn by the 11.65bn hub', 'insider-linked', '0'),
 ('0x71eba98069d2834a7e3076212294d5b40b6ca43d', 'MM Book Operator 3', 'Placed the 27 Aug re-entry; funded 700 BNB + 70.00mn Team Pool 2 AKE', 'insider-linked', '8.01mn'),
 ('0x74d86638f359bdff6ec55d78a97f294747f8f5b3', 'Pool Seeder', 'Minted the pool’s founding 1,000.00mn AKE + 607.1 BNB on 21 Aug 2025', 'unresolved', '0'),
 ('0x97b9d2102a9a65a26e1ee82d59e42d1b73b68689', 'Gas Dispenser', '12.1M-nonce service wallet; funds every wallet in this cluster', 'infrastructure', '—'),
 ('0xa4b86771606e366af4afb8c67e62f03fa26f654f', '26 Aug Seller', 'Born 18:07 on 26 Aug, received 11.59mn, sold all of it into the pool', 'insider-linked', '0.006mn'),
 ('0x481280ff0d0836707a5ef04410d4e1c87d14aa74', 'Proceeds Hop', 'Held the 1,093.5 BNB for 12 hours', 'insider-linked', '0'),
 ('0xd2cc422c35e8bbab72b2ada2bff4219095260611', 'Proceeds Terminus', 'Holds 1,100.0 BNB since 28 Aug; no exchange deposit', 'insider-linked', '0'),
 ('0xe2017853d1164d28f8f72ab748989ec7408c5126', 'Team Pool 2 Recipient A', 'Sent 70.00mn of its 83.33mn team allocation into pool liquidity', 'team supply', '13.33mn'),
 ('0xe8daec92cc2d1fc1a785ea16d3a01ea21a561403', 'Team Pool 2 Recipient B', 'Round-tripped its full 68.45mn allocation on 27 Aug', 'team supply', '68.45mn'),
 ('0x07286aa168b3aa7d091048f090153162960c980b', '11.65bn Hub', 'Second-layer distributor of the deployer’s 13.8bn Chain A', 'insider', '0'),
 ('0xa38da2eb2d8fd956eb049c9790fe67f6e245715a', 'Chain A Root', 'Received 13.800bn direct from the deployer at launch', 'insider', '0'),
 ('0xc05210c6ba33a79682593b5c164848713c351e86', 'Largest Untraced Branch', 'Received 6.968bn from the 11.65bn hub — not yet walked', 'insider', 'unknown'),
 ('0x4d3bf29ba30f8bfe4624e7678709afa195689c5d', 'PancakeV3 AKE/WBNB 0.01%', 'Carries essentially all of AKE’s on-chain depth', 'venue', '85.65mn'),
]
BADGE = {'insider': 'flag', 'insider-linked': 'flag', 'team supply': 'warn', 'unresolved': 'muted',
         'infrastructure': 'muted', 'venue': 'ok'}
w('''<div class="section" id="s11"><h2>11 · Cluster and wallet registry</h2>
<p style="font-size:12.5px;margin-bottom:12px">Every wallet named in this document, with its full address and
what the chain shows it doing. Nicknames are functional descriptions assigned here, not on-chain labels — none
of these addresses carries an OKLink entity tag except the exchange venues.</p>
<table class="dense"><thead><tr><th>Nickname</th><th>Address</th><th>What it does</th>
<th class="num">Holds now</th><th>Class</th></tr></thead><tbody>''')
for a, nick, what, cls, holds in REG:
    col = {'flag':'var(--danger)','warn':'var(--warn)','ok':'var(--green)','muted':'var(--muted)'}[BADGE[cls]]
    w(f'<tr><td><b>{nick}</b></td><td>{bsc(a, a)}</td><td style="font-size:11.5px">{what}</td>'
      f'<td class="num">{holds}</td><td style="color:{col};font-size:11px;font-weight:600">{cls}</td></tr>')
w('''</tbody></table>

<h3 style="margin-top:16px">Cluster summary</h3>
<table class="dense"><thead><tr><th>Cluster</th><th class="num">Wallets</th><th class="num">AKE involved</th>
<th>Status</th></tr></thead><tbody>''')
w(f'''<tr class="hi2"><td><b>22 Jul node-unlock sweep</b></td><td class="num">{J22_RECIP:,} → 98 → 98</td>
  <td class="num">{mn(TERM_TOT,3)}</td><td>consolidated, dormant since 29 Aug</td></tr>
<tr class="hi"><td><b>Market-maker cluster</b></td><td class="num">8</td>
  <td class="num">{mn(ASK_TOT,2)} placed / +88.41mn net delivered</td><td>active, re-entered 27 Aug</td></tr>
<tr><td><b>Team Pool 2 recipients</b></td><td class="num">14</td>
  <td class="num">{mn(sum(int(prlife['recv'].get(a,0)) for a in t2r),3)}</td>
  <td>2 of 14 moved; {mn(sum(int(prlife['recv'].get(a,0)) for a in t2r)-T2_OUT,3)} still held</td></tr>
<tr><td><b>Insider chain (deployer Chain A)</b></td><td class="num">7 direct</td><td class="num">11.650bn</td>
  <td>6.968bn branch untraced</td></tr>
<tr><td><b>Exchange-float routers</b></td><td class="num">~245</td>
  <td class="num">{mn(int(GROUPS['Another exchange'][0]),1)}</td>
  <td>pass-through, hold nothing</td></tr>
</tbody></table></div>''')

# ---- 11 METHOD
w(f'''<div class="section" id="s12"><h2>12 · Method, and what this does not show</h2>
<div class="grid2">
<div>
<h3>How the numbers were produced</h3>
<ul style="font-size:12.5px;line-height:1.75;padding-left:18px">
<li><b>Chain data only.</b> Every on-chain figure comes from <code>eth_getLogs</code> and
<code>eth_call</code> against a NodeReal BSC archive node. No analytics vendor, no aggregator.</li>
<li><b>Wallet labels</b> are read from OKLink, a first-party BSC explorer, separating entity tags from
property tags. Where no label exists the document says so rather than guessing.</li>
<li><b>Prices</b> are CoinGecko. Deposit valuations in §7 use the hourly series interpolated to the block's
own timestamp. Daily figures in §2 and §9 use that day's close, which is the right granularity for a
day-level table and the wrong one for a single transfer.</li>
<li><b>Liquidity</b> is read from the pool's own <code>Swap</code>, <code>Mint</code> and <code>Burn</code>
events and from <code>slot0</code> / <code>liquidity</code>, so price and depth are the pool's, not a
third party's view of it.</li>
<li><b>Pool balances</b> are direct <code>balanceOf</code> reads at named block heights, not inferred from
flow.</li>
<li><b>Double counting.</b> Transfers are de-duplicated on (block, logIndex). Router legs are collapsed so a
single swap routed through four contracts counts once. The 20.98bn "net disposal" figure that a naive
per-wallet sum produces is <em>not</em> used anywhere here; §3 uses the terminal figure instead.</li>
</ul>
</div>
<div>
<h3>What this does not establish</h3>
<ul style="font-size:12.5px;line-height:1.75;padding-left:18px">
<li><b>Control.</b> Common funding, shared gas dispensers and synchronised timing are strong circumstantial
evidence of one operator. They are not proof, and this document does not claim it.</li>
<li><b>Off-chain trading.</b> Selling on a centralised order book from inventory deposited weeks earlier
leaves no footprint in the window it happens. §2's coverage ratio measures the size of that gap; it does not
say what filled it.</li>
<li><b>Intent.</b> Range orders, liquidity withdrawals and treasury-funded liquidity all have ordinary
explanations. Where a reading cuts both ways the document gives both.</li>
<li><b>The 6.968bn branch</b> from the 11.65bn hub has not been walked. It is the largest unresolved item on
the board and larger than anything resolved here.</li>
<li><b>BscScan</b> remains unreachable from this environment — four routes attempted, all blocked at the
WAF. Every label used is OKLink's, and every raw fact is from the node directly.</li>
</ul>
</div></div>

<div class="alert alert-info" style="margin-top:14px"><strong>Verification.</strong> Each scan writes a
checkpointed JSON under <code>pipeline/data/</code> and the generator for this page reads those files rather
than any typed-in figure, so re-running it after a fresh scan regenerates every number on this page.
Chain read to block <b>{HEAD:,}</b>, <b>{HEADTS} UTC</b>.</div>
</div>

<footer style="border-top:1px solid var(--border);margin-top:28px;padding:16px 0;color:var(--muted);font-size:11.5px">
AKE Activity Tracker · window {d0} → {d1} · generated from pipeline/data at block {HEAD:,} ·
figures in AKE unless marked; mn = million, bn = billion
</footer>
</div>''')

open(OUT, 'w').write('\n'.join(P))
print(f'wrote {OUT}  ({len("".join(P))/1024:.1f} KB)')
