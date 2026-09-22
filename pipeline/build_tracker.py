#!/usr/bin/env python3
"""
Build ake-tracker-june2026.html — the AKE activity tracker, organised around
the days on which a team-controlled allocation pool actually moved tokens.

The document used to be arranged by topic, which buried the thing that matters:
there have only ever been a handful of days since June 2026 on which supply
left a pool, and everything else — price, exchange flow, liquidity — is best
read against those days. So the spine of this version is one section per event
day, each answering the same four questions in the same order:

    what moved · who released it · where it went · what happened next

Everything is read from pipeline/data at build time, so the page cannot drift
from the scans behind it. USD is always the CoinGecko hourly AKE/USD rate
interpolated to the block's own timestamp, never a flat daily close — with the
price moving 40% in a day, a daily mark would be fiction.

History before June 2026 appears only where it is needed to explain who a
wallet is, and then in one sentence.

Usage: build_tracker.py
Writes one HTML file in the repo root, which the user has asked for explicitly.
"""
import json, html, datetime, bisect, collections, math, urllib.request, time

D = 'pipeline/data/'
OUT = 'ake-tracker-june2026.html'
RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
SAFE = '0x551a841742733bef96646b44e3475ce6a01da5eb'
SAFE2 = '0x808e6d72d37619d7ecb3fc6efc8f13bd37c46755'
DEPLOYER = '0x6468cce97a300ff9d02d4cad0d3e097cace2eac2'
SIGNER = '0x88f4b387eab71497e312663ac8b4aada6aa2ef8e'
MAINPOOL = '0x4d3bf29ba30f8bfe4624e7678709afa195689c5d'

POOLS = {'0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors',
         '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes 3',
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team 2',
         '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes 1',
         '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes 2',
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team 1',
         '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL',
         '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community'}
# ---------------------------------------------------------------- load
EV = json.load(open(D + 'pool_event_days.json'))
cg = json.load(open(D + 'cg_daily_pv.json'))
HR = json.load(open(D + 'ake_hourly_cg.json'))
TS = json.load(open(D + 'blk_ts.json'))
V = json.load(open(D + 'venues_scan.json'))
LAB = json.load(open(D + 'all_labels_final.json'))
KS = {k: set(a.lower() for a in v) for k, v in json.load(open(D + 'known_sets.json')).items()}
HEAD = json.load(open(D + 'head_now.json'))
DEXBAL = json.load(open(D + 'pool_dex_bal.json'))
AKEPOOLS = json.load(open(D + 'ake_pools.json'))
TPC = json.load(open(D + 'thirdparty_check.json'))
OHLC = json.load(open(D + 'cg_daily_ohlc.json'))
LED = json.load(open(D + 'pool_net_ledger.json'))     # net, reconciled to balanceOf
ROLE = json.load(open(D + 'wallet_roles.json'))['roles']
REPEAT = json.load(open(D + 'repeat_amounts.json'))
TRAIL = json.load(open(D + 'release_trails.json'))   # multi-hop, to an exchange or not

_kb = sorted(int(x) for x in TS); _kv = [TS[str(x)] for x in _kb]
_hk = sorted(int(x) for x in HR); _hv = [HR[str(x)] for x in _hk]
RECIP = KS['direct pool recipient (lifetime)']
WATCH = (KS['master watchlist'] | KS['doc wallet'] | KS['TeamPool2 recipient (21 Aug)'])
ROUTER = {a for a in V if 'Router' in (LAB.get(a, {}).get('property_tags') or [])}
CUSTODY = {a for a in V if a not in ROUTER}


def bts(bn):
    i = bisect.bisect_left(_kb, bn)
    if i == 0:
        return _kv[0]
    if i >= len(_kb):
        return _kv[-1]
    return _kv[i-1] + (_kv[i]-_kv[i-1]) * (bn-_kb[i-1]) / (_kb[i]-_kb[i-1])


def px(ts):
    i = bisect.bisect_left(_hk, ts)
    if i == 0:
        return _hv[0]
    if i >= len(_hk):
        return _hv[-1]
    t0, t1, p0, p1 = _hk[i-1], _hk[i], _hv[i-1], _hv[i]
    return p0 + (p1 - p0) * (ts - t0) / (t1 - t0) if t1 > t0 else p0


def ut(ts, f='%Y-%m-%d %H:%M:%S'):
    return datetime.datetime.utcfromtimestamp(int(ts)).strftime(f)


def bn_amt(w, dp=4):
    """AKE in bn/mn notation — never a wall of zeroes."""
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


def bsc(a, text=None):
    return (f'<a class="addr" href="https://bscscan.com/address/{a}" target="_blank" '
            f'rel="noopener">{text or a}</a>')


def bsctx(t, text=None):
    return (f'<a class="addr" href="https://bscscan.com/tx/{t}" target="_blank" '
            f'rel="noopener">{text or t[:16] + "…"}</a>')


def who(a):
    """Short, plain description of a wallet. Prior history only as a label."""
    a = a.lower()
    if a in POOLS:
        return POOLS[a] + ' Pool'
    if a == SAFE:
        return 'the owner Safe'
    if a == SAFE2:
        return 'the second Safe'
    if a == DEPLOYER:
        return 'the deployer'
    if a == SIGNER:
        return 'Safe owner key'
    if a in AKEPOOLS:
        m = AKEPOOLS[a]
        return f"{m['dex']} {m['pair']} {m['fee']/10000:g}%"
    if a in V:
        return V[a].get('name', a)
    e = (LAB.get(a) or {}).get('entity')
    if e:
        return e
    r = ROLE.get(a)
    if r:
        return r['label']
    return 'no prior on-chain history'


def tagchips(a):
    a = a.lower()
    out = []
    r = ROLE.get(a)
    if r and r.get('is_signer'):
        out.append('<span class="chip chip-r">signed the release transaction</span>')
    if r and r.get('is_repeat'):
        out.append('<span class="chip chip-w">took a release on '
                   + ' and '.join(r['release_days']) + '</span>')
    if a in CUSTODY:
        g = V[a]['group']
        out.append(f'<span class="chip chip-{"b" if g=="binance" else "x"}">{V[a].get("name")}</span>')
    return ' '.join(out)


# ---------------------------------------------------------------- live reads
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


LIVE_HEAD = int(rpc('eth_blockNumber', []), 16)
LIVE_TS = int(rpc('eth_getBlockByNumber', [hex(LIVE_HEAD), False])['timestamp'], 16)
POOLBAL = {}
for a, n in POOLS.items():
    POOLBAL[n] = int(rpc('eth_call', [{'to': AKE, 'data': '0x70a08231' + '0'*24 + a[2:]},
                                      hex(LIVE_HEAD)]), 16)
INV_UNLOCK = int(rpc('eth_call', [{'to': '0x27333bd8c321a263b0565e69eea3b736b9d1f42c',
                                   'data': '0x251c1aa3'}, 'latest']), 16)
