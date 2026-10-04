"""The one-command close (`reports.close`): the six steps, the files, the status, the archive and the refusals.

Everything is written under a temporary folder (`--out`, `--archive`, `--dest`), never the real `out/` or
`reports/`. Counts of exceptions and the statuses of Amazon and ShopGoodwill are not pinned here: they
belong to the rules (`test_reconcile.py`); this file checks that the command reports what the files say.
"""
import contextlib
import copy
import csv
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reports import bc_export as bc
from reports import close, reconcile

INBOX = close.ROOT / "data" / "sample" / "messy_month" / "inbox"
MONTH = "2026-09"
CSVS = ("general_journal", "ar_invoice", "control_totals", "exceptions")
LAST_LINE = "posting: NOT POSTED (import files ready)"


def run_close(base, *inboxes, run_id, month=MONTH):
    """`python -m reports.close` with every folder under `base`. Returns (exit code, stdout lines, stderr)."""
    args = [a for i in inboxes for a in ("--inbox", str(i))]
    args += ["--month", month, "--out", str(base / "close"), "--archive", str(base / "archive"),
             "--dest", str(base / "pages"), "--run-id", run_id]
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = close.main(args)
    return code, out.getvalue().splitlines(), err.getvalue()


def archived(base, run_id):
    return close.fs(close.run_folder(base / "archive", MONTH, run_id))


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def cents(text):
    return round(float(text) * 100)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CloseCommandTest(unittest.TestCase):
    """Two real runs of the messy month into the same folders: `run-1` from the sample inbox, `run-2` from
    the same 38 files split across two inboxes."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        cls.names = sorted(p.name for p in INBOX.iterdir())
        cls.first = run_close(cls.base, INBOX, run_id="run-1")
        cls.halves = [cls.base / "inbox_a", cls.base / "inbox_b"]
        for i, name in enumerate(cls.names):
            cls.halves[i % 2].mkdir(exist_ok=True)
            shutil.copyfile(INBOX / name, cls.halves[i % 2] / name)
        cls.second = run_close(cls.base, *cls.halves, run_id="run-2")
        cls.out = cls.base / "close" / MONTH
        cls.status = json.loads((cls.out / f"close_status_{MONTH}.json").read_text(encoding="utf-8"))
        cls.payload = json.loads((cls.out / f"close_payload_{MONTH}.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def fake_build(self, inbox, month, mapping, engine_out):
        """`reconcile.build` without a second engine run: the engine folder and the payload of this class's runs."""
        shutil.copytree(self.out / "engine", engine_out)
        return copy.deepcopy(self.payload)

    def test_exits_0_and_prints_one_line_per_step_ending_with_not_posted(self):
        for code, lines, _ in (self.first, self.second):
            self.assertEqual(code, 0)
            steps = [line for line in lines if line[:2].isdigit()]
            self.assertEqual([line[3:20].strip() for line in steps], close.STEPS)
            self.assertEqual([line[:2] for line in steps], ["01", "02", "03", "04", "05", "06"])
            self.assertEqual(lines[-1], LAST_LINE)
        self.assertIn("38 files from 1 inbox,", self.first[1][0])
        self.assertIn("38 files from 2 inboxes,", self.second[1][0])

    def test_writes_the_four_csvs_the_payload_the_status_file_and_the_page(self):
        for name in [f"{k}_{MONTH}.csv" for k in CSVS] + [f"close_payload_{MONTH}.json", f"close_status_{MONTH}.json",
                                                         "runs.csv"]:
            self.assertTrue((self.out / name).is_file(), name)
        self.assertEqual(sorted(p.name for p in (self.out / "inbox").iterdir()), self.names)
        page = self.base / "pages" / f"{MONTH}.html"
        self.assertIn("Month-end close", page.read_text(encoding="utf-8"))
        self.assertEqual(sorted(p.name for p in (self.base / "pages" / MONTH).iterdir()),
                         sorted(f"{k}_{MONTH}.csv" for k in CSVS))

    def test_status_file_says_not_posted_and_agrees_with_the_files(self):
        s = self.status
        self.assertEqual((s["month"], s["run_id"]), (MONTH, "run-2"))
        self.assertEqual(s["posting"]["status"], "not_posted")
        self.assertEqual(s["posting"]["problems"], [])
        self.assertEqual(len(s["posting"]["checks"]), 2)
        self.assertEqual(s["origin"], self.payload.get("origin") or self.payload.get("mock"))

        journal = read_csv(self.out / f"general_journal_{MONTH}.csv")
        problems, n_lines, n_docs = bc.verify_files({k: self.out / f"{k}_{MONTH}.csv" for k in CSVS})
        self.assertEqual(problems, [])
        self.assertEqual(s["journal"], {"lines": len(journal), "documents": n_docs, "balanced": True})
        self.assertEqual(n_lines, len(journal))
        invoice = read_csv(self.out / f"ar_invoice_{MONTH}.csv")
        self.assertEqual(s["invoices"], {"documents": len({r["Document No."] for r in invoice}), "lines": len(invoice)})

        # Every source's status and amounts are those of the control totals file.
        key = {m["Label"]: src for src, m in bc.load_mapping().items()}
        control = read_csv(self.out / f"control_totals_{MONTH}.csv")
        self.assertEqual(s["sources"], {key[r["Source"]]: {"status": r["Status"], "open_cents": cents(r["Open Balance"]),
                                                          "unexplained_cents": cents(r["Unexplained"])} for r in control})
        self.assertEqual(s["sources"]["ebay"]["status"], "OPEN")

        exceptions = read_csv(self.out / f"exceptions_{MONTH}.csv")
        self.assertEqual(s["exceptions"]["total"], len(exceptions))
        self.assertEqual(s["exceptions"]["by_kind"],
                         {k: sum(e["Kind"] == k for e in exceptions) for k in sorted({e["Kind"] for e in exceptions})})
        expected_review = (any(r["Status"] not in ("OPEN", "RECONCILED") for r in control)
                           or any(e["Effect"] == "not_posted" for e in exceptions))
        self.assertEqual(s["needs_review"], expected_review)
        self.assertTrue(s["needs_review"])  # the $412.37 deposit nobody can place is held out of the journal

    def test_archive_holds_every_inbox_file_the_outputs_and_a_manifest_with_their_hashes(self):
        for run_id, inboxes in (("run-1", 1), ("run-2", 2)):
            folder = archived(self.base, run_id)
            self.assertEqual(sorted(p.name for p in (folder / "inputs").iterdir()), self.names)
            outputs = sorted([f"{k}_{MONTH}.csv" for k in CSVS] + [f"close_payload_{MONTH}.json", f"close_status_{MONTH}.json"])
            self.assertEqual(sorted(p.name for p in folder.iterdir()), sorted(outputs + ["inputs", "manifest.json"]))
            manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual((manifest["month"], manifest["run_id"]), (MONTH, run_id))
            self.assertEqual(sorted(e["name"] for e in manifest["inputs"]), self.names)
            self.assertEqual(sorted(e["name"] for e in manifest["outputs"]), outputs)
            self.assertEqual(len({e["inbox"] for e in manifest["inputs"]}), inboxes)
            for e in manifest["inputs"]:
                copy_ = folder / "inputs" / e["name"]
                self.assertEqual((e["bytes"], e["sha256"]), (copy_.stat().st_size, digest(copy_)), e["name"])
                self.assertEqual(e["sha256"], digest(INBOX / e["name"]), e["name"])  # the archive is the inbox, byte for byte
            for e in manifest["outputs"]:
                self.assertEqual((e["bytes"], e["sha256"]), ((folder / e["name"]).stat().st_size, digest(folder / e["name"])),
                                 e["name"])
        # The outputs in the month folder are the last run's.
        self.assertEqual(digest(self.out / f"close_status_{MONTH}.json"), digest(folder / f"close_status_{MONTH}.json"))

    def test_manifest_counts_rows_read_and_rejected_from_the_engines_own_files(self):
        manifest = json.loads((archived(self.base, "run-2") / "manifest.json").read_text(encoding="utf-8"))
        by_name = {e["name"]: e for e in manifest["inputs"]}
        engine = self.out / "engine"
        tables = [read_csv(p) for p in sorted(engine.glob("*.csv"))]
        self.assertEqual(sum(e["rows_read"] for e in manifest["inputs"]),
                         sum(len(t) for t in tables if t and "source_file" in t[0]))
        warnings = json.loads((engine / "warnings.json").read_text(encoding="utf-8"))
        self.assertEqual(sum(e["rows_rejected"] for e in manifest["inputs"]), sum(bool(w["source_row"]) for w in warnings))
        # The sample plants one unreadable amount and one impossible date in this eBay file.
        broken = by_name["ebay_transactions_2026-09-15_2026-09-21.csv"]
        self.assertEqual((broken["rejected_by_kind"]["bad_amount"], broken["rejected_by_kind"]["bad_date"]), (1, 1))
        self.assertEqual(broken["rows_rejected"], sum(broken["rejected_by_kind"].values()))
        self.assertGreater(by_name["amazon_daterange_2026-09-01_2026-09-20.csv"]["rows_read"], 0)

    def test_second_run_adds_a_line_to_runs_csv_and_a_second_archive_folder(self):
        runs = read_csv(self.out / "runs.csv")
        self.assertEqual([r["run_id"] for r in runs], ["run-1", "run-2"])
        self.assertEqual(list(runs[0]), close.RUNS_COLUMNS)
        for r, n_inboxes in zip(runs, (1, 2)):
            self.assertEqual(len(r["inboxes"].split("; ")), n_inboxes)
            self.assertEqual((r["journal_lines"], r["journal_documents"]),
                             (str(self.status["journal"]["lines"]), str(self.status["journal"]["documents"])))
            self.assertEqual((r["needs_review"], r["exit_code"]), ("true", "0"))
            self.assertIn("ebay=OPEN", r["statuses"])
            self.assertTrue(r["archive"].endswith(f"E-Commerce JEs/{r['run_id']}"))
        self.assertEqual(sorted(p.name for p in archived(self.base, "run-1").parent.iterdir()), ["run-1", "run-2"])
        self.assertIn("(2 runs)", self.second[1][-2])

    def test_two_inboxes_give_the_same_files_as_one(self):
        self.assertEqual(len(self.status["inboxes"]), 2)
        one, two = archived(self.base, "run-1"), archived(self.base, "run-2")
        for k in CSVS:
            self.assertEqual((one / f"{k}_{MONTH}.csv").read_bytes(), (two / f"{k}_{MONTH}.csv").read_bytes(), k)
        first = json.loads((one / f"close_status_{MONTH}.json").read_text(encoding="utf-8"))
        for field in ("sources", "journal", "invoices", "exceptions", "needs_review"):
            self.assertEqual(first[field], self.status[field], field)

    def test_same_file_name_in_two_inboxes_is_refused_and_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for folder, name in (("a", "bank_activity_2026-09.csv"), ("b", "Bank_Activity_2026-09.CSV")):
                (base / folder).mkdir()
                shutil.copyfile(INBOX / "bank_activity_2026-09.csv", base / folder / name)
            shutil.copyfile(INBOX / self.names[0], base / "a" / self.names[0])
            code, lines, err = run_close(base, base / "a", base / "b", run_id="run-1")
            self.assertEqual(code, 1)
            self.assertIn("Bank_Activity_2026-09.CSV", err)
            self.assertIn("same name", err)
            self.assertEqual(lines, ["posting: NOT POSTED (refused: nothing written)"])
            self.assertEqual(sorted(p.name for p in base.iterdir()), ["a", "b"])

    def test_a_run_that_cannot_start_is_refused_before_anything_changes(self):
        before = digest(self.out / "runs.csv")
        attempts = [((INBOX,), {"run_id": "run-1"}),                       # an archived run is never overwritten
                    ((INBOX,), {"run_id": "run-3", "month": "2026-13"}),
                    ((INBOX,), {"run_id": "../run-3"}),
                    ((self.base / "no_such_inbox",), {"run_id": "run-3"}),
                    ((INBOX, INBOX), {"run_id": "run-3"}),
                    ((self.out / "inbox",), {"run_id": "run-3"})]              # the folder the close empties
        for inboxes, kwargs in attempts:
            code, lines, err = run_close(self.base, *inboxes, **kwargs)
            self.assertEqual((code, lines[-1]), (1, "posting: NOT POSTED (refused: nothing written)"), kwargs)
            self.assertIn("REFUSED", err)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(close.main(["--month", MONTH]), 1)  # no --inbox: a bad command line is 1, never 2
        self.assertEqual(digest(self.out / "runs.csv"), before)
        self.assertEqual(sorted(p.name for p in (self.out / "inbox").iterdir()), self.names)
        self.assertEqual(sorted(p.name for p in archived(self.base, "run-1").parent.iterdir()), ["run-1", "run-2"])

    def test_hidden_files_and_sub_folders_are_not_inputs_and_an_unread_file_is_listed_with_a_note(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(reconcile, "build", self.fake_build):
            base = Path(tmp)
            shutil.copytree(INBOX, base / "inbox")
            for name in (".gitignore", "~$paid_orders.xlsx", "cover_letter.pdf"):
                (base / "inbox" / name).write_text("x", encoding="utf-8")
            (base / "inbox" / "periodic").mkdir()
            (base / "inbox" / "periodic" / "report.csv").write_text("x", encoding="utf-8")
            code, lines, _ = run_close(base, base / "inbox", run_id="run-1")
            self.assertEqual(code, 0)
            self.assertIn("39 files from 1 inbox,", lines[0])
            self.assertIn("1 sub-folder(s) not read", lines[0])
            folder = archived(base, "run-1")
            self.assertEqual(sorted(p.name for p in (folder / "inputs").iterdir()), sorted(self.names + ["cover_letter.pdf"]))
            manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            noted = {e["name"]: e["note"] for e in manifest["inputs"] if "note" in e}
            self.assertEqual(list(noted), ["cover_letter.pdf"])
            self.assertIn("no row and no warning", noted["cover_letter.pdf"])

    def test_unbalanced_journal_is_refused_and_no_csv_page_or_status_file_is_written(self):
        journal, invoice, control, exceptions = bc.build(self.payload, bc.load_mapping())
        journal[1]["Amount"] += 1  # one cent off
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(reconcile, "build", self.fake_build), \
                mock.patch.object(bc, "build", return_value=(journal, invoice, control, exceptions)):
            base = Path(tmp)
            code, lines, err = run_close(base, INBOX, run_id="run-1")
            self.assertEqual(code, 1)
            self.assertIn(f"REFUSED: document {journal[1]['Document No.']} does not balance (off by 0.01)", err)
            self.assertIn("REFUSED", lines[-2])
            self.assertEqual(lines[-1], "posting: NOT POSTED (refused: no import files written)")
            month = base / "close" / MONTH
            self.assertEqual(list(month.glob("*.csv")), [])  # neither the four files nor a runs.csv line
            self.assertFalse((month / f"close_status_{MONTH}.json").exists())
            self.assertFalse((base / "pages").exists())
            # What the refused run was given is kept; a run folder without a manifest is a run that did not finish.
            self.assertEqual([p.name for p in archived(base, "run-1").iterdir()], ["inputs"])

    def test_files_that_fail_the_read_back_check_exit_2_and_the_status_says_so(self):
        problem = "journal document ECOM-2609-EBAY sums to 0.01"
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(reconcile, "build", self.fake_build), \
                mock.patch.object(bc, "verify_files", return_value=([problem], 56, 25)):
            base = Path(tmp)
            code, lines, err = run_close(base, INBOX, run_id="run-1")
            self.assertEqual(code, 2)
            self.assertIn(problem, err)
            self.assertEqual(lines[-1], "posting: NOT POSTED (the written files failed the read-back check: do not import them)")
            status = json.loads((base / "close" / MONTH / f"close_status_{MONTH}.json").read_text(encoding="utf-8"))
            self.assertEqual((status["posting"]["status"], status["posting"]["problems"]), ("not_posted", [problem]))
            self.assertEqual((status["journal"]["balanced"], status["needs_review"]), (False, True))
            self.assertEqual([r["exit_code"] for r in read_csv(base / "close" / MONTH / "runs.csv")], ["2"])
            self.assertTrue((archived(base, "run-1") / "manifest.json").is_file())
            self.assertFalse((base / "pages").exists())  # no page for files that must not be imported


if __name__ == "__main__":
    unittest.main()
