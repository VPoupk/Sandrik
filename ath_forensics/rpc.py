"""Minimal, dependency-free Ethereum JSON-RPC helper (urllib stdlib only).
Handles endpoint failover, retries, batching, and getLogs pagination."""
import json, time, random, urllib.request, urllib.error

ENDPOINTS = [
    "https://ethereum-rpc.publicnode.com",
    "https://eth.drpc.org",
    "https://1rpc.io/eth",
    "https://rpc.mevblocker.io",
]
# Endpoints best suited for heavy eth_getLogs (large responses)
LOG_ENDPOINTS = [
    "https://ethereum-rpc.publicnode.com",
    "https://eth.drpc.org",
]

ATH        = "0xa4ffdf3208f46898ce063e25c1c43056fa754739"
WETH       = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
BIO        = "0xcb1592591996765ec0efc1f92599a19767ee5ffa"
V3_POOL    = "0x8071df1889d60a1c6329ef79976fb1f2e50599af"   # Uniswap V3 ATH/WETH
V4_MANAGER = "0x000000000004444c5dc75cb358380d2e3de08a90"   # Uniswap V4 PoolManager (singleton)
V4_POOLID  = "0x087f9b8edf505c2f190564765c89120d0b6298b606354e57d07ff3f55378c0ab"  # ATH/BIO poolId

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
# V3 Swap(address indexed sender, address indexed recipient, int256 amount0, int256 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick)
V3_SWAP_TOPIC  = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"

_id = 0
def _next_id():
    global _id; _id += 1; return _id

def call(method, params, tries=10, endpoints=None):
    eps = endpoints or ENDPOINTS
    payload = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":_next_id()}).encode()
    last = None
    off = random.randint(0, len(eps)-1)
    for attempt in range(tries):
        ep = eps[(attempt+off) % len(eps)]
        try:
            req = urllib.request.Request(ep, data=payload, headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"application/json"})
            with urllib.request.urlopen(req, timeout=45) as r:
                d = json.loads(r.read())
            if "error" in d:
                last = d["error"]; time.sleep(0.6*(attempt+1)); continue
            return d["result"]
        except Exception as e:
            last = str(e); time.sleep(0.8*(attempt+1))
    raise RuntimeError(f"RPC {method} failed: {last}")

def batch(reqs, tries=6):
    """reqs: list of (method, params). Returns list of results in order. Splits on failure."""
    if not reqs: return []
    body = []
    idmap = {}
    for i,(m,p) in enumerate(reqs):
        rid = _next_id(); idmap[rid] = i
        body.append({"jsonrpc":"2.0","method":m,"params":p,"id":rid})
    payload = json.dumps(body).encode()
    last=None
    for attempt in range(tries):
        ep = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            req = urllib.request.Request(ep, data=payload, headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
            if isinstance(d, dict) and "error" in d:
                last=d["error"]; time.sleep(0.6*(attempt+1)); continue
            out = [None]*len(reqs)
            ok = True
            for item in d:
                idx = idmap.get(item.get("id"))
                if idx is None: continue
                if "error" in item:
                    ok=False; break
                out[idx] = item["result"]
            if ok and all(x is not None for x in out):
                return out
            last = "partial/err in batch"; time.sleep(0.6*(attempt+1))
        except Exception as e:
            last=str(e); time.sleep(0.8*(attempt+1))
    # fallback: split
    if len(reqs) == 1:
        return [call(reqs[0][0], reqs[0][1])]
    mid = len(reqs)//2
    return batch(reqs[:mid]) + batch(reqs[mid:])

def get_logs(address, topics, from_block, to_block, span=40000):
    """Adaptive-span getLogs paginator. address can be str or list. Returns merged logs."""
    out = []
    start = from_block
    cur_span = span
    while start <= to_block:
        end = min(start + cur_span - 1, to_block)
        params = [{
            "fromBlock": hex(start),
            "toBlock": hex(end),
            "topics": topics,
        }]
        if address: params[0]["address"] = address
        try:
            res = call("eth_getLogs", params, tries=6, endpoints=LOG_ENDPOINTS)
            out.extend(res)
            start = end + 1
            # gently grow span back toward target if we shrank
            if cur_span < span:
                cur_span = min(span, cur_span*2)
        except Exception as e:
            msg = str(e).lower()
            if cur_span > 2000 and ("range" in msg or "limit" in msg or "result" in msg or "large" in msg or "many" in msg or "timeout" in msg or "failed" in msg):
                cur_span = max(2000, cur_span//2)
                continue
            # last resort: tiny span
            if cur_span > 500:
                cur_span = 500; continue
            raise
    return out

def block_by_ts(target_ts):
    """Binary search for the first block with timestamp >= target_ts."""
    lo = 1
    hi = int(call("eth_blockNumber", []), 16)
    while lo < hi:
        mid = (lo+hi)//2
        b = call("eth_getBlockByNumber", [hex(mid), False])
        ts = int(b["timestamp"],16)
        if ts < target_ts: lo = mid+1
        else: hi = mid
    return lo

def latest_block():
    return int(call("eth_blockNumber", []), 16)

def erc20_balance(token, holder, block="latest"):
    data = "0x70a08231" + holder.lower().replace("0x","").rjust(64,"0")
    r = call("eth_call", [{"to":token,"data":data}, block])
    return int(r,16)
