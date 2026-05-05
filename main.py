
# ─────────────────────────────────────────────
#  main.py  –  Bank Statement Analyzer Entry Point
#  Usage: python main.py <path_to_statement.pdf>
# ─────────────────────────────────────────────

import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.dirname(__file__))

from modules.ingestion        import ingest
from modules.normalizer       import normalize
from modules.analyzer         import analyse
from modules.report_generator import generate_report


def run(pdf_path: str) -> str:
    """
    Full pipeline: Ingest → Normalize → Analyse → Report
    Returns path to generated PDF report.
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"\n{'='*60}")
    print(f"  Bank Statement Analyzer")
    print(f"{'='*60}")
    print(f"  Input : {os.path.basename(pdf_path)}")

    # ── Phase 1: Ingest & Verify ──────────────────────────────────────────────
    print("\n[Phase 1] Ingesting and verifying document...")
    meta, raw_df, validation = ingest(pdf_path)

    print(f"  Account   : {meta.account_name}")
    print(f"  Period    : {meta.period_start} → {meta.period_end}")
    print(f"  Account # : {meta.account_number}")
    print(f"  Rows read : {len(raw_df)}")
    bal_status = "PASS ✓" if validation["passed"] else "FAIL ✗"
    print(f"  Balance check : {bal_status}")

    # ── Phase 2: Normalize ────────────────────────────────────────────────────
    print("\n[Phase 2] Normalizing and structuring data...")
    clean_df = normalize(raw_df, meta.period_end)
    print(f"  Clean transactions : {len(clean_df)}")

    # ── Phase 3: Analyse ──────────────────────────────────────────────────────
    print("\n[Phase 3] Analysing transactions and detecting anomalies...")
    analysis = analyse(clean_df, validation)
    s = analysis["summary"]
    print(f"  Total Credits  : SGD {s['total_credits']:,.2f}")
    print(f"  Total Debits   : SGD {s['total_debits']:,.2f}")
    print(f"  Net Change     : SGD {s['net_change']:,.2f}")
    print(f"  Anomalies found: {len(analysis['anomalies'])}")
    print(f"  Quality Gate   : {analysis['quality_gate']['status']}")

    # ── Phase 4: Report ───────────────────────────────────────────────────────
    print("\n[Phase 4] Generating PDF report...")
    os.makedirs("output", exist_ok=True)

    # Build output filename from account name + period
    safe_name   = (meta.account_name or "statement").replace(" ", "_").replace(".", "")
    period_tag  = meta.period_end.replace(" ", "_") if meta.period_end else "report"
    output_path = os.path.join("output", f"{safe_name}_{period_tag}.pdf")

    report_path = generate_report(
        output_path = output_path,
        meta        = meta,
        df          = clean_df,
        validation  = validation,
        analysis    = analysis,
    )

    print(f"\n{'='*60}")
    print(f"  Report saved : {report_path}")
    print(f"{'='*60}\n")
    return report_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_bank_statement.pdf>")
        print("Example: python main.py statements/uob_feb2025.pdf")
        sys.exit(1)

    pdf_input = sys.argv[1]
    try:
        out = run(pdf_input)
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
