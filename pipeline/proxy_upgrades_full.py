#!/usr/bin/env python3
"""
Exhaustive Upgraded(address) scan for one proxy, from a block before it existed
to the head, with no seeding from any prior result.

impl_probe.py seeds from upgrade_history.json and then scans only the tail after
the newest seeded block. That silently drops two classes of event: anything
before the oldest seeded block, and any repeat event in a block that was never
seeded. Both happened on the Investors proxy - the original implementation
(0x197c7ad3, 16 Aug 2025) and a same-implementation re-emit (19 Jun 2026) were
both missing from inv_impls.json. A completeness claim cannot rest on a seeded
scan, so this one seeds from nothing.

Checkpointed per CLAUDE.md rule 2: every chunk, resumable from last_block + 1.

Usage: proxy_upgrades_full.py <proxy> <job_name> [from_block]
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, os, re, sys, time, urllib.request, datetime

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
    b = bytes.fromhex(code_hex[2:])
    out, i = [], 0
    while i < len(b):
        op = b[i]
        if op == 0x63 and i + 5 <= len(b):
            out.append('0x' + b[i+1:i+5].hex())
            i += 5
            continue
        if 0x60 <= op <= 0x7f:
            i += 1 + (op - 0x5f)
            continue
        i += 1
    seen, res = set(), []
    for s in out:
        if s not in seen:
            seen.add(s); res.append(s)
    return res


def periods(code_hex):
    """Every duration-shaped constant actually PUSHed, with its code offset."""
    CAND = {86400, 604800, 1209600, 1814400, 2592000, 2629746, 2629800, 2678400,
            5184000, 7776000, 15552000, 31536000, 31557600}
    b = bytes.fromhex(code_hex[2:])
    hits, i = [], 0
    while i < len(b):
        op = b[i]
        if 0x60 <= op <= 0x7f:
            n = op - 0x5f
            v = int.from_bytes(b[i+1:i+1+n], 'big')
            if v in CAND:
                hits.append([i, v])
            i += 1 + n
            continue
        i += 1
    return hits


def slot_sloads(code_hex, slot):
    """Count PUSH1 <slot> ; SLOAD pairs."""
    b = bytes.fromhex(code_hex[2:])
    n, i = 0, 0
    while i < len(b) - 2:
        if b[i] == 0x60 and b[i+1] == slot and b[i+2] == 0x54:
            n += 1
        if 0x60 <= b[i] <= 0x7f:
            i += 1 + (b[i] - 0x5f)
            continue
        i += 1
    return n


def strings(code_hex):
    b = bytes.fromhex(code_hex[2:])
    return sorted({m.decode('ascii', 'ignore') for m in re.findall(rb'[ -~]{3,60}', b)})


def ut(ts):
    return datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def main():
    proxy = sys.argv[1].lower()
    job = sys.argv[2]
    start = int(sys.argv[3]) if len(sys.argv) > 3 else 57_000_000
    cp_path = D + job + '_checkpoint.json'
    head = int(rpc('eth_blockNumber', []), 16)

    events, b, done = [], start, 0
    if os.path.exists(cp_path):
        cp = json.load(open(cp_path))
        if cp.get('proxy') == proxy:
            events = cp['results']['events']
            b = cp['last_block'] + 1
            done = cp['chunks_done']
            print(f'resuming {job} from {b:,} ({done} chunks done, '
                  f'{len(events)} events)', flush=True)

    while b <= head:
        e = min(b + STEP, head)
        for L in rpc('eth_getLogs', [{'address': proxy, 'topics': [UPGRADED],
                                      'fromBlock': hex(b), 'toBlock': hex(e)}]):
            events.append([int(L['blockNumber'], 16), '0x' + L['topics'][1][-40:],
                           L['transactionHash']])
            print(f'  event @ {int(L["blockNumber"], 16):,}  '
                  f'0x{L["topics"][1][-40:]}', flush=True)
        done += 1
        json.dump({'job': job, 'proxy': proxy, 'last_block': e,
                   'total_blocks': head - start + 1, 'chunks_done': done,
                   'results': {'events': events},
                   'timestamp': datetime.datetime.utcnow().isoformat()},
                  open(cp_path, 'w'))
        if done % 100 == 0:
            print(f'  ... {e:,} / {head:,}  ({len(events)} events)', flush=True)
        b = e + 1

    events.sort()
    print(f'\n{len(events)} Upgraded event(s) on {proxy}, '
          f'blocks {start:,} -> {head:,}\n', flush=True)

    impls = {}
    rows = []
    for bn, impl, tx in events:
        ts = int(rpc('eth_getBlockByNumber', [hex(bn), False])['timestamp'], 16)
        t = rpc('eth_getTransactionByHash', [tx])
        repeat = impl in impls
        if not repeat:
            code = rpc('eth_getCode', [impl, 'latest'])
            st = strings(code)
            impls[impl] = {
                'first_block': bn, 'codelen': len(code) // 2 - 1,
                'selectors': selectors(code),
                'periods': periods(code),
                'slot3_sloads': slot_sloads(code, 3),
                'has_fix': 'fix' in st,
                'revert_strings': [s for s in st if re.fullmatch(
                    r"[A-Za-z][A-Za-z0-9 ,.'()/_-]{4,59}", s)],
            }
        r = impls[impl]
        rows.append({'block': bn, 'when_utc': ut(ts), 'impl': impl, 'tx': tx,
                     'caller': t['from'], 'to': t['to'],
                     'call_selector': t['input'][:10],
                     'repeat_of_same_impl': repeat})
        p = ', '.join(f'{v}@0x{o:x}' for o, v in r['periods']) or 'none'
        print(f'  {bn:>12,}  {ut(ts)} UTC  {impl}  {r["codelen"]:>6}B  '
              f'{len(r["selectors"]):>3} sels  slot3={r["slot3_sloads"]}  '
              f'periods=[{p}]' + ('  (repeat)' if repeat else ''), flush=True)

    json.dump({'proxy': proxy, 'scanned_from': start, 'head': head,
               'events': rows, 'impls': impls},
              open(D + job + '.json', 'w'), indent=1)
    print(f'\nwrote {D}{job}.json', flush=True)

    print('\nselector diff between consecutive distinct implementations:')
    order, seen = [], set()
    for r in rows:
        if r['impl'] not in seen:
            seen.add(r['impl']); order.append(r['impl'])
    for a, c in zip(order, order[1:]):
        sa, sb = set(impls[a]['selectors']), set(impls[c]['selectors'])
        add, rem = sorted(sb - sa), sorted(sa - sb)
        print(f'  {a[:10]} -> {c[:10]}   +{len(add)} -{len(rem)}')
        if add:
            print(f'      added:   {add}')
        if rem:
            print(f'      removed: {rem}')
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
