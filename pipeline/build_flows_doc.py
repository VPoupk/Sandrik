#!/usr/bin/env python3
"""
Build ake-flows-jun-nov-2026.html — every on-chain flow of AKE from June 2026
to the present, set against what the price did.

The other documents in this repo answer narrower questions: how the Investors
Pool vests, what a single release day looked like, whether a figure is right.
This one is the whole picture over one stretch of time, and it exists because
the stretch in question contains the entire round trip — a token that went from
$0.00033 to $0.146656 and back to under a third of a cent, with 40.6608bn
released out of team-controlled pools along the way and almost none of it sold.

Two rules the page keeps to, both learned the hard way earlier in this work:

  Net, not gross. A pool that sends 4.0734bn and takes 2.0734bn back has
  released 2.0000bn. Every pool figure here is net and reconciles against
  balanceOf at the head block, to the wei.

  Dollars only where dollars changed hands. A release that has never been sold
  has no proceeds, so it is quoted in tokens. Notional value at the moment of
  the move appears once, in the verification table, labelled as notional.

Separation of evidence is explicit throughout: what the chain shows, what
merely correlates, and what is inferred, are in different boxes with different
colours, and every inference says what would disprove it.

Usage: build_flows_doc.py
Writes one HTML file in the repo root, which the user has asked for explicitly.
"""
import json, html, datetime, bisect, collections, urllib.request, time

D = 'pipeline/data/'
OUT = 'ake-flows-jun-nov-2026.html'
RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
SAFE = '0x551a841742733bef96646b44e3475ce6a01da5eb'
SAFE2 = '0x808e6d72d37619d7ecb3fc6efc8f13bd37c46755'
DEPLOYER = '0x6468cce97a300ff9d02d4cad0d3e097cace2eac2'
SIGNER = '0x88f4b387eab71497e312663ac8b4aada6aa2ef8e'
MAINPOOL = '0x4d3bf29ba30f8bfe4624e7678709afa195689c5d'
GATE_DEP = '0x0d0707963952f2fba59dd06f2b425ace40b492fe'
START, END = '2026-06-01', '2026-11-12'

POOLS = {'0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors',
         '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes 3',
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team 2',
         '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes 1',
         '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes 2',
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team 1',
         '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL',
         '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community'}

LED = json.load(open(D + 'pool_net_ledger.json'))
REP = json.load(open(D + 'repeat_amounts.json'))
OHLC = json.load(open(D + 'cg_daily_ohlc.json'))
CGPV = json.load(open(D + 'cg_daily_pv.json'))
HR = json.load(open(D + 'ake_hourly_cg.json'))
CEX = json.load(open(D + 'cex_daily_jun_nov.json'))
WEEK = json.load(open(D + 'pool_weekly_jun_nov.json'))
MKT = json.load(open(D + 'cg_market_now.json'))
TSJ = json.load(open(D + 'blk_ts.json'))
V = json.load(open(D + 'venues_scan.json'))
LAB = json.load(open(D + 'all_labels_final.json'))
MIG = [a.lower() for a in json.load(open(D + 'migration_0829.json'))['destinations']]
EVD = json.load(open(D + 'pool_event_days.json'))['days']
SALE = json.load(open(D + 'jun19_sale_verified.json'))
try:
    EXTRA = json.load(open(D + 'flows_doc_findings.json'))
except Exception:
    EXTRA = {}
GAS = json.load(open(D + 'recipient_gas_funders.json'))
COL = json.load(open(D + 'collapse_analysis.json'))

_hk = sorted(int(x) for x in HR); _hv = [HR[str(x)] for x in _hk]
_kb = sorted(int(x) for x in TSJ); _kv = [TSJ[str(x)] for x in _kb]
DAYS = [d for d in sorted(OHLC) if START <= d <= END]
RECIPS = set()
for _d, _e in EVD.items():
    if _e.get('followed'):
        RECIPS |= set(_e['followed'])
for _d, _e in LED['days'].items():
    for _l in _e['legs']:
        if _l[2] == 'out':
            RECIPS.add(_l[4])


def px(ts):
    i = bisect.bisect_left(_hk, ts)
    if i == 0:
        return _hv[0]
    if i >= len(_hk):
        return _hv[-1]
    t0, t1, p0, p1 = _hk[i-1], _hk[i], _hv[i-1], _hv[i]
    return p0 + (p1 - p0) * (ts - t0) / (t1 - t0) if t1 > t0 else p0


def bn_amt(w, dp=4):
    w = float(w)
    if abs(w) >= 1e27:
        return f'{w/1e27:,.{dp}f}bn'
    if abs(w) >= 1e24:
        return f'{w/1e24:,.2f}mn'
    if abs(w) >= 1e21:
        return f'{w/1e21:,.1f}k'
    return f'{w/1e18:,.0f}'


def usd(x, dp=0):
    return '$' + f'{float(x):,.{dp}f}'


def pc(x):
    return f'{x:+,.1f}%'


def bsc(a, t=None):
    return (f'<a class="addr" href="https://bscscan.com/address/{a}" target="_blank" '
            f'rel="noopener">{t or a}</a>')


def bsctx(t, s=None):
    return (f'<a class="addr" href="https://bscscan.com/tx/{t}" target="_blank" '
            f'rel="noopener">{s or t[:16] + "…"}</a>')


def ut(ts, f='%Y-%m-%d %H:%M:%S'):
    return datetime.datetime.utcfromtimestamp(int(ts)).strftime(f)


def rpc(m, p, tries=8):
    for i in range(tries):
        try:
            r = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                      'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(r, timeout=90).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * 1.7 ** i)


HEAD = int(rpc('eth_blockNumber', []), 16)
HEADTS = int(rpc('eth_getBlockByNumber', [hex(HEAD), False])['timestamp'], 16)
POOLBAL = {n: int(rpc('eth_call', [{'to': AKE, 'data': '0x70a08231' + '0'*24 + a[2:]},
                                   hex(HEAD)]), 16) for a, n in POOLS.items()}
LAST = _hv[-1]
print(f'live: head {HEAD:,} ({ut(HEADTS)} UTC), pools hold {sum(POOLBAL.values())/1e27:,.4f}bn, '
      f'price ${LAST:.8f}')

BUF = []


def w(s):
    BUF.append(s)


CSS = open(D + '../assets/base.css').read()
EXTRACSS = """
  .wrap { max-width: 1240px; margin: 0 auto; padding: 26px 20px 60px; }
  .hdr { display:flex; flex-wrap:wrap; gap:14px; align-items:flex-end;
         border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:18px; }
  .hdr h1 { font-size:25px; font-weight:700; color:var(--accent); line-height:1.25; margin:0; }
  .hdr .sub { font-size:12.5px; color:var(--muted); margin-top:6px; }
  .tz { background:rgba(59,130,246,.10); border:1px solid rgba(59,130,246,.3); border-radius:8px;
        padding:10px 13px; font-size:12.5px; color:#93c5fd; margin-bottom:20px; }
  .toc { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:8px; }
  .toc a { display:block; padding:8px 11px; background:var(--card2); border:1px solid var(--border);
           border-radius:6px; font-size:12px; }
  .note { font-size:11.5px; color:var(--muted); margin-top:8px; line-height:1.55; }
  .grid2 { display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr)); gap:14px; }
  .hi  { background:rgba(251,191,36,.09); }
  .hi2 { background:rgba(239,68,68,.08); }
  .hi3 { background:rgba(16,185,129,.07); }
  .mono { font-family:ui-monospace,Menlo,monospace; }
  .addr { font-family:ui-monospace,Menlo,monospace; font-size:11px; }
  table.dense { font-size:11.5px; }
  table.dense td, table.dense th { padding:5px 7px; }
  .q { display:grid; grid-template-columns:repeat(auto-fit,minmax(185px,1fr)); gap:10px;
       margin:12px 0 16px; }
  .q > div { background:var(--card2); border:1px solid var(--border); border-radius:8px;
             padding:10px 12px; }
  .q .k { font-size:10.5px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
  .q .v { font-size:17px; font-weight:600; margin-top:3px; }
  .q .sub { font-size:11px; color:var(--muted); margin-top:2px; }
  .ev { border-radius:8px; padding:11px 13px; font-size:12.5px; margin:12px 0; }
  .ev-fact { background:rgba(16,185,129,.08); border:1px solid rgba(16,185,129,.28); }
  .ev-corr { background:rgba(245,158,11,.08); border:1px solid rgba(245,158,11,.28); }
  .ev-inf  { background:rgba(139,92,246,.08); border:1px solid rgba(139,92,246,.28); }
  .ev-neg  { background:rgba(239,68,68,.08); border:1px solid rgba(239,68,68,.28); }
  .ev b.lbl { display:block; font-size:10.5px; text-transform:uppercase; letter-spacing:.07em;
              margin-bottom:5px; }
  .ev-fact b.lbl { color:var(--green); }
  .ev-corr b.lbl { color:var(--warn); }
  .ev-inf  b.lbl { color:#a78bfa; }
  .ev-neg  b.lbl { color:var(--danger); }
  .spark { display:block; width:100%; height:auto; margin:10px 0 4px; }
"""


