"""Cross-file dedupe (task P-V5): the same transaction exported twice must count once.

Overlapping or re-downloaded exports produce rows with the same txn_id. The first one (in sorted
file order) is kept. A dropped copy is logged as a `duplicate` warning; if its amounts differ from
the kept row the warning says so, because that is a conflict a person should look at, not a harmless
re-download.
"""
_COMPARED = ("gross_cents", "fee_cents", "business_date", "customer_id")


def dedupe_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    kept: dict[str, dict] = {}
    warnings: list[dict] = []
    for row in rows:
        first = kept.get(row["txn_id"])
        if first is None:
            kept[row["txn_id"]] = row
            continue
        differs = [c for c in _COMPARED if str(first[c]) != str(row[c])]
        reason = f"same transaction as {first['source_file']} row {first['source_row']}"
        if differs:
            reason += f", but {', '.join(differs)} differ; kept the first"
        warnings.append({"source_file": row["source_file"], "source_row": row["source_row"],
                         "kind": "duplicate", "reason": reason})
    return list(kept.values()), warnings


def dedupe_payouts(payouts: list[dict]) -> tuple[list[dict], list[dict]]:
    """The same payout in overlapping downloads (same payout_id) counts once; first copy wins."""
    return _dedupe(payouts, lambda p: p["payout_id"], "payout", ("amount_cents",))


def dedupe_bank(lines: list[dict]) -> tuple[list[dict], list[dict]]:
    """Overlapping bank exports: a line is the same line only when its running balance matches too.
    Without a balance, two same-day lines of the same amount may be two real payments, so both stay."""
    def key(b):
        if b["balance_cents"] == "":
            return b["bank_txn_id"]
        return (b["account"], b["posting_date"], b["description"], b["amount_cents"], b["balance_cents"])
    return _dedupe(lines, key, "bank line", ())


# How to tell that two rows of a close table are the same row arriving twice (overlapping exports).
# A row without the identifying value is never merged.
_TABLE_IDS = {
    "ledger": ("ledger entry", lambda r: r["entry_no"]),
}


def dedupe_table(name: str, items: list[dict]) -> tuple[list[dict], list[dict]]:
    if name not in _TABLE_IDS:
        return items, []
    what, ident = _TABLE_IDS[name]
    return _dedupe(items, lambda r: ident(r) or (r["source_file"], r["source_row"]), what, ())


def _dedupe(items: list[dict], key, what: str, compared: tuple[str, ...]) -> tuple[list[dict], list[dict]]:
    kept: dict = {}
    warnings: list[dict] = []
    for item in items:
        first = kept.setdefault(key(item), item)
        if first is item:
            continue
        reason = f"same {what} as {first['source_file']} row {first['source_row']}"
        differs = [c for c in compared if str(first[c]) != str(item[c])]
        if differs:
            reason += f", but {', '.join(differs)} differ; kept the first"
        warnings.append({"source_file": item["source_file"], "source_row": item["source_row"],
                         "kind": "duplicate", "reason": reason})
    return list(kept.values()), warnings
