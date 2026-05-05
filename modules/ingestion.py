# ─────────────────────────────────────────────
#  modules/ingestion.py  –  Phase 1: Ingest & Verify (with OCR)
# ─────────────────────────────────────────────

import re
import os
import pdfplumber
import pandas as pd
from dataclasses import dataclass
from typing import Optional

try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

MONTH_ABBR = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
DATE_PAT   = re.compile(rf"^\s*(\d{{1,2}}\s+{MONTH_ABBR})\b", re.IGNORECASE)
MONEY_PAT  = re.compile(r"([\d,]+\.\d{{2}}(?:OD)?)")
MONEY_PAT  = re.compile(r"([\d,]+\.\d{2}(?:OD)?)")


@dataclass
class StatementMeta:
    account_name:    str   = ""
    account_number:  str   = ""
    bank_name:       str   = "United Overseas Bank (UOB)"
    period_start:    str   = ""
    period_end:      str   = ""
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    currency:        str   = "SGD"
    source_file:     str   = ""
    is_scanned:      bool  = False


def _parse_float(text: str) -> float:
    if not text:
        return 0.0
    clean = re.sub(r"[,\s$]", "", str(text))
    negative = clean.upper().endswith("OD")
    if negative:
        clean = clean[:-2]
    try:
        val = float(clean)
        return -val if negative else val
    except ValueError:
        return 0.0


def _is_scanned(pdf_path: str) -> bool:
    if FITZ_AVAILABLE:
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                if page.get_text().strip():
                    return False
            return True
        except Exception:
            pass
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t and t.strip():
                    return False
        return True
    except Exception:
        return True


def _extract_all_text_ocr(pdf_path: str, dpi: int = 250) -> list:
    pages_img = convert_from_path(pdf_path, dpi=dpi)
    return [pytesseract.image_to_string(img, config="--psm 6") for img in pages_img]


