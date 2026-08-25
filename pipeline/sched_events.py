#!/usr/bin/env python3
"""
Every emission of the pool's schedule-change event, across all eight pools,
for the token's whole life.

The Investors Pool's vesting start date was altered on 18 Nov 2025 with no
implementation change - a plain owner-only setter writing to storage. So the
schedule is mutable state, not immutable code, and this scan finds every time
that lever was pulled on any pool.
Data-only.
"""
import json, sys, bisect, datetime, urllib.request, time
RPC='https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
TOPIC='0xdb7a8975d58ea1ab96ed39c17e3423a2d07d5c03fcbc58efab16e9e36921eac7'
STEP=49_999
D='pipeline/data/'
TS=json.load(open(D+'blk_ts.json')); _tb=sorted(int(k) for k in TS); _tv=[TS[str(x)] for x in _tb]
POOLS={'0x27333bd8c321a263b0565e69eea3b736b9d1f42c':'Investors Pool',
 '0xaf66503770451c83a4f12a1146a32271893508ce':'Nodes Pool 3',
 '0xd229b65d50e412cc3c394233e7a53a1dac4da457':'Team Pool 2',
 '0xb7c7786b6ca1130584f005e9c86554114b7fad62':'Nodes Pool 1',
 '0xd2f72669e560c7ecd3c681612963990ef6f1981b':'Nodes Pool 2',
 '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248':'Team Pool 1 (Advisors)',
 '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5':'KOL Pool',
 '0x6b394c413d60b2aadb37a907a73a6f9a91c35015':'Community Pool'}
def rpc(m,p,tries=12):
    for i in range(tries):
        try:
            r=urllib.request.Request(RPC,data=json.dumps({'jsonrpc':'2.0','id':1,'method':m,'params':p}).encode(),
                                     headers={'Content-Type':'application/json'})
            j=json.loads(urllib.request.urlopen(r,timeout=180).read())
            if 'error' in j: raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i==tries-1: raise
            time.sleep(min(60,1.5*(1.8**i)))
def bdt(bn):
    i=bisect.bisect_left(_tb,bn)
    t=_tv[0] if i==0 else (_tv[-1] if i>=len(_tb) else _tv[i-1]+(_tv[i]-_tv[i-1])*(bn-_tb[i-1])/(_tb[i]-_tb[i-1]))
    return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d %H:%M:%S')
lo,hi=int(sys.argv[1]),int(sys.argv[2])
out=[]; b=lo
while b<=hi:
    e=min(b+STEP,hi)
    for L in rpc('eth_getLogs',[{'address':sorted(POOLS),'topics':[TOPIC],'fromBlock':hex(b),'toBlock':hex(e)}]):
        bn=int(L['blockNumber'],16)
        out.append([bn,bdt(bn),(L['address'] or '').lower(),L['data'],L['transactionHash']])
    b=e+1
print(f'{len(out)} schedule-change events across the eight pools\n')
for bn,d,a,data,tx in out:
    words=[data[2+64*i:2+64*(i+1)] for i in range((len(data)-2)//64)]
    dec=[]
    for w in words:
        v=int(w,16)
        if 1_600_000_000<v<2_200_000_000: dec.append(datetime.datetime.utcfromtimestamp(v).strftime('%Y-%m-%d %H:%M'))
        elif v>10**20: dec.append(f'{v/1e18:,.0f} AKE')
        else: dec.append(str(v))
    print(f'  {d}  {POOLS[a]:24} {" | ".join(dec)}')
    print(f'      tx {tx}')
json.dump(out, open(D+'sched_events.json','w'), indent=1)
