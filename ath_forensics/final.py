"""FINAL unified seller table: direct (V3/V4) + CoW sells by real owner.
Columns: ATH sold, USD sold (realized @ sale time), holdings now, net, 2026 activity, DAO-source%, provenance."""
import json
from datetime import datetime, timezone
from collections import defaultdict

USER="0xf0940b14e8a4be798cd713a6807e95f47b769d9c"
ZERO="0x"+"0"*40
GEN="0x4d754910d570b30f9a0150eeb7281cb3ce0cf42f"
V3P="0x8071df1889d60a1c6329ef79976fb1f2e50599af"; MGR="0x000000000004444c5dc75cb358380d2e3de08a90"
COW="0x9008d19f58aabd9ed0d60971565aa8510560ab41"
BASE_BRIDGE="0x3154cf16ccdb4c6d922629664174b904d80f2c35"
LIFI="0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae"
VENUE_EXT={V3P,MGR,COW}

allt=json.load(open('all_transfers.json'))
T2026=json.load(open('ath_transfers_raw.json'))   # raw 2026 (decode below)
sells=[s for s in json.load(open('sells.json')) if not s['seller'].startswith("COW:")]
cow_sells=json.load(open('cow_sells.json'))
buys=json.load(open('buys.json'))
bal=json.load(open('balances_all.json'))
ts_map={int(k):v for k,v in json.load(open('ts_map.json')).items()}

def taddr(t): return "0x"+t[-40:].lower()
T=[{'from':taddr(l['topics'][1]),'to':taddr(l['topics'][2]),'val':int(l['data'],16)/1e18,'tx':l['transactionHash']} for l in T2026]

# DAO-controlled set
out_from_gen=defaultdict(float)
for x in allt:
    if x['from']==GEN: out_from_gen[x['to']]+=x['val']
DAO_VESTING={a for a,v in out_from_gen.items() if v>=300000 and a not in (V3P,MGR,BASE_BRIDGE)}
DAO={GEN}|DAO_VESTING; POOLS={V3P,MGR}
def src_class(a):
    if a==GEN: return "DAO treasury"
    if a in DAO_VESTING: return "DAO vesting"
    if a in POOLS: return "DEX"
    if a==COW: return "CoW"
    if a==BASE_BRIDGE: return "Base bridge"
    if a==LIFI: return "LiFi bridge"
    if a==ZERO: return "mint"
    return "wallet"

# all-time inbound per addr
inbound=defaultdict(lambda:defaultdict(float))
for x in allt: inbound[x['to']][x['from']]+=x['val']

# ---- aggregate sells (direct + cow) per wallet ----
W=defaultdict(lambda:{'ath':0.0,'usd':0.0,'v3':0.0,'v4':0.0,'cow':0.0,'legs':0,'cow_fills':0,
                      'first':None,'last':None,'days':set()})
def add_sell(s,is_cow=False):
    w=W[s['seller']]; w['ath']+=s['ath']; w['usd']+=s['usd']; w['legs']+=1; w['days'].add(s['day'])
    w[s['venue'].lower() if not is_cow else 'cow']+=s['ath']
    if is_cow: w['cow_fills']+=1
    w['first']=s['ts'] if w['first'] is None else min(w['first'],s['ts'])
    w['last'] =s['ts'] if w['last']  is None else max(w['last'], s['ts'])
for s in sells: add_sell(s)
for s in cow_sells: add_sell(s,True)

# buys per wallet
B=defaultdict(lambda:{'ath':0.0,'usd':0.0,'legs':0})
for b in buys:
    B[b['buyer']]['ath']+=b['ath']; B[b['buyer']]['usd']+=b['usd']; B[b['buyer']]['legs']+=1