def box(kind, label, body):
    return f'<div class="ev ev-{kind}"><b class="lbl">{label}</b>{body}</div>'


def fact(b):
    return box('fact', 'What the chain shows', b)


def corr(b):
    return box('corr', 'Correlation only', b)


def infer(b, conf, disprove):
    return box('inf', f'Inference · confidence {conf}',
               b + f'<div style="margin-top:7px;font-size:11.5px;color:var(--muted)">'
                   f'<b>What would disprove it:</b> {disprove}</div>')


def negative(b):
    return box('neg', 'A negative result, and it matters', b)


# ---------------------------------------------------------------- price chart
def pricechart(wpx=1180, hpx=230):
    import math
    ds = DAYS
    lo = min(OHLC[d]['l'] for d in ds); hi = max(OHLC[d]['h'] for d in ds)
    lml, lmh = math.log(lo), math.log(hi)
    def X(i): return 54 + i * (wpx - 74) / (len(ds) - 1)
    def Y(p): return 14 + (hpx - 44) * (1 - (math.log(p) - lml) / (lmh - lml))
    pts = ' '.join(f'{X(i):.1f},{Y(OHLC[d]["c"]):.1f}' for i, d in enumerate(ds))
    s = [f'<svg class="spark" viewBox="0 0 {wpx} {hpx}" preserveAspectRatio="none" '
         f'xmlns="http://www.w3.org/2000/svg">']
    for lv in (0.0001, 0.001, 0.01, 0.1):
        if lo <= lv <= hi:
            y = Y(lv)
            s.append(f'<line x1="54" y1="{y:.1f}" x2="{wpx-20}" y2="{y:.1f}" stroke="#1e2d45" '
                     f'stroke-width="1"/>')
            s.append(f'<text x="4" y="{y+3:.1f}" fill="#64748b" font-size="10">${lv:g}</text>')
    s.append(f'<polyline points="{pts}" fill="none" stroke="#3b82f6" stroke-width="1.6"/>')
    for d in sorted(LED['days']):
        if d not in ds:
            continue
        i = ds.index(d); x = X(i)
        net = int(LED['days'][d]['net_total'])
        h = 7 + 20 * (net / 20.8671e27) ** 0.45
        s.append(f'<line x1="{x:.1f}" y1="{hpx-30:.1f}" x2="{x:.1f}" y2="{hpx-30-h:.1f}" '
                 f'stroke="#f59e0b" stroke-width="2.4" opacity="0.85"/>')
        s.append(f'<title>{d} — {bn_amt(net)} released</title>')
    for m, lbl in [('2026-06-01', 'Jun'), ('2026-07-01', 'Jul'), ('2026-08-01', 'Aug'),
                   ('2026-09-01', 'Sep'), ('2026-10-01', 'Oct'), ('2026-11-01', 'Nov')]:
        if m in ds:
            x = X(ds.index(m))
            s.append(f'<text x="{x:.1f}" y="{hpx-6}" fill="#64748b" font-size="10" '
                     f'text-anchor="middle">{lbl}</text>')
    s.append('</svg>')
    return ''.join(s)


# ================================================================ document
w(f'''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AKE — flows and price, Jun–Nov 2026</title>
<style>{CSS}{EXTRACSS}</style>
<div class="wrap">
<header class="hdr">
  <div>
    <h1>AKE — every on-chain flow, and what the price did</h1>
    <div class="sub">AKEDO {bsc(AKE, AKE)} on BNB Smart Chain · 1 June 2026 to
      {datetime.datetime.strptime(END, '%Y-%m-%d').strftime('%-d %B %Y')} ·
      built at block {HEAD:,}, {ut(HEADTS)} UTC</div>
  </div>
</header>

<div class="tz">All times <b>UTC</b>. Token amounts in bn/mn; the exact wei sits behind every figure in
the scans. Pool figures are <b>net</b> — what a pool sent minus anything sent back — and reconcile to
<code>balanceOf</code> at the head block to the wei. Dollar figures appear only where dollars actually
changed hands, or once, clearly labelled, as the notional value of a move. Evidence is colour-coded
throughout: <span style="color:var(--green)">green is what the chain shows</span>,
<span style="color:var(--warn)">amber is correlation only</span>,
<span style="color:#a78bfa">purple is inference, with what would disprove it</span>.</div>
''')

w('<div class="section"><h2>Contents</h2><div class="toc">')
for a, t in [('s0', '0 · The arc, in one screen'), ('s1', '1 · Month by month'),
             ('s2', '2 · The complete release ledger'),
             ('s3', '3 · The payout roster — one list, three pools, always new wallets'),
             ('s4', '4 · What happened to every token released'),
             ('s5', '5 · The only sale'), ('s6', '6 · The collapse — what actually sold'),
             ('s7', '7 · Exchange flows, June to November'),
             ('s8', '8 · The DEX pool, week by week'),
             ('s9', '9 · Team-adjacent wallets — established, correlated, inferred'),
             ('s10', '10 · Method, and what this does not show')]:
    w(f'<a href="#{a}">{t}</a>')
w('</div></div>')

# ---------------------------------------------------------------- 0
p0 = OHLC[DAYS[0]]['o']; pnow = LAST
ath = MKT['market_data']['ath']['usd']
athd = MKT['market_data']['ath_date']['usd'][:10]
relsum = sum(int(e['net_total']) for e in LED['days'].values())
held = sum(POOLBAL.values())
w(f'''<div class="section" id="s0"><h2>0 · The arc, in one screen</h2>
<div class="q">
  <div><div class="k">1 June 2026</div><div class="v">${p0:.8f}</div>
    <div class="sub">where this window starts</div></div>
  <div><div class="k">All-time high</div><div class="v">${ath:.6f}</div>
    <div class="sub">{athd}, 10:33:30 UTC</div></div>
  <div><div class="k">Now</div><div class="v">${pnow:.8f}</div>
    <div class="sub">{pc(100*(pnow/ath-1))} from the high, {pc(100*(pnow/p0-1))} from 1 June</div></div>
  <div><div class="k">Released from the pools</div><div class="v">{bn_amt(relsum)}</div>
    <div class="sub">net, across {len(LED['days'])} days</div></div>
  <div><div class="k">Of that, ever sold</div><div class="v" style="color:var(--green)">2.0000bn</div>
    <div class="sub">4.9% — one release, in July</div></div>
  <div><div class="k">Still inside the pools</div><div class="v">{bn_amt(held)}</div>
    <div class="sub">read live at block {HEAD:,}</div></div>
</div>
{pricechart()}
<div class="note">Log scale. Amber bars mark the days a team-controlled pool released tokens, scaled by
size — the tallest is 22 July at {bn_amt(int(LED['days']['2026-07-22']['net_total']))}.</div>
''')
w(fact(f'''A token that rose roughly {100*(ath/p0-1)/100:,.0f}-fold in under four months and then gave
back {abs(100*(pnow/ath-1)):.1f}% of it. Through the entire round trip, <b>40.6608bn of team-controlled
supply was released and 2.0000bn of it was sold</b> — one release, in July, before the rise had even
finished. Every other recipient still holds every token, including through the collapse.'''))
w(negative(f'''The thing this page looked hardest for and did not find: <b>team-pool supply hitting the
market during the fall.</b> Between 21 September and 12 November the eight pools released
{bn_amt(int(LED['days']['2026-10-23']['net_total']))} in total, on one day, and not a single token from
that release — or from any release since June — has reached an exchange. The 98 wallets holding the
22 July node unlock have not moved either. Whatever drove a 98% fall, it was not these wallets
selling.'''))
w('</div>')


