#!/usr/bin/env python3
"""
Hard validation of ledger.json against the chain itself.

For every sampled address the identity
    balanceOf(head) - balanceOf(start-1)  ==  recv - sent
must hold exactly. It is violated by a dropped segment, a duplicated segment,
an inverted field order, or a mis-stated block boundary — i.e. by every way the
merge can silently go wrong. Any mismatch is printed, not absorbed.

Usage: validate_ledger.py [n_sample]
Data-only.
"""
import json, sys, random
sys.path.insert(0, 'pipeline')
from probe import rpc

D    = 'pipeline/data/'
AKE  = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
L    = json.load(open(D + 'ledger.json'))
LO, HI = L['from'], L['to']
N    = int(sys.argv[1]) if len(sys.argv) > 1 else 60


def bal(a, blk):
    return int(rpc('eth_call', [{'to': AKE,
                                 'data': '0x70a08231' + a[2:].rjust(64, '0')}, hex(blk)]), 16)


def main():
    addrs = set(L['recv']) | set(L['sent'])
    addrs.discard('0x0000000000000000000000000000000000000000')
    net = {a: int(L['recv'].get(a, 0)) - int(L['sent'].get(a, 0)) for a in addrs}
    top = sorted(addrs, key=lambda a: -abs(net[a]))[:N // 2]
    rnd = random.Random(20260808).sample(sorted(addrs), min(N - len(top), len(addrs)))
    sample = list(dict.fromkeys(top + rnd))

    print(f'validating {len(sample)} addresses over blocks {LO:,}-{HI:,}\n')
    bad = 0
    for a in sample:
        b0 = bal(a, LO - 1)
        b1 = bal(a, HI)
        if (b1 - b0) != net[a]:
            bad += 1
            print(f'  MISMATCH {a}')
            print(f'      chain delta {(b1-b0)/1e18:>22,.4f}')
            print(f'      ledger net  {net[a]/1e18:>22,.4f}')
            print(f'      difference  {((b1-b0)-net[a])/1e18:>22,.4f}')
    print(f'\n{len(sample)-bad}/{len(sample)} addresses reconcile exactly to the chain')
    if bad:
        raise SystemExit(f'{bad} MISMATCHES — ledger is not trustworthy')
    print('LEDGER VALIDATED')


if __name__ == '__main__':
    main()
