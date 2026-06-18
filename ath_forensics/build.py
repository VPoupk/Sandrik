"""Core ATH sell analysis (validated decoders).
Outputs per-wallet: gross ATH sold, USD realized at sale time, net flow, holdings, activity."""
import rpc, json, os
from datetime import datetime, timezone
from collections import defaultdict

USER = "0xf0940b14e8a4be798cd713a6807e95f47b769d9c"
ZERO = "0x0000000000000000000000000000000000000000"
COW  = "0x9008d19f58aabd9ed0d60971565aa8510560ab41"  # CoW Protocol GPv2Settlement

bj = json.load(open('blocks.json')); START, LATEST = bj['start'], bj['latest']
PX = json.load(open('prices_daily.json'))
V3P=rpc.V3_POOL.lower(); MGR=rpc.V4_MANAGER.lower()
VENUES={V3P:'V3', MGR:'V4'}

def to_int256(h):
    v=int(h,16); return v-(1<<256) if v>=(1<<255) else v
def taddr(t): return "0x"+t[-40:].lower()
def day_of(ts): return datetime.fromtimestamp(ts,tz=timezone.utc).strftime("%Y-%m-%d")
def px(sym,day):
    d=PX[sym]
    if day in d: return d[day]
    ks=sorted(d); best=None
    for k in ks:
        if k<=day: best=k
        else: break
    return d[best] if best else d[ks[0]]

# ---- load ----
transfers=json.load(open('ath_transfers_raw.json'))
v3_swaps =json.load(open('v3_swaps_raw.json'))
v4_swaps =json.load(open('v4_swaps_raw.json'))

T=[]
for l in transfers:
    T.append({'from':taddr(l['topics'][1]),'to':taddr(l['topics'][2]),'val':int(l['data'],16)/1e18,
              'bn':int(l['blockNumber'],16),'tx':l['transactionHash'],'li':int(l['logIndex'],16)})
T.sort(key=lambda x:(x['bn'],x['li']))

ts_map={int(k):v for k,v in json.load(open('ts_map.json')).items()} if os.path.exists('ts_map.json') else {}
need=sorted({x['bn'] for x in T}|{int(l['blockNumber'],16) for l in v3_swaps+v4_swaps} - set(ts_map))
if need:
    print("fetching",len(need),"ts...")
    for i in range(0,len(need),100):
        ch=need[i:i+100]
        for b,r in zip(ch,rpc.batch([("eth_getBlockByNumber",[hex(b),False]) for b in ch])): ts_map[b]=int(r['timestamp'],16)
    json.dump(ts_map,open('ts_map.json','w'))

bytx=defaultdict(list)
for x in T: bytx[x['tx']].append(x)

# ---- V3 swaps per tx (pool perspective: amount0>0 => ATH in => SELL) ----
v3tx=defaultdict(lambda:{'ath_sell':0.0,'weth_out':0.0,'ath_buy':0.0,'weth_in':0.0})
for l in v3_swaps:
    b=l['data'][2:]; a0=to_int256(b[0:64]); a1=to_int256(b[64:128]); tx=l['transactionHash']
    if a0>0: v3tx[tx]['ath_sell']+=a0/1e18
    else:    v3tx[tx]['ath_buy'] +=(-a0)/1e18
    if a1<0: v3tx[tx]['weth_out']+=(-a1)/1e18
    else:    v3tx[tx]['weth_in'] +=a1/1e18

# ---- V4 swaps per tx (swapper perspective: amount0<0 => ATH in => SELL) ----
v4tx=defaultdict(lambda:{'ath_sell':0.0,'bio_out':0.0,'ath_buy':0.0,'bio_in':0.0})
for l in v4_swaps:
    b=l['data'][2:]; a0=to_int256(b[0:64]); a1=to_int256(b[64:128]); tx=l['transactionHash']
    if a0<0: v4tx[tx]['ath_sell']+=(-a0)/1e18; v4tx[tx]['bio_out']+=a1/1e18 if a1>0 else 0
    else:    v4tx[tx]['ath_buy'] +=a0/1e18;     v4tx[tx]['bio_in'] +=(-a1)/1e18 if a1<0 else 0

# ---- contract detection for venue-inbound senders + tx.origin map ----
senders=sorted({x['from'] for x in T if x['to'] in VENUES})
code_map={}
for i in range(0,len(senders),100):
    ch=senders[i:i+100]
    for a,r in zip(ch,rpc.batch([("eth_getCode",[a,"latest"]) for a in ch])): code_map[a]=(r not in ("0x","0x0",None))
swap_txs=sorted(set(v3tx)|set(v4tx))
if os.path.exists('tx_origin.json'):
    origin=json.load(open('tx_origin.json'))
else:
    origin={}