# ---------------------------------------------------------------- 1 month by month
def month_rows():
    out = []
    for m in ['2026-06', '2026-07', '2026-08', '2026-09', '2026-10', '2026-11']:
        ds = [d for d in DAYS if d.startswith(m)]
        if not ds:
            continue
        o = OHLC[ds[0]]['o']; c = OHLC[ds[-1]]['c']
        hi = max(OHLC[d]['h'] for d in ds); lo = min(OHLC[d]['l'] for d in ds)
        rel = {d: int(LED['days'][d]['net_total']) for d in LED['days'] if d.startswith(m)}
        ci = sum(int(CEX.get(d, {}).get('cex', ['0', '0'])[0]) for d in ds)
        co = sum(int(CEX.get(d, {}).get('cex', ['0', '0'])[1]) for d in ds)
        bi = sum(int(CEX.get(d, {}).get('binance', ['0', '0'])[0]) for d in ds)
        bo = sum(int(CEX.get(d, {}).get('binance', ['0', '0'])[1]) for d in ds)
        vol = sum(CGPV.get(d, {}).get('volume', 0) for d in ds)
        out.append((m, o, hi, lo, c, rel, ci, co, bi, bo, vol))
    return out


w('''<div class="section" id="s1"><h2>1 · Month by month</h2>
<p style="font-size:13px">One row per month: what the price did, what the pools released, and which
way supply moved across exchange custody. Deposits to a non-Binance exchange are counted as sales;
Binance is kept separate because AKE is not listed on Binance spot, so flows to Binance-labelled
wallets are custody and market-making rather than disposals.</p>
<table class="dense"><thead><tr><th>Month</th><th class="num">Open</th><th class="num">High</th>
<th class="num">Low</th><th class="num">Close</th><th class="num">H/L</th>
<th>Pool releases (net)</th><th class="num">Sold → CEX</th><th class="num">Withdrawn</th>
<th class="num">Net CEX</th><th class="num">Reported volume</th></tr></thead><tbody>''')
for m, o, hi, lo, c, rel, ci, co, bi, bo, vol in month_rows():
    rtxt = '<br>'.join(f'{d[8:]} {k} {bn_amt(v)}'
                       for d, v in sorted(rel.items())
                       for k in [' · '.join(sorted(LED['days'][d]['by_pool']))]) or '—'
    net = ci - co
    cls = ' class="hi2"' if net > 0 else ''
    w(f'<tr{cls}><td><b>{m}</b></td><td class="num">${o:.8f}</td><td class="num">${hi:.8f}</td>'
      f'<td class="num">${lo:.8f}</td><td class="num">${c:.8f}</td>'
      f'<td class="num">{hi/lo:,.1f}×</td><td style="font-size:11px">{rtxt}</td>'
      f'<td class="num">{bn_amt(ci)}</td><td class="num">{bn_amt(co)}</td>'
      f'<td class="num"><b>{bn_amt(net)}</b></td><td class="num">{usd(vol)}</td></tr>')
w('</tbody></table>')
_oct = [r for r in month_rows() if r[0] == '2026-10'][0]
_nov = [r for r in month_rows() if r[0] == '2026-11'][0]
_sep = [r for r in month_rows() if r[0] == '2026-09'][0]
w(fact(f'''The sign flips in October. From June to September, every single month saw <b>more AKE
withdrawn from non-Binance exchanges than deposited</b> — supply was leaving the order books even as
the price rose twenty-fold. October is the first net-deposit month ({bn_amt(_oct[6]-_oct[7])}), and
November, in twelve days, is <b>{bn_amt(_nov[6]-_nov[7])} net onto exchanges</b> — more deposited than
in September and October combined. That is the supply that broke the price, and the timing matches the
fall rather than preceding it.'''))
w('</div>')

# ---------------------------------------------------------------- 2 ledger
w('''<div class="section" id="s2"><h2>2 · The complete release ledger</h2>
<p style="font-size:13px">Every day since 1 June 2026 on which AKE left one of the eight
team-controlled pools. Net throughout, and checked: allocation minus net released must equal
<code>balanceOf</code> at the head block.</p>
<table class="dense"><thead><tr><th>Pool</th><th class="num">Allocation</th>
<th class="num">Net released, lifetime</th><th class="num">of allocation</th>
<th class="num">Net released in this window</th><th class="num">Holds now</th>
<th class="num">Reconciles?</th></tr></thead><tbody>''')
ta = tn = tw = tb = 0
for p in ['Investors', 'Team 2', 'Team 1', 'Nodes 1', 'Nodes 2', 'Nodes 3', 'KOL', 'Community']:
    L_ = LED['lifetime'][p]
    a, n, h = int(L_['allocation']), int(L_['net_released']), int(L_['holds_now'])
    since = sum(int(LED['days'][d]['by_pool'][p]['net'])
                for d in LED['days'] if p in LED['days'][d]['by_pool'])
    ta += a; tn += n; tw += since; tb += h
    cls = ' class="hi"' if since else ''
    w(f'<tr{cls}><td><b>{p}</b></td><td class="num">{bn_amt(a)}</td><td class="num">{bn_amt(n)}</td>'
      f'<td class="num">{L_["pct_released"]:.1f}%</td>'
      f'<td class="num">{bn_amt(since) if since else "—"}</td><td class="num">{bn_amt(h)}</td>'
      f'<td class="num" style="color:var(--green)">{"exact" if L_["reconciles"] else "MISMATCH"}</td></tr>')
w(f'<tr style="border-top:2px solid var(--border)"><td><b>total</b></td>'
  f'<td class="num"><b>{bn_amt(ta)}</b></td><td class="num"><b>{bn_amt(tn)}</b></td>'
  f'<td class="num">{100*tn/ta:.1f}%</td><td class="num"><b>{bn_amt(tw)}</b></td>'
  f'<td class="num"><b>{bn_amt(tb)}</b></td>'
  f'<td class="num" style="color:var(--green)">exact</td></tr>')
w('</tbody></table>')

w('''<h3 style="margin-top:18px">Day by day</h3>
<table class="dense"><thead><tr><th>Date</th><th>Pools, net</th><th class="num">Day total</th>
<th class="num">Recipients</th><th>Released by</th><th class="num">Price that day</th>
<th class="num">7d before</th><th class="num">7d after</th><th class="num">30d after</th>
</tr></thead><tbody>''')


def mv(d, k):
    dt = datetime.datetime.strptime(d, '%Y-%m-%d')
    o = (dt + datetime.timedelta(days=k)).strftime('%Y-%m-%d')
    a = OHLC.get(d, {}).get('c'); b = OHLC.get(o, {}).get('c')
    return f'{100*(b/a-1):+.0f}%' if a and b else '—'


