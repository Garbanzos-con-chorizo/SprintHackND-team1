# Claims on shared files

Add a row before editing anything outside your lane (shared config, dependency files, contracts). Delete your row when your PR is merged. Check here before touching shared files.

| Path | Who | Since | Why |
|------|-----|-------|-----|
| `reports/scorecard.py`, `reports/hub.py` | Victor (assigned by Dani) | 2026-10-03 23:55 | R1, R3, R4: sell-through boxes, day / week / month scorecards on the portal, CSV and PDF links (`docs/PLAN_PHASE_2_3.md` section 11) |
| `reports/weekly.py`, `reports/kpi.py` | Victor (assigned by Dani) | 2026-10-03 23:55 | R2: weekly page from the KPI file; `reports/kpi.py` is deleted |
| `data/generate.py`, `data/sample/` (a new August scenario only) | Victor (assigned by Dani) | 2026-10-03 23:55 | R5: prior month for Revenue Growth % |
| `docs/pitch/` (a new demo script, `kpi_catalog.md`) | Victor (assigned by Dani) | 2026-10-03 23:55 | R6: demo script for phases 2 and 3 |
