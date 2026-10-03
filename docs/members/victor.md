# Status — Victor (core engine, `engine/`)

Only the owner edits this file, except the "Requests to me" section, where teammates/agents may append.

**Last updated:** 2026-10-03 · **Branch:** victor/phase1-contracts

## Done
- Phase split of all tasks: `docs/PHASES.md`
- Phase 1 transaction contract (draft): `docs/contracts/transaction.md`, mock `docs/contracts/examples/transactions.sample.csv`
- Handoff map: `docs/HANDOFFS.md` (PR #4)
- `out/.gitignore` so generated output is not committed (no root file touched)

## In progress
- Planning my phase 1 work before building (see Next)

## Blocked / needs from others
- Dani: write `docs/contracts/pulse.md` (P0); confirm or change the pulse JSON shape proposed in `docs/HANDOFFS.md`
- Orlando: sample exports (O1, P-O1) so parsers match real column names; until then I code against hand-made rows
- Team: confirm `transaction.md` (task 0.6) and pick the engine language (V1)

## Next (phase 1, in order)
1. V1 scaffold in `engine/` (language, test runner, run command) once the stack is agreed
2. V2 parser base interface and source detection
3. V3 parsers: ShopGoodwill, eBay, Amazon
4. V6 cleaning and warnings, P-V5 dedupe, P-V3 day boundary
5. P-V1 marketplace tagging, P-V2 customer identity
6. V9 runner and P-V4 source status
Phase 3 (V4, V5, V7, V8, V10, V11, rule contract 0.2) comes after the pulse works end to end.

## How to run / test my part
- Not built yet. Command will be added here after V1.

## Requests to me (append only: `- [from X, time] request`)