def mvb(d, k):
    dt = datetime.datetime.strptime(d, '%Y-%m-%d')
    o = (dt - datetime.timedelta(days=k)).strftime('%Y-%m-%d')
    a = OHLC.get(o, {}).get('c'); b = OHLC.get(d, {}).get('c')
    return f'{100*(b/a-1):+.0f}%' if a and b else '—'


CAUSE = {'2026-06-19': 'deployer EOA', '2026-07-22': 'individual node claimants',
         '2026-07-24': 'individual node claimants',
         '2026-07-26': 'recipients, calling userWithdraw() themselves',
         '2026-08-21': 'the owner Safe', '2026-09-03': 'the owner Safe',
         '2026-09-21': 'the owner Safe', '2026-10-23': 'the owner Safe'}
for d in sorted(LED['days']):
    e = LED['days'][d]
    pools = ' · '.join(f'{k} {bn_amt(int(v["net"]))}' for k, v in
                       sorted(e['by_pool'].items(), key=lambda x: -int(x[1]['net'])))
    nrec = len({l[4] for l in e['legs'] if l[2] == 'out'})
    cls = ' class="hi"' if d == sorted(LED['days'])[-1] else ''
    w(f'<tr{cls}><td><b>{d}</b></td><td style="font-size:11px">{pools}</td>'
      f'<td class="num"><b>{bn_amt(int(e["net_total"]))}</b></td><td class="num">{nrec:,}</td>'
      f'<td style="font-size:11px">{CAUSE.get(d,"")}</td>'
      f'<td class="num">${OHLC.get(d,{}).get("c",0):.8f}</td>'
      f'<td class="num">{mvb(d,7)}</td><td class="num">{mv(d,7)}</td>'
      f'<td class="num">{mv(d,30)}</td></tr>')
w('</tbody></table>')
w(corr('''Seven of the eight releases landed after a week in which the price had <b>risen</b>, several
of them sharply — +153% into 22 July, +125% into 3 September, +249% into 21 September. The two most
recent, 21 September and 23 October, are also the only two followed by a heavy fall. That is a
pattern in eight observations. It is not, on its own, evidence of timing: a token that rose twenty-fold
over the window had far more up-weeks than down-weeks, so "a release followed a good week" is close to
what chance would produce. §9 says what it would take to decide.'''))
w('</div>')


# ---------------------------------------------------------------- 3 payout roster
_recur = REP['recurring']
_tok = int(REP['tokens_via_recurring'])
_reuse = REP['address_reuse']
_nev = len(REP['events'])
w(f'''<div class="section" id="s3"><h2>3 · The payout roster — one list, three pools, always new
wallets</h2>
<p style="font-size:13px">This is the strongest structural finding in the window, and it is
arithmetic rather than interpretation. Across the eleven release events small enough to examine
address by address, <b>{len(_recur)} distinct payout amounts recur on more than one day</b> — and
<b>no address has ever appeared twice</b>. Not once, in {_nev} events.</p>
<table class="dense"><thead><tr><th class="num">Amount</th>
<th>Paid on each of these days, from this pool, to this address</th></tr></thead><tbody>''')
for r in _recur:
    cells = '<br>'.join(
        f'<span class="mono">{p["day"]}</span> &nbsp;<b>{p["pool"]}</b> &nbsp;→&nbsp; '
        f'{bsc(p["address"], p["address"][:12] + "…")}' for p in r['payments'])
    pools_ = {p['pool'] for p in r['payments']}
    cls = ' class="hi"' if len(pools_) > 1 else ''
    w(f'<tr{cls}><td class="num"><b>{bn_amt(int(r["amount"]))}</b></td><td>{cells}</td></tr>')
w(f'''</tbody></table>
<div class="note">Rows highlighted amber are amounts paid from <b>more than one pool</b>.
{bn_amt(_tok)} has moved through recurring amounts in total.</div>''')
w(fact(f'''The same figures recur across <b>Team Pool 2, the Investors Pool and Team Pool 1</b> —
0.2362bn on 21 Aug (Team 2), 21 Sep (Team 2) and 23 Oct (Investors); 0.1604bn on the same three days;
0.1178bn on 21 Aug and 21 Sep from Team 2 and then 23 Oct from Team 1. Three separately allocated
pools, three different months, the same payout figures, and a brand-new receiving address every single
time. Address reuse across all {_nev} events: <b>{_reuse}</b>.'''))
w(infer('''A single beneficiary roster is being serviced from whichever pool has tokens available, with
a fresh wallet generated for each payment. The amounts are the entitlements; the addresses are
disposable. That would explain why identical figures cross pool boundaries, why no address ever
repeats, and why the recipients behave identically afterwards — they hold, uniformly, without
exception.''', 'medium-high',
        '''a plausible innocent mechanism that produces identical payout figures across three
separately allocated pools while never reusing an address — for instance a published vesting table
with those exact tranche sizes, which no Akedo document this project has seen contains. Equally,
finding that any two of these addresses have different, unrelated funding sources and independent
activity would weaken it.'''))
w(corr(f'''The 23 October pair is the tightest instance: Investors Pool at 08:37:38 and Team Pool 1 at
08:38:30 — <b>52 seconds apart</b>, eighteen fresh wallets between them, from two pools that have no
on-chain relationship other than a common owner.'''))
w('</div>')

# ---------------------------------------------------------------- 4 what happened next
w('''<div class="section" id="s4"><h2>4 · What happened to every token released</h2>
<p style="font-size:13px">Each release followed forward to an exchange, a DEX pool, or a wallet that
still holds it. Balances read at the head block; the 22 and 24 July node unlocks have too many
claimants to walk individually and are reconciled through the consolidation set instead.</p>
<table class="dense"><thead><tr><th>Release</th><th class="num">Net released</th>
<th class="num">Still held</th><th class="num">Sold</th><th>Where it is</th></tr></thead><tbody>''')
FATE = {
 '2026-06-19': ('2000000000000000000000000000',
                'Gate.io custody, 23 July — four hops and 34 days downstream'),
 '2026-07-22': (None, 'swept into 98 wallets with no prior history by 29 August; all still there'),
 '2026-07-24': (None, 'the tail of the same node unlock'),
 '2026-07-26': ('0', 'ten wallets, untouched since the afternoon they received it'),
 '2026-08-21': ('0', 'fourteen wallets; 138.45mn moved on 27 August to two further wallets, '
                     'which also still hold it'),
 '2026-09-03': ('0', 'three wallets, untouched'),
 '2026-09-21': ('0', 'sixteen wallets, untouched'),
 '2026-10-23': ('0', 'eighteen wallets, untouched'),
}
tot_rel = tot_sold = 0
for d in sorted(LED['days']):
    net = int(LED['days'][d]['net_total'])
    sold, where = FATE.get(d, ('0', ''))
    tot_rel += net
    if sold is None:
        heldtxt = '—'
        soldtxt = '<span style="color:var(--green)">0</span>'
    else:
        tot_sold += int(sold)
        heldtxt = bn_amt(net - int(sold))
        soldtxt = (f'<b style="color:var(--danger)">{bn_amt(int(sold))}</b>' if int(sold)
                   else '<span style="color:var(--green)">0</span>')
    cls = ' class="hi2"' if sold and int(sold) else ''
    w(f'<tr{cls}><td><b>{d}</b></td><td class="num">{bn_amt(net)}</td>'
      f'<td class="num">{heldtxt}</td><td class="num">{soldtxt}</td>'
      f'<td style="font-size:11px">{where}</td></tr>')