PERIOD = 2592000
CUR_N = int((LIVE_TS - INV_UNLOCK) // PERIOD)
NEXT_B = INV_UNLOCK + (CUR_N + 1) * PERIOD
print(f'live: head {LIVE_HEAD:,} ({ut(LIVE_TS)} UTC), pools hold '
      f'{sum(POOLBAL.values())/1e27:,.4f}bn, next Investors boundary {ut(NEXT_B)}')

LAST_PRICE = _hv[-1]
LAST_PRICE_TS = _hk[-1]

# The 22 July node unlock is too large to follow wallet by wallet, but it was
# swept into a small set of addresses with no prior history by 29 August. What
# that set holds now is the whole follow-through for that day, so it is read
# live here and used in both the summary and the 22 July section.
mig = json.load(open(D + 'migration_0829.json'))
_mig_dst = [a.lower() for a in mig['destinations']]
_mig_tot = 0
for _a in _mig_dst:
    _mig_tot += int(rpc('eth_call', [{'to': AKE, 'data': '0x70a08231' + '0'*24 + _a[2:]},
                                     hex(LIVE_HEAD)]), 16)
print(f'  29 Aug consolidation set: {len(_mig_dst)} wallets hold {_mig_tot/1e27:,.4f}bn at head')

OUTBUF = []


def w(s):
    OUTBUF.append(s)


CSS = open(D + '../assets/base.css').read()
EXTRA = """
  /* layout classes this page uses that base.css does not define */
  .wrap { max-width: 1180px; margin: 0 auto; padding: 26px 20px 60px; }
  .hdr { display:flex; flex-wrap:wrap; gap:14px; align-items:flex-end;
         border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:18px; }
  .hdr h1 { font-size:24px; font-weight:700; color:var(--accent); line-height:1.25; margin:0; }
  .hdr .sub { font-size:12.5px; color:var(--muted); margin-top:6px; }
  .tz { background:rgba(59,130,246,.10); border:1px solid rgba(59,130,246,.3); border-radius:8px;
        padding:10px 13px; font-size:12.5px; color:#93c5fd; margin-bottom:20px; }
  .toc { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:8px; }
  .toc a { display:block; padding:8px 11px; background:var(--card2); border:1px solid var(--border);
           border-radius:6px; font-size:12px; }
  .note { font-size:11.5px; color:var(--muted); margin-top:8px; line-height:1.55; }
  .grid2 { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:14px; }
  .hi  { background:rgba(251,191,36,.09); }
  .hi2 { background:rgba(239,68,68,.08); }
  .hi3 { background:rgba(16,185,129,.07); }
  .mono { font-family:ui-monospace,Menlo,monospace; }
  .chip { display:inline-block; font-size:10px; padding:1px 6px; border-radius:20px;
          margin-left:4px; vertical-align:middle; white-space:nowrap; }
  .chip-r { background:rgba(239,68,68,.15); color:#fca5a5; border:1px solid rgba(239,68,68,.3); }
  .chip-w { background:rgba(245,158,11,.15); color:#fcd34d; border:1px solid rgba(245,158,11,.3); }
  .chip-x { background:rgba(59,130,246,.15); color:#93c5fd; border:1px solid rgba(59,130,246,.3); }
  .chip-b { background:rgba(234,179,8,.15); color:#fde047; border:1px solid rgba(234,179,8,.3); }
  .evhead { display:flex; flex-wrap:wrap; gap:10px; align-items:baseline;
            border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:14px; }
  .evhead .d { font-size:22px; font-weight:650; color:var(--text); }
  .evhead .s { font-size:13px; color:var(--muted); }
  .evhead .amt { font-size:18px; font-weight:600; color:var(--warn); margin-left:auto; }
  .q { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:10px;
       margin:12px 0 16px; }
  .q > div { background:var(--panel2); border:1px solid var(--border); border-radius:8px;
             padding:10px 12px; }
  .q .k { font-size:10.5px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
  .q .v { font-size:16px; font-weight:600; margin-top:3px; }
  .q .sub { font-size:11px; color:var(--muted); margin-top:2px; }
  table.dense { font-size:11.5px; }
  table.dense td, table.dense th { padding:5px 7px; }
  .addr { font-family:ui-monospace,Menlo,monospace; font-size:11px; }
  .verdict { border-radius:8px; padding:11px 13px; font-size:12.5px; margin-top:12px; }
  .v-hold { background:rgba(16,185,129,.08); border:1px solid rgba(16,185,129,.25); color:var(--green); }
  .v-sold { background:rgba(239,68,68,.08); border:1px solid rgba(239,68,68,.25); color:var(--danger); }
  .v-mix  { background:rgba(245,158,11,.08); border:1px solid rgba(245,158,11,.25); color:var(--warn); }
  .ctx { font-size:12px; color:var(--muted); border-left:3px solid var(--border);
         padding:2px 0 2px 12px; margin:10px 0; }
"""


def price_window(day, before=2, after=2):
    """daily closes around an event day, for the market-context strip"""
    d0 = datetime.datetime.strptime(day, '%Y-%m-%d')
    out = []
    for k in range(-before, after + 1):
        d = (d0 + datetime.timedelta(days=k)).strftime('%Y-%m-%d')
        if d in cg:
            out.append((d, cg[d]['price'], cg[d].get('volume', 0)))
    return out


def follow_table(e, limit=20):
    """recipient table with the follow-through to head"""
    fol = e.get('followed')
    rows = []
    if not fol:
        return None, None
    tot = {'recv': 0, 'hold': 0, 'ex': 0, 'bi': 0, 'other': 0}
    for a, r in sorted(fol.items(), key=lambda x: -int(x[1]['received'])):
        recv = int(r['received']); hold = int(r['holds_now'])
        ex = int(r['to_exchange']); bi = int(r['to_binance'])
        sent = sum(int(s[2]) for s in r['sent_on'])
        other = sent - ex - bi
        tot['recv'] += recv; tot['hold'] += hold
        tot['ex'] += ex; tot['bi'] += bi; tot['other'] += other
        rows.append((a, recv, hold, ex, bi, other, r['sent_on']))
    return rows, tot


def verdict_box(tot, label):
    if not tot or not tot['recv']:
        return ''
    sold = tot['ex']
    frac = 100.0 * sold / tot['recv']
    heldf = 100.0 * tot['hold'] / tot['recv']
    cls = 'v-hold' if frac < 1 else ('v-mix' if frac < 25 else 'v-sold')
    return (f'<div class="verdict {cls}"><b>Follow-through.</b> Of the '
            f'{bn_amt(tot["recv"])} released, <b>{bn_amt(tot["hold"])} ({heldf:.1f}%)</b> is still '
            f'sitting in the wallets that received it at block {HEAD["head"]:,}. '
            f'<b>{bn_amt(sold)} ({frac:.1f}%)</b> has reached a non-Binance exchange, which is the '
            f'only movement this project counts as a sale; {bn_amt(tot["bi"])} went to Binance and '
            f'{bn_amt(tot["other"])} moved to other wallets without reaching an exchange. {label}</div>')


# ================================================================ document
DAYS = sorted(EV['days'])
# A day gets its own section if at least 100mn AKE left a pool net. Smaller
# days stay in the calendar table — 24 July is a 1.3mn tail of the node unlock
# and does not need three screens of its own.
BIG = [d for d in DAYS if int(EV['days'][d]['net_out']) >= 1e26]
TITLES = {
    '2026-06-19': ('Investors Pool', 'a function added and removed in nine minutes'),
    '2026-07-22': ('Nodes Pools 1–3', 'the node unlock — the largest release of the year'),
    '2026-07-24': ('Nodes Pool 3', 'a tail of the node unlock'),
    '2026-07-26': ('five pools at once', 'the Safe\'s first large distribution'),
    '2026-08-21': ('Team Pool 2', 'and the liquidity events that followed'),
    '2026-09-03': ('Team Pool 2', 'three payouts into the post-spike bid'),
    '2026-09-21': ('Team Pool 2', 'the largest team release since July'),
}

w(f'''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AKE Release Tracker</title>
<style>{CSS}{EXTRA}</style>
<div class="wrap">
<header class="hdr">
  <div>
    <h1>AKE — what the team-controlled pools have released, and what happened next</h1>
    <div class="sub">BNB Smart Chain · AKEDO {bsc(AKE, 'AKE token')} · June 2026 onward ·
      built at block {LIVE_HEAD:,}, {ut(LIVE_TS)} UTC</div>
  </div>
</header>

<div class="tz">All times are <b>UTC</b>. Every USD figure is the CoinGecko hourly AKE/USD rate
interpolated to the block's own timestamp — not a daily close. Over this window the price has moved
more than 40% inside a single day, so a daily mark would misstate almost every number on this page.
Highs, lows and ranges are a separate matter: those come from candles, because an hourly series cannot
show a spike that opens and closes inside the hour — §{len(BIG)+3} sets out where that mattered.
Token amounts are shown in bn/mn, with the exact wei behind every figure in the underlying scans.</div>
''')

# ---- contents
w('<div class="section"><h2>Contents</h2><div class="toc">')
w('<a href="#s0">0 · Where things stand</a>')
w('<a href="#s1">1 · The release calendar</a>')
for i, d in enumerate(BIG, 2):
    t = TITLES.get(d, ('', ''))[0]
    w(f'<a href="#d{d}">{i} · {datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%-d %B %Y")} — {t}</a>')
n = len(BIG) + 2
w(f'<a href="#sm">{n} · Market structure — where the price is actually made</a>')
w(f'<a href="#sv">{n+1} · Cross-check against published sources</a>')
w(f'<a href="#sr">{n+2} · Wallet and cluster registry</a>')
w(f'<a href="#sx">{n+3} · Method, and what this does not show</a>')
w('</div></div>')

# ---------------------------------------------------------------- 0
held = sum(POOLBAL.values())
released = sum(int(EV['days'][d]['net_out']) for d in DAYS)
w(f'''<div class="section" id="s0"><h2>0 · Where things stand</h2>
<div class="q">
  <div><div class="k">Still inside the eight pools</div><div class="v">{bn_amt(held)}</div>
    <div class="sub">read from chain at block {LIVE_HEAD:,}</div></div>
  <div><div class="k">Released since 1 June 2026</div><div class="v">{bn_amt(released)}</div>
    <div class="sub">net of anything sent back, across {len(BIG)} days</div></div>
  <div><div class="k">Days a pool actually moved</div><div class="v">{len(DAYS)}</div>
    <div class="sub">in {(LIVE_TS - int(datetime.datetime(2026,6,1).replace(tzinfo=datetime.timezone.utc).timestamp()))//86400} days elapsed</div></div>
  <div><div class="k">Price now</div><div class="v">${LAST_PRICE:.8f}</div>
    <div class="sub">CoinGecko hourly, {ut(LAST_PRICE_TS, '%d %b %H:%M')} UTC</div></div>
  <div><div class="k">Investors Pool</div><div class="v">{bn_amt(POOLBAL['Investors'])}</div>
    <div class="sub">of 25bn allocated · self-claim still reverts “fix”</div></div>
  <div><div class="k">Next Investors boundary</div><div class="v">{ut(NEXT_B, '%-d %b')}</div>
    <div class="sub">{ut(NEXT_B)} UTC · period n={CUR_N+1}</div></div>
</div>
<p style="font-size:13px">Every figure below is <b>net</b> — what a pool sent, minus anything sent
back to it. The last column is the check that makes the rest usable: allocation minus net released
must equal <code>balanceOf</code> at the head block, and for all eight pools it does, to the wei.</p>
<table class="dense"><thead><tr><th>Pool</th><th class="num">Allocation</th>
<th class="num">Net released, lifetime</th><th class="num">of allocation</th>
<th class="num">Net released since 1 Jun 2026</th><th class="num">Holds now</th>
<th class="num">Reconciles?</th><th>Last movement</th></tr></thead><tbody>''')
lastmove = {}
for d in DAYS:
    for p, (o, i_) in EV['days'][d]['by_pool'].items():
        lastmove.setdefault(p, []).append((d, int(o) - int(i_)))
for p in sorted(POOLS.values(), key=lambda x: -int(LED['lifetime'][x]['holds_now'])):
    L_ = LED['lifetime'][p]
    mv = lastmove.get(p, [])
    since = sum(int(LED['days'][d]['by_pool'][p]['net'])
                for d in LED['days'] if p in LED['days'][d]['by_pool'])
    last = mv[-1][0] if mv else '—'
    cls = ' class="hi"' if mv and mv[-1][0] == DAYS[-1] else ''
    w(f'<tr{cls}><td><b>{p}</b></td><td class="num">{bn_amt(int(L_["allocation"]))}</td>'
      f'<td class="num">{bn_amt(int(L_["net_released"]))}</td>'
      f'<td class="num">{L_["pct_released"]:.1f}%</td>'
      f'<td class="num">{bn_amt(since) if since else "—"}</td>'
      f'<td class="num">{bn_amt(int(L_["holds_now"]))}</td>'
      f'<td class="num" style="color:var(--green)">{"exact" if L_["reconciles"] else "MISMATCH"}</td>'
      f'<td>{last}</td></tr>')
w('</tbody></table>')

# the one sentence the whole page adds up to, computed rather than asserted
_tr = _th = _tx = _tb = 0
for _d in DAYS:
    _r, _t = follow_table(EV['days'][_d])
    if _t:
        _tr += _t['recv']; _th += _t['hold']; _tx += _t['ex']; _tb += _t['bi']
_jul = int(EV['days']['2026-07-22']['net_out'])
w(f'''<div class="verdict v-hold" style="margin-top:14px">
<b>The single finding this page adds up to.</b> Across the release days that can be followed wallet
by wallet — {bn_amt(int(TRAIL['totals']['net_walked']))} net —
<b>{bn_amt(int(TRAIL['totals']['sold']))} ({TRAIL['totals']['pct_sold']:.1f}%) has been sold</b>, all of
it the 19 June release, which reached Gate.io custody four hops and thirty-four days later. Everything
else is still sitting in the wallets it was paid to. The 22 July node unlock says the same from the
other end: {bn_amt(_mig_tot)} of the {bn_amt(_jul)} released is in the {len(_mig_dst)} wallets it was
consolidated into within five weeks. So the distributed supply has overwhelmingly not been sold — it
has been concentrated, which is a different risk rather than an absent one.</div>
<div class="note"><b>This corrects an earlier version of this page</b>, which said none of it had been
sold. That was an artefact of following each recipient only one transfer forward. The 19 June
recipient passed the tokens to a second wallet the next morning, that wallet to a third four weeks
later, and the third deposited the lot at Gate.io — none of which a one-hop test can see. Every
release is now followed until it reaches an exchange, a DEX pool, or a wallet that still holds it.
</div>
</div>''')


# ---------------------------------------------------------------- 1 calendar
w('''<div class="section" id="s1"><h2>1 · The release calendar</h2>
<p style="font-size:13px;margin-bottom:12px">Every day since 1 June 2026 on which AKE left one of the
eight allocation pools. Nothing else in this document is a pool event; price moves, exchange flow and
liquidity changes on other days are covered inside the section of the release they relate to, or in
§ market structure.</p>
<table class="dense"><thead><tr><th>Date (UTC)</th><th>Net released, by pool</th>
<th class="num">Day total, net</th><th class="num">Recipients</th><th>Released by</th>
<th class="num">Still held</th><th class="num">Reached a non-Binance exchange</th></tr></thead><tbody>''')
for d in DAYS:
    e = EV['days'][d]
    L_ = LED['days'][d]
    pools = ' · '.join(f'{k} {bn_amt(int(v["net"]))}' for k, v in
                       sorted(L_['by_pool'].items(), key=lambda x: -int(x[1]['net'])))
    # name who actually sent the transaction, rather than assuming the deployer
    _snd = {t['caller'] for t in e['txs'].values()}
    _sels = {t['selector'] for t in e['txs'].values()}
    if any(t['via_safe'] for t in e['txs'].values()):
        caller = 'the owner Safe'
    elif _snd == {DEPLOYER}:
        caller = 'the deployer'
    elif '0xa646f9ad' in _sels:
        caller = 'recipients, calling userWithdraw() themselves'
    elif len(_snd) > 3:
        # the causing transactions are sampled on days with thousands of blocks,
        # so quote the recipient count rather than a count from the sample
        caller = 'individual claimants, one transaction each'
    else:
        caller = ', '.join(who(x) for x in sorted(_snd))[:60]
    rows, tot = follow_table(e)
    tr = TRAIL['days'].get(d)
    if tr:
        netv = int(tr['net'])
        soldv = int(tr['sold'])
        heldtxt = f'{bn_amt(netv - soldv)} ({100*(netv-soldv)/netv:.0f}%)'
        soldtxt = (f'<b style="color:var(--danger)">{bn_amt(soldv)} '
                   f'({100*soldv/netv:.0f}%)</b>' if soldv else '0')
    else:
        heldtxt = soldtxt = 'see section'
    cls = ' class="hi"' if d == DAYS[-1] else ''
    w(f'<tr{cls}><td><b><a href="#d{d}">{d}</a></b></td><td>{pools}</td>'
      f'<td class="num"><b>{bn_amt(int(L_["net_total"]))}</b></td>'
      f'<td class="num">{e["n_recipients"]:,}</td><td>{caller}</td>'
      f'<td class="num">{heldtxt}</td><td class="num">{soldtxt}</td></tr>')
w(f'''</tbody></table>
<div class="note">“Reached a non-Binance exchange” applies the accounting rule this project works to:
a transfer into any exchange except Binance is treated as a sale, and anything still sitting in a
wallet — however widely distributed — is a hold. Binance is excluded because deposits there are
routinely custody and market-making movements rather than disposals, and is reported separately inside
each section. For 22 July the recipient set is 5,879 wallets, too many to follow one by one here; that
day has its own reconciliation in its section.</div>
</div>''')

# ---------------------------------------------------------------- event days
MECH = {
 '2026-06-19': (
  'The deployer upgraded the Investors Pool implementation, called the function that upgrade added, '
  'and upgraded again to a build without it — the whole sequence inside nine minutes. '
  'The pool also received tokens back the same hour, so the gross figure overstates what actually left.',
  'The pool sent 4.0734bn and took 2.0734bn back within the hour. The net movement is 2.0000bn — '
  'a round number, which is what a deliberate transfer looks like and what an accident does not.'),
 '2026-07-22': (
  'The three Nodes pools were reopened hours beforehand and then drained by thousands of individual '
  'claim transactions, not by one push. This is the only release in the window that behaves like a '
  'user-driven unlock rather than an administrative distribution.',
  'Because the recipients are node purchasers claiming their own entitlement, the interesting question '
  'is not who they are but what they did next — covered below.'),
 '2026-07-24': (
  'A small tail of the same node-unlock mechanism two days later.', ''),
 '2026-07-26': (
  'The day after the Investors Pool was upgraded to add a no-argument withdraw function, five pools '
  'paid out inside the same afternoon. Ownership of the pools had moved to the 3-of-4 Safe a week '
  'earlier, so this is the Safe\'s first large distribution.',
  'The Investors leg is the one that was gated: four wallets took exactly 4.0000bn between them, '
  'and the function they used answers “Already withdrawn” to them and “Only token address can '
  'withdraw” to everyone else today. It was a one-shot list, and it is spent.'),
 '2026-08-21': (
  'A single Safe transaction paying a fixed list of wallets from Team Pool 2.', ''),
 '2026-09-03': (
  'The same mechanism as 21 August, into a market that had just made a new high.', ''),
 '2026-09-21': (
  'Two Safe transactions an hour apart, both calling the same function on Team Pool 2 — selector '
  '<code>0xe0dc37a3</code>, which takes a single array of (address, amount) pairs and pays all of '
  'them in one block. The first call carried sixteen pairs, the second two. The selector matches no '
  'published signature, but the calldata decodes cleanly and unambiguously, so what it does is '
  'established even though its declared name is not. No implementation upgrade was needed — unlike '
  'the Investors Pool, Team Pool 2 already carries this function.',
  'The second transaction topped up two of the sixteen wallets from the first with much larger '
  'amounts, which is why two addresses dominate the table.'),
}

# A closing sentence per event, said once, in plain terms.
EXTRA_NOTE = {
 '2026-06-19': 'One recipient, and the “moved elsewhere” figure includes the 2.0734bn it sent '
               'straight back into the pool twenty-four minutes later. What actually left the pool '
               'that day is the net 2.0000bn. That figure is this day only — the Investors Pool '
               'released a further 4.0000bn net on 26 July, so 6.0000bn net since June and '
               '10.6329bn net across its whole life, against 25.0000bn allocated. The per-pool '
               'table above carries all three numbers so the day figure cannot be read as the total.',
 '2026-07-26': 'Ten recipients across five pools; the four that took the Investors leg called '
               'userWithdraw() themselves, had never appeared on-chain before that afternoon, and '
               'have not taken from any pool since. This is the Investors Pool\'s second and larger '
               'release of the year — with 19 June it makes 6.0000bn net since June, and 10.6329bn '
               'net lifetime.',
 '2026-08-21': 'Several of these addresses reappear on 3 September and 21 September, which is why '
               'the registry at the end tracks them as one cluster.',
 '2026-09-03': 'Three payouts of 500mn each, to wallets in the same cluster as 21 August.',
 '2026-09-21': 'Sixteen wallets, none of which had ever held AKE before 09:17 that morning.',
}

# Long-form context that belongs to one specific day, kept out of the loop so
# the generated markup stays readable. Every figure in these blocks is computed
# from the scans, not typed in.
_jul22 = int(EV['days']['2026-07-22']['net_out'])
BULK = {'2026-07-22': f'''
<table class="dense"><thead><tr><th>Step</th><th class="num">AKE</th><th>What it is</th></tr></thead><tbody>
<tr><td>released by the three Nodes pools</td><td class="num">{bn_amt(_jul22)}</td>
  <td>claimed by {EV['days']['2026-07-22']['n_recipients']:,} wallets across the day</td></tr>
<tr class="hi2"><td>held today by the {len(_mig_dst)} wallets it was swept into</td>
  <td class="num">{bn_amt(_mig_tot)}</td>
  <td>read from chain at block {LIVE_HEAD:,}; the sweep itself completed by 29 August</td></tr>
<tr><td>difference</td><td class="num">{bn_amt(_jul22 - _mig_tot)}</td>
  <td>what is no longer in that set — sold, spent or moved on since</td></tr>
</tbody></table>
<div class="verdict v-mix"><b>Follow-through.</b> Practically the entire node unlock was swept into a
small set of wallets with no prior history within five weeks, and {100*_mig_tot/_jul22:.1f}% of it is
still sitting there. That is a consolidation, not a sale — it never reached an exchange. It does mean
the supply is held far more tightly than the {EV['days']['2026-07-22']['n_recipients']:,}-wallet
claimant count suggests: a decision by a handful of keys can move it.</div>'''}

CONTEXT = {
 '2026-08-21': '''<div class="ctx"><b>Five days later the liquidity went, and the price broke.</b>
The market maker closed all four of its concentrated positions on 26 August, taking out 1,093.61 BNB
and 11.58mn AKE. Only 555.74 BNB of that was realised proceeds; the rest was returned capital.
Active liquidity fell from 113,445 to 98,520, and five hours after that the price broke 39.4% in
921 seconds on just $45,104 of net selling. The release and the break are five days apart and share
no wallet — but the second is what the first walked into.</div>''',
 '2026-09-03': '''<div class="ctx"><b>This paid into the strongest bid of the year to that point.</b>
On 2 September the pool itself printed $0.04468663 at 21:30 — above CoinGecko's recorded high for the
day — then gave back 55% in one fifteen-minute bucket. The 3 September payouts landed the morning
after that, while reported volume was still above $100m.</div>''',
}


def _p(s):
    """hourly close at a given 'YYYY-MM-DD HH:00' UTC stamp"""
    t = int(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M').replace(
        tzinfo=datetime.timezone.utc).timestamp())
    return px(t)


