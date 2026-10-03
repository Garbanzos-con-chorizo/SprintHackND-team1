# Pulse fixtures (D1)

Hand-made mock engine output, one folder per scenario, each shaped like `out/` in `docs/contracts/transaction.md`. All report `2026-10-02`. Orlando's P-O1 sample days replace or join these at integration.

| Scenario | What is in it | Expected for 2026-10-02 |
|---|---|---|
| `clean_day` | Three sources `ok`, no refunds, plus rows for 2026-10-01 so the delta has a prior day | Enterprise revenue 30147 (prior day 25800) |
| `refund_day` | eBay refund of a same-day sale and of a sale from the day before | eBay gross 4449, refunds -4199, revenue 250, orders 2 |
| `missing_source` | eBay `missing`, Amazon `stale` (only 2026-10-01 rows) | Only ShopGoodwill in the total: 20900; eBay and Amazon null |
| `duplicate_rows` | One `txn_id` repeated in the CSV (should not happen, the loader drops it) and two `duplicate` warnings from the engine | Same numbers as the clean day; `data_quality.by_kind.duplicate` = 2 |
| `zero_revenue` | eBay's only sale fully refunded | eBay `ok` with revenue 0 (a real zero, not null), orders 1 |
