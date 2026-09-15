#!/usr/bin/env python3
"""
Find every block at which a storage slot changed, over an arbitrary range, by
recursive bisection on eth_getStorageAt.

This is the authoritative way to answer "was this value ever altered". Scanning
for events misses a write that emits nothing; scanning for transactions to the
contract misses a write made through a delegatecall or an upgrade's initializer.
The slot itself cannot lie: if the value at block A differs from block B, some
write happened between them, and bisection finds exactly where.

Usage: slot_history.py <address> <slot-hex> <from> <to> [out_name]
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, sys, time, urllib.request, datetime

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
D = 'pipeline/data/'

_calls = 0


def rpc(m, p, tries=10):
    global _calls
    for i in range(tries):
        try:
            r = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                      'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(r, timeout=120).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            _calls += 1
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(40, 1.5 * (1.7 ** i)))


def main():
    addr = sys.argv[1].lower()
    slot = sys.argv[2]
    lo, hi = int(sys.argv[3]), int(sys.argv[4])
    out = sys.argv[5] if len(sys.argv) > 5 else None

    cache = {}

    def val(b):
        if b not in cache:
            cache[b] = rpc('eth_getStorageAt', [addr, slot, hex(b)])
        return cache[b]

    changes = []

    def scan(a, b, va, vb, depth=0):
        if va == vb or depth > 48:
            return
        if b - a <= 1:
            changes.append((b, va, vb))
            return
        mid = (a + b) // 2
        vm = val(mid)
        scan(a, mid, va, vm, depth + 1)
        scan(mid, b, vm, vb, depth + 1)

    v_lo, v_hi = val(lo), val(hi)
    print(f'slot {slot} on {addr}', flush=True)
    print(f'  at {lo:,}: {v_lo}', flush=True)
    print(f'  at {hi:,}: {v_hi}', flush=True)
    scan(lo, hi, v_lo, v_hi)
    changes.sort()

    print(f'\n{len(changes)} change(s) found in {_calls} RPC calls\n', flush=True)
    rows = []
    for b, before, after in changes:
        ts = int(rpc('eth_getBlockByNumber', [hex(b), False])['timestamp'], 16)
        when = datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        blk = rpc('eth_getBlockByNumber', [hex(b), True])
        callers = []
        for t in blk['transactions']:
            if (t.get('to') or '').lower() == addr:
                callers.append({'tx': t['hash'], 'from': t['from'],
                                'selector': t['input'][:10]})
        def dec(v):
            n = int(v, 16)
            if 1_500_000_000 < n < 2_500_000_000:
                return f'{n} = {datetime.datetime.utcfromtimestamp(n).strftime("%Y-%m-%d %H:%M:%S")} UTC'
            return str(n)
        print(f'  block {b:,}  {when} UTC', flush=True)
        print(f'     before: {dec(before)}', flush=True)
        print(f'     after : {dec(after)}', flush=True)
        for c in callers:
            print(f'     tx {c["tx"]}  from {c["from"]}  sel {c["selector"]}', flush=True)
        if not callers:
            print('     (no direct transaction to this address in the block — '
                  'written via an internal call)', flush=True)
        rows.append({'block': b, 'when_utc': when, 'before': before, 'after': after,
                     'callers': callers})

    if out:
        json.dump({'address': addr, 'slot': slot, 'from': lo, 'to': hi,
                   'value_at_from': v_lo, 'value_at_to': v_hi,
                   'changes': rows, 'rpc_calls': _calls},
                  open(D + out + '.json', 'w'), indent=1)
        print(f'\nwrote {D}{out}.json', flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