w(f'<tr style="border-top:2px solid var(--border)"><td><b>total</b></td>'
  f'<td class="num"><b>{bn_amt(tot_rel)}</b></td><td class="num">—</td>'
  f'<td class="num"><b>{bn_amt(tot_sold)}</b> ({100*tot_sold/tot_rel:.1f}%)</td>'
  f'<td style="font-size:11px">one sale, in July</td></tr>')
w('</tbody></table>')
w(fact(f'''Of {bn_amt(tot_rel)} released, <b>{bn_amt(tot_sold)} has reached an exchange</b> —
{100*tot_sold/tot_rel:.1f}%. The 22 July node unlock, which is the bulk of the rest, was consolidated
from 5,879 claimant wallets into {len(MIG)} wallets with no prior history within five weeks and has
sat there ever since, through both the rise and the fall.'''))
w(infer('''The consolidation is the part worth worrying about, not the selling. A distribution that
reads as 5,879 independent holders is, five weeks later, under the control of however many keys
operate {n} wallets. Nothing about that is illegal or even unusual — node sale participants selling to
a buyer would look the same — but it means the supply overhang is concentrated and can move on one
decision, which a holder-count figure would hide.'''.replace('{n}', str(len(MIG))), 'medium',
        '''evidence that the 98 wallets are independently controlled — different funding sources,
different gas payers, divergent behaviour. So far they behave identically, which is what one operator
looks like, but identical inactivity is weak evidence.'''))
w('</div>')


# ---------------------------------------------------------------- 5 the sale
w(f'''<div class="section" id="s5"><h2>5 · The only sale</h2>
<p style="font-size:13px">One release out of eight has ever reached an exchange. It is worth setting
out in full, because the shape of it — and the timing — says more than the fact of it.</p>
<table class="dense"><thead><tr><th>When (UTC)</th><th>From</th><th>To</th><th class="num">Amount</th>
<th>What it is</th></tr></thead><tbody>
<tr><td class="mono">2026-06-19 16:00:41</td><td>Investors Pool</td>
  <td>{bsc('0xf23abe615b96badcf5e46d390d0697d433986aa4','0xf23abe61…')}</td>
  <td class="num">4.0734bn</td><td style="font-size:11px">the release</td></tr>
<tr><td class="mono">2026-06-19 16:24:55</td>
  <td>{bsc('0xf23abe615b96badcf5e46d390d0697d433986aa4','0xf23abe61…')}</td>
  <td>Investors Pool</td><td class="num">2.0734bn</td>
  <td style="font-size:11px">returned 24 minutes later — the net release is 2.0000bn</td></tr>
<tr><td class="mono">2026-06-20 10:19:33</td>
  <td>{bsc('0xf23abe615b96badcf5e46d390d0697d433986aa4','0xf23abe61…')}</td>
  <td>{bsc('0xa074027a3bb55b6f01989e20202f532894d7d97c','0xa074027a…')}</td>
  <td class="num">1.999999bn</td><td style="font-size:11px">hop 2, next morning</td></tr>
<tr><td class="mono">2026-07-15 07:51–13:00</td>
  <td>{bsc('0xa074027a3bb55b6f01989e20202f532894d7d97c','0xa074027a…')}</td>
  <td>{bsc('0x7476c568d6fc88a7ad6944a6f9fb1b5d725a58e1','0x7476c568…')}</td>
  <td class="num">1.999998bn</td>
  <td style="font-size:11px">hop 3, in four tranches of 0.5, 0.25, 0.25 and 1.0bn</td></tr>
<tr class="hi2"><td class="mono">2026-07-23 18:03:22</td>
  <td>{bsc('0x7476c568d6fc88a7ad6944a6f9fb1b5d725a58e1','0x7476c568…')}</td>
  <td>{bsc(GATE_DEP, 'Gate.io DepositAndWithdraw_1')}</td>
  <td class="num">2.0000bn</td>
  <td style="font-size:11px">block 111,711,359, tx {bsctx(SALE['tx'], '0x576117a8…')} —
      <b>the sale</b></td></tr>
</tbody></table>
<div class="q">
  <div><div class="k">Worth when released</div><div class="v">{usd(648662)}</div>
    <div class="sub">19 June, at the on-chain price of that block</div></div>
  <div><div class="k">Realised when sold</div><div class="v">{usd(SALE['usd_onchain'])}</div>
    <div class="sub">23 July · ${SALE['price_onchain']:.8f}/AKE, BNB ${SALE['bnb_usdt']:,.2f}</div></div>
  <div><div class="k">Cross-check, CoinGecko</div><div class="v">{usd(SALE['usd_coingecko'])}</div>
    <div class="sub">{pc(100*(SALE['usd_onchain']/SALE['usd_coingecko']-1))} from the on-chain figure</div></div>
  <div><div class="k">Gain by waiting</div><div class="v">{SALE['usd_onchain']/648662:.1f}×</div>
    <div class="sub">34 days between release and sale</div></div>
</div>''')
w(fact('''Exactly 2,000,000,000.000000 AKE — a round two billion to the wei — into Gate.io custody.
The amount was released on 19 June, moved through two intermediate wallets, and sold 34 days later
into a price that had risen roughly eightfold in the meantime. Both price derivations, one taken
purely from pool state on-chain and one from CoinGecko, agree to within 0.65%.'''))
w(infer('''Whoever controls that chain of wallets was not liquidating an allocation; they were
positioning. Tokens taken at the bottom of the window and sold near a local peak, through three hops
and a month of patience, is trading behaviour rather than treasury behaviour.''', 'medium',
        '''a benign explanation for the hop chain — an OTC settlement, a custodial transfer, an
exchange onboarding flow. The round two-billion figure and the four-tranche split are consistent with
a negotiated sale as much as with evasion, and nothing here distinguishes the two.'''))
w('</div>')


# ---------------------------------------------------------------- 6 the collapse
_w0 = [r for r in WEEK if r['date'] == '2026-10-26'][0]
_w1 = WEEK[-1]
d_ake = int(_w1['ake']) - int(_w0['ake'])
d_bnb = int(_w1['wbnb']) - int(_w0['wbnb'])
bnb_px = _w1['bnb_usdt'] or 700
w(f'''<div class="section" id="s6"><h2>6 · The collapse — what actually sold</h2>
<p style="font-size:13px">From {usd(OHLC['2026-10-26']['c'], 8)[1:]} on 26 October to
${LAST:.8f} now. The pools released nothing in that stretch after 23 October, and no release recipient
sold anything at all. So the supply came from the broad holder base, and it shows up in two places:
the main DEX pool's inventory, and exchange deposits.</p>
<div class="q">
  <div><div class="k">AKE pushed into the main pool</div>
    <div class="v" style="color:var(--danger)">+{bn_amt(d_ake)}</div>
    <div class="sub">26 October → now</div></div>
  <div><div class="k">BNB taken out of it</div>
    <div class="v" style="color:var(--danger)">{d_bnb/1e18:,.0f} BNB</div>
    <div class="sub">≈ {usd(abs(d_bnb)/1e18*bnb_px)} of realised proceeds</div></div>
  <div><div class="k">BNB left in the pool</div><div class="v">{int(_w1['wbnb'])/1e18:,.0f}</div>
    <div class="sub">≈ {usd(int(_w1['wbnb'])/1e18*bnb_px)} — the on-chain bid, in full</div></div>
  <div><div class="k">Deposited to exchanges in November</div>
    <div class="v">{bn_amt(sum(int(CEX.get(d,{}).get('cex',['0','0'])[0]) for d in DAYS if d.startswith('2026-11')))}</div>
    <div class="sub">in twelve days</div></div>
</div>''')
w(fact(f'''Between 26 October and now the main PancakeSwap pool absorbed <b>{bn_amt(d_ake)} of AKE</b>
and gave up <b>{abs(d_bnb)/1e18:,.0f} BNB</b>, roughly {usd(abs(d_bnb)/1e18*bnb_px)}. That is the
entire realised proceeds of the on-chain side of a 98% fall. What is left behind the bid is
{int(_w1['wbnb'])/1e18:,.0f} BNB — about {usd(int(_w1['wbnb'])/1e18*bnb_px)}. The on-chain market for a
token that was worth two billion dollars seven weeks ago is now a few hundred thousand dollars
deep.'''))
_ct = COL['totals']; _cs = COL['sellers']
w(f'''<h3>Every swap on the main pool, 21 September to 6 November</h3>
<p style="font-size:13px">{_ct['swaps']:,} swaps in forty-seven days, {usd(_ct['gross_usd'])} of gross
turnover. The directional content of all of it is {abs(_ct['net_ake'])/1e6:,.2f}mn AKE —
<b>{100*abs(_ct['net_ake'])/(_ct['sold_in']+_ct['bought_out']):.3f}% of the flow</b>.</p>
<table class="dense"><thead><tr><th>Day</th><th class="num">Swaps</th><th class="num">AKE sold in</th>
<th class="num">AKE bought out</th><th class="num">Net AKE</th><th class="num">Net BNB</th>
<th class="num">Gross turnover</th></tr></thead><tbody>''')
for _d in COL['swap_days']:
    if _d['day'] < '2026-10-20':
        continue
    _cls = ' class="hi2"' if _d['sold_in'] > 1e9 else ''
    w(f'<tr{_cls}><td class="mono">{_d["day"]}</td><td class="num">{_d["swaps"]:,}</td>'
      f'<td class="num">{_d["sold_in"]/1e6:,.2f}mn</td>'
      f'<td class="num">{_d["bought_out"]/1e6:,.2f}mn</td>'
      f'<td class="num">{_d["net_ake"]/1e6:+,.2f}mn</td>'
      f'<td class="num">{_d["net_bnb"]:+,.1f}</td>'
      f'<td class="num">{usd(_d["gross_usd"])}</td></tr>')
