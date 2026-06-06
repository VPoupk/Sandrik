#!/usr/bin/env python3
"""Scan OUTBOUND (disposal) AKE transfers for every in-scope wallet.

Uses a single combined topics OR-filter (sender IN scope) over the full block
range in 50k-block chunks, so all wallets are covered in ~one pass instead of
one scan per wallet. Resumable: checkpoints events + scanned_to to
data/disposals_raw.json every ~15 chunks. On any getLogs failure the block
range is recursively halved (handles range/result-size limits).
"""
import os
from pl_common import (rpc, log, AKE, TRANSFER, DEC, DATA, topic_addr,
                       head_block, load_json, save_json, set_status)

CHUNK = 50000
GROUP = 45            # max sender addresses per topics OR-filter
CKPT = os.path.join(DATA, "disposals_raw.json")


def get_logs_safe(b, hi, topic, depth=0):
    try:
        return rpc("eth_getLogs", [{
            "address": AKE, "fromBlock": hex(b), "toBlock": hex(hi),
            "topics": [TRANSFER, topic]}])
    except Exception as e:
        if hi > b and depth < 20:
            mid = (b + hi) // 2
            return (get_logs_safe(b, mid, topic, depth + 1) +
                    get_logs_safe(mid + 1, hi, topic, depth + 1))
        log("  getLogs FAILED %d-%d: %s" % (b, hi, e))
        raise


def main():
    wallets = load_json(os.path.join(DATA, "wallets.json"), {})
    addrs = sorted(wallets.keys())
    if not addrs:
        log("scan_disposals: no wallets in scope, abort")
        return
    start = min(int(wallets[a].get("first_blk", 57800000)) for a in addrs)

    ck = load_json(CKPT, None)
    if ck and ck.get("addrs") == addrs and ck.get("head_target") and not ck.get("done"):
        scanned_to = ck["scanned_to"]
        events = ck["events"]
        head = ck["head_target"]
        log("scan_disposals: RESUMING at block %d (%d events so far)"
            % (scanned_to, len(events)))
    elif ck and ck.get("addrs") == addrs and ck.get("done"):
        log("scan_disposals: already COMPLETE (%d events) — nothing to do"
            % len(ck.get("events", [])))
        set_status(stage="scan_disposals_done",
                   outbound_events=len(ck.get("events", [])), scan_pct=100.0)
        return
    else:
        head = head_block()
        scanned_to = start - 1
        events = []
        log("scan_disposals: START fresh  %d..%d  wallets=%d"
            % (start, head, len(addrs)))

    groups = [addrs[i:i + GROUP] for i in range(0, len(addrs), GROUP)]
    topics = [[topic_addr(a) for a in g] for g in groups]
    topics = [(t[0] if len(t) == 1 else t) for t in topics]

    total_chunks = (head - start) // CHUNK + 1
    b = scanned_to + 1
    since = 0
    while b <= head:
        hi = min(b + CHUNK - 1, head)
        for t in topics:
            for lg in get_logs_safe(b, hi, t):
                events.append([
                    int(lg["blockNumber"], 16),
                    "0x" + lg["topics"][1][-40:],
                    "0x" + lg["topics"][2][-40:],
                    int(lg["data"], 16) / 10 ** DEC,
                    lg["transactionHash"]])
        scanned_to = hi
        b = hi + 1
        since += 1
        if since >= 15 or b > head:
            save_json(CKPT, {"addrs": addrs, "head_target": head,
                             "scanned_to": scanned_to, "events": events,
                             "done": b > head})
            done = (scanned_to - start) // CHUNK + 1
            pct = round(100 * done / max(total_chunks, 1), 1)
            set_status(stage="scan_disposals", scan_scanned_to=scanned_to,
                       scan_head=head, scan_pct=pct, outbound_events=len(events))
            log("  scan %.1f%%  block %d/%d  events=%d"
                % (pct, scanned_to, head, len(events)))
            since = 0

    save_json(CKPT, {"addrs": addrs, "head_target": head,
                     "scanned_to": scanned_to, "events": events, "done": True})
    log("scan_disposals: COMPLETE  %d outbound events / %d wallets"
        % (len(events), len(addrs)))
    set_status(stage="scan_disposals_done", outbound_events=len(events),
               scan_pct=100.0)


if __name__ == "__main__":
    main()