# 2026 activity: tx sets per wallet
sell_txs=defaultdict(set); buy_txs=defaultdict(set); in_txs=defaultdict(set); out_txs=defaultdict(set)
recv=defaultdict(float); sent=defaultdict(float)
for s in sells: sell_txs[s['seller']].add(s['tx'])
for s in cow_sells: sell_txs[s['seller']].add(s['tx'])
for b in buys: buy_txs[b['buyer']].add(b['tx'])
for x in T:
    f,t,v=x['from'],x['to'],x['val']
    if f not in VENUE_EXT and t not in VENUE_EXT:
        if f!=ZERO and t!=ZERO:
            out_txs[f].add(x['tx']); sent[f]+=v
            in_txs[t].add(x['tx']); recv[t]+=v

# ---- build rows for wallets with USD sold >= 1000 ----
rows=[]
for a,w in W.items():
    if w['usd']<1000: continue
    b=B.get(a,{'ath':0.0,'usd':0.0,'legs':0})
    net=w['ath']-b['ath']
    # provenance
    srcs=inbound.get(a,{}); tot_in=sum(srcs.values())
    bucket=defaultdict(float)
    for s,val in srcs.items(): bucket[src_class(s)]+=val
    dao_amt=bucket.get("DAO treasury",0)+bucket.get("DAO vesting",0)
    dao_pct=100*dao_amt/tot_in if tot_in>0 else 0
    top_src=sorted(srcs.items(),key=lambda kv:-kv[1])[:3]
    ntx=len(sell_txs[a]|buy_txs[a]|in_txs[a]|out_txs[a])
    # classification
    g=w['ath']
    ratio=min(g,b['ath'])/max(g,b['ath'],1e-9)
    if ratio>0.85 and b['legs']>=3: cls="arb/MM bot"
    elif dao_pct>=80: cls="DAO-allocation seller"
    elif bucket.get("DEX",0)/max(tot_in,1e-9)>0.6 and b['ath']>0: cls="market trader"
    elif net>0: cls="market distributor"
    else: cls="other"
    rows.append({'addr':a,'is_user':a==USER,'cls':cls,
        'ath_sold':w['ath'],'usd_sold':w['usd'],'v3':w['v3'],'v4':w['v4'],'cow':w['cow'],
        'sell_txs':len(sell_txs[a]),'cow_fills':w['cow_fills'],
        'ath_bought':b['ath'],'buy_txs':len(buy_txs[a]),'net':net,
        'holdings':bal.get(a,0.0),'recv':recv.get(a,0),'sent':sent.get(a,0),
        'in_txs':len(in_txs[a]),'out_txs':len(out_txs[a]),'ntx':ntx,
        'dao_pct':dao_pct,'tot_in':tot_in,'top_src':top_src,
        'first':w['first'],'last':w['last'],'days':len(w['days'])})

rows.sort(key=lambda r:-r['usd_sold'])
json.dump(rows,open('final_table.json','w'),default=str)

def dt(ts): return datetime.fromtimestamp(ts,tz=timezone.utc).strftime("%m-%d") if ts else "-"
print(f"TOTAL >$1k sellers: {len(rows)}")
print(f"{'#':>2} {'address':42} {'class':22} {'ATHsold':>10} {'USDsold':>8} {'hold':>8} {'net':>9} {'stx':>4} {'btx':>4} {'2026tx':>6} {'DAO%':>5} {'first':>6} {'last':>6}")
for i,r in enumerate(rows):
    tag=' YOU' if r['is_user'] else ''
    print(f"{i+1:>2} {r['addr']} {r['cls']:22} {r['ath_sold']:>10,.0f} {r['usd_sold']:>8,.0f} {r['holdings']:>8,.0f} {r['net']:>9,.0f} {r['sell_txs']:>4} {r['buy_txs']:>4} {r['ntx']:>6} {r['dao_pct']:>4.0f}% {dt(r['first']):>6} {dt(r['last']):>6}{tag}")
print(f"\nTOTAL ATH sold (>$1k sellers): {sum(r['ath_sold'] for r in rows):,.0f}  USD: ${sum(r['usd_sold'] for r in rows):,.0f}")
