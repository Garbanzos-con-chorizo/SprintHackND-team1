# 002 — Engine in Python

- **Date / author:** 2026-10-03, Victor
- **Status:** accepted. Dani and Orlando both accepted it in their status files (2026-10-03). Minimum Python is 3.12, because `reports/pulse.py` uses an f-string syntax that 3.11 rejects; the engine itself runs on 3.11.

## Context
`engine/` parses messy CSV/XLSX exports, cleans them and writes the files in `docs/contracts/transaction.md`. The stack line in `CLAUDE.md` was still TBD when this was written. Python 3.11 was what Victor's machine had.

## Decision
Python 3.12+ for the repo as a whole (the engine alone also runs on 3.11). Dependencies kept to: `openpyxl` (read .xlsx), `pytest` (tests), `tzdata` (Windows Python ships no timezone database, so `America/New_York` fails without it). Listed in `engine/requirements.txt`. Standard library `csv`, `json`, `decimal`, `datetime`, `zoneinfo` for the rest. Config as YAML only when the rules engine needs it (phase 3), at which point `pyyaml` is added by its own decision.

Interface for the others: files in `out/`, plus the command `python -m engine run` (set in V1). Dani and Orlando do not import engine code; they read the files.

## Consequences
- Dani and Orlando can use any language, because the contract is files.
- Adding any other dependency needs a new decision record.