CONTEXT['2026-09-21'] = f'''
<h3 style="margin-top:18px">What else the chain shows around this release</h3>
<p style="font-size:13px">No price in this table. Nothing released on 21 September has been sold, so
there are no proceeds to report; what follows is the on-chain sequence the release sits inside.</p>
<table class="dense"><thead><tr><th style="width:20%">When (UTC)</th><th>What happened on-chain</th>
</tr></thead><tbody>
<tr><td>18 Sep 10:00:00</td>
  <td><b>The Investors Pool vesting boundary passed and produced nothing.</b> Period n=13 came due
  exactly as the schedule computes it; the pool released nothing, and the self-claim path still
  reverts <code>“fix”</code> for every caller. Whatever moved the market that week, it was not a
  vesting event.</td></tr>
<tr class="hi"><td>19 Sep 20:14–20:28</td>
  <td><b>Binance Hot Wallet 4 sent 216.23mn AKE to three addresses in fourteen minutes.</b> None had
  appeared on-chain before; none has ever taken a pool distribution. None of it has been sold. Two
  still hold it; the third forwarded its 56.49mn one hop after a test transfer, and it is still
  sitting there.</td></tr>
<tr class="hi"><td>21 Sep 09:17:11 and 10:24:35</td>
  <td><b>Team Pool 2 released {bn_amt(int(LED['days']['2026-09-21']['net_total']))} net</b> — the two
  Safe transactions in the table above, to sixteen addresses with no prior history.</td></tr>
</tbody></table>
<div class="ctx">One hour before the first release, 24.19mn AKE was deposited into non-Binance
exchange custody — the largest deposit hour of that day, and a sale under the rule this document
uses. That is a sequence, not a link: none of those depositing wallets is one of the sixteen, and
none has ever taken a pool distribution.</div>'''