miss=[h for h in swap_txs if h not in origin]
for i in range(0,len(miss),100):
    ch=miss[i:i+100]
    for h,r in zip(ch,rpc.batch([("eth_getTransactionByHash",[h]) for h in ch])):
        if r: origin[h]=(r.get('from') or '').lower()
json.dump(origin,open('tx_origin.json','w'))

def attribute(seller_from, tx):
    """Map the on-chain ATH sender into a venue to the responsible wallet."""
    s=seller_from
    if s==COW: return ('COW:'+ (origin.get(tx,'?')), True)   # CoW settlement - solver origin, end-user opaque
    if code_map.get(s) or s==ZERO:
        return (origin.get(tx,s), True)   # routed through a contract -> use tx signer
    return (s, False)

# ---- build SELL legs and BUY legs (from venues) ----
sells=[]; buys=[]
for tx,items in bytx.items():
    # ---- V3 ----
    d=v3tx.get(tx)
    if d:
        if d['ath_sell']>1e-9:
            ins=[x for x in items if x['to']==V3P]; tot=sum(x['val'] for x in ins)
            if tot>1e-9:
                day=day_of(ts_map[ins[0]['bn']]); usd=d['weth_out']*px('ETH',day)
                for x in ins:
                    slr,routed=attribute(x['from'],tx)
                    sells.append({'tx':tx,'bn':x['bn'],'ts':ts_map[x['bn']],'day':day,'venue':'V3',
                        'seller':slr,'routed':routed,'ath':x['val'],'usd':usd*x['val']/tot})
        if d['ath_buy']>1e-9:
            outs=[x for x in items if x['from']==V3P]; tot=sum(x['val'] for x in outs)
            if tot>1e-9:
                day=day_of(ts_map[outs[0]['bn']]); usd=d['weth_in']*px('ETH',day)
                for x in outs:
                    byr,routed=attribute(x['to'],tx)
                    buys.append({'tx':tx,'bn':x['bn'],'ts':ts_map[x['bn']],'day':day,'venue':'V3',
                        'buyer':byr,'ath':x['val'],'usd':usd*x['val']/tot})
    # ---- V4 ----
    d=v4tx.get(tx)
    if d:
        if d['ath_sell']>1e-9:
            ins=[x for x in items if x['to']==MGR]; tot=sum(x['val'] for x in ins)
            if tot>1e-9:
                day=day_of(ts_map[ins[0]['bn']]); usd=d['bio_out']*px('BIO',day)
                for x in ins:
                    slr,routed=attribute(x['from'],tx)
                    sells.append({'tx':tx,'bn':x['bn'],'ts':ts_map[x['bn']],'day':day,'venue':'V4',
                        'seller':slr,'routed':routed,'ath':x['val'],'usd':usd*x['val']/tot})
        if d['ath_buy']>1e-9:
            outs=[x for x in items if x['from']==MGR]; tot=sum(x['val'] for x in outs)
            if tot>1e-9:
                day=day_of(ts_map[outs[0]['bn']]); usd=d['bio_in']*px('BIO',day)
                for x in outs:
                    byr,routed=attribute(x['to'],tx)
                    buys.append({'tx':tx,'bn':x['bn'],'ts':ts_map[x['bn']],'day':day,'venue':'V4',
                        'buyer':byr,'ath':x['val'],'usd':usd*x['val']/tot})

json.dump(sells,open('sells.json','w')); json.dump(buys,open('buys.json','w'))

# ---- per-wallet aggregation ----
W=defaultdict(lambda:{'ath_sold':0.0,'usd_sold':0.0,'sell_legs':0,'ath_bought':0.0,'usd_bought':0.0,'buy_legs':0,
                      'venues':set(),'first_sell':None,'last_sell':None,'sell_days':set(),'routed_legs':0})
for s in sells:
    w=W[s['seller']]; w['ath_sold']+=s['ath']; w['usd_sold']+=s['usd']; w['sell_legs']+=1
    w['venues'].add(s['venue']); w['sell_days'].add(s['day']); w['routed_legs']+=1 if s['routed'] else 0
    w['first_sell']=s['ts'] if w['first_sell'] is None else min(w['first_sell'],s['ts'])
    w['last_sell'] =s['ts'] if w['last_sell']  is None else max(w['last_sell'], s['ts'])
for b in buys:
    w=W[b['buyer']]; w['ath_bought']+=b['ath']; w['usd_bought']+=b['usd']; w['buy_legs']+=1; w['venues'].add(b['venue'])

print(f"SELLS legs:{len(sells)} BUYS legs:{len(buys)}")
print(f"TOTAL gross ATH sold:{sum(s['ath'] for s in sells):,.0f}  USD:${sum(s['usd'] for s in sells):,.0f}")
print(f"distinct sellers:{len(set(s['seller'] for s in sells))}")
json.dump({k:{**v,'venues':sorted(v['venues']),'sell_days':len(v['sell_days'])} for k,v in W.items()},
          open('wallets_core.json','w'))
print("CORE DONE")