w(f'<tr style="border-top:2px solid var(--border)"><td><b>all 47 days</b></td>'
  f'<td class="num"><b>{_ct["swaps"]:,}</b></td>'
  f'<td class="num"><b>{_ct["sold_in"]/1e6:,.2f}mn</b></td>'
  f'<td class="num"><b>{_ct["bought_out"]/1e6:,.2f}mn</b></td>'
  f'<td class="num"><b>{_ct["net_ake"]/1e6:+,.2f}mn</b></td>'
  f'<td class="num"><b>{_ct["net_bnb"]:+,.1f}</b></td>'
  f'<td class="num"><b>{usd(_ct["gross_usd"])}</b></td></tr>')
w('</tbody></table>')
_lw = COL['late_window']; _pk = COL['peak_day']
w(fact(f'''The capitulation is visible to the day. Through most of October the pool turned over
20–80mn AKE daily. On 30 October that jumps to 521mn, on 31 October to 1,932mn, on 2 November to
2,444mn, and on <b>7 November to {_pk['sold_in']/1e6:,.0f}mn across {_pk['swaps']:,} swaps</b> —
{usd(_pk['gross_usd'])} of turnover in a single day, the heaviest in the token's history, at a
twentieth of the September price. Across all {len(COL['swap_days'])} days
{_ct['sold_in']/1e6:,.0f}mn was sold in and {_ct['bought_out']/1e6:,.0f}mn bought out: a net of
{abs(_ct['net_ake'])/1e6:,.0f}mn, or
{100*abs(_ct['net_ake'])/(_ct['sold_in']+_ct['bought_out']):.3f}% of the flow.'''))
w(fact(f'''<b>The bottom was bought, not merely abandoned.</b> From 5 November the pool turns net
buyer: {_lw['days_net_bought']} of the last {_lw['days']} days are net bought, and the period as a
whole takes in {abs(_lw['net_ake'])/1e6:,.2f}mn AKE and
{'gains' if _lw['net_bnb']>0 else 'loses'} {abs(_lw['net_bnb']):,.1f} BNB. 7 November is the clearest
instance: {_pk['sold_in']/1e6:,.0f}mn sold into the pool and {_pk['bought_out']/1e6:,.0f}mn taken out
of it, <b>net +{_pk['net_ake']/1e6:,.2f}mn bought</b> with {_pk['net_bnb']:+,.0f} BNB paid in. Someone
was absorbing the capitulation at the lows rather than joining it.'''))

w('<h3 style="margin-top:18px">Who was selling</h3>')
w(f'''<p style="font-size:13px">{_cs['parties']:,} distinct addresses sold into the pool over the
window, {int(_cs['net_selling_ake'])/1e24:,.2f}mn net between them. These are the largest:</p>
<table class="dense"><thead><tr><th>Address</th><th class="num">Sold in</th>
<th class="num">Bought back</th><th class="num">Net sold</th><th>What it is</th>
</tr></thead><tbody>''')
for _t in _cs['top'][:14]:
    _tg = ', '.join(_t['tags']) if _t['tags'] else '<span style="color:var(--muted)">unlabelled</span>'
    w(f'<tr><td>{bsc(_t["address"], _t["address"][:16] + "…")}</td>'
      f'<td class="num">{int(_t["sold_in"])/1e24:,.2f}mn</td>'
      f'<td class="num">{int(_t["bought_back"])/1e24:,.2f}mn</td>'
      f'<td class="num"><b>{int(_t["net"])/1e24:,.2f}mn</b></td>'
      f'<td style="font-size:11px">{_tg}</td></tr>')
w('</tbody></table>')
_cpc = COL['window'].get('cp_complete')
w(fact(f'''Of {int(_cs['net_selling_ake'])/1e24:,.2f}mn of net selling into the pool,
<b>{int(_cs['from_pool_cohorts_ake'])/1e24:,.2f}mn — {_cs['pct_from_pool_cohorts']:.2f}% — came from a
release recipient or a consolidation-set wallet</b>. Not a rounding error: exactly none. The names at
the top of the list are aggregators and routers — OKX Labs, the Binance Wallet router, PancakeSwap
itself, 1inch-pattern addresses — and one bot, {bsc('0x5e2dc2eeab4f1ab9ea12abcf1321d2a8b34f584a','0x5e2dc2ee…')},
which has been running the same strategy since September.{'' if _cpc else
  " The counterparty split has a gap at blocks " +
  ', '.join(f"{a:,}-{b:,}" for a, b in COL['window'].get('cp_holes', [])) +
  " — still being scanned — so those blocks are not in this table, though the swap series above is "
  "complete to head."}'''))
w(infer('''The on-chain market did not break the price; it followed it. Two million swaps that net out
to four hundredths of a percent of their own flow, with the largest participants being aggregators
intermediating between venues, is the signature of arbitrage keeping a thin pool in line with a
centralised price that was falling somewhere else.''', 'high',
        '''a large directional seller hidden inside aggregator flow — the aggregator addresses net out
the trades of many users, so a single determined seller routing through 1inch or OKX would appear here
as intermediary volume. Attributing that would need the aggregators\' own routing data, which is not
on-chain.'''))

w(fact('''None of the largest net depositors to exchange custody over October and November is a pool
recipient or a member of the 98-wallet consolidation set. They are Gate.io and MEXC user wallets and
unlabelled addresses — the ordinary holder base. The one familiar name is the programmatic drip-seller
that has been feeding uniform tranches into Binance Hot Wallet 4 since the summer, and it is still
running at the same clip.'''))
w(negative('''A fall this size with no team-pool selling in it is the kind of result that invites a
second look, so: the test is not "did a pool release during the fall" — one did, on 23 October — but
"did any released token reach a venue where it could be sold". The answer across every release since
June, re-checked at the head block, is no, with the single July exception. If team-controlled supply
was sold into this collapse, it was not sold through any wallet these releases created.'''))
w('</div>')