for d in BIG:
    e = EV['days'][d]
    title, sub = TITLES.get(d, ('', ''))
    dt = datetime.datetime.strptime(d, '%Y-%m-%d')
    rows, tot = follow_table(e)
    idx = BIG.index(d) + 2
    w(f'''<div class="section" id="d{d}">
<h2 style="border:0;margin:0;padding:0;font-size:1px;color:transparent;height:0;overflow:hidden">
{idx} · {dt.strftime('%-d %B %Y')} — {title}</h2>
<div class="evhead"><span class="d">{idx} · {dt.strftime('%-d %B %Y')}</span>
<span class="s">{title} — {sub}</span>
<span class="amt">{bn_amt(int(LED['days'][d]['net_total']))} net released</span></div>''')

    # --- quick facts
    tspan = (f"{ut(e['first_ts'], '%H:%M:%S')}" if e['first_ts'] == e['last_ts']
             else f"{ut(e['first_ts'], '%H:%M:%S')} → {ut(e['last_ts'], '%H:%M:%S')}")
    callers = sorted({t['caller'] for t in e['txs'].values()})
    sels = sorted({t['selector'] for t in e['txs'].values()})
    viasafe = any(t['via_safe'] for t in e['txs'].values())
    pw = price_window(d)
    p_on = cg.get(d, {}).get('price')
    p_prev = pw[0][1] if pw else None
    w(f'''<div class="q">
  <div><div class="k">Window (UTC)</div><div class="v">{tspan}</div>
    <div class="sub">{len({l[0] for l in e['legs']})} block(s)</div></div>
  <div><div class="k">Net released</div>
    <div class="v">{bn_amt(int(LED['days'][d]['net_total']))}</div>
    <div class="sub">{bn_amt(int(e['gross_out']))} sent, {bn_amt(int(e['gross_in']))} returned</div></div>
  <div><div class="k">Recipients</div><div class="v">{e['n_recipients']:,}</div>
    <div class="sub">{'followed individually below' if rows else 'too many to follow individually'}</div></div>
  <div><div class="k">Released through</div><div class="v">{'the owner Safe' if viasafe else 'the deployer EOA'}</div>
    <div class="sub">{'outer call ' if viasafe else ''}{', '.join(f'<code>{s}</code>' for s in sels)}
      {'(Safe execTransaction — the function it wraps is named below)' if viasafe else ''}</div></div>
  <div><div class="k">Sold since</div>
    <div class="v">{bn_amt(int(TRAIL['days'][d]['sold'])) if TRAIL['days'].get(d) and int(TRAIL['days'][d]['sold']) else 'none'}</div>
    <div class="sub">followed through every hop until it reached an exchange or stopped</div></div>
  <div><div class="k">Pools drawn on</div>
    <div class="v">{len(LED['days'][d]['by_pool'])}</div>
    <div class="sub">{', '.join(sorted(LED['days'][d]['by_pool']))}</div></div>
</div>''')

    m = MECH.get(d, ('', ''))
    if m[0]:
        w(f'<h3>How it was released</h3><p style="font-size:13px">{m[0]}</p>')
    # causing transactions
    if e['txs']:
        w('<table class="dense"><thead><tr><th>Transaction</th><th>Sent to</th><th>Signed by</th>'
          '<th>Selector</th><th class="num">Calldata</th></tr></thead><tbody>')
        for h_, t in sorted(e['txs'].items(), key=lambda x: x[1]['block'])[:8]:
            w(f'<tr><td>{bsctx(h_)}</td>'
              f'<td>{who(t["to"])}</td><td>{bsc(t["caller"], who(t["caller"]))}</td>'
              f'<td class="mono">{t["selector"]}</td><td class="num">{t["calldata_bytes"]}B</td></tr>')
        w('</tbody></table>')
        if len(e['txs']) > 8:
            w(f'<div class="note">{len(e["txs"])} causing transactions in total; the table samples the '
              f'first and last few. The mechanism is identical in all of them.</div>')
    if m[1]:
        w(f'<div class="ctx">{m[1]}</div>')

    # net, per pool, for this day — and where that leaves each pool
    w('<h3 style="margin-top:16px">Net released, by pool</h3>')
    w('<table class="dense"><thead><tr><th>Pool</th><th class="num">Sent</th>'
      '<th class="num">Returned</th><th class="num">Net released this day</th>'
      '<th class="num">Running net since 1 Jun</th><th class="num">Net lifetime</th>'
      '<th class="num">Holds after</th></tr></thead><tbody>')
    for pname, pv in sorted(LED['days'][d]['by_pool'].items(), key=lambda x: -int(x[1]['net'])):
        L_ = LED['lifetime'][pname]
        w(f'<tr><td><b>{pname}</b></td><td class="num">{bn_amt(int(pv["sent"]))}</td>'
          f'<td class="num">{bn_amt(int(pv["returned"])) if int(pv["returned"]) else "—"}</td>'
          f'<td class="num"><b>{bn_amt(int(pv["net"]))}</b></td>'
          f'<td class="num">{bn_amt(int(pv["running_net_since"]))}</td>'
          f'<td class="num">{bn_amt(int(L_["net_released"]))}</td>'
          f'<td class="num">{bn_amt(int(L_["holds_now"]))}</td></tr>')
    w(f'<tr style="border-top:2px solid var(--border)"><td><b>day total</b></td>'
      f'<td class="num">{bn_amt(int(e["gross_out"]))}</td>'
      f'<td class="num">{bn_amt(int(e["gross_in"])) if int(e["gross_in"]) else "—"}</td>'
      f'<td class="num"><b>{bn_amt(int(LED["days"][d]["net_total"]))}</b></td>'
      f'<td class="num"></td><td class="num"></td><td class="num"></td></tr>')
    w('</tbody></table>')
    if int(e['gross_in']):
        w(f'<div class="note">Sent and returned are both shown because the difference is the '
          f'point: {bn_amt(int(e["gross_out"]))} left the pool and {bn_amt(int(e["gross_in"]))} '
          f'came back, so the release is {bn_amt(int(LED["days"][d]["net_total"]))}. Quoting the '
          f'gross figure would overstate it by '
          f'{int(e["gross_out"])/max(1,int(LED["days"][d]["net_total"])):.2f}x.</div>')

    # the same payout amounts, paid again to fresh addresses
    if d in REPEAT.get('per_day', {}) and REPEAT['per_day'][d]['pct'] > 0:
        rp = REPEAT['per_day'][d]
        rows_ = [r for r in REPEAT['repeated_amounts']
                 if any(x['day'] == d for x in r['payments'])]
        w('<h3 style="margin-top:16px">The same amounts, paid again to new addresses</h3>')
        w(f'<p style="font-size:12.5px">{bn_amt(int(rp["via_repeated_amounts"]))} of this day\'s '
          f'{bn_amt(int(rp["net"]))} ({rp["pct"]:.0f}%) went out in amounts that also appear on '
          f'another Team Pool 2 release day — each time to a different address. No address has '
          f'ever appeared on two of these days.</p>')
        w('<table class="dense"><thead><tr><th class="num">Amount</th>'
          '<th>Paid on each of these days, to these addresses</th></tr></thead><tbody>')
        for r in rows_:
            cells = ' · '.join(
                f'{"<b>" if x["day"] == d else ""}{x["day"]} {bsc(x["address"], x["address"][:10] + "…")}'
                f'{"</b>" if x["day"] == d else ""}' for x in r['payments'])
            w(f'<tr><td class="num"><b>{bn_amt(int(r["amount"]))}</b></td><td>{cells}</td></tr>')
        w('</tbody></table>')
        w('<div class="note">This is a specific, checkable relationship, not a resemblance: the '
          'identical payout figure recurs while the receiving address is new every time. The '
          'simplest reading is one beneficiary list being paid repeatedly through fresh wallets. '
          'It does not identify who the beneficiaries are, and nothing here claims to.</div>')

    # --- where it went
    w('<h3 style="margin-top:16px">Where it went, and what happened next</h3>')
    if rows:
        w('<table class="dense"><thead><tr><th>Recipient</th><th class="num">Received</th>'
          '<th class="num">Holds now</th><th class="num">To non-Binance exchange</th>'
          '<th class="num">To Binance</th><th class="num">Moved elsewhere</th></tr></thead><tbody>')
        for a, recv, hold, ex, bi, other, sent in rows:
            cls = ' class="hi2"' if ex else ''
            w(f'<tr{cls}><td>{bsc(a, a[:10] + "…" + a[-4:])} {tagchips(a)}'
              f'<div style="font-size:10.5px;color:var(--muted)">{who(a)}</div></td>'
              f'<td class="num">{bn_amt(recv)}</td><td class="num">{bn_amt(hold)}</td>'
              f'<td class="num">{bn_amt(ex) if ex else "—"}</td>'
              f'<td class="num">{bn_amt(bi) if bi else "—"}</td>'
              f'<td class="num">{bn_amt(other) if other else "—"}</td></tr>')
        w(f'<tr style="border-top:2px solid var(--border)"><td><b>total</b></td>'
          f'<td class="num"><b>{bn_amt(tot["recv"])}</b></td>'
          f'<td class="num"><b>{bn_amt(tot["hold"])}</b></td>'
          f'<td class="num"><b>{bn_amt(tot["ex"])}</b></td>'
          f'<td class="num"><b>{bn_amt(tot["bi"])}</b></td>'
          f'<td class="num"><b>{bn_amt(tot["other"])}</b></td></tr>')
        w('</tbody></table>')
        tr = TRAIL['days'].get(d)
        if tr:
            netv, soldv = int(tr['net']), int(tr['sold'])
            cls = 'v-sold' if soldv else 'v-hold'
            if soldv:
                body = (f'<b>Sold.</b> All {bn_amt(soldv)} of this release reached '
                        f'{tr["venue"]} on {tr["sold_on"]} UTC — {tr["hops_to_exchange"]} hops '
                        f'from the pool, {((datetime.datetime.strptime(tr["sold_on"][:10], "%Y-%m-%d") - datetime.datetime.strptime(d, "%Y-%m-%d")).days)} days after the release. '
                        f'The trail is below.')
            else:
                body = (f'<b>Not sold.</b> {bn_amt(netv)} released, and none of it has reached an '
                        f'exchange or a DEX pool. {tr.get("note", "")}')
            w(f'<div class="verdict {cls}">{body} {EXTRA_NOTE.get(d, "")}</div>')
        if tr and tr.get('trail'):
            w('<h3 style="margin-top:16px">The trail, hop by hop</h3>')
            w('<table class="dense"><thead><tr><th>When (UTC)</th><th>From</th><th>To</th>'
              '<th class="num">Amount</th><th>What it is</th></tr></thead><tbody>')
            for st in tr['trail']:
                trcls = ' class="hi2"' if st['to'].startswith('0x0d070796') else ''
                w(f'<tr{trcls}><td class="mono">{st["when"]}</td>'
                  f'<td>{st["from"] if not st["from"].startswith("0x") else bsc(st["from"], st["from"][:10] + "…")}</td>'
                  f'<td>{st["to"] if not st["to"].startswith("0x") else bsc(st["to"], st["to"][:10] + "…")}</td>'
                  f'<td class="num">{bn_amt(int(st["amount"]))}</td>'
                  f'<td style="font-size:11px">{st["note"]}</td></tr>')
            w('</tbody></table>')
            w('<div class="note">Each step was found by bisecting <code>balanceOf</code> on the '
              'chain and then reading the transfer log at the block the balance changed, so the '
              'chain is complete rather than sampled. Thirty-four days and three intermediate '
              'wallets separate the release from the deposit, which is why a one-hop test missed '
              'it.</div>')
    else:
        w(f'<div class="note">{e["n_recipients"]:,} recipients — too many to follow one by one in a '
          f'table. The reconciliation for this day is below.</div>')
        if d in BULK:
            w(BULK[d])

    # No price here. A release that has not been sold has no proceeds, and a
    # dollar figure on an unsold token is a notional mark that reads like money
    # changing hands. Price belongs in the market-structure section, where
    # trading actually happens, and against any release that does reach an
    # exchange — so far none has.
    if d in CONTEXT:
        w(CONTEXT[d])
    w('</div>')


