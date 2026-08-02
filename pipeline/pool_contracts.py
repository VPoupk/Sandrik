#!/usr/bin/env python3
"""Resolve each pool proxy's ERC1967 implementation, pull its bytecode, and
extract embedded name/function strings + 4-byte selectors. Data-only."""
import json, urllib.request, time, re

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
IMPL_SLOT = '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
ADMIN_SLOT = '0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
OWNER_SEL = '0x8da5cb5b'   # owner()

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
            time.sleep(min(60, 2 * (1.8 ** i)))


out = {}
impl_cache = {}
for n, a in POOLS.items():
    impl = '0x' + rpc('eth_getStorageAt', [a, IMPL_SLOT, 'latest'])[-40:]
    adm = '0x' + rpc('eth_getStorageAt', [a, ADMIN_SLOT, 'latest'])[-40:]
    try:
        own = '0x' + (rpc('eth_call', [{'to': a, 'data': OWNER_SEL}, 'latest']) or '0x')[-40:]
    except Exception:
        own = None
    if impl not in impl_cache:
        code = rpc('eth_getCode', [impl, 'latest'])
        b = bytes.fromhex(code[2:])
        strs = sorted(set(m.decode() for m in re.findall(rb'[\x20-\x7e]{5,80}', b)))
        impl_cache[impl] = {'codelen': len(b), 'strings': strs}
    out[n] = {'proxy': a, 'impl': impl, 'admin_slot': adm, 'owner': own,
              'codelen': impl_cache[impl]['codelen'],
              'strings': impl_cache[impl]['strings']}
    print(f'{n:16} impl {impl} admin {adm} owner {own} codelen {out[n]["codelen"]}', flush=True)

json.dump(out, open('pipeline/data/pool_contracts.json', 'w'), indent=1)

print('\n--- implementation grouping ---')
g = {}
for n, v in out.items():
    g.setdefault(v['impl'], []).append(n)
for i, ns in g.items():
    print(f'{i}  <-  {", ".join(ns)}')
    hits = [s for s in impl_cache[i]['strings']
            if re.search(r'Pool|Team|Advis|Investor|Community|Node|KOL|Creat', s)]
    print('    name strings:', sorted(set(hits))[:10])
