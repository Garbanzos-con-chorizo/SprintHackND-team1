"""source_status.json (task P-V4): for the pulse day, did each marketplace's data arrive?

Keyed by marketplace, not by file source, because one file can feed several marketplaces (a Cash Monkey
export carries Amazon, eBay and Goodwillbooks) and the pulse is organized by marketplace.

  ok       a file feeding this marketplace was read and has rows for the day
  stale    a file feeding it was read but has no rows for the day (a quiet day and an old export look
           the same, so the pulse treats it as no data)
  missing  no file that could feed it was read (never downloaded, or unreadable: see warnings.json)
"""
from .contract import EXPECTED_MARKETPLACES


def build_source_status(business_date: str, generated_at: str, files: list[dict], rows: list[dict]) -> dict:
    day_rows: dict[str, list[dict]] = {}
    for r in rows:
        if r["business_date"] == business_date:
            day_rows.setdefault(r["marketplace"], []).append(r)

    sources: dict[str, dict] = {}
    # `other` is reported only when it has rows that day; otherwise it is left out on purpose.
    marketplaces = list(EXPECTED_MARKETPLACES) + (["other"] if "other" in day_rows else [])
    for m in marketplaces:
        feeding = [f["file"] for f in files if m in f["feeds"]]
        todays = day_rows.get(m, [])
        if not feeding and not todays:
            sources[m] = {"status": "missing", "files": [], "rows": 0}
        elif todays:
            contributing = sorted({r["source_file"] for r in todays})
            sources[m] = {"status": "ok", "files": contributing, "rows": len(todays)}
        else:
            sources[m] = {"status": "stale", "files": sorted(set(feeding)), "rows": 0}
    return {"generated_at": generated_at, "business_date": business_date, "sources": sources}
