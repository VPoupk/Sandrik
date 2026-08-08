#!/usr/bin/env python3
"""
Exactly who received AKE in the last ~2.4 months.

The window is blocks 100,940,328 -> 114,777,002 = 28 May 2026 14:40 UTC to
8 Aug 2026 17:29 UTC. That is not an arbitrary choice: five completed scan
segments tile it exactly, so the recipient list is complete rather than sampled,
and the tiling is asserted before anything is summed.

Writes pipeline/data/recent_window.json. Data-only.
"""
import json, collections

D = 'pipeline/data/'
SEGS = [('ake_gap_may_jun_2026_checkpoint.json', 100_940_328, 102_669_786, 'agg'),
        ('ake_delta_v2_checkpoint.json',         102_669_787, 110_819_786, 'agg'),
        ('master_jul19_26.json',                 110_819_787, 112_252_391, 'master'),
        ('sells_jul26_agg.json',                 112_252_392, 113_384_906, 'master'),
        ('master_recent.json',                   113_384_907, 114_777_002, 'master')]

V = json.load(open(D + 'venues.json'))
POOLS = {
    '0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors Pool',
    '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes Pool 3',
    '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team Pool 2',
    '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes Pool 1',
    '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes Pool 2',
    '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team Pool 1 (Advisors)',
    '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL Pool',
    '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community Pool',
}


def main():
    recv = collections.Counter(); sent = collections.Counter()
    prev = None
    for fn, a, b, fmt in SEGS:
        s = json.load(open(D + fn))
        if s['last_block'] != b:
            raise SystemExit(f'{fn}: last_block {s["last_block"]:,} != declared {b:,}')
        if prev is not None and a != prev + 1:
            raise SystemExit(f'gap/overlap before {fn}')
        prev = b
        if fmt == 'master':
            for k, v in s['recv'].items():
                recv[k] += int(v)
            for k, v in s['sent'].items():
                sent[k] += int(v)
        else:
            # [out_amt, out_n, in_amt, in_n] -- sent first
            for k, q in s['agg'].items():
                sent[k] += int(q[0]); recv[k] += int(q[2])

    lo, hi = SEGS[0][1], SEGS[-1][2]
    tot_r = sum(recv.values()); tot_s = sum(sent.values())
    print(f'window blocks {lo:,} -> {hi:,}   (2026-05-28 14:40 UTC -> 2026-08-08 17:29 UTC)')
    print(f'gross received {tot_r/1e27:,.3f}bn   gross sent {tot_s/1e27:,.3f}bn   '
          f'difference {tot_r-tot_s} (must be 0)')
    print(f'{len(recv):,} addresses received AKE in the window\n')

    bal = {}
    for f in ('bal_top400.json', 'bal_top250.json'):
        try:
            bal.update(json.load(open(D + f)))
        except Exception:
            pass

    net = {a: recv[a] - sent[a] for a in recv}
    nonv = [(a, n) for a, n in net.items()
            if a not in V and a not in POOLS
            and a != '0x0000000000000000000000000000000000000000']
    nonv.sort(key=lambda kv: -kv[1])

    print('TOP 40 NET RECIPIENTS IN THE WINDOW (excluding exchanges, pools, routers)')
    print(f'{"address":44}{"net mn":>12}{"received":>12}{"sent":>12}{"held now":>12}')
    for a, n in nonv[:40]:
        b = int(bal[a]) / 1e24 if a in bal else float('nan')
        print(f'{a:44}{n/1e24:>12,.1f}{recv[a]/1e24:>12,.1f}{sent[a]/1e24:>12,.1f}{b:>12,.1f}')

    pos = [n for _, n in nonv if n > 0]
    print(f'\n{len(pos):,} addresses ended the window with more AKE than they started, '
          f'totalling {sum(pos)/1e27:,.3f}bn')
    for k, lbl in [(40, 'top 40'), (100, 'top 100'), (400, 'top 400')]:
        print(f'   {lbl:8} account for {sum(pos[:k])/1e27:>8,.3f}bn '
              f'({100*sum(pos[:k])/sum(pos):.1f}% of it)')

    print('\nWHAT THE POOLS PAID OUT IN THE WINDOW')
    for a, nm in POOLS.items():
        if recv[a] or sent[a]:
            print(f'   {nm:24} paid out {sent[a]/1e24:>10,.1f}mn   took back {recv[a]/1e24:>10,.1f}mn')
    tp = sum(sent[a] for a in POOLS) - sum(recv[a] for a in POOLS)
    print(f'   {"NET OUT OF ALL POOLS":24}{tp/1e24:>19,.1f}mn  = {tp/1e18/1e9:.3f}bn '
          f'= {tp/1e18/1e11*100:.2f}% of total supply')

    json.dump({'from': lo, 'to': hi,
               'recv': {k: str(v) for k, v in recv.items()},
               'sent': {k: str(v) for k, v in sent.items()}},
              open(D + 'recent_window.json', 'w'))
    print('\nwrote', D + 'recent_window.json')


if __name__ == '__main__':
    main()
