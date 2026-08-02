#!/usr/bin/env python3
"""Full ERC1967 implementation-upgrade history for every pool proxy, by binary
search on the implementation storage slot. Data-only."""
import json, urllib.request, time, datetime, os

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
SLOT = '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
HEAD = 113_384_906
OUT = 'pipeline/data/upgrade_history.json'

POOLS = {
    'Investors Pool': '0x27333bd8c321a263b0565e69eea3b736b9d1f42c',
    'Nodes Pool 3':   '0xaf66503770451c83a4f12a1146a32271893508ce',
    'Team Pool 2':    '0xd229b65d50e412cc3c394233e7a53a1dac4da457',
    'Nodes Pool 1':   '0xb7c7786b6ca1130584f005e9c86554114b7fad62',
    'Nodes Pool 2':   '0xd2f72669e560c7ecd3c681612963990ef6f1981b',
    'Team Pool 1':    '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248',
    'KOL Pool':       '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5',
    'Community Pool': '0x6b394c413d60b2aadb37a907a73a6f9a91c35015',
}


def rpc(m, p, tries=10):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(req, timeout=120).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(60, 1.5 * (1.8 ** i)))


def impl(a, b):
    return '0x' + rpc('eth_getStorageAt', [a, SLOT, hex(b)])[-40:]


def ts(b):
    return int(rpc('eth_getBlockByNumber', [hex(b), False])['timestamp'], 16)


def main():
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for n, a in POOLS.items():
        if n in out:
            continue
        cur = 57_840_400
        v = impl(a, cur)
        chain = [[cur, v, ts(cur)]]
        for _ in range(25):
            if impl(a, HEAD) == v:
                break
            lo, hi = cur + 1, HEAD
            while lo < hi:
                mid = (lo + hi) // 2
                if impl(a, mid) == v:
                    lo = mid + 1
                else:
                    hi = mid
            v = impl(a, lo)
            cur = lo
            chain.append([lo, v, ts(lo)])
        out[n] = chain
        json.dump(out, open(OUT, 'w'), indent=1)
        print(f'{n}: {len(chain)} implementations', flush=True)
        for b, i, t in chain:
            print(f'    blk {b:<11} {datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")}  {i}', flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
