#!/usr/bin/env python3
"""Render node-buyback-analysis.html from pipeline/data/buyback_final.json."""
import json, datetime

D = 'pipeline/data/'
S = '/tmp/claude-0/-home-user-Sandrik/4d5dfae8-d9f1-59c8-a7af-703ef8978ed1/scratchpad/'
F = json.load(open(D + 'buyback_final.json'))
W, T = F['wallets'], F['totals']
CG = json.load(open(D + 'ake_daily_prices_cg.json'))
TODAY = sorted(CG)[-1]
SPOT = T['spot']

FUNDER_NAME = {
    '0x8894e0a0c962cb723c1976a4421c95949be2d4e3': 'Binance 51',
    '0xdccf3b77da55107280bd850ea519df3705d1a75a': 'Binance: Hot Wallet 9',
    '0xf5988713400da6fc8a58ec9515e2b0df9b40b115': 'OKX: DepositAndWithdraw_173',
}
INSIDER_WHEN = {
    'Binance 51': 'also funded <strong>Alpha Feeder C</strong> — but on 2025-11-25, 2 months later',
    'Binance: Hot Wallet 9': 'also funded <strong>Alpha Feeder E</strong> — but on 2026-04-17, 3½ months later',
    'OKX: DepositAndWithdraw_173': 'also funded <strong>Twin Wallets A and B</strong> — but on 2026-04-24, 8 months later',
}
BBSET = set(W)


def A(x):
    a = abs(x)
    if a >= 1e9: return f'{x/1e9:.3f}bn'
    if a >= 1e6: return f'{x/1e6:.3f}mn'
    if a >= 1e3: return f'{x/1e3:.1f}k'
    return f'{x:,.0f}'


def U(x):
    a = abs(x)
    if a >= 1e6: return f'${x/1e6:.2f}M'
    if a >= 1e3: return f'${x:,.0f}'
    return f'${x:,.2f}' if a < 100 else f'${x:,.0f}'


def sh(a):
    return f'{a[:10]}…{a[-6:]}'


def rows():
    return sorted(W.items(), key=lambda kv: -kv[1]['pool_ake'])


def wallet_table():
    out = ['<div class="table-wrap"><table><thead><tr>'
           '<th>#</th><th>Wallet</th><th>Type</th><th>Nonce</th>'
           '<th>AKE from project pools</th><th>Value at receipt dates</th>'
           '<th>Same AKE at today\'s price</th><th>Total AKE in / out</th>'
           '<th>USDT paid out</th><th>Active</th><th>Gas funder</th>'
           '</tr></thead><tbody>']
    for i, (a, v) in enumerate(rows(), 1):
        typ = ('<span class="badge badge-purple">contract</span>' if v['is_contract']
               else '<span class="badge badge-gray">EOA</span>')
        pre = ' <span class="badge badge-green">pre-AKE</span>' if v['pre_ake'] else ''
        ins = ''
        if v['insider_funder']:
            ins = f' <span class="badge badge-yellow">{v["insider_funder"][0]}</span>'
        elif v['funders'] and v['funders'][0][0] in BBSET:
            ins = ' <span class="badge badge-orange">funded by another list wallet</span>'
        gas = ('pre-dates AKE' if v['pre_ake'] else
               (FUNDER_NAME.get(v['funders'][0][0], sh(v['funders'][0][0])) if v['funders'] else '—'))
        span = f"{v['first']} → {v['last']}" if v['first'] else '—'
        out.append(
            f'<tr><td class="num">{i}</td>'
            f'<td><a href="https://bscscan.com/address/{a}" target="_blank"><code>{sh(a)}</code></a>{pre}{ins}</td>'
            f'<td>{typ}</td><td class="num">{v["nonce"]}</td>'
            f'<td class="num">{A(v["pool_ake"])}</td>'
            f'<td class="num">{U(v["pool_usd"])}</td>'
            f'<td class="num">{U(v["pool_ake"]*SPOT)}</td>'
            f'<td class="num">{A(v["in_ake"])} / {A(v["out_ake"])}</td>'
            f'<td class="num">{U(v["usdt_out"]) if v["usdt_out"] else "—"}</td>'
            f'<td style="font-size:11px">{span}</td>'
            f'<td style="font-size:11px">{gas}</td></tr>')
    out.append(
        f'<tr><td colspan="4"><strong>TOTAL — {T["n"]} wallets</strong></td>'
        f'<td class="num"><strong>{A(T["pool_ake"])}</strong></td>'
        f'<td class="num"><strong>{U(T["pool_usd"])}</strong></td>'
        f'<td class="num"><strong>{U(T["pool_ake"]*SPOT)}</strong></td>'
        f'<td class="num"><strong>{A(T["in_ake"])} / {A(T["out_ake"])}</strong></td>'
        f'<td class="num"><strong>{U(T["usdt_out"])}</strong></td>'
        f'<td colspan="2"></td></tr>')
    out.append('</tbody></table></div>')
    return '\n'.join(out)


