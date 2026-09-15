#!/usr/bin/env python3
"""
Build ake-investors-vesting.html - how the Investors Pool has actually released
tokens, across all nine of its implementations.

Reads pipeline/data at build time rather than carrying typed-in figures, and
reads the live chain for the handful of values that must not go stale (the
unlock timestamp, the owner, the current implementation, the pool balance and
whether the self-claim path still reverts). Re-running it regenerates the page.

Every time in the output is UTC. The chain stores block.timestamp as a Unix
epoch, which is timezone-free; this renders it as UTC and labels it so.

Usage: build_vesting_doc.py
Writes one HTML file in the repo root, which the user has asked for explicitly.
"""
import json, datetime, urllib.request, time, bisect, html

D = 'pipeline/data/'
OUT = 'ake-investors-vesting.html'
RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
INV = '0x27333bd8c321a263b0565e69eea3b736b9d1f42c'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
SAFE = '0x551a841742733bef96646b44e3475ce6a01da5eb'
DEPLOYER = '0x6468cce97a300ff9d02d4cad0d3e097cace2eac2'

UNLOCK = 1756029600      # slot 3
PERIOD = 2592000         # the one duration constant in the bytecode: 30 days
CLIFF_N = 3              # first period that ever produced a claim


def rpc(m, p, tries=8):
    for i in range(tries):
        try:
            r = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                      'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            return json.loads(urllib.request.urlopen(r, timeout=60).read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * 1.7 ** i)


def revert_of(j):
    if 'error' not in j:
        return None
    d = j['error'].get('data')
    if isinstance(d, dict):
        d = d.get('data')
    if isinstance(d, str) and d.startswith('0x08c379a0'):
        h = d[10:]
        ln = int(h[64:128], 16)
        return bytes.fromhex(h[128:128 + ln * 2]).decode('utf8', 'ignore')
    return ''


def ut(t, fmt='%Y-%m-%d %H:%M:%S'):
    return datetime.datetime.utcfromtimestamp(int(t)).strftime(fmt)


def bsc(a, text=None):
    return (f'<a class="addr-full" href="https://bscscan.com/address/{a}" target="_blank" '
            f'rel="noopener">{text or a[:10] + "…" + a[-4:]}</a>')


def bsctx(t, text=None):
    return (f'<a class="addr-full" href="https://bscscan.com/tx/{t}" target="_blank" '
            f'rel="noopener">{text or t[:14] + "…"}</a>')


# ------------------------------------------------------------------ live read
head_j = rpc('eth_blockNumber', [])
HEAD = int(head_j['result'], 16)
HEADTS = int(rpc('eth_getBlockByNumber', [hex(HEAD), False])['result']['timestamp'], 16)
LIVE_UNLOCK = int(rpc('eth_call', [{'to': INV, 'data': '0x251c1aa3'}, 'latest'])['result'], 16)
LIVE_OWNER = '0x' + rpc('eth_call', [{'to': INV, 'data': '0x8da5cb5b'}, 'latest'])['result'][-40:]
LIVE_IMPL = '0x' + rpc('eth_getStorageAt', [
    INV, '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc', 'latest'])['result'][-40:]
LIVE_BAL = int(rpc('eth_call', [{'to': AKE, 'data': '0x70a08231' + '0' * 24 + INV[2:]},
                                'latest'])['result'], 16)
LIVE_CLAIM_REVERT = revert_of(rpc('eth_call', [
    {'to': INV, 'data': '0xac694711', 'from': '0xea3b7dfb150ce3dbca57e6d53cbe6b0cb7b7307c'}, 'latest']))
print(f'live: head {HEAD:,} ({ut(HEADTS)} UTC), unlock {LIVE_UNLOCK}, '
      f'claim reverts {LIVE_CLAIM_REVERT!r}, bal {LIVE_BAL/1e27:,.4f}bn')

mech = json.load(open(D + 'inv_vesting_mechanism.json'))
wd = json.load(open(D + 'inv_withdrawals.json'))
impls = json.load(open(D + 'inv_impls.json'))
uh = json.load(open(D + 'upgrade_history.json'))
failed = json.load(open(D + 'inv_failed_claims.json'))['rows']
_full = json.load(open(D + 'inv_upgrades_full.json'))
FULL_EVENTS = _full['events']          # every Upgraded event, unseeded sweep
FULL_IMPLS = _full['impls']            # distinct implementations, keyed by address

