#!/usr/bin/env python3
"""
Fetch every implementation a proxy has ever pointed at and pull out what can be
read from the bytecode alone: the function selectors in its dispatcher, the
revert strings, and any embedded version marker.

The vesting question - was a schedule hardcoded, or is it storage the owner can
rewrite - is answerable from this. A hardcoded schedule leaves constants in the
code and no setter selector; a storage schedule leaves a setter and a revert
string guarding it. Comparing the selector sets across implementations shows
exactly which version introduced or removed which control.

Usage: impl_probe.py <proxy> <out_name>
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, re, sys, time, urllib.request, collections

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
D = 'pipeline/data/'
UPGRADED = '0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
STEP = 49_999


def rpc(m, p, tries=10):
    for i in range(tries):
        try:
            r = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                      'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(r, timeout=180).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(40, 1.5 * (1.7 ** i)))


def selectors(code_hex):
    """PUSH4 <sel> in a Solidity dispatcher. Over-collects slightly; the
    dispatcher constants dominate and false positives are rare and obvious."""
    b = bytes.fromhex(code_hex[2:]) if code_hex.startswith('0x') else bytes.fromhex(code_hex)
    out = []
    i = 0
    while i < len(b):
        op = b[i]
        if op == 0x63 and i + 5 <= len(b):          # PUSH4
            out.append('0x' + b[i+1:i+5].hex())
            i += 5
            continue
        if 0x60 <= op <= 0x7f:                       # other PUSHn - skip payload
            i += 1 + (op - 0x5f)
            continue
        i += 1
    # keep those that look like real selectors (appear in the first 2/3, the
    # dispatcher region) and de-dup preserving order
    seen, res = set(), []
    for s in out:
        if s not in seen:
            seen.add(s); res.append(s)
    return res


def strings(code_hex):
    b = bytes.fromhex(code_hex[2:])
    return sorted({m.decode('ascii', 'ignore') for m in re.findall(rb'[ -~]{6,60}', b)})


def main():
    proxy = sys.argv[1].lower()
    out = sys.argv[2]
    head = int(rpc('eth_blockNumber', []), 16)

    # seed from the known history so only the unscanned tail is walked; the
    # seeded entries carry no tx hash, so re-read their blocks to recover it
    ups = []
    _uh = json.load(open(D + 'upgrade_history.json'))
    NAME = {'0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors Pool',
            '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes Pool 3',
            '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team Pool 2',
            '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes Pool 1',
            '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes Pool 2',
            '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team Pool 1',
            '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL Pool',
            '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community Pool'}
    seed = _uh.get(NAME.get(proxy, proxy), [])
    start = 57_000_000
    if seed:
        for bn, impl, _ts in seed:
            for L in rpc('eth_getLogs', [{'address': proxy, 'topics': [UPGRADED],
                                          'fromBlock': hex(bn), 'toBlock': hex(bn)}]):
                ups.append([int(L['blockNumber'], 16), '0x' + L['topics'][1][-40:],
                            L['transactionHash']])
        start = max(bn for bn, _, _ in seed) + 1
        print(f'seeded {len(ups)} known upgrades; scanning {start:,} -> {head:,}', flush=True)
    b = start
    while b <= head:
        e = min(b + STEP, head)
        for L in rpc('eth_getLogs', [{'address': proxy, 'topics': [UPGRADED],
                                      'fromBlock': hex(b), 'toBlock': hex(e)}]):
            ups.append([int(L['blockNumber'], 16), '0x' + L['topics'][1][-40:],
                        L['transactionHash']])
        b = e + 1
    ups.sort()
    print(f'{len(ups)} Upgraded events on {proxy}', flush=True)

    res = {}
    for bn, impl, tx in ups:
        code = rpc('eth_getCode', [impl, 'latest'])
        t = rpc('eth_getTransactionByHash', [tx])
        sels = selectors(code)
        st = strings(code)
        ver = [s for s in st if re.fullmatch(r'\d+\.\d+\.\d+', s)]
        res[impl] = {
            'block': bn, 'tx': tx, 'caller': t['from'], 'to': t['to'],
            'call_selector': t['input'][:10],
            'codelen': len(code) // 2 - 1,
            'version': ver,
            'selectors': sels,
            'revert_strings': [s for s in st if re.fullmatch(r"[A-Za-z][A-Za-z0-9 ,.'()/_-]{5,59}", s)],
        }
        print(f'  {bn:>12,}  {impl}  {len(code)//2-1:>6}B  {len(sels):>3} sels  ver={ver}', flush=True)

    json.dump({'proxy': proxy, 'head': head, 'upgrades': ups, 'impls': res},
              open(D + out + '.json', 'w'), indent=1)
    print(f'\nwrote {D}{out}.json', flush=True)

    # selector diff across the timeline
    order = [i for _, i, _ in ups]
    print('\nselector changes between consecutive implementations:')
    for a, b_ in zip(order, order[1:]):
        sa, sb = set(res[a]['selectors']), set(res[b_]['selectors'])
        add, rem = sb - sa, sa - sb
        print(f'  {a[:10]} -> {b_[:10]}   +{len(add)} -{len(rem)}')
        if add:
            print(f'      added:   {sorted(add)}')
        if rem:
            print(f'      removed: {sorted(rem)}')


if __name__ == '__main__':
    main()