def _extract_all_text_native(pdf_path: str) -> list:
    with pdfplumber.open(pdf_path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def _extract_meta(all_texts: list, pdf_path: str) -> StatementMeta:
    meta = StatementMeta(source_file=pdf_path)
    full = "\n".join(all_texts)

    # Account name
    for pat in [
        r"([A-Z0-9 &.\-]{3,50}(?:PTE\.?\s*LTD\.?|LLC|SDN\s+BHD|HOLDINGS))",
        r"([A-Z][A-Z0-9 &.\-]{2,40}(?:ACCOUNT|OFFICE ACCOUNT))",
    ]:
        m = re.search(pat, full[:2000], re.IGNORECASE)
        if m:
            meta.account_name = m.group(1).strip().title()
            break

    # Account number
    acc = re.search(r"\b(\d{3}-\d{3}-\d{3,}-\d)\b", full)
    if acc:
        meta.account_number = acc.group(1)

    # Period
    period = re.search(
        rf"Period[:\s]+(\d{{1,2}}\s+{MONTH_ABBR}\s+\d{{4}})\s+to\s+(\d{{1,2}}\s+\w+\s+\d{{4}})",
        full, re.IGNORECASE
    )
    if period:
        meta.period_start = period.group(1)
        meta.period_end   = period.group(2)

    # Closing balance
    bal = re.findall(r"(?:Grand Total.*?|Deposits\s+)([\d,]+\.\d{2})", full[:3000])
    if bal:
        meta.closing_balance = _parse_float(bal[-1])

    return meta


SKIP_TOKENS = {
    "date", "description", "withdrawals", "deposits", "balance",
    "sgd", "end of transaction", "end of summary", "total",
    "please note", "united overseas", "page ", "balance b/f",
    "interest earned", "grand total", "account overview",
    "account transaction", "foreign exchange", "important",
    "deposit insurance", "uob's fair", "general information",
    "highlights", "useful links", "overseas card",
    "closure of", "cessation", "rates against", "code", "fx, gold",
    "©", "p0", "br-3", "br-360",
}


def _should_skip(line: str) -> bool:
    ll = line.lower().strip()
    if not ll or len(ll) < 3:
        return True
    for s in SKIP_TOKENS:
        if ll.startswith(s):
            return True
    if re.match(r"^[\d\s,.%\-*]+$", ll):
        return True
    return False


def _assign_amounts(moneys: list) -> tuple:
    vals = [_parse_float(m) for m in moneys]
    if len(vals) >= 3:
        return vals[0], vals[1], vals[2]
    elif len(vals) == 2:
        return vals[0], 0.0, vals[1]
    elif len(vals) == 1:
        return 0.0, 0.0, vals[0]
    return 0.0, 0.0, 0.0


def _parse_transactions(page_texts: list) -> pd.DataFrame:
    rows = []
    current = None

    for page_text in page_texts:
        for line in page_text.splitlines():
            line = line.strip()
            if _should_skip(line):
                continue

            dm = DATE_PAT.match(line)
            if dm:
                if current:
                    rows.append(current)

                date_str = dm.group(1).strip()
                rest     = line[dm.end():].strip()
                moneys   = MONEY_PAT.findall(rest)
                desc     = MONEY_PAT.sub("", rest)
                desc     = re.sub(r"\s{2,}", " ", desc).strip()
                w, d, b  = _assign_amounts(moneys)

                current = {
                    "raw_date": date_str,
                    "description": desc,
                    "withdrawals": w,
                    "deposits": d,
                    "balance": b,
                }
            elif current is not None:
                moneys_here = MONEY_PAT.findall(line)
                line_clean  = MONEY_PAT.sub("", line).strip()

                if moneys_here and not line_clean:
                    if current["withdrawals"] == 0 and current["deposits"] == 0 and current["balance"] == 0:
                        w, d, b = _assign_amounts(moneys_here)
                        current["withdrawals"] = w
                        current["deposits"]    = d
                        current["balance"]     = b
                elif line_clean and len(line_clean) > 2:
                    # Skip pure reference codes
                    if not re.match(r"^[A-Z0-9]{12,}$", line_clean):
                        current["description"] += " " + line_clean

    if current:
        rows.append(current)

    if not rows:
        return pd.DataFrame(columns=["raw_date", "description", "withdrawals", "deposits", "balance"])

    df = pd.DataFrame(rows)
    for col in ["withdrawals", "deposits", "balance"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def _validate(df: pd.DataFrame, meta: StatementMeta) -> dict:
    opening = meta.opening_balance
    if opening == 0 and not df.empty:
        first   = df.iloc[0]
        opening = first["balance"] - first["deposits"] + first["withdrawals"]
        if opening < 0:
            opening = 0.0
        meta.opening_balance = round(opening, 2)

    total_dep = df["deposits"].sum()
    total_wd  = df["withdrawals"].sum()
    net       = total_dep - total_wd
    computed  = opening + net
    stated    = meta.closing_balance

    if stated == 0 and not df.empty:
        stated = df.iloc[-1]["balance"]
        meta.closing_balance = round(stated, 2)

    passed = abs(computed - stated) <= 2.0

    return {
        "opening_balance":   round(opening, 2),
        "total_deposits":    round(total_dep, 2),
        "total_withdrawals": round(total_wd, 2),
        "net_change":        round(net, 2),
        "stated_closing":    round(stated, 2),
        "computed_closing":  round(computed, 2),
        "passed":            passed,
    }


def ingest(pdf_path: str) -> tuple:
    scanned = _is_scanned(pdf_path)

    if scanned:
        if not OCR_AVAILABLE:
            raise RuntimeError("Scanned PDF – install: pip install pdf2image pytesseract")
        print("  [OCR] Scanned PDF – running Tesseract OCR (this may take 30-60s)...")
        all_texts = _extract_all_text_ocr(pdf_path, dpi=250)
    else:
        print("  [Native] Digital PDF – extracting text natively...")
        all_texts = _extract_all_text_native(pdf_path)

    meta            = _extract_meta(all_texts, pdf_path)
    meta.is_scanned = scanned
    raw_df          = _parse_transactions(all_texts)
    validation      = _validate(raw_df, meta)

    return meta, raw_df, validation