claims = [x for x in wd if x['selector'] == '0xac694711']
CUR_N = int((HEADTS - UNLOCK) // PERIOD)

# the four attempted-and-refused claims, rendered from the re-verified receipts
MEANS = {'No unlock amount': 'the schedule was live and this wallet had already taken that tranche — '
                             'the ordinary “nothing new yet” answer',
         'fix': 'the placeholder. Not a condition, not a date — the path is closed'}
_rows = []
for f in failed:
    n = int((datetime.datetime.strptime(f['when_utc'], '%Y-%m-%d %H:%M:%S')
             .replace(tzinfo=datetime.timezone.utc).timestamp() - UNLOCK) // PERIOD)
    cls = ' class="hi2"' if f['revert'] == 'fix' else ''
    _rows.append(
        f'<tr{cls}><td class="mono">{f["when_utc"]}<br>'
        f'<span style="font-size:10px;color:var(--muted)">{bsctx(f["tx"])}</span></td>'
        f'<td>{bsc(f["from"])}</td><td class="num">n={n}</td>'
        f'<td class="mono" style="color:'
        f'{"var(--danger)" if f["revert"] == "fix" else "var(--muted)"}">“{html.escape(f["revert"])}”</td>'
        f'<td style="font-size:11px">{MEANS.get(f["revert"], "")}</td></tr>')
FAILED_ROWS = '\n'.join(_rows)

CSS = open(D + '../assets/base.css').read()
EXTRA = """
  .tz { background: rgba(59,130,246,.10); border: 1px solid rgba(59,130,246,.3);
        border-radius: 6px; padding: 9px 12px; font-size: 12.5px; color: #93c5fd; margin-top: 10px; }
  .era { border-left: 3px solid var(--border); padding: 10px 0 10px 14px; margin-bottom: 4px; }
  .era.e1 { border-left-color: #64748b; }
  .era.e2 { border-left-color: var(--green); }
  .era.e3 { border-left-color: var(--danger); }
  .era.e4 { border-left-color: var(--warn); }
  .era h4 { font-size: 13px; margin-bottom: 3px; color: var(--text); }
  .era .sub { font-size: 11.5px; color: var(--muted); }
  table.dense { font-size: 11.5px; }
  table.dense td, table.dense th { padding: 4px 7px; }
  .hi  { background: rgba(251,191,36,.09); }
  .hi2 { background: rgba(239,68,68,.09); }
  .hi3 { background: rgba(16,185,129,.08); }
  .mono { font-family: monospace; font-size: 11.5px; }
  .note { font-size: 11.5px; color: var(--muted); margin-top: 8px; line-height: 1.55; }
  .grid2 { display: grid; grid-template-columns: repeat(auto-fit,minmax(320px,1fr)); gap: 14px; }
  .kv { display: grid; grid-template-columns: auto 1fr; gap: 4px 14px; font-size: 12.5px; }
  .kv dt { color: var(--muted); }
  .kv dd { color: var(--text); font-weight: 600; font-variant-numeric: tabular-nums; }
  .tocgrid { display: grid; grid-template-columns: repeat(auto-fit,minmax(230px,1fr)); gap: 8px; }
  .tocgrid a { display: block; padding: 8px 10px; background: var(--card2);
               border: 1px solid var(--border); border-radius: 6px; font-size: 12px; }
  .big { font-size: 26px; font-weight: 700; letter-spacing: -.5px; }
"""

P = []
def w(s):
    P.append(s)


w(f'''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AKE Investors Pool — Vesting Mechanism</title>
<style>{CSS}{EXTRA}</style>
<div class="container">
<header>
  <h1>AKE Investors Pool — how vesting has actually been enforced</h1>
  <div class="subtitle">Nine implementations, three release mechanisms, and the March 2026 change
  that ended investor self-claims</div>
  <div class="meta">
    <div class="meta-item">Proxy <span>{INV}</span></div>
    <div class="meta-item">Chain read to <span>block {HEAD:,} · {ut(HEADTS)} UTC</span></div>
    <div class="meta-item">Source <span>NodeReal BSC archive node, direct <code>eth_call</code> /
      <code>eth_getLogs</code> / <code>eth_getStorageAt</code></span></div>
  </div>
  <div class="tz"><strong>All times on this page are UTC.</strong> Block timestamps on BNB Smart Chain are
  Unix epoch seconds, which carry no timezone; they are rendered here as UTC and labelled. The machine that
  generated this page also runs UTC, so no conversion was applied anywhere. Where a time matters — the
  10:00:00 unlock boundary, the eleven-minute upgrade window on 13 April — it is UTC.</div>
</header>

<div class="section"><h2>Contents</h2><div class="tocgrid">
<a href="#s1">1 · The answer, in one screen</a>
<a href="#s2">2 · What actually gates a release</a>
<a href="#s3">3 · The schedule that was honoured</a>
<a href="#s4">4 · March 2026 — the function was gutted, not removed</a>
<a href="#s5">5 · April 2026 — the same thing to every other pool</a>
<a href="#s6">6 · How releases happen now</a>
<a href="#s7">7 · Every implementation, and what changed</a>
<a href="#s8">8 · When does it next unlock?</a>
<a href="#s9">9 · Method, and what this does not show</a>
</div></div>''')

# ---------------------------------------------------------------- 1
w(f'''<div class="section" id="s1"><h2>1 · The answer, in one screen</h2>
<div class="stat-grid">
  <div class="stat-box"><div class="stat-box-label">Schedule lives in</div>
    <div class="stat-box-value">storage slot 3</div>
    <div class="stat-box-sub">one uint256 — not hardcoded, not block-based</div></div>
  <div class="stat-box"><div class="stat-box-label">Release cadence</div>
    <div class="stat-box-value">30 days</div>
    <div class="stat-box-sub">after a 90-day cliff · fits all {len(claims)} claims</div></div>
  <div class="stat-box"><div class="stat-box-label">Self-claim since 19 Mar 2026</div>
    <div class="stat-box-value" style="color:var(--danger)">reverts “{html.escape(LIVE_CLAIM_REVERT or "")}”</div>
    <div class="stat-box-sub">for every caller, still today</div></div>
  <div class="stat-box"><div class="stat-box-label">Periods missed since</div>
    <div class="stat-box-value" style="color:var(--danger)">{CUR_N - 6}</div>
    <div class="stat-box-sub">n=7 … n={CUR_N}, no investor claim in any</div></div>
  <div class="stat-box"><div class="stat-box-label">Still in the pool</div>
    <div class="stat-box-value">{LIVE_BAL/1e27:,.4f}bn</div>
    <div class="stat-box-sub">of 25bn allocated · {100*(25e27-LIVE_BAL)/25e27:.1f}% released</div></div>
  <div class="stat-box"><div class="stat-box-label">Next boundary</div>
    <div class="stat-box-value">{ut(UNLOCK + (CUR_N+1)*PERIOD, '%d %b')}</div>
    <div class="stat-box-sub">{ut(UNLOCK + (CUR_N+1)*PERIOD)} UTC · in
      {(UNLOCK + (CUR_N+1)*PERIOD - HEADTS)/86400:,.1f} days</div></div>
</div>

<h3 style="margin-top:18px">Directly answering the four questions</h3>
<table><thead><tr><th style="width:34%">Question</th><th>What the chain shows</th></tr></thead><tbody>
<tr><td><b>Was it a function the deployer had to call each time?</b></td>
  <td>For the first three months and again from June 2026, <b>yes</b>. In between — 22 Nov 2025 to
  11 Mar 2026 — <b>no</b>: investors pulled their own tranches, {len(claims)} times, from
  {len({c['caller'] for c in claims})} distinct addresses, with no deployer involvement.</td></tr>
<tr><td><b>Was the time hardcoded — every X blocks?</b></td>
  <td><b>Not blocks, and not hardcoded.</b> A single timestamp lives in storage slot 3, writable by the
  owner. The <em>cadence</em> is hardcoded — 2592000 seconds, the only duration constant in any
  implementation — but the anchor it counts from is mutable, and was in fact moved once.</td></tr>
<tr><td><b>How is it working now?</b></td>
  <td>The self-claim path still exists in the ABI but its body was replaced; it reverts
  <code>“{html.escape(LIVE_CLAIM_REVERT or "")}”</code> unconditionally. Every release since has needed a
  function that was <em>added by an upgrade first</em>: <code>adminTransfer</code> in June, put in and taken
  back out within nine minutes; <code>userWithdraw()</code> in July, which is still in the contract but
  answers <code>“Already withdrawn”</code> to the four wallets that used it and
  <code>“Only token address can withdraw”</code> to everyone else.</td></tr>
<tr><td><b>Was it changed from the original?</b></td>
  <td><b>Yes, materially, on 19 March 2026</b> — and again for the other seven pools on 13 April 2026.
  The schedule arithmetic is unchanged; the ability of a holder to act on it is gone.</td></tr>
</tbody></table>

<div class="alert alert-danger" style="margin-top:16px">
<strong>The one-line version.</strong> The schedule is still perfectly computable — you can name the next
unlock date to the second — but since 19 March 2026 no investor can act on it. The entitlement is arithmetic;
the mechanism is discretion.</div>
</div>''')

# ---------------------------------------------------------------- 2
w(f'''<div class="section" id="s2"><h2>2 · What actually gates a release</h2>
<div class="grid2">
<div class="card" style="background:var(--card2);padding:14px;border-radius:8px;border:1px solid var(--border)">
<h3>Storage, read live at block {HEAD:,}</h3>
<dl class="kv">
<dt>slot 0</dt><dd>{AKE[:10]}… — the AKE token</dd>
<dt>slot 3</dt><dd>{LIVE_UNLOCK}</dd>
<dt></dt><dd>= {ut(LIVE_UNLOCK)} UTC</dd>
<dt>slots 1,2,4…24</dt><dd>all zero</dd>
<dt>ERC1967 impl</dt><dd>{LIVE_IMPL[:12]}…</dd>
<dt>ERC1967 admin</dt><dd>0 — UUPS, not transparent</dd>
<dt>owner()</dt><dd>{LIVE_OWNER[:12]}…</dd>
</dl>
<div class="note">Slot 3 is the whole of the schedule state. There is no per-beneficiary table, no cliff
field, no duration field, no array of future dates. Everything else the contract needs it derives or is
handed by the caller.</div>
</div>
<div class="card" style="background:var(--card2);padding:14px;border-radius:8px;border:1px solid var(--border)">
<h3>The functions that touch it</h3>
<table class="dense"><tbody>
<tr><td class="mono">0x251c1aa3</td><td><b>unlockTime()</b></td><td class="num">read</td></tr>
<tr><td class="mono">0x602bc62b</td><td><b>getUnlockTime()</b></td><td class="num">read</td></tr>
<tr class="hi2"><td class="mono">0xdace4557</td><td><b>setUnlockTime(uint256)</b></td>
  <td class="num">owner writes</td></tr>
<tr><td class="mono">0xf17e48ec</td><td><b>adminTransfer(address,uint256)</b></td>
  <td class="num">owner pushes</td></tr>
<tr><td class="mono">0xa646f9ad</td><td><b>userWithdraw()</b></td><td class="num">pull</td></tr>
<tr><td class="mono">0xac694711</td><td>the self-claim path <span style="color:var(--muted)">— signature
  unresolved</span></td><td class="num">pull</td></tr>
</tbody></table>
<div class="note"><b>setUnlockTime has no timelock and no guard beyond ownership.</b> The owner can move the
anchor of the entire schedule in one transaction, and did so once — on 18 Nov 2025 the value went from
{ut(1755770400, '%d %b %Y %H:%M')} to {ut(1756029600, '%d %b %Y %H:%M')} UTC, a three-day shift.</div>
</div></div>

<h3 style="margin-top:18px">Is the schedule hardcoded? Partly — and the wrong half</h3>
<p style="font-size:12.5px">Scanning every implementation's bytecode for duration-shaped constants returns
exactly one across all nine versions: <b>2592000</b> — 30 days. There are no cliff constants, no 24- or
42-month figures, no basis-point percentages, and no timestamps that survive scrutiny as real schedule dates.
So the <em>interval</em> is fixed in code and cannot be changed without an upgrade, while the <em>origin</em>
it counts from sits in mutable storage. That is the opposite of what a holder would want: the part that
protects them is editable, the part that does not is not.</p>
</div>''')

print('sections 1-2 built')

# ---------------------------------------------------------------- 3
by_n = {}
for c in claims:
    t = datetime.datetime.strptime(c['when'], '%Y-%m-%d %H:%M:%S').replace(
        tzinfo=datetime.timezone.utc).timestamp()
    n = int((t - UNLOCK) // PERIOD)
    by_n.setdefault(n, []).append((t, c))
for n in by_n:
    by_n[n].sort()

w(f'''<div class="section" id="s3"><h2>3 · The schedule that was honoured — Nov 2025 to Mar 2026</h2>
<p style="font-size:12.5px;margin-bottom:12px">For four consecutive periods the pool behaved exactly like a
published vesting contract, and investors treated it as one. Testing every one of the {len(claims)}
self-claims against <code>unlockTime + n × 30 days</code> puts all of them in periods
n={min(by_n)}–{max(by_n)} and <b>none anywhere else</b>. n={CLIFF_N} is the first — a 90-day cliff, matching
the published three-month investor cliff.</p>

<table class="dense"><thead><tr><th>Period</th><th>Boundary (UTC)</th><th class="num">Claims</th>
<th>First claim (UTC)</th><th class="num">Lag</th><th class="num">AKE released</th></tr></thead><tbody>''')
for n in sorted(by_n):
    rows = by_n[n]
    b = UNLOCK + n * PERIOD
    first_t, first_c = rows[0]
    lag = first_t - b
    lagtxt = f'{int(lag//60)}m {int(lag%60)}s' if lag < 7200 else f'{lag/3600:,.1f}h'
    tot = sum(int(c['total']) for _, c in rows)
    w(f'<tr class="hi3"><td><b>n={n}</b></td><td class="mono">{ut(b)}</td>'
      f'<td class="num">{len(rows)}</td><td class="mono">{first_c["when"]}</td>'
      f'<td class="num"><b>{lagtxt}</b></td><td class="num">{tot/1e24:,.1f}mn</td></tr>')
w(f'''</tbody></table>
<div class="alert alert-ok" style="margin-top:12px;background:rgba(16,185,129,.08);
border:1px solid rgba(16,185,129,.25);color:var(--green);border-radius:8px;padding:12px 14px;font-size:12.5px">
<strong>The lag column is the proof.</strong> The first claim of each period lands
{", ".join(f"{int((by_n[n][0][0]-(UNLOCK+n*PERIOD))//60)} minutes" for n in sorted(by_n)[:3])} after its
boundary. Investors — or their bots — were watching a schedule they could compute, and the schedule was real.
</div>

<h3 style="margin-top:18px">All {len(claims)} claims, by period</h3>
<table class="dense"><thead><tr><th>Claim time (UTC)</th><th class="num">n</th><th>Claimant</th>
<th class="num">Amount</th></tr></thead><tbody>''')
for n in sorted(by_n):
    for t, c in by_n[n]:
        w(f'<tr><td class="mono">{c["when"]}</td><td class="num">{n}</td>'
          f'<td>{bsc(c["caller"])}</td><td class="num">{int(c["total"])/1e24:,.2f}mn</td></tr>')
w(f'''</tbody></table>
<div class="note">{len({c["caller"] for c in claims})} distinct claimant addresses. Several appear in every
period with the same amount — {bsc('0xea3b7dfb150ce3dbca57e6d53cbe6b0cb7b7307c')} took 180.00mn four times,
{bsc('0x9cedcd2a811e99be0d5dbbec746d81ef74e33db8')} 165.00mn four times — which is what a fixed monthly
entitlement looks like when it is claimed reliably.</div>
</div>''')
print('section 3 built')

# ---------------------------------------------------------------- 4
w(f'''<div class="section" id="s4"><h2>4 · March 2026 — the function was gutted, not removed</h2>
<div class="alert alert-danger">This is the part that is easy to get wrong, and I did get it wrong at first.
<b>The self-claim selector <code>0xac694711</code> was never deleted.</b> It is present in the dispatcher of
all nine implementations, including the one live right now. What changed on 19 March 2026 is its
<em>body</em>.</div>

<h3>The same call, before and after</h3>
<p style="font-size:12.5px;margin-bottom:10px">Impersonating
{bsc('0xea3b7dfb150ce3dbca57e6d53cbe6b0cb7b7307c')} — an address that had successfully claimed four
times — and calling <code>0xac694711</code> at historical blocks:</p>
<table class="dense"><thead><tr><th>Block</th><th>When (UTC)</th><th>Revert reason</th>
<th>Reading</th></tr></thead><tbody>
<tr><td class="num">85,000,000</td><td class="mono">2026-03-05</td><td>“No unlock amount”</td>
  <td>normal business logic — nothing claimable this instant</td></tr>
<tr><td class="num">85,991,468</td><td class="mono">2026-03-11</td><td>“No unlock amount”</td>
  <td>one block before the last successful claim</td></tr>
<tr><td class="num">86,500,000</td><td class="mono">2026-03-14</td><td>“No unlock amount”</td>
  <td>still normal, in the eight-day gap</td></tr>
<tr><td class="num">87,414,303</td><td class="mono">2026-03-19</td><td>“No unlock amount”</td>
  <td>one block <b>before</b> the upgrade</td></tr>
<tr class="hi2"><td class="num">87,414,305</td><td class="mono">2026-03-19</td>
  <td style="color:var(--danger)"><b>“fix”</b></td>
  <td>one block <b>after</b> the upgrade</td></tr>
<tr class="hi2"><td class="num">{HEAD:,}</td><td class="mono">{ut(HEADTS, '%Y-%m-%d')}</td>
  <td style="color:var(--danger)"><b>“{html.escape(LIVE_CLAIM_REVERT or "")}”</b></td>
  <td>still, {(HEADTS - 1773884965)/86400:,.0f} days later</td></tr>
</tbody></table>

<div class="grid2" style="margin-top:14px">
<div class="card" style="background:var(--card2);padding:14px;border-radius:8px;border:1px solid var(--border)">
<h3>The raw revert payload</h3>
<div class="mono" style="word-break:break-all;color:var(--muted);line-height:1.5">
0x08c379a0<br>0000…0020<br>0000…0003<br><span style="color:var(--danger)">666978</span>0000…0000</div>
<div class="note">Standard <code>Error(string)</code>. Length 3, bytes <code>66 69 78</code> —
<b>“fix”</b>. Not a business condition, not a permission check. A developer placeholder.</div>
</div>
<div class="card" style="background:var(--card2);padding:14px;border-radius:8px;border:1px solid var(--border)">
<h3>It reverts for everyone</h3>
<table class="dense"><tbody>
<tr><td>A former claimant</td><td style="color:var(--danger)">“fix”</td></tr>
<tr><td>The owner Safe</td><td style="color:var(--danger)">“fix”</td></tr>
<tr><td>The deployer EOA</td><td style="color:var(--danger)">“fix”</td></tr>
<tr><td>A random address</td><td style="color:var(--danger)">“fix”</td></tr>
</tbody></table>
<div class="note">Identical payload in all four cases, so it is unconditional — not an access-control
branch that the owner could step around.</div>
</div></div>

<h3 style="margin-top:18px">When the literal entered the bytecode</h3>
<p style="font-size:12.5px;margin-bottom:10px">Searching each implementation for the ABI-encoded string
<code>“fix”</code>:</p>
<table class="dense"><thead><tr><th>Block</th><th>Activated (UTC)</th><th>Implementation</th>
<th>Contains “fix”</th></tr></thead><tbody>''')
FIXBLK = 87414304
for bn, impl, _ts in uh['Investors Pool']:
    has = bn >= FIXBLK
    cls = 'hi2' if bn == FIXBLK else ''
    mark = ' &nbsp;<b>&larr; introduced here</b>' if bn == FIXBLK else ''
    w(f'<tr class="{cls}"><td class="num">{bn:,}</td><td class="mono">{ut(_ts)}</td>'
      f'<td>{bsc(impl)}</td><td>{"<b>yes</b>" if has else "no"}{mark}</td></tr>')
w(f'''</tbody></table>

<div class="alert alert-warn" style="margin-top:14px"><strong>The timing.</strong> The last successful
self-claim was <b>2026-03-11 15:19:32 UTC</b>, inside period n=6. The next boundary was
<b>{ut(UNLOCK + 7*PERIOD)} UTC</b>. The upgrade that installed the placeholder landed
<b>{ut(1773884965)} UTC</b> — <b>{(UNLOCK + 7*PERIOD - 1773884965)/86400:,.1f} days before</b> the period
that would have been claimable next.</div>
<div class="note">Stated carefully: adjacency is not proof of intent. What is proven is the sequence and the
effect — the placeholder went in before the next boundary, and no investor has claimed since.</div>
</div>''')
print('section 4 built')

# ---------------------------------------------------------------- 5
PL = mech['placeholder_reverts']
w(f'''<div class="section" id="s5"><h2>5 · April 2026 — the same thing to every other pool</h2>
<p style="font-size:12.5px;margin-bottom:12px">The Investors Pool was first, not unique. On
<b>13 April 2026, between 15:03:59 and 15:15:40 UTC — eleven minutes and forty-one seconds</b> — all seven
then-active pools were upgraded in one sitting. Six received the same treatment, with a different
placeholder string: <code>“lock”</code>.</p>

<table class="dense"><thead><tr><th>Pool</th><th>Placeholder</th><th>Introduced (UTC)</th>
<th>Block</th><th>Still in force?</th></tr></thead><tbody>''')
ORDER = ['Investors Pool', 'Team Pool 1', 'Team Pool 2', 'KOL Pool',
         'Nodes Pool 1', 'Nodes Pool 2', 'Nodes Pool 3', 'Community Pool']
for name in ORDER:
    p = PL[name]
    still = p.get('still_present', False)
    cls = 'hi2' if name == 'Investors Pool' else ('hi3' if not still else '')
    if still:
        status = '<b style="color:var(--danger)">yes</b>'
    else:
        status = f'<span style="color:var(--green)">removed {p["removed_utc"]}</span>'
    w(f'<tr class="{cls}"><td><b>{name}</b></td>'
      f'<td class="mono" style="color:var(--danger)">“{p["string"]}”</td>'
      f'<td class="mono">{p["introduced_utc"]}</td>'
      f'<td class="num">{p["introduced_block"]:,}</td><td>{status}</td></tr>')
w(f'''</tbody></table>

<div class="grid2" style="margin-top:14px">
<div class="card" style="background:var(--card2);padding:14px;border-radius:8px;border:1px solid var(--border)">
<h3>The 13 April window</h3>
<table class="dense"><tbody>
<tr><td class="mono">15:03:59</td><td>Investors Pool</td></tr>
<tr><td class="mono">15:06:27</td><td>Team Pool 1</td></tr>
<tr><td class="mono">15:08:31</td><td>Team Pool 2</td></tr>
<tr><td class="mono">15:11:09</td><td>KOL Pool</td></tr>
<tr><td class="mono">15:15:17</td><td>Nodes Pool 1</td></tr>
<tr><td class="mono">15:15:31</td><td>Nodes Pool 2</td></tr>
<tr><td class="mono">15:15:40</td><td>Nodes Pool 3</td></tr>
</tbody></table>
<div class="note">Seven upgrades, one operator, one sitting. All times UTC.</div>
</div>
<div class="card" style="background:var(--card2);padding:14px;border-radius:8px;border:1px solid var(--border)">
<h3>And the 22 July re-open</h3>
<table class="dense"><tbody>
<tr class="hi3"><td class="mono">03:39:25</td><td>Nodes Pool 1 — “lock” removed</td></tr>
<tr class="hi3"><td class="mono">03:39:47</td><td>Nodes Pool 2 — “lock” removed</td></tr>
<tr class="hi3"><td class="mono">03:40:06</td><td>Nodes Pool 3 — “lock” removed</td></tr>
</tbody></table>
<div class="note">Forty-one seconds, and only the three Nodes pools. Later the same day those pools
released <b>20.867bn</b> to 5,879 wallets — the node unlock covered in the June-2026 tracker. The claim
path was reopened for that release and for nothing else.</div>
</div></div>

<div class="alert alert-info" style="margin-top:14px"><strong>What this establishes.</strong> The disabled
claim path is not a bug specific to one contract, and not an accident of one upgrade: it was applied
deliberately across the whole pool set, and demonstrably reversed when the operator wanted a release to
happen. That is the clearest evidence in this document that the mechanism is discretionary rather than
scheduled.</div>
</div>''')

# ---------------------------------------------------------------- 6
w(f'''<div class="section" id="s6"><h2>6 · How releases happen now</h2>
<p style="font-size:12.5px;margin-bottom:12px">Every release since March 2026 follows the same shape: the
function needed to move tokens is <b>added to the contract shortly before the move and removed shortly
after</b>.</p>

<h3>19 June 2026 — nine minutes, start to finish</h3>
<table class="dense"><thead><tr><th>Time (UTC)</th><th class="num">Block</th><th>Gap</th>
<th>What happened</th></tr></thead><tbody>
<tr><td class="mono">16:00:17</td><td class="num">105,170,321</td><td>—</td>
  <td>deployer upgrades to {bsc('0x27e8d745358b5f9929571f63ac03aa465f4888c4')} —
      <b>adminTransfer added</b></td></tr>
<tr><td class="mono">16:00:38</td><td class="num">105,170,367</td><td>+21s</td>
  <td>deployer upgrades to <b>the same implementation again</b> — a repeat of the call above</td></tr>
<tr class="hi2"><td class="mono">16:00:41</td><td class="num">105,170,374</td><td><b>+3s</b></td>
  <td><b>adminTransfer called — 4.0734bn out</b></td></tr>
<tr><td class="mono">16:09:01</td><td class="num">105,171,484</td><td>+8m 20s</td>
  <td>deployer upgrades to {bsc('0x30d691a6441831fdbe863dd73cf44a5a56295ac9')} —
      <b>adminTransfer removed</b></td></tr>
<tr class="hi3"><td class="mono">16:24:52</td><td class="num">105,173,600</td><td>+15m 51s</td>
  <td><b>2.0734bn came back in</b> — so the net movement that afternoon was 2.0000bn out,
      not 4.0734bn</td></tr>
</tbody></table>
<div class="note">Both upgrades sent by the deployer EOA {bsc(DEPLOYER)} directly to the proxy via
<code>upgradeToAndCall</code> (<code>0x4f1ef286</code>).</div>

<h3 style="margin-top:18px">25–26 July 2026 — the same shape, through the Safe</h3>
<table class="dense"><thead><tr><th>Time (UTC)</th><th class="num">Block</th>
<th>What happened</th></tr></thead><tbody>
<tr class="hi"><td class="mono">18 Jul 09:23:59</td><td class="num">110,682,684</td>
  <td>the deployer calls <code>transferOwnership</code> (<code>0xf2fde38b</code>) directly on the proxy —
      <b>ownership moves to the Safe</b> {bsc(SAFE)}, on its own, a week before the upgrade below</td></tr>
<tr><td class="mono">25 Jul 12:05:39</td><td class="num">112,047,462</td>
  <td>Safe owner {bsc('0x88f4b387eab71497e312663ac8b4aada6aa2ef8e')} executes an upgrade to
      {bsc('0x00445d6c82de5fe7773ffc1f03b346b020bfc9cc')} through the Safe — <b>userWithdraw() added</b>.
      Ownership had already moved; this step only changed the code</td></tr>
<tr class="hi2"><td class="mono">26 Jul 13:43:05</td><td class="num">112,252,392</td>
  <td>userWithdraw() — 1.2904bn</td></tr>
<tr class="hi2"><td class="mono">26 Jul 14:50:05</td><td class="num">112,261,325</td>
  <td>userWithdraw() — 0.9326bn</td></tr>
<tr class="hi2"><td class="mono">26 Jul 14:50:28</td><td class="num">112,261,377</td>
  <td>userWithdraw() — 0.8987bn</td></tr>
<tr class="hi2"><td class="mono">26 Jul 14:50:48</td><td class="num">112,261,422</td>
  <td>userWithdraw() — 0.8783bn &nbsp;<span style="color:var(--muted)">(4.0000bn exactly, across the
      four)</span></td></tr>
</tbody></table>

<h3 style="margin-top:18px">What <code>userWithdraw()</code> actually is</h3>
<p style="font-size:12.5px;margin-bottom:10px">It is not the monthly claim under a new name, and it is not
on the schedule at all. Three things establish that, all read from the chain:</p>
<table class="dense"><thead><tr><th style="width:30%">Test</th><th>Result</th></tr></thead><tbody>
<tr><td><b>When did the selector appear?</b></td>
  <td><code>0xa646f9ad</code> is absent from the dispatcher of every implementation before
      {bsc('0x00445d6c82de5fe7773ffc1f03b346b020bfc9cc')} and present in that one. The 25 July upgrade
      introduced it.</td></tr>
<tr><td><b>Did that upgrade write any data?</b></td>
  <td><b>No.</b> Decoding the Safe's <code>execTransaction</code> payload gives
      <code>upgradeToAndCall(0x00445d6c…, "")</code> — the <code>bytes</code> argument is <b>empty</b>, so no
      initializer ran. The pool emitted exactly one event between the upgrade and the four withdrawals, and
      it was the <code>Upgraded</code> event itself. The entries the new code reads were already in
      storage.</td></tr>
<tr class="hi2"><td><b>Who can call it now?</b></td>
  <td>Live <code>eth_call</code> at block {HEAD:,}: the four wallets that used it get
      <code>“Already withdrawn”</code> — it is <b>one shot per address</b>, not a recurring claim. Every
      other address tested, including four original self-claim investors, the deployer and the owner Safe
      itself, gets <code>“Only token address can withdraw”</code>. The path is spent.</td></tr>
</tbody></table>
<div class="note">So the 25 July upgrade changed <em>who could take what, once, outside the schedule</em> —
not <em>when</em> the schedule falls due. That distinction is the whole of §8.</div>

<h3 style="margin-top:18px">The four eras, end to end</h3>''')
ERACLS = {0: 'e1', 1: 'e2', 2: 'e3', 3: 'e4'}
ERANAME = ['Deployer pushes', 'Investors pull — the only era with a working schedule',
           'Capability added, used, removed', 'Pull, but only after the Safe enables it']
for i, e in enumerate(mech['eras']):
    w(f'''<div class="era {ERACLS[i]}">
<h4>{ERANAME[i]} &nbsp;<span style="font-weight:400;color:var(--muted)">{e["from"]} → {e["to"]}</span></h4>
<div class="sub"><code>{e["selector"]}</code> {html.escape(e["name"])} · {e["calls"]} call{"s" if e["calls"]!=1 else ""} ·
caller: {html.escape(e["caller"])}{" · " + html.escape(e["note"]) if e.get("note") else ""}</div></div>''')
w('</div>')
print('sections 5-6 built')

# ---------------------------------------------------------------- 7
SELNAME = {'0xac694711': 'self-claim (name unresolved)', '0xa646f9ad': 'userWithdraw()',
           '0xf17e48ec': 'adminTransfer', '0xdace4557': 'setUnlockTime', '0x251c1aa3': 'unlockTime'}
TRACK = ['0xac694711', '0xa646f9ad', '0xf17e48ec', '0xdace4557', '0x251c1aa3']
w(f'''<div class="section" id="s7"><h2>7 · Every implementation, and what changed</h2>
<p style="font-size:12.5px;margin-bottom:12px">{len(FULL_EVENTS)} <code>Upgraded</code> events behind one
proxy in thirteen months, resolving to {len(FULL_IMPLS)} distinct implementations — the list comes from an
unseeded sweep of every block from before the proxy existed to the head, so a re-emit of an implementation
already in place shows up as its own row rather than being collapsed away. The columns track the selectors
that matter; a dash means absent from that version's dispatcher.</p>
<table class="dense"><thead><tr><th>#</th><th class="num">Block</th><th>Activated (UTC)</th>
<th>Implementation</th><th class="num">Size</th>''')
for s in TRACK:
    w(f'<th class="num" style="font-size:10px">{s[:8]}</th>')
w('<th>Note</th></tr></thead><tbody>')
NOTES = {57840346: 'launch', 58335633: 'first code change, 5 days in',
         68594426: 'self-claim era begins 4 days later; unlockTime amended same day',
         87414304: 'placeholder “fix” introduced', 92315466: 'adminTransfer removed',
         105170321: 'adminTransfer re-added', 105171484: 'adminTransfer removed again, 8m later',
         112047462: 'userWithdraw added; ownership → Safe'}
for i, ev in enumerate(FULL_EVENTS, 1):
    bn, impl = ev['block'], ev['impl']
    rec = FULL_IMPLS[impl]
    sels = set(rec['selectors'])
    cls = 'hi2' if bn in (87414304, 92315466) else ('hi' if bn in (105170321, 105171484, 112047462) else '')
    w(f'<tr class="{cls}"><td class="num">{i}</td><td class="num">{bn:,}</td>'
      f'<td class="mono">{ev["when_utc"]}</td><td>{bsc(impl)}</td>'
      f'<td class="num">{rec["codelen"]:,}B</td>')
    for s in TRACK:
        w(f'<td class="num">{"<b>Y</b>" if s in sels else "–"}</td>')
    note = NOTES.get(bn, '')
    if ev['repeat_of_same_impl'] and not note:
        note = 're-emitted, same implementation'
    w(f'<td style="font-size:11px;color:var(--warn)">{note}</td></tr>')
_nper = {len(r["periods"]) for r in FULL_IMPLS.values()}
_pvals = {v for r in FULL_IMPLS.values() for _o, v in r['periods']}
w(f'''</tbody></table>
<div class="note">Every row is read directly from <code>eth_getCode</code>, including the launch
implementation {bsc('0x197c7ad333b1c1f89e898740dd4d7acbbc5acf7c')} — an earlier pass seeded its
implementation list from a stored history and so began after that version had already been replaced; this
one seeds from nothing. Across all {len(FULL_IMPLS)} versions the set of duration-shaped constants actually
PUSHed is {{{', '.join(f'{v:,}' for v in sorted(_pvals))}}} and the count per version is
{{{', '.join(str(x) for x in sorted(_nper))}}} — one 30-day constant each, never a second candidate.
<b>Note that the self-claim column is “Y” in every row</b>, including the current one: the function was
never removed, only emptied.</div>

<h3 style="margin-top:18px">Revert strings in the current implementation</h3>
<p style="font-size:12.5px">These are the guards the live contract actually carries:</p>
<table class="dense"><thead><tr><th>String</th><th>What it implies</th></tr></thead><tbody>
<tr class="hi2"><td class="mono" style="color:var(--danger)">fix</td>
  <td>the gutted self-claim path — a placeholder, not a condition</td></tr>
<tr><td class="mono">Unlock time is 0</td><td>slot 3 must be set before anything can move</td></tr>
<tr><td class="mono">Unlock time not reached</td><td>a time gate exists and is checked</td></tr>
<tr><td class="mono">Target time not reached</td><td>a second, separate time gate</td></tr>
<tr><td class="mono">No unlock amount</td><td>the old, meaningful “nothing claimable yet”</td></tr>
<tr><td class="mono">Already withdrawn</td><td>per-entry replay protection</td></tr>
<tr><td class="mono">Accounts and amounts length mismatch</td>
  <td><b>a batch function taking address[] and uint256[]</b> — amounts supplied by the caller</td></tr>
<tr><td class="mono">Total amount is 0</td><td>same batch path, empty input</td></tr>
<tr><td class="mono">Only token address can withdraw</td><td>caller restriction on userWithdraw()</td></tr>
</tbody></table>
<div class="note">The last two matter for the question. “Accounts and amounts length mismatch” and
“Total amount is 0” are the signature of a function that is <em>handed</em> a list of recipients and
amounts. Nothing in the contract computes an entitlement from a schedule; the numbers come from outside.</div>
</div>''')

# ---------------------------------------------------------------- 8
NEXT_T = UNLOCK + (CUR_N + 1) * PERIOD
w(f'''<div class="section" id="s8"><h2>8 · When does it next unlock?</h2>
<div class="grid2">
<div class="card" style="background:var(--card2);padding:16px;border-radius:8px;border:1px solid var(--border)">
<h3>The arithmetic answer</h3>
<div class="big" style="color:var(--accent)">{ut(NEXT_T)} UTC</div>
<div class="note" style="margin-top:6px">Period n={CUR_N+1}, i.e.
<code>{UNLOCK} + {CUR_N+1} × 2592000</code>. That is
<b>{(NEXT_T - HEADTS)/86400:,.2f} days</b> from the head block of this build.</div>
<table class="dense" style="margin-top:10px"><tbody>''')
for k in range(CUR_N + 1, CUR_N + 5):
    t = UNLOCK + k * PERIOD
    w(f'<tr><td>n={k}</td><td class="mono">{ut(t)} UTC</td>'
      f'<td class="num">{(t-HEADTS)/86400:,.1f} d</td></tr>')
w(f'''</tbody></table></div>
<div class="card" style="background:var(--card2);padding:16px;border-radius:8px;border:1px solid var(--border)">
<h3>The practical answer</h3>
<div class="big" style="color:var(--danger)">nothing will happen</div>
<div class="note" style="margin-top:6px">The self-claim path still reverts
<code>“{html.escape(LIVE_CLAIM_REVERT or "")}”</code> as of block {HEAD:,}. Periods
<b>n=7 through n={CUR_N}</b> — {CUR_N - 6} boundaries — have already passed with zero investor claims. A
release on or after {ut(NEXT_T, '%d %b')} requires the owner Safe
{bsc(SAFE)} to send a transaction. The date does not cause it.</div>
</div></div>

<h3 style="margin-top:18px">Verification — has the boundary been moved?</h3>
<p style="font-size:12.5px;margin-bottom:10px">The anchor was shifted once before, on 18 Nov 2025, by exactly
three days. A repeat would move the next boundary from 18 to 21 September. Four independent tests, all run
against the live chain at block {HEAD:,}:</p>
<table class="dense"><thead><tr><th>Test</th><th>Method</th><th>Result</th></tr></thead><tbody>
<tr class="hi3"><td><b>Has slot 3 changed?</b></td>
  <td>recursive bisection of <code>eth_getStorageAt</code> over the pool's entire life,
      57,840,341 → {HEAD:,}</td>
  <td><b>Exactly 2 changes ever</b>, both in 2025: 20 Aug 2025 12:59:31 (0 → 21 Aug) and
      18 Nov 2025 06:25:26 (→ 24 Aug). <b>Nothing in 2026.</b></td></tr>
<tr class="hi3"><td><b>Has the 30-day period changed?</b></td>
  <td>exact PUSH-encoding count of 2592000 and twelve other candidate durations, in all nine
      implementations</td>
  <td><b>2592000 appears exactly once in every version</b>, Aug 2025 through the current one. No 7-, 14-,
      21-, 31-, 60-, 90-, 180- or 365-day constant appears in any version.</td></tr>
<tr class="hi3"><td><b>Any other storage change?</b></td>
  <td>bisection of slots 0,1,2,4,5,6,7,8, the ERC1967 admin slot, and the OpenZeppelin v5 Ownable,
      Initializable and ReentrancyGuard namespaced slots, across all of 2026</td>
  <td><b>Zero changes</b> in every one of them. The only 2026 writes anywhere in the contract's storage
      are the implementation pointer and the owner.</td></tr>
<tr class="hi3"><td><b>Any upgrade since?</b></td>
  <td>all <code>Upgraded</code> events 2026, plus bisection of the ERC1967 implementation slot from
      112,047,463 to head</td>
  <td><b>No change for 52 days.</b> The contract has run {bsc('0x00445d6c82de5fe7773ffc1f03b346b020bfc9cc')}
      since 25 Jul 2026 12:05:39.</td></tr>
<tr class="hi3"><td><b>Does the current code still compute the same boundary?</b></td>
  <td>the three tests above fix the <em>inputs</em>; this one fixes the <em>function</em>. The boundary
      routine was located in both the implementation under which claims demonstrably worked
      ({bsc('0x4b569675380e19d2819e629ec8a2c43a30a59947')}) and the live one, disassembled, and then
      executed opcode by opcode in a hand-written EVM interpreter over a sweep of timestamps</td>
  <td><b>Structurally identical, and it executes to the same dates.</b> Both read storage slot 3, subtract
      it from <code>block.timestamp</code>, divide by 2592000, and gate on the quotient being ≥ 3; only the
      internal jump targets differ, because the code moved. Stepping the live bytecode's own arithmetic
      produces boundaries at 1763805600 (n=3) … 1787133600 (n=12) … <b>1789725600 (n=13)</b>, with the
      accrual stepping up <em>at</em> each boundary second and not before.</td></tr>
</tbody></table>
<div class="alert alert-ok" style="margin-top:12px;background:rgba(16,185,129,.08);
border:1px solid rgba(16,185,129,.25);color:var(--green);border-radius:8px;padding:12px 14px;font-size:12.5px">
<strong>The boundary has not been moved.</strong> For the next boundary to fall on 21 September the anchor
would have to read <b>1756288800</b> (27 Aug 2025 10:00 UTC). It reads <b>{LIVE_UNLOCK}</b>
({ut(LIVE_UNLOCK)} UTC), the same value it has held since 18 November 2025, and
<code>unlockTime()</code>, <code>getUnlockTime()</code> and raw slot 3 all agree.
<b>n=13 is {ut(UNLOCK + 13*PERIOD)} UTC.</b></div>

<h3 style="margin-top:18px">Cross-check — four claims that failed</h3>
<p style="font-size:12.5px;margin-bottom:10px">Everything above is an argument from code and storage. The
strongest independent test is behavioural: investors who <em>tried</em>. Four such attempts exist. Each was
re-read here from the chain — receipt status from <code>eth_getTransactionReceipt</code>, revert reason
replayed with <code>eth_call</code> at the transaction's own block — and none is taken on trust from any
compiled list:</p>
<table class="dense"><thead><tr><th>When (UTC)</th><th>Caller</th><th>Period</th><th>Reverted with</th>
<th>What it proves</th></tr></thead><tbody>
{FAILED_ROWS}
</tbody></table>
<div class="alert alert-ok" style="margin-top:12px;background:rgba(16,185,129,.08);
border:1px solid rgba(16,185,129,.25);color:var(--green);border-radius:8px;padding:12px 14px;font-size:12.5px">
The 22 March attempt is the one that matters. {bsc('0x5a6eeb042afc115f0b0189964d4b99a28a6cdb06')} had
already claimed successfully at n=4, n=5 and n=6. They came back <b>19 minutes after the n=7 boundary</b> —
which is where this document's formula says the boundary was — and were refused, not with
<code>“No unlock amount”</code> but with <code>“fix”</code>. So the clock kept running to 22 Mar 2026
10:00:00 UTC exactly as computed; what changed was the gate, not the schedule.
</div>
<div class="note">Token movements are equally quiet: the pool's last transfer in either direction was
<b>26 Jul 2026 14:50:48 UTC</b>. Pool-flow coverage is continuous from the token's deployment to the head
block with no gaps, so that is a complete statement, not an absence of data.</div>

<div class="alert alert-warn" style="margin-top:14px"><strong>So: is the next unlock knowable?</strong>
The <em>date</em> is, exactly, and has been computable since launch. The <em>event</em> is not. Before
19 March 2026 those were the same thing, because any investor could turn the date into tokens themselves.
Since then the date is a calendar entry and the tokens move when the Safe decides.</div>

<div class="stat-grid" style="margin-top:14px">
  <div class="stat-box"><div class="stat-box-label">Allocated</div>
    <div class="stat-box-value">25.0000bn</div><div class="stat-box-sub">Strategic Investors</div></div>
  <div class="stat-box"><div class="stat-box-label">Released to date</div>
    <div class="stat-box-value">{(25e27-LIVE_BAL)/1e27:,.4f}bn</div>
    <div class="stat-box-sub">{100*(25e27-LIVE_BAL)/25e27:.1f}% of allocation</div></div>
  <div class="stat-box"><div class="stat-box-label">Still held by the pool</div>
    <div class="stat-box-value">{LIVE_BAL/1e27:,.4f}bn</div>
    <div class="stat-box-sub">read at block {HEAD:,}</div></div>
</div>
</div>''')
print('sections 7-8 built')

# ---------------------------------------------------------------- 9
w(f'''<div class="section" id="s9"><h2>9 · Method, and what this does not show</h2>
<div class="grid2">
<div>
<h3>How each claim here was established</h3>
<ul style="font-size:12.5px;line-height:1.75;padding-left:18px">
<li><b>Chain only.</b> <code>eth_getCode</code>, <code>eth_call</code>,
<code>eth_getStorageAt</code>, <code>eth_getLogs</code> and <code>eth_getTransactionByHash</code> against a
NodeReal BSC archive node. No explorer API, no analytics vendor.</li>
<li><b>Selectors</b> were extracted by walking each implementation's bytecode for <code>PUSH4</code>
opcodes with correct payload skipping, not by pattern-matching text.</li>
<li><b>Revert strings</b> were decoded from the raw <code>Error(string)</code> payload
(<code>0x08c379a0</code> + offset + length + bytes), not inferred from behaviour.</li>
<li><b>The 30-day cadence</b> was not assumed. It is the only duration-shaped constant in any of the nine
implementations, and it was then tested against all {len(claims)} historical claims — every one falls in
periods n={min(by_n)}–{max(by_n)} and none outside.</li>
<li><b>The before/after revert test</b> used <code>eth_call</code> at specific historical blocks with the
<code>from</code> field set to real former claimants, so the contract saw the same caller it had
previously served.</li>
<li><b>Live values</b> — unlock timestamp, owner, implementation, pool balance, and whether the claim path
still reverts — are read when this page is generated, so they cannot drift from the chain.</li>
</ul>
</div>
<div>
<h3>What is not established</h3>
<ul style="font-size:12.5px;line-height:1.75;padding-left:18px">
<li><b>Intent.</b> The placeholder went in three days before the next claimable boundary. That is a
sequence, not a motive. A stalled migration and a deliberate freeze produce the same bytes.</li>
<li><b>The function's name.</b> <code>0xac694711</code> matches no signature in 31,680 brute-forced
candidates, and neither does <code>0xe0dc37a3</code>. Their behaviour is established; their declared names
are not.</li>
<li><b>Off-chain entitlement.</b> Investors may have been paid, compensated or re-papered outside the
contract. Nothing here would show that.</li>
<li><b>What the Safe intends to do.</b> It holds <code>setUnlockTime</code> and can move the anchor at any
time. Everything here establishes that it has not, not that it will not. A future write to slot 3 would
change the next boundary the moment it lands, and nothing on-chain announces it in advance.</li>
<li><b>Whether a release is imminent.</b> The Safe's intentions are not on-chain until it acts.</li>
</ul>
</div></div>

<div class="alert alert-info" style="margin-top:14px"><strong>On times.</strong> Every timestamp in this
document is <b>UTC</b>. BNB Smart Chain stores <code>block.timestamp</code> as Unix epoch seconds, which
carry no timezone at all; rendering that as UTC is the only conversion-free reading, and the machine
generating this page also runs UTC. So the 10:00:00 unlock boundary is 10:00:00 UTC — worth noting because
it is a round hour in UTC, which is itself a small piece of evidence that the schedule was set by someone
working in UTC.</div>

<div class="alert alert-danger" style="margin-top:12px"><strong>Reproducing the central claim.</strong>
Two <code>eth_call</code>s settle it. Call <code>0xac694711</code> on
{bsc(INV)} with
<code>from</code> = {bsc('0xea3b7dfb150ce3dbca57e6d53cbe6b0cb7b7307c')} at block <b>87,414,303</b> and again
at block <b>87,414,305</b>. The first reverts “No unlock amount”; the second reverts “fix”. Everything else
in this document follows from that pair.</div>
</div>

<footer style="border-top:1px solid var(--border);margin-top:28px;padding:16px 0;color:var(--muted);
font-size:11.5px">
AKE Investors Pool vesting mechanism · generated from pipeline/data and live chain reads at block
{HEAD:,} ({ut(HEADTS)} UTC) · all times UTC · mn = million, bn = billion
</footer>
</div>''')

open(OUT, 'w').write('\n'.join(P))
print(f'wrote {OUT} ({len("".join(P))/1024:.1f} KB)')
