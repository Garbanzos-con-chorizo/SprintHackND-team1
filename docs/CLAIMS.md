# Claims on shared files

Add a row before editing anything outside your lane (shared config, dependency files, contracts). Delete your row when your PR is merged. Check here before touching shared files.

| Path | Who | Since | Why |
|------|-----|-------|-----|
| `reports/reconcile.py`, `reports/bc_export.py`, `reports/close_report.py`, `reports/mock_recon.py`, `reports/config/bc_mapping.csv`, `reports/tests/test_reconcile.py`, `reports/tests/test_bc_export.py`, and the new `reports/close.py`, `reports/config/close_*.csv`, `reports/tests/test_close*.py` | Dani | 2026-10-04 00:20 EDT | Phase 3 while Orlando is away (decision 009, proposed; `docs/PLAN_PHASE_3.md`). Held until he takes them back or the freeze |
| `data/generate.py`, `data/sample/messy_month/`, `data/sample/tidy_month/`, `data/README.md` | Dani | 2026-10-04 00:20 EDT | Same: the tidy month, the side folders and the late reports are in. No existing sample changed |
| `docs/contracts/close-payload.md`, `close-outputs.md`, `close-rules.md` | Dani | 2026-10-04 00:20 EDT | Same: the close's contracts (payload v0.5, outputs v0.1, rules v0.1) |
