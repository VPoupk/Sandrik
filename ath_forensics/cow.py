"""Parse CoW Protocol Trade events for ATH sells -> attribute to real owner with exact USD proceeds."""
import rpc, json, keccak
from datetime import datetime, timezone
from collections import defaultdict
sells=json.load(open('sells.json'))
PX=json.load(open('prices_daily.json'))
ts_map={int(k):v for k,v in json.load(open('ts_map.json')).items()}
TRADE=keccak.topic("Trade(address,address,address,uint256,uint256,uint256,bytes)")
ATH=rpc.ATH
TOKS={ "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2":("WETH",18,"ETH"),
       "0xcb1592591996765ec0efc1f92599a19767ee5ffa":("BIO",18,"BIO"),
       "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48":("USDC",6,"USD"),
       "0xdac17f958d2ee523a2206206994597c13d831ec7":("USDT",6,"USD"),
       "0x6b175474e89094c44da98b954eedeac495271d0f":("DAI",18,"USD"),
       "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":("ETH",18,"ETH")}
def day_of(ts): return datetime.fromtimestamp(ts,tz=timezone.utc).strftime("%Y-%m-%d")
def px(sym,day):
    if sym=="USD": return 1.0
    d=PX[sym]
    if day in d: return d[day]
    ks=sorted(d); best=None
    for k in ks:
        if k<=day: best=k
        else: break
    return d[best] if best else d[ks[0]]

cow_txs=sorted({s['tx'] for s in sells if s['seller'].startswith("COW:")})
recs={}
for i in range(0,len(cow_txs),40):
    ch=cow_txs[i:i+40]
    for h,r in zip(ch,rpc.batch([("eth_getTransactionReceipt",[h]) for h in ch])): recs[h]=r
# need block ts
need=sorted({int(r['blockNumber'],16) for r in recs.values()} - set(ts_map))
for i in range(0,len(need),100):
    ch=need[i:i+100]
    for b,rr in zip(ch,rpc.batch([("eth_getBlockByNumber",[hex(b),False]) for b in ch])): ts_map[b]=int(rr['timestamp'],16)

cow_sells=[]
unknown_tok=set()
for h,r in recs.items():
    bn=int(r['blockNumber'],16); ts=ts_map[bn]; day=day_of(ts)
    for lg in r['logs']:
        if lg['topics'] and lg['topics'][0]==TRADE:
            owner="0x"+lg['topics'][1][-40:].lower()
            d=lg['data'][2:]
            sellTok="0x"+d[0:64][-40:].lower(); buyTok="0x"+d[64:128][-40:].lower()
            sellAmt=int(d[128:192],16); buyAmt=int(d[192:256],16)
            if sellTok!=ATH: continue
            ath=sellAmt/1e18
            if buyTok in TOKS:
                nm,dec,psym=TOKS[buyTok]; usd=(buyAmt/10**dec)*px(psym,day)
            else:
                unknown_tok.add(buyTok); usd=ath*px("ATH",day)  # fallback spot
            cow_sells.append({'tx':h,'bn':bn,'ts':ts,'day':day,'venue':'CoW','seller':owner,'ath':ath,'usd':usd})
json.dump(cow_sells,open('cow_sells.json','w'))
agg=defaultdict(lambda:[0.0,0.0,0])
for s in cow_sells: agg[s['seller']][0]+=s['ath']; agg[s['seller']][1]+=s['usd']; agg[s['seller']][2]+=1
print("=== CoW ATH sellers w/ realized USD ===")
for o,(a,u,n) in sorted(agg.items(),key=lambda kv:-kv[1][1]):
    print(f"  {o}  {a:>10,.0f} ATH  ${u:>8,.0f}  ({n} fills)")
print("unknown buyTokens:",unknown_tok)
json.dump(ts_map,open('ts_map.json','w'))
