# ─────────────────────────────────────────────
#  modules/report_generator.py  –  Phase 4: PDF Report
# ─────────────────────────────────────────────

import os
from datetime import datetime

import pandas as pd
from reportlab.lib          import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles   import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units    import mm
from reportlab.platypus     import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)


# ── Colour Palette ────────────────────────────────────────────────────────────
C_DARK   = colors.HexColor("#1a2940")   # Navy – headings
C_MID    = colors.HexColor("#2e5090")   # Blue – sub-headings / rule lines
C_LIGHT  = colors.HexColor("#e8edf5")   # Light blue-grey – table header bg
C_PASS   = colors.HexColor("#1a7a4a")   # Green – PASS
C_FAIL   = colors.HexColor("#c0392b")   # Red   – FAIL
C_WARN   = colors.HexColor("#d35400")   # Orange – anomaly
C_WHITE  = colors.white
C_ROW_A  = colors.HexColor("#f7f9fc")   # alternating row A
C_ROW_B  = colors.white                 # alternating row B
C_BORDER = colors.HexColor("#c5cfe0")


# ── Style Setup ───────────────────────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    custom = {
        "ReportTitle": ParagraphStyle(
            "ReportTitle", parent=base["Title"],
            fontSize=20, textColor=C_DARK, spaceAfter=4,
            fontName="Helvetica-Bold",
        ),
        "ReportSub": ParagraphStyle(
            "ReportSub", parent=base["Normal"],
            fontSize=10, textColor=C_MID, spaceAfter=12,
        ),
        "SectionHead": ParagraphStyle(
            "SectionHead", parent=base["Heading2"],
            fontSize=12, textColor=C_DARK, fontName="Helvetica-Bold",
            spaceBefore=14, spaceAfter=6,
        ),
        "BodyText": ParagraphStyle(
            "BodyText", parent=base["Normal"],
            fontSize=9, leading=14, textColor=colors.HexColor("#333333"),
        ),
        "SmallNote": ParagraphStyle(
            "SmallNote", parent=base["Normal"],
            fontSize=7.5, textColor=colors.grey, leading=10,
        ),
        "PassText": ParagraphStyle(
            "PassText", parent=base["Normal"],
            fontSize=11, textColor=C_PASS, fontName="Helvetica-Bold",
        ),
        "FailText": ParagraphStyle(
            "FailText", parent=base["Normal"],
            fontSize=11, textColor=C_FAIL, fontName="Helvetica-Bold",
        ),
        "WarnHead": ParagraphStyle(
            "WarnHead", parent=base["Normal"],
            fontSize=9, textColor=C_WARN, fontName="Helvetica-Bold",
        ),
    }
    return {**{k: base[k] for k in base.byName}, **custom}


# ── Table Helpers ─────────────────────────────────────────────────────────────
def _hdr_style(col_count: int, row_idx: int = 0) -> TableStyle:
    return TableStyle([
        ("BACKGROUND",  (0, row_idx), (-1, row_idx), C_LIGHT),
        ("TEXTCOLOR",   (0, row_idx), (-1, row_idx), C_DARK),
        ("FONTNAME",    (0, row_idx), (-1, row_idx), "Helvetica-Bold"),
        ("FONTSIZE",    (0, row_idx), (-1, row_idx), 8),
        ("BOTTOMPADDING", (0, row_idx), (-1, row_idx), 6),
        ("TOPPADDING",    (0, row_idx), (-1, row_idx), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_ROW_A, C_ROW_B]),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("TOPPADDING",  (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("GRID",        (0, 0), (-1, -1), 0.4, C_BORDER),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ])


def _money(val: float) -> str:
    if val == 0:
        return "-"
    return f"{val:,.2f}"


def _sgd(val: float) -> str:
    return f"SGD {val:,.2f}"


# ── Section Builders ──────────────────────────────────────────────────────────

def _section_cover(story, meta, styles):
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph("Bank Statement Analysis Report", styles["ReportTitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=C_MID, spaceAfter=8))

    info = [
        ["Account Holder",  meta.account_name or "—"],
        ["Bank",            meta.bank_name or "UOB"],
        ["Account Number",  meta.account_number or "—"],
        ["Statement Period", f"{meta.period_start}  to  {meta.period_end}"],
        ["Currency",        meta.currency],
        ["Report Generated", datetime.now().strftime("%d %B %Y, %H:%M")],
        ["Source File",     os.path.basename(meta.source_file)],
    ]

    tbl = Table(info, colWidths=[55*mm, 100*mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), C_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, C_BORDER),
    ]))
    story.append(tbl)
    story.append(PageBreak())


