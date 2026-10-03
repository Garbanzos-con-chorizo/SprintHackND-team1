# Proposal: pulse JSON (`out/pulse/<YYYY-MM-DD>.json`)

> **Superseded** by Dani's `docs/contracts/pulse.md` (schema_version 1). The renderer and `reports/mock_pulse.py` now follow that contract. Kept for history.

- **From:** Orlando (with Gemini), for **Dani** to accept, change or replace in `docs/contracts/pulse.md` (P0). Dani owns the contract; this is only a starting point so P-O2 isn't blocked.
- **Status:** proposed, `schema_version: "0.1-proposed"`
- **Producer:** `pulse --date YYYY-MM-DD` (Dani, P-D4). **Consumer:** `python -m reports.pulse` (Orlando, P-O2).
- **Mock:** `python -m reports.mock_pulse --scenario day_refund` builds this file from `data/sample/<scenario>/expected.json` until the real command exists.

## Rules
- Money is integer USD cents. Counts are integers.
- A source with `status` other than `ok` has **`null`** for every number, never `0`. The renderer shows "No data", not $0.
- Enterprise totals only add marketplaces with `status: ok`, and list what was left out.
- Every delta can be `null`, with a `reason` the page can show.
- Unknown fields are ignored by the renderer, so adding fields is not a breaking change.

## Shape
```json
{
  "schema_version": "0.1-proposed",
  "business_date": "2026-10-03",
  "prior_date": "2026-10-02",
  "timezone": "America/New_York",
  "generated_at": "2026-10-04T02:15:00-04:00",
  "marketplaces": {
    "shopgoodwill": {
      "label": "ShopGoodwill",
      "status": "ok",
      "sales_cents": 232400,
      "refunds_cents": 0,
      "revenue_cents": 232400,
      "fees_cents": 0,
      "orders": 68,
      "customers": 62,
      "customer_basis": "buyer",
      "delta": { "revenue_cents": 109600, "revenue_pct": 89.3, "orders": 25, "reason": null }
    },
    "amazon": { "...": "same fields, customer_basis: order" },
    "ebay": {
      "label": "eBay",
      "status": "missing",
      "sales_cents": null, "refunds_cents": null, "revenue_cents": null, "fees_cents": null,
      "orders": null, "customers": null, "customer_basis": "buyer",
      "delta": { "revenue_cents": null, "revenue_pct": null, "orders": null, "reason": "no data today" }
    },
    "other": {
      "label": "Other",
      "status": "not_tracked",
      "...": "all numbers null, reason: no source mapped to Other yet"
    }
  },
  "enterprise": {
    "sales_cents": 266632, "refunds_cents": 0, "revenue_cents": 266632, "fees_cents": 9452,
    "orders": 85, "customers": 79,
    "included": ["shopgoodwill", "amazon"],
    "excluded": ["ebay"],
    "complete": false,
    "delta": {
      "basis": ["shopgoodwill", "amazon"],
      "revenue_cents": 124394, "revenue_pct": 87.5, "orders": 30,
      "reason": "like-for-like: only marketplaces with data on both days"
    }
  },
  "data_quality": {
    "warnings_total": 46,
    "by_kind": { "duplicate": 46 },
    "rows_rejected": 0
  },
  "definitions": {
    "revenue": "item subtotal of sales minus refunds; excludes shipping, tax and fees",
    "fees": "marketplace fees on sales, shown separately",
    "customers": "distinct buyers; Amazon has no buyer id so it counts orders",
    "business_date": "order (or refund) time in America/New_York",
    "enterprise_customers": "sum of per-marketplace counts; buyers can't be matched across marketplaces"
  }
}
```

## Fields
| Field | Type | Notes |
|---|---|---|
| `marketplaces` | object | Keys always `shopgoodwill`, `amazon`, `ebay`, `other` so the page always has four rows. |
| `marketplaces.*.status` | enum | `ok`, `missing` (no file), `stale` (file but no rows that day), `not_tracked` (no source mapped, used for `other` in phase 1). From `out/source_status.json`. |
| `*.sales_cents` / `refunds_cents` | int or null | `refunds_cents` is ≤ 0. `revenue_cents = sales_cents + refunds_cents`. |
| `*.customer_basis` | enum | `buyer` or `order`; the page labels counts by order. |
| `*.delta` | object | vs `prior_date`. `null` values when either day lacks data or the prior revenue is 0 (pct only); `reason` explains. |
| `enterprise.included` / `excluded` / `complete` | list, list, bool | `complete=false` drives a "totals exclude eBay" banner. |
| `enterprise.delta.basis` | list | Like-for-like: only marketplaces `ok` on both days, so a missing file doesn't look like a revenue drop. |
| `data_quality` | object | Counts from `out/warnings.json` for this run. |
| `definitions` | object | Shown verbatim as the page footnote, so changing a definition never needs a code change. |

## Open for Dani
1. Is `not_tracked` for `other` fine, or should `other` be omitted until a source exists?
2. Should the enterprise delta be like-for-like (proposed) or the raw total vs total?
3. `latest.json` copy as proposed in `HANDOFFS.md`: keep it.
