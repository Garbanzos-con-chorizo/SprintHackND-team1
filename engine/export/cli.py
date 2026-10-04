"""python -m engine.export kpi-csv | pdf  (--kpi-file F | --period day|week|month) [--dest DIR]
   python -m engine.export bc-api --month YYYY-MM [--close-dir out/close] [--send [--reviewed] [--allow-sample]]"""
import argparse
import sys
from pathlib import Path

from . import bc_api
from .kpi_csv import write_kpi_csv
from .pdf import PdfError, scorecard_page, write_pdf

KPI_DIR = Path("out") / "kpi"
DEST = Path("reports") / "scorecard"  # next to the scorecard page of the same name, for its download links


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine.export")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, text in (("kpi-csv", "the KPI file as one long CSV for Excel and Power BI"),
                       ("pdf", "the scorecard page printed to a one-page PDF (headless Edge or Chrome)")):
        p = sub.add_parser(name, help=text)
        src = p.add_mutually_exclusive_group(required=True)
        src.add_argument("--kpi-file", type=Path, help="a KPI file from python -m recon.kpi")
        src.add_argument("--period", choices=["day", "week", "month"], help="use out/kpi/latest-<period>.json")
        p.add_argument("--dest", type=Path, default=DEST, help=f"output folder (default: {DEST.as_posix()})")
    bc = sub.add_parser("bc-api", help="the month-end close as Business Central API requests: a dry run unless --send")
    bc.add_argument("--month", required=True, help="the month closed, YYYY-MM")
    bc.add_argument("--close-dir", type=Path, default=Path("out") / "close", help="the close's --out folder (default: out/close)")
    bc.add_argument("--send", action="store_true", help="send the drafts to the Business Central named by the BC_* environment variables")
    bc.add_argument("--reviewed", action="store_true", help="with --send: someone has reviewed a close that reads 'needs review'")
    bc.add_argument("--allow-sample", action="store_true", help="with --send: allow a close built from the synthetic samples (a sandbox only)")
    args = parser.parse_args(argv)
    if args.command == "bc-api":
        return bc_api_command(args)

    kpi_path = args.kpi_file or KPI_DIR / f"latest-{args.period}.json"
    if not kpi_path.exists():
        print(f"export: no KPI file at {kpi_path}; run `python -m recon.kpi` first", file=sys.stderr)
        return 1
    try:
        if args.command == "kpi-csv":
            print(f"export: wrote {write_kpi_csv(kpi_path, args.dest)}")
        else:
            pdf, pages = write_pdf(kpi_path, args.dest)
            print(f"export: wrote {pdf} ({pages} page{'s' if pages != 1 else ''})")
        scorecard_page(kpi_path, args.dest)  # draw the page again so it links the file just written (and the portal card)
    except (ValueError, KeyError) as e:
        print(f"export: {kpi_path} does not follow docs/contracts/kpi.md ({e})", file=sys.stderr)
        return 1
    except PdfError as e:
        print(f"export: PDF not written: {e}", file=sys.stderr)
        return 1
    return 0


def bc_api_command(args, env: dict | None = None) -> int:
    """Dry run: write the requests and send nothing. --send: load them as drafts; nothing is ever posted."""
    if env is None:
        from ..scrapers.env import load_env
        env = load_env()  # the environment, with .env filling in what is not set
    try:
        journal, invoices, status = bc_api.load_close(args.close_dir, args.month)
        dimension = env.get("BC_DEPARTMENT_DIMENSION") or bc_api.DEPARTMENT_DIMENSION
        requests = bc_api.build_requests(journal, invoices, args.month, dimension=dimension)
        s = bc_api.summary(requests)
        shape = (f"{s['journal_lines']} journal lines in {s['journal_batches']} batch, {s['sales_invoices']} sales invoice(s) "
                 f"with {s['sales_invoice_lines']} lines, {s['department_dimensions']} department dimensions")
        if not args.send:
            path = bc_api.write_dry_run(args.close_dir, args.month, requests, status)
            print(f"export: {s['requests']} Business Central API requests for {args.month}: {shape}")
            print(f"export: wrote {path}")
            print("export: NOT SENT (dry run: no Business Central connection). Drafts only: nothing here posts.")
            return 0
        bc_api.check_sendable(status, reviewed=args.reviewed, allow_sample=args.allow_sample)
        result = bc_api.BcClient(env).send(requests)
    except bc_api.Refused as e:
        print(f"export: REFUSED, nothing sent: {e}", file=sys.stderr)
        return 1
    except bc_api.NotConfigured as e:
        print(f"export: not configured, nothing sent: {e}", file=sys.stderr)
        return 1
    except bc_api.HttpError as e:
        print(f"export: sign-in failed, nothing sent: {e}", file=sys.stderr)
        return 1
    if result["failed_step"]:
        print(f"export: STOPPED at request {result['failed_step']} of {result['of']} ({result['what']}): {result['error']}. "
              f"{result['sent']} request(s) went through: delete the journal batch and any draft invoice in Business "
              f"Central before sending again.", file=sys.stderr)
        return 1
    print(f"export: sent {result['sent']} requests as DRAFTS: {shape}. Nothing is posted: review and post in Business Central.")
    return 0
