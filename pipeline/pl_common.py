"""Shared helpers for the AKE disposal/proceeds pipeline.

This pipeline ONLY collects on-chain + price data and writes results to
pipeline/data/. It deliberately does NOT touch the HTML docs and does NOT
run git — applying results to the docs is a separate, manual step. (A prior
auto-apply/auto-commit pipeline repeatedly clobbered manual work; this one
does not.)
"""
import json, urllib.request, time, datetime, os

RPC = "https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3"
AKE = "0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
DEC = 18

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
LOGF = os.path.join(HERE, "pipeline.log")
os.makedirs(DATA, exist_ok=True)


def log(msg):
    line = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") + "Z  " + str(msg)
    print(line, flush=True)
    try:
        with open(LOGF, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def rpc(method, params, retries=6):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                       "params": params}).encode()
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(
                RPC, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=45) as r:
                d = json.loads(r.read())
            if "error" in d:
                last = d["error"]
                time.sleep(1.5 * (i + 1)); continue
            return d["result"]
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError("rpc %s failed after %d tries: %s" % (method, retries, last))


def topic_addr(a):
    return "0x" + a[2:].lower().rjust(64, "0")


def head_block():
    return int(rpc("eth_blockNumber", []), 16)


def balance_of(addr, block="latest"):
    data = "0x70a08231" + addr[2:].lower().rjust(64, "0")
    b = block if block == "latest" else hex(block)
    return int(rpc("eth_call", [{"to": AKE, "data": data}, b]), 16) / 10 ** DEC


_TS_CACHE = os.path.join(DATA, "blk_dates.json")


def load_ts():
    return load_json(_TS_CACHE, {})


def save_ts(c):
    save_json(_TS_CACHE, c)


def blk_date(blk, cache):
    k = str(blk)
    if k in cache:
        return cache[k]
    bh = rpc("eth_getBlockByNumber", [hex(blk), False])
    ts = int(bh["timestamp"], 16)
    d = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
    cache[k] = d
    return d


def load_json(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def set_status(**kw):
    p = os.path.join(DATA, "status.json")
    s = load_json(p, {})
    s.update(kw)
    s["updated"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") + "Z"
    save_json(p, s)
