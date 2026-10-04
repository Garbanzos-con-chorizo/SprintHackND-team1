"""Decision 010: reports added from the portal are kept apart, checked, and handed to the same close."""
import json

import pytest

from reports import close_upload, hub, run_scheduled

MONTH = "2026-09"


def test_only_report_files_with_a_plain_name_are_kept(tmp_path):
    assert close_upload.save(MONTH, "amazon_daterange_2026-09-21_2026-09-22.csv", b"a,b\n1,2\n", tmp_path).exists()
    assert close_upload.save(MONTH, r"C:\Users\me\Downloads\paid_orders (4).xlsx", b"PK", tmp_path).name == "paid_orders (4).xlsx"
    assert close_upload.added(MONTH, tmp_path) == ["amazon_daterange_2026-09-21_2026-09-22.csv", "paid_orders (4).xlsx"]
    for name in ("run.exe", "notes.txt", ".hidden.csv", "~$lock.xlsx", "", "a;b.csv", "page.html"):
        with pytest.raises(close_upload.Rejected):
            close_upload.save(MONTH, name, b"x", tmp_path)
    assert close_upload.save(MONTH, "../../outside.csv", b"x", tmp_path).parent == tmp_path / MONTH   # the folder part is dropped
    assert not (tmp_path.parent / "outside.csv").exists()
    with pytest.raises(close_upload.Rejected):
        close_upload.save(MONTH, "empty.csv", b"", tmp_path)
    with pytest.raises(close_upload.Rejected):
        close_upload.save(MONTH, "big.csv", b"x" * (close_upload.MAX_BYTES + 1), tmp_path)
    for month in ("2026-13", "../2026-09", "202609", ""):
        with pytest.raises(close_upload.Rejected):
            close_upload.save(month, "a.csv", b"x", tmp_path)


def test_clear_takes_only_the_added_files_of_that_month(tmp_path):
    close_upload.save(MONTH, "a.csv", b"x", tmp_path)
    close_upload.save("2026-08", "b.csv", b"x", tmp_path)
    close_upload.clear(MONTH, tmp_path)
    assert close_upload.added(MONTH, tmp_path) == [] and close_upload.added("2026-08", tmp_path) == ["b.csv"]
    close_upload.clear(MONTH, tmp_path)   # nothing there: no error


def test_rerun_uses_the_last_run_s_inboxes_plus_the_added_files(tmp_path, monkeypatch):
    out, uploads, sample = tmp_path / "out", tmp_path / "out" / "uploads", tmp_path / "sample" / "inbox"
    sample.mkdir(parents=True)
    (out / "close" / MONTH).mkdir(parents=True)
    status = out / "close" / MONTH / f"close_status_{MONTH}.json"
    status.write_text(json.dumps({"inboxes": [str(sample), str(uploads / MONTH)]}), encoding="utf-8")
    calls = []
    monkeypatch.setattr(run_scheduled, "OUT", out)
    monkeypatch.setattr(run_scheduled, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(run_scheduled, "close_from", lambda month, inboxes: calls.append((month, list(inboxes))) or print("ran") or True)
    monkeypatch.setattr(hub, "build", lambda root: calls.append(("portal", root)))

    ok, log = close_upload.rerun(MONTH, uploads)          # nothing added: the upload folder is not an inbox
    assert ok and "ran" in log and calls[0] == (MONTH, [sample]) and calls[1][0] == "portal"

    close_upload.save(MONTH, "late.csv", b"x", uploads)
    close_upload.rerun(MONTH, uploads)                    # added: it is the last inbox, once
    assert calls[2] == (MONTH, [sample, (uploads / MONTH).resolve()])

    with pytest.raises(close_upload.Rejected, match="no close has run"):
        close_upload.rerun("2026-08", uploads)


def test_the_close_list_has_the_panel_and_names_the_missing_reports(tmp_path):
    month = tmp_path / "close" / MONTH
    month.mkdir(parents=True)
    (tmp_path / "close" / f"{MONTH}.html").write_text("<p>close</p>", encoding="utf-8")
    (month / f"exceptions_{MONTH}.csv").write_text(
        "Kind,Source,Detail\nmissing_report,Amazon,no Amazon report covers 2026-09-21\nin_transit,eBay,paid\n", encoding="utf-8")
    hub.close_index(tmp_path)
    html = (tmp_path / "close" / "index.html").read_text(encoding="utf-8")
    assert f'id="add" data-month="{MONTH}"' in html and 'type="file"' in html
    assert "<li><strong>Amazon:</strong> no Amazon report covers 2026-09-21</li>" in html and "<li><strong>eBay" not in html
    assert "Nothing is posted" in html and "synthetic samples" in html
