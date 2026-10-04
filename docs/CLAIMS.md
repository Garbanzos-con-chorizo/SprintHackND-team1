# Claims on shared files

Add a row before editing anything outside your lane (shared config, dependency files, contracts). Delete your row when your PR is merged. Check here before touching shared files.

| Path | Who | Since | Why |
|------|-----|-------|-----|
| `reports/reconcile.py`, `reports/bc_export.py`, `reports/close_report.py`, `reports/mock_recon.py`, `reports/config/bc_mapping.csv`, `reports/tests/test_reconcile.py`, `reports/tests/test_bc_export.py` | Dani | 2026-10-04 00:20 EDT | Phase 3 while Orlando is away (decision 009, proposed; `docs/PLAN_PHASE_3.md`). Held until he takes them back or the freeze |
| `data/generate.py`, `data/sample/messy_month/`, `data/README.md` | Dani | 2026-10-04 00:20 EDT | Same: a tidy month for the close and the two late reports. No existing sample changes |
| `docs/contracts/close-payload.md` | Dani | 2026-10-04 00:20 EDT | Same: v0.4 (payout windows, `INCOMPLETE`) |
| `docs/ASSUMPTIONS.md`, section 2c only | Dani | 2026-10-04 00:45 EDT | The month-end sources assumed to come from APIs (released when PR 53 merges) |
