# 002 — Engine in Python

- **Date / author:** 2026-10-03, Victor
- **Status:** proposed (Dani and Orlando to accept or object in the PR)

## Context
`engine/` parses messy CSV/XLSX exports, cleans them and writes the files in `docs/contracts/transaction.md`. The stack in `CLAUDE.md` is still TBD. Python 3.11 is installed on Victor's machine.

## Decision
Python 3.11+. Dependencies kept to: `openpyxl` (read .xlsx), `pytest` (tests). Standard library `csv`, `json`, `decimal`, `datetime`, `zoneinfo` for the rest. Config as YAML only when the rules engine needs it (phase 3), at which point `pyyaml` is added by its own decision.

Interface for the others: files in `out/`, plus the command `python -m engine run` (set in V1). Dani and Orlando do not import engine code; they read the files.

## Consequences
- Dani and Orlando can use any language, because the contract is files.
- Adding any other dependency needs a new decision record.
