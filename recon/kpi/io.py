"""Write the KPI files (docs/contracts/kpi.md)."""
import json
import shutil
from pathlib import Path


def write_kpis(out_dir, doc):
    """Write <out_dir>/<type>-<id>.json and refresh latest-<type>.json. Returns the path written."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    kind = doc["period"]["type"]
    target = out_dir / f"{kind}-{doc['period']['id']}.json"
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    # Period ids sort as text (2026-09 < 2026-10, 2026-W38 < 2026-W39), so the greatest name is the latest.
    newest = max(out_dir.glob(f"{kind}-*.json"), key=lambda p: p.stem)
    shutil.copyfile(newest, out_dir / f"latest-{kind}.json")
    return target