def _section_validation(story, validation, styles):
    story.append(Paragraph("Section 1 — Balance Verification", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))
    story.append(Paragraph(
        "Per SOP §1: Opening Balance + Total Deposits − Total Withdrawals = Closing Balance",
        styles["SmallNote"]
    ))
    story.append(Spacer(1, 4))

    rows = [
        ["Item", "Amount (SGD)"],
        ["Opening Balance",    _sgd(validation["opening_balance"])],
        ["(+) Total Deposits", _sgd(validation["total_deposits"])],
        ["(−) Total Withdrawals", _sgd(validation["total_withdrawals"])],
        ["Net Change",         _sgd(validation["net_change"])],
        ["Stated Closing Balance",   _sgd(validation["stated_closing"])],
        ["Computed Closing Balance", _sgd(validation["computed_closing"])],
    ]

    tbl = Table(rows, colWidths=[100*mm, 55*mm])
    style = _hdr_style(2)
    # Highlight last two rows
    style.add("FONTNAME", (0, 5), (-1, 6), "Helvetica-Bold")
    style.add("BACKGROUND", (0, 5), (-1, 6), colors.HexColor("#eef4ff"))
    tbl.setStyle(style)
    story.append(tbl)

    story.append(Spacer(1, 6))
    passed = validation["passed"]
    label  = "Validation Result: PASS — Balances reconcile correctly." if passed \
             else "Validation Result: FAIL — Balance discrepancy detected."
    story.append(Paragraph(label, styles["PassText"] if passed else styles["FailText"]))
    story.append(Spacer(1, 8))


def _section_summary(story, summary, styles):
    story.append(Paragraph("Section 2 — Financial Summary", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))

    rows = [
        ["Metric", "Value"],
        ["Total Credits (Income / Inflows)",  _sgd(summary["total_credits"])],
        ["Total Debits (Expenses / Outflows)", _sgd(summary["total_debits"])],
        ["Net Change",                         _sgd(summary["net_change"])],
        ["Total Transactions",                 str(summary["transaction_count"])],
        ["Average Debit per Transaction",      _sgd(summary["avg_debit"])],
        ["Average Credit per Transaction",     _sgd(summary["avg_credit"])],
        ["Largest Single Debit",               _sgd(summary["largest_debit"])],
        ["Largest Single Credit",              _sgd(summary["largest_credit"])],
    ]

    tbl = Table(rows, colWidths=[100*mm, 55*mm])
    tbl.setStyle(_hdr_style(2))
    story.append(tbl)
    story.append(Spacer(1, 8))


def _section_categories(story, cat_df, styles):
    story.append(Paragraph("Section 3 — Spending by Category", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))
    story.append(Paragraph(
        "Per SOP §3.2: Fixed, Discretionary, and Financial transaction categorisation.",
        styles["SmallNote"]
    ))
    story.append(Spacer(1, 4))

    rows = [["Category", "Transactions", "Total Debits (SGD)", "Total Credits (SGD)"]]
    for _, r in cat_df.iterrows():
        rows.append([
            r["category"],
            str(r["tx_count"]),
            _money(r["total_debit"]),
            _money(r["total_credit"]),
        ])

    tbl = Table(rows, colWidths=[65*mm, 30*mm, 45*mm, 45*mm])
    tbl.setStyle(_hdr_style(4))
    story.append(tbl)
    story.append(Spacer(1, 8))


