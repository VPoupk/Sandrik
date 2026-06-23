# VITARNA — Holder, Buyer & Cluster Analysis

On-chain forensic analysis of **VitaRNA (VITARNA)** — the tokenized IP of the Artan Bio
IP-NFT (VitaDAO IP-NFT #28) on **Ethereum mainnet**.

**Contract:** `0x7b66E84Be78772a3afAF5ba8c1993a1B5D05F9C2`

Open **[`index.html`](index.html)** in a browser for the full interactive report (self-contained;
data is embedded inline, D3 loaded from CDN).

## Headline findings (snapshot 2026-06-23)

- **Treasury-dominated:** the `vitadao.eth` Safe holds **47.9%** of supply; treasury + genesis
  distributor combined = **57.6%**. Top-10 control **89.4%**, Gini **0.967**.
- **Thin real float:** only **15.2%** of supply sits in ordinary EOAs. ~8.9% is still vesting via
  Sablier, and DEX liquidity is just **1.64%** of supply — the asset is thinly traded by design.
- **36h buying is organic & small:** 45 net buyers vs 8 sellers; 39/45 entered through DEX or
  aggregator routes (0x, 1inch, Uniswap UniversalRouter, CoW, Relay). The single largest "buy"
  (37,218) is a **Sablier vesting claim**, not a market order. Real on-market buying ≈ 42k VITARNA (~$40k).
- **Largest real cluster:** a 5-wallet entity around **holder #6** (`0xa6b6…eac2`, 221k), totalling
  238k VITARNA (4.3%), linked by a shared personal funder (`0x8ca5…`) **and** direct transfers.
- **`zeusxbt.eth` entity** is tied to the biggest non-infrastructure past exit (`0x6221…`, peaked
  320k) — which moved wallet→multisig (a custody move, not a market dump).
- **Past exits are mostly structural:** the 600k–1M historical positions are project *contracts*
  (distributor, vesting, crowdsale). Among ordinary wallets, exits are internal restructuring +
  small DEX round-trips.

## Pipeline

| Step | Script | Output |
|------|--------|--------|
| 1 | `fetch_data.py` | holders + bulk transfers → `data/raw_data.json` |
| 2 | `fetch_transfers_v2.py` | complete transfer history (cursor-paginated, deduped) |
| 3 | `enrich.py` | per-wallet labels + first ETH funder → `data/enrich.json` |
| 4 | `vet_funders.py` | funder out-degree (CEX vs personal) → `data/funder_vet.json` |
| 5 | `process_data.py` | balances, concentration, 36h flows, clusters → `data/processed.json` |
| 6 | `build.py` — inline D3 + inject `data/processed.json` into `template.html` → **`index.html`** |

```bash
python3 fetch_data.py && python3 fetch_transfers_v2.py
python3 enrich.py && python3 vet_funders.py && python3 process_data.py
python3 build.py   # writes a fully self-contained index.html (no external deps)
```

`index.html` is self-contained — D3 is inlined and all data is embedded, so it works offline and
needs no server. `vendor/d3.v7.min.js` is vendored only so `build.py` can rebuild the file.

## Data sources

- **Blockscout** (`eth.blockscout.com`) — token metadata, holder list, full transfer history,
  address labels (ENS / contract names / protocol tags). No API key required.
- **Ethereum JSON-RPC** — chain id, block heights, `eth_call` metadata.
- **Dexscreener** — DEX pair discovery (Uniswap V3 VITARNA/VITA & VITARNA/WETH, Uniswap V4 VITARNA/BIO).

## Clustering methodology

Distribution **hubs** (token contract, pools, routers/settlers, genesis distributor, treasury,
vesting/crowdsale/Safe contracts, and any wallet with >40 counterparties) are **never** used to glue
wallets together — receiving a project allocation is not a peer relationship. Entities are inferred from
(a) direct VITARNA transfers between non-hub wallets, and (b) a shared **low-throughput personal** ETH
funder (high-throughput exchange/service funders are identified by out-degree and excluded).

Clustering proves *linkage*, not legal identity. This is research-grade pattern analysis, **not**
financial advice or an allegation of wrongdoing.
