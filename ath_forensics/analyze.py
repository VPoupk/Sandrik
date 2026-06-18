"""ATH forensic analysis: decode transfers + swaps, attribute sells, price in USD,
compute holdings, activity, and provenance. Pure on-chain + CoinGecko daily px."""
import rpc, json, time
from datetime import datetime, timezone
from collections import defaultdict

USER = "0xf0940b14e8a4be798cd713a6807e95f47b769d9c"

bj = json.load(open('blocks.json')); START, LATEST = bj['start'], bj['latest']
PX = json.load(open('prices_daily.json'))

def to_int256(h):
    v = int(h, 16)
    return v - (1 << 256) if v >= (1 << 255) else v

def topic_addr(t):  # 32-byte topic -> 0x addr (lowercase)
    return "0x" + t[-40:]

def day_of(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

def px(sym, day):
    d = PX[sym]
    if day in d: return d[day]
    # nearest earlier day fallback
    ks = sorted(d.keys())
    best = None
    for k in ks:
        if k <= day: best = k
        else: break
    return d[best] if best else d[ks[0]]

# ---------- load raw ----------
transfers = json.load(open('ath_transfers_raw.json'))
v3_swaps  = json.load(open('v3_swaps_raw.json'))
bio_out   = json.load(open('bio_out_v4_raw.json'))   # BIO leaving V4 mgr (proceeds to V4 ATH sellers)
bio_in    = json.load(open('bio_in_v4_raw.json'))    # BIO entering V4 mgr (V4 ATH buyers pay)
weth_out  = json.load(open('weth_out_v3_raw.json'))  # WETH leaving V3 pool

print("loaded:", len(transfers),"ATH transfers,",len(v3_swaps),"V3 swaps,",
      len(bio_out),"bio_out,",len(bio_in),"bio_in,",len(weth_out),"weth_out")

# ---------- decode ATH transfers ----------
T = []  # list of dicts
blocks_needed = set()
for l in transfers:
    frm = topic_addr(l['topics'][1]); to = topic_addr(l['topics'][2])
    val = int(l['data'], 16)
    bn  = int(l['blockNumber'], 16)
    T.append({'from':frm,'to':to,'val':val,'bn':bn,'tx':l['transactionHash'],
              'li':int(l['logIndex'],16)})
    blocks_needed.add(bn)
for l in v3_swaps: blocks_needed.add(int(l['blockNumber'],16))
for l in bio_out+bio_in+weth_out: blocks_needed.add(int(l['blockNumber'],16))

# ---------- block timestamps (batched) ----------
print("fetching", len(blocks_needed), "block timestamps...")
blocks_needed = sorted(blocks_needed)
ts_map = {}
B = 100
for i in range(0, len(blocks_needed), B):
    chunk = blocks_needed[i:i+B]
    reqs = [("eth_getBlockByNumber",[hex(b),False]) for b in chunk]
    res = rpc.batch(reqs)
    for b, r in zip(chunk, res):
        ts_map[b] = int(r['timestamp'],16)
    if i % 1000 == 0: print(f"  {i}/{len(blocks_needed)}")
json.dump(ts_map, open('ts_map.json','w'))
print("saved ts_map.json")
print("DONE transfers+timestamps stage")