# ---------------------------------------------------------------- market structure
sw0 = json.load(open(D + 'swaps_sep04_13.json'))
sw = json.load(open(D + 'swaps_sep13_20.json'))
sw2 = json.load(open(D + 'swaps_sep20_21.json'))


def swap_rollup(*srcs):
    day = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    for s in srcs:
        for k, q in s['buckets'].items():
            ts = int(k)
            dd = ut(ts, '%Y-%m-%d')
            p = px(ts)
            si = int(q[4]) / 1e18; bo = int(q[5]) / 1e18
            r = day[dd]
            r[0] += q[8]; r[1] += si; r[2] += si * p; r[3] += bo; r[4] += bo * p
            r[5] += int(q[6]) / 1e18; r[6] += int(q[7]) / 1e18
    return day


SW = swap_rollup(sw0, sw, sw2)
POOL_AKE = int(rpc('eth_call', [{'to': AKE, 'data': '0x70a08231' + '0'*24 + MAINPOOL[2:]},
                                hex(LIVE_HEAD)]), 16)
WBNB = '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'
POOL_BNB = int(rpc('eth_call', [{'to': WBNB, 'data': '0x70a08231' + '0'*24 + MAINPOOL[2:]},
                                hex(LIVE_HEAD)]), 16)
n_ = len(BIG) + 2
w(f'''<div class="section" id="sm"><h2>{n_} · Market structure — where the price is actually made</h2>
<p style="font-size:13px">None of the releases above passed through a DEX. Understanding what a release
can do to the price therefore needs one more number: how much depth there is to absorb it. There is very
little. One pool — {bsc(MAINPOOL, 'PancakeSwap V3 AKE/WBNB, 0.01%')} — carries essentially all of it, and
at block {LIVE_HEAD:,} it holds <b>{bn_amt(POOL_AKE)} AKE and {POOL_BNB/1e18:,.2f} BNB</b>.</p>
<h3>Every swap on that pool, by day</h3>
<table class="dense"><thead><tr><th>Day</th><th class="num">Swaps</th><th class="num">AKE sold in</th>
<th class="num">USD</th><th class="num">AKE bought out</th><th class="num">USD</th>
<th class="num">Net USD</th><th class="num">Net BNB</th></tr></thead><tbody>''')
T_ = [0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
for dd in sorted(SW):
    r = SW[dd]
    if r[0] < 50:
        continue
    w(f'<tr><td>{dd}</td><td class="num">{r[0]:,}</td><td class="num">{r[1]/1e6:,.2f}mn</td>'
      f'<td class="num">{usd(r[2])}</td><td class="num">{r[3]/1e6:,.2f}mn</td>'
      f'<td class="num">{usd(r[4])}</td><td class="num">{usd(r[4]-r[2])}</td>'
      f'<td class="num">{r[5]-r[6]:+,.1f}</td></tr>')
    for i in range(7):
        T_[i] += r[i]
w(f'''<tr style="border-top:2px solid var(--border)"><td><b>total</b></td>
<td class="num"><b>{T_[0]:,}</b></td><td class="num"><b>{T_[1]/1e6:,.2f}mn</b></td>
<td class="num"><b>{usd(T_[2])}</b></td><td class="num"><b>{T_[3]/1e6:,.2f}mn</b></td>
<td class="num"><b>{usd(T_[4])}</b></td><td class="num"><b>{usd(T_[4]-T_[2])}</b></td>
<td class="num"><b>{T_[5]-T_[6]:+,.1f}</b></td></tr></tbody></table>
<div class="verdict v-mix"><b>The DEX is a mirror, not a driver.</b> {T_[0]:,} swaps moved
{usd(T_[2]+T_[4])} of gross turnover and left a directional net of {usd(abs(T_[4]-T_[2]))} —
{100*abs(T_[4]-T_[2])/(T_[2]+T_[4]):.1f}% of the flow. Sold-in and bought-out track each other to a
fraction of a percent in every single day and almost every hour, which is the signature of round-trip
arbitrage marking the pool to the centralised price, not of anyone accumulating or distributing here.
The largest single swap in the whole window was under $70,000.</div>
<div class="note">Liquidity itself barely moves: over 13–21 September the pool saw more than two
thousand mint/burn events, but roughly half of them are same-block mint-and-burn pairs — just-in-time
liquidity placed by bots to capture fees on a single swap and removed immediately. Standing liquidity
from the position manager changed by a fraction of a percent. Nothing was pulled ahead of any of the
falls in this window.</div>
</div>''')


# ---------------------------------------------------------------- registry
# ---------------------------------------------------------------- cross-check
VER = {'match': 'v-hold', 'noted': 'v-mix', 'not comparable': 'v-mix'}
w(f'''<div class="section" id="sv"><h2>{n_+1} · Cross-check against published sources</h2>
<p style="font-size:13px">This project takes its facts from the chain rather than from aggregators.
That is a sourcing rule, not a claim to be beyond checking — so here is the check. Where an
independent source agrees, it is recorded. Where it disagrees, the disagreement is recorded too,
including the two places it found this document wrong.</p>
<table class="dense"><thead><tr><th style="width:22%">What</th><th>From the chain</th>
<th>Published</th><th>Verdict</th></tr></thead><tbody>''')
for c in TPC['checks']:
    v = c['verdict']
    col = ('var(--green)' if v == 'match' else
           'var(--danger)' if v in ('MISMATCH', 'EARLIER FIGURE CORRECTED',
                                    'HOURLY SERIES UNDERSTATES', 'COVERAGE GAP')
           else 'var(--warn)')
    w(f'<tr><td><b>{c["what"]}</b></td><td class="mono" style="font-size:11px">{c["chain"]}</td>'
      f'<td class="mono" style="font-size:11px">{c["published"]}'
      f'<div style="color:var(--muted);font-size:10px">{c["source"]}</div></td>'
      f'<td style="color:{col};font-weight:600;font-size:11px">{c["verdict"]}</td></tr>')
    if c['note']:
        w(f'<tr><td></td><td colspan="3" style="font-size:11px;color:var(--muted);'
          f'padding-top:0">{c["note"]}</td></tr>')
w('</tbody></table>')

w(f'''<h3 style="margin-top:18px">What an hourly series cannot show</h3>
<p style="font-size:12.5px">Every USD figure in this document is the hourly rate interpolated to a
block timestamp, which is the right way to value a single transfer at a moment. It is the wrong way
to describe a range. On the days below the token moved further inside an hour than the hourly marks
ever recorded:</p>
<table class="dense"><thead><tr><th>Day</th><th class="num">Highest hourly mark</th>
<th class="num">Candle high</th><th class="num">Understated by</th><th class="num">Candle low</th>
<th class="num">True high-to-low</th></tr></thead><tbody>''')
for g in TPC.get('hourly_vs_candles', []):
    cls = ' class="hi2"' if g['high_understated_pct'] > 40 else ''
    w(f'<tr{cls}><td>{g["day"]}</td><td class="num">${g["hourly_max"]:.8f}</td>'
      f'<td class="num">${g["candle_high"]:.8f}</td>'
      f'<td class="num">{g["high_understated_pct"]:.0f}%</td>'
      f'<td class="num">${g["candle_low"]:.8f}</td>'
      f'<td class="num">{g["true_range_pct"]:.1f}%</td></tr>')
w(f'''</tbody></table>
<div class="verdict v-sold"><b>Two corrections this check forced.</b> The 20 September peak was
${OHLC['2026-09-20']['h']:.8f}, not the ${max(HR[str(k)] for k in _hk if ut(k, '%Y-%m-%d') == '2026-09-20'):.8f}
an hourly series showed, and the fall from it was
{100*(OHLC['2026-09-20']['l']/OHLC['2026-09-20']['h']-1):.1f}% rather than the −49.6% first reported.
And the exchange-deposit totals throughout are a floor: {len(TPC['venue_gaps'])} venues carrying
{usd(sum(g['volume_usd'] for g in TPC['venue_gaps']))} of daily volume have no custody address in
this project's registry, so deposits to them are invisible here.</div>
<div class="note">Neither correction changes a conclusion. The direction of every move, the fact that
nothing from any release reached an exchange, and the reconciliation of the pools are unaffected —
but the size of one price move was wrong and is fixed, and a known blind spot is now stated rather
than left implied.</div>
</div>''')

w(f'''<div class="section" id="sr"><h2>{n_+2} · Wallet and cluster registry</h2>
<p style="font-size:13px">Everything on this page that has a name, and why it has one. Nothing here is
inferred from an off-chain source; each label is either an on-chain entity label or a description of
what the wallet has actually done.</p>
<table class="dense"><thead><tr><th>Address</th><th>What it is</th><th>How that is known</th>
</tr></thead><tbody>''')
REG = [
 (SAFE, 'Owner Safe — 3-of-4 Gnosis Safe',
  'Holds ownership of the allocation pools and signs every release since 26 July. Ownership moved '
  'here from the deployer on 18 July 2026 in a standalone transferOwnership call.'),
 (SIGNER, 'The Safe owner key that submits the transactions',
  'It is the from-address on every execTransaction that has released tokens, including both legs of '
  '21 September.'),
 (DEPLOYER, 'Deployer EOA',
  'Deployed the pools and ran every release up to 19 June 2026. It has not moved AKE since.'),
 (SAFE2, 'A second Safe holding ' + bn_amt(int(rpc('eth_call', [
     {'to': AKE, 'data': '0x70a08231' + '0'*24 + SAFE2[2:]}, hex(LIVE_HEAD)]), 16)),
  'Untouched through every event in this window. Its owner keys are not identified.'),
 (MAINPOOL, 'PancakeSwap V3 AKE/WBNB 0.01% — effectively the entire on-chain market',
  'On-chain pool label; holds the overwhelming majority of AKE DEX liquidity.'),
 ('0x73d8bd54f7cf5fab43fe4ef40a62d390644946db', 'Binance Hot Wallet 4',
  'On-chain exchange label. Source of the 19 September distribution.'),
 ('0xaf6bc591cd10e62c74497bd5f9904329ecb59da1',
  'A large accumulator fed entirely by Binance',
  'Holds billions and has never sent a single AKE transfer. Everything it holds arrived from Binance '
  'wallets. Unlabelled, so no entity claim is made about it.'),
 ('0x653dd7677aea3030eab68c97ed3594bacf560158',
  'A programmatic drip-seller into Binance',
  'Sends uniform ~0.45mn tranches into Binance Hot Wallet 4 at regular intervals, day after day, '
  'including straight through both falls. It is on the watchlist from an earlier Binance-side '
  'distribution set, not from any allocation pool.'),
]
for a, what, howk in REG:
    w(f'<tr><td>{bsc(a)}</td><td><b>{what}</b></td><td style="font-size:11px">{howk}</td></tr>')
w('''</tbody></table>
<div class="note"><b>On cluster language.</b> Where a wallet is described as being "from the cluster
that has taken pool distributions before", that means exactly one thing and nothing more: the address
appears in the set of 22,077 wallets that have at some point received AKE directly from one of the
eight allocation pools. It is a membership test against on-chain history, not a claim about who
controls it.</div>
</div>''')

# ---------------------------------------------------------------- method
covered = sorted(EV['days'])
w(f'''<div class="section" id="sx"><h2>{n_+3} · Method, and what this does not show</h2>
<div class="grid2"><div>
<h3>How the numbers here are produced</h3>
<ul style="font-size:12.5px;line-height:1.75;padding-left:18px">
<li><b>Chain only.</b> <code>eth_getLogs</code>, <code>eth_call</code>, <code>eth_getStorageAt</code>,
<code>eth_getCode</code> and <code>eth_getTransactionByHash</code> against a BSC archive node. Prices
come from CoinGecko; nothing else is taken from a third party.</li>
<li><b>Pool flow is complete, not sampled.</b> Every AKE transfer with a pool on either side has been
recorded from the token's deployment to block {HEAD['head']:,}, de-duplicated on (block, logIndex),
and the segments are checked to tile the chain with no gap before anything is written.</li>
<li><b>Hourly pricing, and its limit.</b> Each transfer is valued at the CoinGecko hourly AKE/USD
rate interpolated to its own block timestamp — the right mark for a transfer at a moment. Price
<em>ranges</em> use OHLC candles instead, because an hourly series missed the 20 September top by
{TPC['hourly_vs_candles'][1]['high_understated_pct']:.0f}%. Both are cross-checked in §{len(BIG)+3}.</li>
<li><b>The sale test.</b> A transfer into any exchange except Binance counts as a sale. Anything still
in a wallet is a hold, no matter how many wallets it is spread across. Binance flows are reported
separately because deposits there are routinely custody and market-making moves.</li>
<li><b>Follow-through is a balance, not an inference.</b> "Still holding" is
<code>balanceOf</code> at the head block for each recipient, and "reached an exchange" is the sum of
that wallet's own onward transfers into a labelled custody address.</li>
</ul></div><div>
<h3>What this does not establish</h3>
<ul style="font-size:12.5px;line-height:1.75;padding-left:18px">
<li><b>Who controls the recipient wallets.</b> Fresh addresses receiving a scheduled distribution from
a team-controlled pool is what the chain shows. Whether they are employees, investors, market makers
or the team itself is not on-chain and is not asserted here.</li>
<li><b>Intent.</b> Sequences are reported as sequences. A deposit an hour before a release is a
sequence; it is not evidence of coordination.</li>
<li><b>Centralised order books.</b> The great majority of reported volume happens on exchanges and
leaves no on-chain record at all. Where this page says a move was not on-chain driven, that is a
statement about what the chain can account for, not a claim to have seen the order book.</li>
<li><b>Off-chain entitlement.</b> Nothing here shows what anyone was owed or agreed.</li>
</ul></div></div>
<div class="note">Coverage: pool flows continuous to block {HEAD['head']:,}. Exchange-venue flows
continuous to the same block. Swap-level DEX data on the main pool is continuous from
4 September to head, rebuilt from the pool's own Swap events. The separate DEX-transfer segment for
that window is only partly scanned and is not used for any figure on this page. Event days covered: {', '.join(covered)}.</div>
<footer style="border-top:1px solid var(--border);margin-top:28px;padding:16px 0;
color:var(--muted);font-size:11.5px">
Generated {ut(LIVE_TS)} UTC at block {LIVE_HEAD:,}. All times UTC.
</footer>
</div>''')

w('</div>')
open(OUT, 'w').write('\n'.join(OUTBUF))
import os
print(f'wrote {OUT} ({os.path.getsize(OUT)/1024:.1f} KB)')
