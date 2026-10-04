"""Enrichment across files (step 03 of Goodwill's target close, deck slide 40: "supplier assignment").

One rule so far: each jewelry sale gets the supplier the lookup file gives for its item. An item the lookup
does not know keeps an empty supplier and becomes a `missing_supplier` warning: never a guess.
"""


def assign_suppliers(items: list[dict], lookup: list[dict]) -> list[dict]:
    """Fill `supplier` on the jewelry rows in place from the lookup rows; return the warnings."""
    warnings: list[dict] = []
    known: dict[str, dict] = {}
    for row in lookup:
        first = known.setdefault(row["item_id"], row)
        if first is not row and first["supplier"] != row["supplier"]:
            warnings.append({"source_file": row["source_file"], "source_row": row["source_row"], "kind": "duplicate",
                             "reason": f"item {row['item_id']} has supplier {first['supplier']!r} in "
                                       f"{first['source_file']} row {first['source_row']} and {row['supplier']!r} here; "
                                       f"kept the first"})
    for item in items:
        if item["supplier"]:
            continue  # the report already says who supplied it
        if item["item_id"] in known:
            item["supplier"] = known[item["item_id"]]["supplier"]
            continue
        why = "is not in the supplier lookup" if lookup else "has no supplier lookup: no supplier lookup file was read"
        warnings.append({"source_file": item["source_file"], "source_row": item["source_row"], "kind": "missing_supplier",
                         "reason": f"jewelry item {item['item_id']} (${item['amount_cents'] / 100:,.2f}) {why}, "
                                   f"so no supplier is assigned"})
    return warnings