def _section_ledger(story, df, styles):
    story.append(Paragraph("Section 4 — Full Transaction Ledger", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))
    story.append(Paragraph(
        "Normalised per SOP §2 schema. Clean merchant names extracted per §3.1.",
        styles["SmallNote"]
    ))
    story.append(Spacer(1, 4))

    headers = ["Date", "Merchant / Description", "Category", "Debit", "Credit", "Balance"]
    rows    = [headers]

    for _, r in df.iterrows():
        merchant = r["clean_merchant"] or r["description"]
        # Truncate long descriptions
        if len(merchant) > 35:
            merchant = merchant[:33] + "…"
        rows.append([
            r["transaction_date"],
            merchant,
            r["category"],
            _money(r["debit"]),
            _money(r["credit"]),
            _money(r["running_balance"]),
        ])

    col_w = [22*mm, 65*mm, 28*mm, 22*mm, 22*mm, 22*mm]
    # Split into chunks to avoid overflow
    chunk_size = 35
    for start in range(0, len(rows), chunk_size):
        chunk = rows[start:start + chunk_size]
        if start > 0:
            chunk = [headers] + chunk   # repeat header on continuation
        tbl = Table(chunk, colWidths=col_w, repeatRows=1)
        tbl.setStyle(_hdr_style(len(col_w)))
        story.append(KeepTogether([tbl]))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 8))


def _section_anomalies(story, anomalies_df, styles):
    story.append(Paragraph("Section 5 — Anomaly Flags", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))
    story.append(Paragraph(
        "Per SOP §3.3: Duplicate transactions, subscription spikes, large one-off debits (>20% avg monthly spend).",
        styles["SmallNote"]
    ))
    story.append(Spacer(1, 4))

    if anomalies_df.empty:
        story.append(Paragraph(
            "No anomalies detected. All transactions appear within normal parameters.",
            styles["PassText"]
        ))
    else:
        rows = [["Type", "Date", "Description", "Amount (SGD)", "Detail"]]
        for _, r in anomalies_df.iterrows():
            rows.append([
                r["anomaly_type"],
                r["date"],
                str(r["description"])[:30],
                _money(r["amount"]),
                str(r["detail"])[:40],
            ])

        col_w = [30*mm, 20*mm, 40*mm, 25*mm, 55*mm]
        tbl   = Table(rows, colWidths=col_w)
        style = _hdr_style(5)
        style.add("TEXTCOLOR", (0, 1), (0, -1), C_WARN)
        style.add("FONTNAME",  (0, 1), (0, -1), "Helvetica-Bold")
        tbl.setStyle(style)
        story.append(tbl)

    story.append(Spacer(1, 8))


def _section_quality_gate(story, qg, styles):
    story.append(Paragraph("Section 6 — Quality Gate", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))
    story.append(Paragraph(
        "SOP Final Gate: Total Credits − Total Debits must equal Net Change in account balance.",
        styles["SmallNote"]
    ))
    story.append(Spacer(1, 4))

    rows = [
        ["Check", "Value"],
        ["Computed Net Change (Credits − Debits)", _sgd(qg["computed_net_change"])],
        ["Stated Net Change (from statement)",      _sgd(qg["stated_net_change"])],
        ["Difference",                              _sgd(qg["difference"])],
        ["Status",                                  qg["status"]],
    ]

    tbl = Table(rows, colWidths=[100*mm, 55*mm])
    style = _hdr_style(2)
    passed = qg["passed"]
    style.add("TEXTCOLOR",  (1, 4), (1, 4), C_PASS if passed else C_FAIL)
    style.add("FONTNAME",   (1, 4), (1, 4), "Helvetica-Bold")
    tbl.setStyle(style)
    story.append(tbl)
    story.append(Spacer(1, 16))

    footer = Paragraph(
        "Report generated by Bank Statement Analyzer | Compliant with SOP: Comprehensive Bank Statement Analysis",
        styles["SmallNote"]
    )
    story.append(footer)


# ── Main Generator ────────────────────────────────────────────────────────────

def generate_report(
    output_path: str,
    meta,
    df: pd.DataFrame,
    validation: dict,
    analysis: dict,
) -> str:
    """
    Build and save the PDF report.
    Returns the output file path.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm,  bottomMargin=18*mm,
        title=f"Bank Statement Analysis – {meta.account_name}",
        author="Bank Statement Analyzer",
    )

    styles  = _styles()
    story   = []

    _section_cover(story, meta, styles)
    _section_validation(story, validation, styles)
    _section_summary(story, analysis["summary"], styles)
    _section_categories(story, analysis["category_breakdown"], styles)
    _section_ledger(story, df, styles)
    _section_anomalies(story, analysis["anomalies"], styles)
    _section_quality_gate(story, analysis["quality_gate"], styles)

    doc.build(story)
    return output_path
