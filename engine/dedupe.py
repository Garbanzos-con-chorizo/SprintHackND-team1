"""Cross-file dedupe (task P-V5): the same transaction exported twice must count once.

Overlapping or re-downloaded exports produce rows with the same txn_id. The first one (in sorted
file order) is kept. A dropped copy is logged as a `duplicate` warning; if its amounts differ from
the kept row the warning says so, because that is a conflict a person should look at, not a harmless
re-download.
"""
_COMPARED = ("gross_cents", "fee_cents", "shipping_cents", "handling_cents", "business_date", "customer_id")


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
