"""The settled month through the close: one report missing, then every marketplace RECONCILED.

Synthetic (`data/generate.py`, `settled_month`): the same September cut to the activity whose payout reached
the bank by Sep 30, so nothing is in transit. Everything is written to a temporary folder.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from reports import bc_export as bc
from reports import reconcile

SAMPLE = reconcile.ROOT / "data" / "sample" / "settled_month"


class SettledMonthCloseTest(unittest.TestCase):
    def close(self, *inboxes):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Path(tmp) / "inbox"
            inbox.mkdir()
            for folder in inboxes:
                for f in folder.iterdir():
                    shutil.copy(f, inbox / f.name)
            mapping = bc.load_mapping()
            payload = reconcile.build(inbox, "2026-09", mapping, Path(tmp) / "engine")
            return {r["Source"]: r["Status"] for r in bc.build(payload, mapping)[2]}

    def test_without_the_late_report_only_shopgoodwill_is_incomplete(self):
        status = self.close(SAMPLE / "inbox", SAMPLE / "periodic")
        self.assertEqual(sorted(status.values()), ["INCOMPLETE", "RECONCILED", "RECONCILED"], status)

    def test_with_the_one_late_report_every_marketplace_is_reconciled(self):
        status = self.close(SAMPLE / "inbox", SAMPLE / "periodic", SAMPLE / "late")
        self.assertEqual(set(status.values()), {"RECONCILED"}, status)
