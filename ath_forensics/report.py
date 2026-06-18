"""Enrich wallets: holdings, net flow, non-venue transfers, activity classification.
Produce the >$1k seller table."""
import rpc, json
from datetime import datetime, timezone
from collections import defaultdict

USER="0xf0940b14e8a4be798cd713a6807e95f47b769d9c"
ZERO="0x0000000000000000000000000000000000000000"
bj=json.load(open('blocks.json')); LATEST=bj['latest']
V3P=rpc.V3_POOL.lower(); MGR=rpc.V4_MANAGER.lower(); VEN={V3P,MGR}

def taddr(t): return "0x"+t[-40:].lower()
T=[]
for l in json.load(open('ath_transfers_raw.json')):
    T.append({'from':taddr(l['topics'][1]),'to':taddr(l['topics'][2]),'val':int(l['data'],16)/1e18,
              'bn':int(l['blockNumber'],16),'tx':l['transactionHash']})
core=json.load(open('wallets_core.json'))
sells=json.load(open('sells.json')); buys=json.load(open('buys.json'))

# Per-entity activity. Entity = attributed actor for swaps (seller/buyer in sells/buys),
# and the raw address for direct (non-venue) transfers.
act=defaultdict(lambda:{'sell_txs':set(),'buy_txs':set(),'recv':0.0,'recv_legs':0,'recv_txs':set(),
                        'sent':0.0,'sent_legs':0,'sent_txs':set(),'mint':0.0,'mint_legs':0})
for s in sells: act[s['seller']]['sell_txs'].add(s['tx'])
for b in buys:  act[b['buyer']]['buy_txs'].add(b['tx'])
for x in T:
    f,t,v=x['from'],x['to'],x['val']
    if f not in VEN and t not in VEN:        # wallet<->wallet (non-venue) transfer
        if f==ZERO:
            act[t]['mint']+=v; act[t]['mint_legs']+=1
        else:
            act[f]['sent']+=v; act[f]['sent_legs']+=1; act[f]['sent_txs'].add(x['tx'])
        if t!=ZERO and f!=ZERO:
            act[t]['recv']+=v; act[t]['recv_legs']+=1; act[t]['recv_txs'].add(x['tx'])

# wallets that sold >$1k
cand={a:d for a,d in core.items() if d['usd_sold']>=1000 and not a.startswith('COW:')}
# also surface COW aggregate
cow_usd=sum(d['usd_sold'] for a,d in core.items() if a.startswith('COW:'))
cow_ath=sum(d['ath_sold'] for a,d in core.items() if a.startswith('COW:'))

addrs=sorted(cand)
# holdings now (batch balanceOf)
bal={}
for i in range(0,len(addrs),60):
    ch=addrs[i:i+60]
    data=["0x70a08231"+a[2:].rjust(64,"0") for a in ch]
    res=rpc.batch([("eth_call",[{"to":rpc.ATH,"data":dd},hex(LATEST)]) for dd in data])
    for a,r in zip(ch,res): bal[a]=int(r,16)/1e18 if r and r!="0x" else 0.0
# also code (contract?) for labeling
codes={}
for i in range(0,len(addrs),100):
    ch=addrs[i:i+100]
    for a,r in zip(ch,rpc.batch([("eth_getCode",[a,"latest"]) for a in ch])): codes[a]=(r not in("0x","0x0",None))

rows=[]
for a in addrs:
    d=cand[a]; ac=act.get(a,{})
    net=d['ath_sold']-d['ath_bought']
    sell_txs=ac.get('sell_txs',set()); buy_txs=ac.get('buy_txs',set())
    recv_txs=ac.get('recv_txs',set()); sent_txs=ac.get('sent_txs',set())
    n_txs=len(sell_txs|buy_txs|recv_txs|sent_txs)
    rows.append({'addr':a,'is_user':a==USER,'contract':codes.get(a,False),
        'ath_sold':d['ath_sold'],'usd_sold':d['usd_sold'],'sell_legs':d['sell_legs'],'sell_txs':len(sell_txs),
        'ath_bought':d['ath_bought'],'usd_bought':d['usd_bought'],'buy_legs':d['buy_legs'],'buy_txs':len(buy_txs),
        'net_ath':net,'holdings':bal.get(a,0.0),'venues':d['venues'],'sell_days':d['sell_days'],
        'first_sell':d['first_sell'],'last_sell':d['last_sell'],
        'recv':ac.get('recv',0),'recv_legs':ac.get('recv_legs',0),
        'sent':ac.get('sent',0),'sent_legs':ac.get('sent_legs',0),
        'mint':ac.get('mint',0),'n_txs':n_txs})
    # classify
    g=d['ath_sold']; b=d['ath_bought']
    ratio=min(g,b)/max(g,b,1e-9)
    if ratio>0.85 and d['buy_legs']>=3:
        cls='arb/MM bot'
    elif net>0 and b<0.2*g:
        cls='net distributor'
    elif net>0:
        cls='net seller (also buys)'
    else:
        cls='net accumulator'
    rows[-1]['class']=cls

rows.sort(key=lambda r:-r['usd_sold'])
json.dump(rows,open('table_rows.json','w'))

def dts(ts): return datetime.fromtimestamp(ts,tz=timezone.utc).strftime("%m-%d %H:%M") if ts else "-"
print(f"{'#':>2} {'address':42} {'cls':18} {'ATHsold':>11} {'USDsold':>9} {'hold':>9} {'net':>10} {'selltx':>6} {'buytx':>6} {'in':>4} {'out':>4} {'ntx':>4} {'first':>11} {'last':>11}")
for i,r in enumerate(rows):
    tag=' <-YOU' if r['is_user'] else (' [C]' if r['contract'] else '')
    print(f"{i+1:>2} {r['addr']} {r['class']:18} {r['ath_sold']:>11,.0f} {r['usd_sold']:>9,.0f} {r['holdings']:>9,.0f} {r['net_ath']:>10,.0f} {r['sell_txs']:>6} {r['buy_txs']:>6} {r['recv_legs']:>4} {r['sent_legs']:>4} {r['n_txs']:>4} {dts(r['first_sell']):>11} {dts(r['last_sell']):>11}{tag}")
print(f"\n# wallets sold>=$1k: {len(rows)}")
print(f"CoW-routed (end-user opaque): {cow_ath:,.0f} ATH / ${cow_usd:,.0f}")
print(f"TOTAL across >$1k sellers: {sum(r['ath_sold'] for r in rows):,.0f} ATH / ${sum(r['usd_sold'] for r in rows):,.0f}")