def scenario_table():
    out = ['<div class="table-wrap"><table><thead><tr>'
           '<th>If a node cost…</th><th>Buyback pays (×1.20)</th>'
           '<th>AKE needed at today\'s $%.8f</th>' % SPOT +
           '<th>vs the AKE that wallet has already been paid</th></tr></thead><tbody>']
    avg_pool_usd = T['pool_usd'] / T['n']
    for price in (250, 500, 1000, 2500, 5000):
        pay = price * 1.20
        need = pay / SPOT
        ratio = pay / avg_pool_usd if avg_pool_usd else 0
        out.append(f'<tr><td class="num">${price:,}</td><td class="num">${pay:,.0f}</td>'
                   f'<td class="num">{A(need)} AKE</td>'
                   f'<td class="num">{ratio:.1f}× the ${avg_pool_usd:,.0f} of rewards the average wallet has already had</td></tr>')
    out.append('</tbody></table></div>')
    return '\n'.join(out)


def build():
    head = open(S + 'head.html').read().replace(
        '<title>AKEDO (AKE) — On-Chain Distribution Analysis</title>',
        '<title>AKEDO — ADODO Node Buyback Wallet Analysis</title>')
    ins_rows = []
    for a, v in W.items():
        if v['insider_funder']:
            nm = v['insider_funder'][0]
            dt = (datetime.datetime.utcfromtimestamp(int(v['gas_ts'])).strftime('%Y-%m-%d')
                  if v['gas_ts'] else '?')
            ins_rows.append((a, nm, dt, v['funders'][0][1]))
    intra = [(a, v['funders'][0][0]) for a, v in W.items()
             if v['funders'] and v['funders'][0][0] in BBSET]
    no_pool = [a for a, v in W.items() if v['pool_ake'] == 0]

    body = f'''<body>
<div class="container">

<header>
  <h1>AKEDO — ADODO Node Buyback: Eligible Wallet Analysis</h1>
  <div class="subtitle">{T['n']} wallets from the published eligibility sheet · full-history on-chain trace · cross-checked against the AKE insider set</div>
  <div class="meta">
    <div class="meta-item">Wallets <span>{T['n']}</span></div>
    <div class="meta-item">Analysis date <span>{TODAY}</span></div>
    <div class="meta-item">AKE spot <span>${SPOT:.8f}</span></div>
    <div class="meta-item">Announced terms <span>100% of remaining node value + 20%</span></div>
    <div class="meta-item">Verification closes <span>Aug 5, 2026</span></div>
  </div>
</header>

<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:24px">
  <a href="ake-analysis.html" style="padding:7px 14px;background:var(--card2);border:1px solid var(--border);border-radius:7px;font-size:12px;font-weight:600">① Distribution Overview →</a>
  <a href="pool-outflows.html" style="padding:7px 14px;background:var(--card2);border:1px solid var(--border);border-radius:7px;font-size:12px;font-weight:600">② Official Pool Outflows →</a>
  <a href="insider-outflows.html" style="padding:7px 14px;background:var(--card2);border:1px solid var(--border);border-radius:7px;font-size:12px;font-weight:600">③ Insider / Deployer-Linked Outflows →</a>
  <span style="padding:7px 14px;background:rgba(59,130,246,0.18);border:1px solid var(--accent);border-radius:7px;font-size:12px;font-weight:600;color:#93c5fd">④ Node Buyback Wallets <span style="color:var(--muted);font-weight:400">(this page)</span></span>
</div>

<!-- ===================== VERDICT ===================== -->
<div class="section">
  <h2>Verdict — This List Does Not Carry the Insider Signature</h2>

  <div class="alert alert-green" style="margin-bottom:14px">
    <strong>On every test that identified the AKE insider cluster, the {T['n']} buyback wallets come back clean.</strong>
    Not one of them is among the ten wallets that took 9.54bn out of the pools on 26 July. Not one appears among the
    6,227 addresses that claimed the July node distribution. <strong>{T['pre_ake']} of the {T['n']} already held BNB before the AKE
    token contract existed.</strong> No gas funder is shared by more than one wallet on the list — the exact opposite of the ten
    July-26 wallets, which were all funded from one address in identical 0.0020 BNB amounts inside a single hour.
    Nonces run from 9 to 1,827; these are used wallets with histories, not burners.
  </div>

  <div class="stat-grid" style="margin-bottom:14px">
    <div class="stat-box"><div class="stat-box-label">Overlap with the ten Jul-26 wallets</div><div class="stat-box-value" style="color:var(--green)">0 / {T['n']}</div><div class="stat-box-sub">no address appears in both sets</div></div>
    <div class="stat-box"><div class="stat-box-label">Overlap with Jul-22/26 node claimants</div><div class="stat-box-value" style="color:var(--green)">0 / {T['n']}</div><div class="stat-box-sub">a different population from the 6,227</div></div>
    <div class="stat-box"><div class="stat-box-label">Pre-date the AKE contract</div><div class="stat-box-value">{T['pre_ake']} / {T['n']}</div><div class="stat-box-sub">held BNB before block 57,840,341</div></div>
    <div class="stat-box"><div class="stat-box-label">Shared gas funders</div><div class="stat-box-value" style="color:var(--green)">none</div><div class="stat-box-sub">47 wallets, 47 distinct funding paths</div></div>
    <div class="stat-box"><div class="stat-box-label">Smart-contract wallets</div><div class="stat-box-value">{T['n_contract']} / {T['n']}</div><div class="stat-box-sub">rest are plain EOAs</div></div>
    <div class="stat-box"><div class="stat-box-label">AKE from project pools</div><div class="stat-box-value">{A(T['pool_ake'])}</div><div class="stat-box-sub">{U(T['pool_usd'])} at the prices on the days it was paid</div></div>
  </div>

  <div class="alert alert-warn" style="margin-bottom:0">
    <strong>Three weak links exist and are reported here for completeness, not because they carry weight.</strong>
    Three wallets were first funded from exchange hot wallets that also, at other times, funded AKE insider wallets. In every
    case the two fundings are months apart, and the funders are exchange withdrawal addresses that serve millions of unrelated
    users. This is the specific test — "funded from the same exchange as an AKE insider in the same time window" — and it
    <em>fails to produce a match on the time-window half in all three cases</em>.
  </div>
</div>

<!-- ===================== SOURCE & TERMS ===================== -->
<div class="section">
  <h2>What Was Supplied, and What the Buyback Actually Promises</h2>
  <div class="grid-2" style="margin-bottom:14px">
    <div class="card" style="background:var(--card)">
      <h3>The eligibility sheet</h3>
      <ul style="font-size:12px;color:var(--muted);padding-left:18px;line-height:1.8">
        <li>Google Sheet <code>17JqpDOk1s0z…FfJDM</code>, one tab, one column headed "Address"</li>
        <li><strong>{T['n']} addresses</strong>, all well-formed, no duplicates</li>
        <li><strong>No node counts, no purchase amounts, no dates, no tiers</strong> — the sheet carries addresses only</li>
        <li>Everything else on this page is derived from chain, not from the sheet</li>
      </ul>
    </div>
    <div class="card" style="background:var(--card)">
      <h3>The announced terms</h3>
      <ul style="font-size:12px;color:var(--muted);padding-left:18px;line-height:1.8">
        <li>Eligible ADODO node holders receive <strong>100% of remaining node purchase value plus a 20% bonus</strong></li>
        <li>Payable in <strong>AKE or USDT</strong></li>
        <li>Wallet verification closes <strong>5 August 2026</strong></li>
        <li>Announced <strong>27 July 2026</strong> — five days after the node distribution and one day after the ten wallets drew 9.54bn</li>
        <li><span class="badge badge-yellow">provenance</span> These terms come from a news summary of an AKEDO social post. The primary account is not machine-readable from here and no contract, dollar figure or per-node price has been published. Treat the terms as reported, not verified.</li>
      </ul>
    </div>
  </div>
</div>

<!-- ===================== CROSS-CONNECTION TESTS ===================== -->
<div class="section">
  <h2>Cross-Connection Tests Against the AKE Insider Set</h2>
  <div class="card" style="margin-bottom:12px">
    <div class="table-wrap"><table>
      <thead><tr><th>Test</th><th>What was compared</th><th>Result</th></tr></thead>
      <tbody>
        <tr><td><strong>Direct address overlap — the ten</strong></td>
            <td>The {T['n']} against the ten wallets that withdrew 9.540bn on 26 Jul 2026</td>
            <td><span class="badge badge-green">0 matches</span></td></tr>
        <tr><td><strong>Direct address overlap — July claimants</strong></td>
            <td>The {T['n']} against all 6,227 addresses paid by the Nodes pools on 22 and 26 Jul 2026</td>
            <td><span class="badge badge-green">0 matches</span> — a different population entirely</td></tr>
        <tr><td><strong>Direct address overlap — insider chain</strong></td>
            <td>The {T['n']} against the Founder Wallet, Mega Forwarder, Merge Wallet, Cold Hold, Fan-Out Root, sub-distributors, all five Alpha Feeders, both Pool Drain wallets, the Whale Insider, Silent Whale, Twin Wallets and Batch Holder</td>
            <td><span class="badge badge-green">0 matches</span></td></tr>
        <tr><td><strong>Appears in earlier published editions</strong></td>
            <td>The {T['n']} against the 1,447 addresses in prior full-history pool scans and the three published pages</td>
            <td><span class="badge badge-yellow">8 matches</span> — all ordinary Nodes Pool 3 / Community Pool claimants receiving 1.3–5.5mn, all now at zero</td></tr>
        <tr><td><strong>Shared gas funder</strong></td>
            <td>First BNB funding transaction read out of the block for all {T['n']}</td>
            <td><span class="badge badge-green">no funder used twice</span> — vs. one funder for all ten Jul-26 wallets</td></tr>
        <tr><td><strong>Identical gas amounts</strong></td>
            <td>Funding amounts across the list</td>
            <td><span class="badge badge-green">all different</span> — vs. exactly 0.0020 BNB ten times for the Jul-26 set</td></tr>
        <tr><td><strong>Pre-existence</strong></td>
            <td>Did the wallet hold BNB before the AKE contract was deployed?</td>
            <td><span class="badge badge-green">{T['pre_ake']} of {T['n']} yes</span> — cannot be purpose-built AKE wallets</td></tr>
        <tr><td><strong>Same exchange, same window</strong></td>
            <td>Funded by an exchange wallet that also funded an insider, at a comparable date</td>
            <td><span class="badge badge-yellow">3 same-exchange, 0 same-window</span> — see below</td></tr>
      </tbody>
    </table></div>
  </div>

  <div class="card" style="margin-bottom:12px">
    <h3>The three same-exchange links, in full</h3>
    <div class="table-wrap"><table>
      <thead><tr><th>Buyback wallet</th><th>Funded by</th><th>Amount</th><th>Date funded</th><th>Same funder also funded</th></tr></thead>
      <tbody>
''' + '\n'.join(
        f'        <tr><td><a href="https://bscscan.com/address/{a}" target="_blank"><code>{sh(a)}</code></a></td>'
        f'<td>{nm}</td><td class="num">{bnbv} BNB</td><td>{dt}</td>'
        f'<td>{INSIDER_WHEN.get(nm, "")}</td></tr>'
        for a, nm, dt, bnbv in ins_rows) + f'''
      </tbody>
    </table></div>
    <div class="alert alert-info" style="margin:12px 0 0">
      <strong>How much weight this carries: very little.</strong> Binance 51, Binance Hot Wallet 9 and OKX's deposit/withdraw
      address process millions of withdrawals for unrelated users. A shared exchange funder is only meaningful when it comes
      with a tight time window, a repeated amount, or a shared destination — the combination that made the ten July-26 wallets
      conclusive. Here the fundings are months apart, the amounts differ, and no destination is shared.
      A fourth pattern worth noting is benign: two wallets on the list were gas-funded by two other wallets
      <em>on the same list</em> ({', '.join(f'<code>{sh(a)}</code> ← <code>{sh(b)}</code>' for a, b in intra)}),
      which is what you would expect from people running more than one wallet.
    </div>
  </div>
</div>

<!-- ===================== BEHAVIOUR ===================== -->
<div class="section">
  <h2>What These Wallets Actually Did On-Chain</h2>
  <div class="grid-3" style="margin-bottom:14px">
    <div><div class="stat-box-label">AKE received from project pools</div><div class="stat-box-value">{A(T['pool_ake'])}</div><div class="stat-box-sub">{U(T['pool_usd'])} at the price on each payment date</div></div>
    <div><div class="stat-box-label">AKE received in total</div><div class="stat-box-value">{A(T['in_ake'])}</div><div class="stat-box-sub">{U(T['in_usd'])} — the rest came from DEX and Alpha trades</div></div>
    <div><div class="stat-box-label">AKE sent out in total</div><div class="stat-box-value">{A(T['out_ake'])}</div><div class="stat-box-sub">{U(T['out_usd'])} — they sold as they went</div></div>
  </div>

  <div class="alert alert-warn" style="margin-bottom:14px">
    <strong>The node rewards these wallets received are small.</strong> Across all {T['n']} wallets the project's pools paid out
    <strong>{A(T['pool_ake'])} AKE</strong> in total, worth <strong>{U(T['pool_usd'])}</strong> at the prices on the days it was
    paid — an average of <strong>{U(T['pool_usd']/T['n'])} per wallet</strong>. Every one of those payments came from
    <strong>Nodes Pool 3</strong> ({A(19.44e6)}) or the <strong>Community Pool</strong> ({A(5.418e6)}), between August 2025 and
    April 2026. The wallets hold {A(T['ake_now'])} AKE between them today — they have essentially all exited.
    {len(no_pool)} of the {T['n']} never received anything from a project pool at all.
  </div>

  <div class="card">
    <h3>Per-wallet detail</h3>
    <p style="color:var(--muted);font-size:12px;margin-bottom:10px">
      Sorted by AKE received from the project's pools. "Value at receipt dates" prices every payment at the CoinGecko daily
      price for the day it landed; the next column reprices the same tokens at today's ${SPOT:.8f} to show the difference
      holding would have made. <span class="badge badge-green">pre-AKE</span> marks a wallet that already held BNB before the
      AKE contract was deployed.
    </p>
    {wallet_table()}
  </div>
</div>

<!-- ===================== ECONOMICS ===================== -->
<div class="section">
  <h2>What They Spent, and What the Buyback Would Return</h2>

  <div class="alert alert-danger" style="margin-bottom:14px">
    <strong>The node purchase is not visible on-chain from these wallets, and that is a finding rather than a gap in the scan.</strong>
    A full-history AKE trace and a USDT trace across the whole node-sale window (blocks 57,840,000 → {T['usdt_scanned_to']:,},
    August 2025 to January 2026) show <strong>no payment of node-purchase size to any project contract</strong>.
    Total USDT moved out by all {T['n']} wallets across that window is <strong>{U(T['usdt_out'])}</strong>, and it is composed of
    DEX swap legs — the largest single flow is a $10,734 pass-through, routed via 1inch. There is no common recipient contract,
    no repeated ticket size, nothing shaped like a node sale.
    <br><br>
    The project did deploy seven "position" contracts (revert strings <em>"Position does not exist"</em>,
    <em>"user not match or already withdrawn"</em>) — but not until <strong>4 December 2025</strong>, months after node rewards
    had already started flowing, and they carry about ten events each and hold zero AKE, zero USDT and zero BNB today.
    The conclusion the data supports is that <strong>ADODO nodes were paid for off-chain</strong> — fiat, an exchange account, or
    a payment rail that leaves no trace on BSC.
  </div>

  <div class="card" style="margin-bottom:12px">
    <h3>What the buyback pays, per node price</h3>
    <p style="color:var(--muted);font-size:12px;margin-bottom:10px">
      Because the node price is neither published nor observable, the payout can only be given as a function of it.
      "Remaining node purchase value" is read here at face value — the announced terms do not define whether rewards already
      received are deducted. Both readings are shown below the table.
    </p>
    {scenario_table()}
    <div class="alert alert-warn" style="margin:12px 0 0">
      <strong>The asymmetry that matters.</strong> These wallets were paid their node rewards in AKE during
      August 2025 – April 2026, when AKE traded between $0.00019 and $0.0024. The buyback, if settled in AKE, is priced at
      today's <strong>${SPOT:.8f}</strong> — the token is at or near its all-time high. The {A(T['pool_ake'])} AKE the project
      has already paid this group was worth <strong>{U(T['pool_usd'])}</strong> when paid; the same tokens are worth
      <strong>{U(T['pool_ake']*SPOT)}</strong> today. Whichever way "remaining value" is calculated, a buyback settled in AKE at
      today's price costs the project far fewer tokens than the same dollar promise would have cost at any point in the
      preceding twelve months.
    </div>
  </div>

  <div class="card">
    <h3>Two readings of "remaining node purchase value"</h3>
    <div class="table-wrap"><table>
      <thead><tr><th>Reading</th><th>Formula</th><th>For a $1,000 node against the {U(T['pool_usd']/T['n'])} average already received</th></tr></thead>
      <tbody>
        <tr><td><strong>Gross</strong> — the full purchase price is refunded</td>
            <td><code>payout = 1.20 × purchase</code></td>
            <td class="num">$1,200 → {A(1200/SPOT)} AKE</td></tr>
        <tr><td><strong>Net of rewards</strong> — value already distributed is deducted</td>
            <td><code>payout = 1.20 × (purchase − rewards received)</code></td>
            <td class="num">${1.20*(1000-T['pool_usd']/T['n']):,.0f} → {A(1.20*(1000-T['pool_usd']/T['n'])/SPOT)} AKE</td></tr>
      </tbody>
    </table></div>
    <div style="margin-top:10px;font-size:11px;color:var(--muted)">
      The two readings differ by only about {100*(T['pool_usd']/T['n'])/1000:.0f}% at a $1,000 node price, because the rewards
      actually paid to this group are small relative to any plausible node price. The material uncertainty is the node price
      itself, not the deduction.
    </div>
  </div>
</div>

<!-- ===================== METHOD ===================== -->
<div class="section">
  <h2>Method, Coverage and Limitations</h2>
  <div class="grid-2" style="margin-bottom:14px">
    <div class="card" style="background:var(--card)">
      <h3>What was run</h3>
      <ul style="font-size:12px;color:var(--muted);padding-left:18px;line-height:1.8">
        <li><strong>AKE transfer scan</strong>, topic-filtered on all {T['n']} addresses in both directions, blocks 57,840,000 → 84,689,999 continuous, plus 85,600,000 → 91,449,999.</li>
        <li><strong>USDT (BSC-USD) transfer scan</strong>, same filter, blocks 57,840,000 → {T['usdt_scanned_to']:,}.</li>
        <li><strong>Recent-period pool coverage</strong> is complete from the verified pool reconciliation in the main report (blocks 100,940,328 → 113,384,906), which is how the zero-overlap with the July claimants is established.</li>
        <li><strong>Gas-funder trace</strong> for all {T['n']}: binary-search <code>eth_getBalance</code> to the first block each wallet held BNB, then read that block's transactions to find the crediting transfer. No explorer "Funded By" field was used.</li>
        <li><strong>Profiles</strong>: <code>eth_getCode</code>, <code>eth_getTransactionCount</code>, <code>balanceOf</code> at chain head.</li>
        <li><strong>Dating</strong>: 423-point block-timestamp grid; interpolation verified exact to the minute against four independently fetched blocks.</li>
        <li><strong>Pricing</strong>: CoinGecko daily series for <code>akedo</code>, applied per transfer date. The only flat price used is today's ${SPOT:.8f}, and only where a present-day snapshot is explicitly being valued.</li>
      </ul>
    </div>
    <div class="card" style="background:var(--card)">
      <h3>What this does not establish</h3>
      <ul style="font-size:12px;color:var(--muted);padding-left:18px;line-height:1.8">
        <li><strong>Identity.</strong> Nothing here names anyone. The tests rule out the specific insider signature; they do not prove independence.</li>
        <li><strong>AKE coverage gap</strong> between blocks 84,690,000 and 85,600,000 and after 91,450,000 for non-pool counterparties. Pool-side flows in the recent period are covered separately and completely.</li>
        <li><strong>USDT after block {T['usdt_scanned_to']:,}</strong> (January 2026 onward) was not scanned. A node purchase settled after that date would not appear.</li>
        <li><strong>Other rails.</strong> BNB, other stablecoins, other chains and off-chain payment were not traced. The absence of an on-chain node purchase is evidence about BSC AKE and USDT only.</li>
        <li><strong>The buyback terms are second-hand.</strong> No official document, contract or per-node price has been located.</li>
        <li><strong>A clean list is not a clean programme.</strong> These wallets look like ordinary node buyers. That says nothing about who set the buyback price, who funds it, or whether the ten July-26 wallets are connected to it.</li>
      </ul>
    </div>
  </div>

  <div style="text-align:center;color:var(--muted);font-size:11px;padding:14px 0 0;border-top:1px solid var(--border)">
    AKEDO (AKE) on BNB Smart Chain · ADODO node buyback eligibility list · {T['n']} wallets · chain state {TODAY}<br>
    Prices: CoinGecko daily, per transaction date · Entity labels: BscScan/Blockscan family and OKLink
  </div>
</div>

</div>
</body>
</html>
'''
    open('node-buyback-analysis.html', 'w').write(head + body)
    print('node-buyback-analysis.html written')


if __name__ == '__main__':
    build()