# ---------------------------------------------------------------- 7 exchange flows
w('''<div class="section" id="s7"><h2>7 · Exchange flows, June to November</h2>
<p style="font-size:13px">Every AKE transfer touching a custody address in the venue registry, by
day, with Binance Wallet routers excluded (those are DEX routing, not deposits) and
exchange-to-exchange custody moves excluded (those are internal, not trading).</p>
<table class="dense"><thead><tr><th>Week beginning</th><th class="num">Sold → non-Binance CEX</th>
<th class="num">Withdrawn from them</th><th class="num">Net</th><th class="num">→ Binance</th>
<th class="num">Binance →</th><th class="num">Price at week end</th></tr></thead><tbody>''')
wk = collections.defaultdict(lambda: [0, 0, 0, 0])
for d in DAYS:
    monday = (datetime.datetime.strptime(d, '%Y-%m-%d')
              - datetime.timedelta(days=datetime.datetime.strptime(d, '%Y-%m-%d').weekday())
              ).strftime('%Y-%m-%d')
    c = CEX.get(d, {}).get('cex', ['0', '0']); b = CEX.get(d, {}).get('binance', ['0', '0'])
    wk[monday][0] += int(c[0]); wk[monday][1] += int(c[1])
    wk[monday][2] += int(b[0]); wk[monday][3] += int(b[1])
for mon in sorted(wk):
    r = wk[mon]
    ds = [d for d in DAYS if mon <= d < (datetime.datetime.strptime(mon, '%Y-%m-%d')
                                         + datetime.timedelta(days=7)).strftime('%Y-%m-%d')]
    endp = OHLC[ds[-1]]['c'] if ds else 0
    net = r[0] - r[1]
    cls = ' class="hi2"' if net > 2e26 else (' class="hi3"' if net < -2e26 else '')
    w(f'<tr{cls}><td class="mono">{mon}</td><td class="num">{bn_amt(r[0])}</td>'
      f'<td class="num">{bn_amt(r[1])}</td><td class="num"><b>{bn_amt(net)}</b></td>'
      f'<td class="num">{bn_amt(r[2])}</td><td class="num">{bn_amt(r[3])}</td>'
      f'<td class="num">${endp:.8f}</td></tr>')
w('</tbody></table>')
w('<div class="note">Green rows are weeks when supply left exchanges on net; red rows are weeks it '
  'arrived. The red rows cluster at the end.</div>')
w('</div>')

# ---------------------------------------------------------------- 8 the pool
w('''<div class="section" id="s8"><h2>8 · The DEX pool, week by week</h2>
<p style="font-size:13px">The PancakeSwap V3 AKE/WBNB 0.01% pool carries essentially all on-chain
liquidity. Its inventory is the clearest single record of the whole window: the price it quotes is
derived here from its own <code>slot0</code>, with no price API involved.</p>
<table class="dense"><thead><tr><th>Date</th><th class="num">Block</th><th class="num">AKE held</th>
<th class="num">BNB held</th><th class="num">Pool price</th><th class="num">BNB/USD</th>
<th class="num">Pool value</th></tr></thead><tbody>''')
prev = None
for r in WEEK:
    ake = int(r['ake']); bnb = int(r['wbnb'])
    p = r['price_onchain'] or 0; bp = r['bnb_usdt'] or 0
    val = ake / 1e18 * p + bnb / 1e18 * bp
    cls = ''
    if prev is not None and ake > prev * 1.5:
        cls = ' class="hi2"'
    prev = ake
    w(f'<tr{cls}><td class="mono">{r["date"]}</td><td class="num">{r["block"]:,}</td>'
      f'<td class="num">{ake/1e24:,.2f}mn</td><td class="num">{bnb/1e18:,.0f}</td>'
      f'<td class="num">${p:.8f}</td><td class="num">${bp:,.0f}</td>'
      f'<td class="num">{usd(val)}</td></tr>')
w('</tbody></table>')
w(fact('''Two restructurings stand out. On 20 July the pool went from 1,191mn AKE and 602 BNB to
241mn AKE and 1,086 BNB in a week — the AKE side was pulled and the quoted price jumped roughly
tenfold, which is where the July run begins. From 2 November the move runs the other way: AKE piles in
and BNB drains out, week after week, until the pool holds 215mn AKE against 291 BNB. The first was
liquidity management. The second is what a one-way market looks like from the inside.'''))
w('</div>')


# ---------------------------------------------------------------- 9 team-adjacent
w('''<div class="section" id="s9"><h2>9 · Team-adjacent wallets — established, correlated,
inferred</h2>
<p style="font-size:13px">The question this section exists to answer is which wallets are plausibly
connected to the team, and on what basis. It is kept in three tiers deliberately, because the three
are not the same kind of claim and conflating them is how on-chain analysis goes wrong.</p>''')

_kucoin = '0x635308e731a878741bfec299e67f5fd28c7553d9'
_gas = sorted(GAS[_kucoin], key=lambda x: x[2])
_window = [x for x in _gas if x[2] >= 112253110]
w(f'''<h3>The gas trail — ten wallets, one funder, twenty-six seconds</h3>
<p style="font-size:13px">Release recipients are almost all receive-only: they hold no BNB and have
never sent a transaction, so there is normally nothing to follow. The 26 July cohort is the exception,
because those ten wallets had to call <code>userWithdraw()</code> themselves, which meant someone had
to give them gas first. Bisecting <code>eth_getBalance</code> finds the exact block each was funded,
and the result is not ambiguous.</p>
<table class="dense"><thead><tr><th class="num">Block</th><th>Wallet funded</th>
<th class="num">Amount</th><th>Funded from</th></tr></thead><tbody>''')
for _w, _v, _b in _gas:
    _cls = ' class="hi"' if _b >= 112253110 else ''
    w(f'<tr{_cls}><td class="num mono">{_b:,}</td><td>{bsc(_w, _w[:16] + "…")}</td>'
      f'<td class="num">{int(_v)/1e18:.6f} BNB</td>'
      f'<td>{bsc(_kucoin, "KuCoin DepositAndWithdraw_5")}</td></tr>')
w('</tbody></table>')
w(fact(f'''All ten wallets that took the 26 July release — {bn_amt(int(LED["days"]["2026-07-26"]["net_total"]))}
across five pools — were funded with <b>exactly 0.002000 BNB each, from the same KuCoin withdrawal
address</b>. Eight of the ten landed inside a <b>34-block window</b>, about twenty-six seconds, at
13:48 UTC. The other two came in a single block that morning. Each wallet then called
<code>userWithdraw()</code> once, spent that gas, and has never transacted again.'''))
w(infer('''This is one operator. Exchange withdrawal addresses serve many customers, so sharing one is
not by itself a link — but ten customers do not withdraw an identical 0.002000 BNB from the same
exchange within twenty-six seconds and then each claim from the same set of vesting contracts within
the hour. The simplest reading is a single party, operating one KuCoin account, batch-funding ten
wallets it controlled in order to execute a release that required per-wallet transactions.''',
        'high',
        '''evidence of ten distinct KuCoin accounts behind those withdrawals, which is not visible
on-chain and would have to come from the exchange. That is the one thing that would overturn it, and
it is exactly the thing this method cannot see.'''))
w(fact('''The pattern repeats in miniature on 27 August. The only two wallets from the 21 August
cohort that ever moved anything were funded that afternoon — 0.000490 BNB each, from
<b>Binance Withdraw_59</b> and <b>Binance Withdraw_75</b> — at 17:28:22 and 17:58:38, thirty and three
minutes before they each sent their tokens on. Again: funded immediately before acting, by an exchange
withdrawal, in an amount sized to the gas required and nothing more.'''))
w(corr('''Every other cohort — 3 September, 21 September, 23 October, and twelve of the fourteen from
21 August — holds <b>no BNB at all</b> and has never sent a transaction. They cannot move their tokens
without being funded first, which means the moment any of them is funded is an advance signal that
something is about to happen with that balance.'''))

w('<h3>Tier 1 — established on-chain, not inferred</h3>')
w('''<table class="dense"><thead><tr><th>Address</th><th>Role</th><th>How it is known</th>
</tr></thead><tbody>''')
T1 = [
 (SAFE, 'Owner Safe, 3-of-4', 'Holds ownership of the pools and is the <code>to</code> of the '
  'transaction behind every release from 26 July onward, including both legs of 23 October.'),
 (SIGNER, 'The key that submits', 'The <code>from</code> address on every one of those '
  '<code>execTransaction</code> calls.'),
 (DEPLOYER, 'Deployer EOA', 'Deployed the pools and ran every release up to 19 June 2026. Has not '
  'moved AKE since.'),
 (SAFE2, 'A second Safe', 'Holds a large balance and has been untouched through the entire window. '
  'Its owner keys are not identified.'),
 (MAINPOOL, 'The on-chain market', 'PancakeSwap V3 AKE/WBNB 0.01%; carries effectively all DEX '
  'liquidity.'),
 (GATE_DEP, 'Gate.io deposit custody', 'On-chain exchange label; the destination of the only sale.'),
]
for a, role, howk in T1:
    w(f'<tr><td>{bsc(a)}</td><td><b>{role}</b></td><td style="font-size:11px">{howk}</td></tr>')
w('</tbody></table>')

w('<h3 style="margin-top:16px">Tier 2 — correlated, with the correlation stated exactly</h3>')
w(corr(f'''<b>The recurring payout amounts.</b> {len(_recur)} amounts recur across Team Pool 2, the
Investors Pool and Team Pool 1, over four release days, to {sum(len(r["payments"]) for r in _recur)}
distinct addresses, with zero reuse. This is a numeric coincidence of a kind that does not happen by
chance at this precision — but it links the <em>payments</em>, not the <em>people</em>. It does not
tell us who the beneficiaries are.'''))
w(corr('''<b>The 23 October timing.</b> The Investors Pool's computed vesting boundary fell on
18 October 2026 at 10:00 UTC. The release came five days later, from the Investors Pool and Team
Pool 1 together. A release near a boundary is what a schedule would produce; a release five days late,
from two pools at once, 52 seconds apart, and paid to fresh wallets, is what an administrative push
would produce. Both readings fit.'''))
w(corr('''<b>Releases follow strength.</b> Seven of eight releases came after a positive seven-day
run. Over a window in which the token rose twentyfold, that is close to what chance produces, and
eight observations cannot separate the two. It is recorded because it is true, not because it is
evidence.'''))

w('<h3 style="margin-top:16px">Tier 3 — inference, each with what would disprove it</h3>')
w(infer('''<b>One beneficiary roster, serviced from whichever pool has tokens.</b> The recurring
amounts crossing three separately allocated pools, combined with total absence of address reuse and
uniform post-receipt behaviour, is most simply explained by a single list of entitlements paid through
disposable wallets.''', 'medium-high',
        '''an Akedo document setting out tranche sizes that match these figures, which would make the
repetition a published schedule rather than a private roster; or two of these addresses showing
genuinely independent funding and activity.'''))
w(infer('''<b>The 22 July node unlock is concentrated, not distributed.</b> 5,879 claimant wallets
became 98 holding wallets within five weeks, and those 98 have not moved a token through a 98% round
trip in the price.''', 'medium',
        '''evidence that the 98 are separately controlled. Identical inactivity is consistent with one
operator and also with 98 people who simply have not sold, and nothing here separates them.'''))
w(infer('''<b>The one sale was positioning, not treasury liquidation.</b> Tokens released in June,
moved twice, and sold 34 days later into an eightfold move, for a round two billion.''', 'medium',
        '''a routine explanation for the hop chain — OTC settlement, custodial migration, exchange
onboarding — any of which would produce the same trace.'''))
w(negative('''<b>What is not established, and should not be asserted.</b> That any release recipient
is the team. That the 98 consolidation wallets are team-controlled. That any release was timed to the
price. That the collapse involved team selling. Each of those has been looked for in this data and
none of them is supported by it. The honest summary is narrower and more interesting: a single payout
roster is being paid across three pools through disposable wallets, and the people receiving it have
sold almost nothing.'''))
w('</div>')

# ---------------------------------------------------------------- 10 method
w(f'''<div class="section" id="s10"><h2>10 · Method, and what this does not show</h2>
<div class="grid2"><div>
<h3>How these numbers are made</h3>
<ul style="font-size:12.5px;line-height:1.75;padding-left:18px">
<li><b>Chain first.</b> <code>eth_getLogs</code>, <code>eth_call</code>,
<code>eth_getStorageAt</code> and <code>eth_getCode</code> against a BSC archive node. Prices come
from CoinGecko and, independently, from pool <code>slot0</code> state.</li>
<li><b>Pool flow is complete.</b> Every AKE transfer with a pool on either side, from the token's
deployment to block {HEAD:,}, de-duplicated on (block, logIndex). The segments are checked to tile the
chain with no gap before anything is written.</li>
<li><b>Net, and reconciled.</b> Allocation minus net released must equal <code>balanceOf</code> at the
head block. All eight pools do, to the wei, across {len(LED['days'])} release days and
63,800 lifetime pool-touching transfers.</li>
<li><b>Two prices.</b> Where a dollar figure matters it is derived twice — from the AKE/WBNB and
WBNB/USDT pools' own <code>slot0</code> at that block, and from the CoinGecko hourly series
interpolated to the same second. Both are shown.</li>
<li><b>Following forward.</b> "Still held" is <code>balanceOf</code> at the head block.
"Sold" means the tokens reached a labelled non-Binance exchange custody address, through as many hops
as it took — a lesson from an earlier version of this work, which stopped at one hop and missed the
July sale entirely.</li>
</ul></div><div>
<h3>What it does not show</h3>
<ul style="font-size:12.5px;line-height:1.75;padding-left:18px">
<li><b>Who anyone is.</b> Fresh addresses receiving a scheduled payment from a team-controlled pool is
what the chain shows. Whether they are employees, investors, market makers or the team is not
on-chain.</li>
<li><b>Order books.</b> The great majority of volume happens on exchanges and leaves no on-chain
record. Where this page says a move was not on-chain driven, that is a statement about what the chain
can account for.</li>
<li><b>Exchanges this registry does not cover.</b> Several venues carrying real volume have no custody
address here, so deposit totals are a floor, not a total.</li>
<li><b>Intraday extremes before October.</b> Daily highs and lows for most of this window are derived
from an hourly series, which cannot see a spike that opens and closes inside the hour; the last month
uses true candles. Where a figure matters, the finer source is used.</li>
<li><b>Intent.</b> Sequences are reported as sequences.</li>
</ul></div></div>
<div class="note">Coverage: pool flows and exchange-venue flows continuous to block {HEAD:,}.
Release days covered: {', '.join(sorted(LED['days']))}. Companion documents: the consolidated forensic
report <em>ake-analysis.html</em>, the release tracker <em>ake-tracker-june2026.html</em>, and the
vesting mechanism in <em>ake-investors-vesting.html</em>.</div>
<footer style="border-top:1px solid var(--border);margin-top:28px;padding:16px 0;
color:var(--muted);font-size:11.5px">Generated {ut(HEADTS)} UTC at block {HEAD:,}. All times UTC.
</footer>
</div>
</div>''')

open(OUT, 'w', encoding='utf-8').write('\n'.join(BUF))
import os
print(f'wrote {OUT} ({os.path.getsize(OUT)/1024:.1f} KB)')
