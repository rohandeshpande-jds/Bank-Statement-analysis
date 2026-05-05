# ─────────────────────────────────────────────
#  modules/normalizer.py  –  Phase 2: Normalize & Structure
# ─────────────────────────────────────────────

import re
import pandas as pd
from config import NOISE_PATTERNS, CATEGORY_RULES

MONTH_MAP = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}


def _parse_date(raw_date: str, year: str) -> str:
    parts = raw_date.strip().split()
    if len(parts) != 2:
        return raw_date
    day   = parts[0].zfill(2)
    month = MONTH_MAP.get(parts[1], "00")
    return f"{year}-{month}-{day}"


def _extract_year(period_end: str) -> str:
    m = re.search(r"\b(20\d{2})\b", period_end or "")
    return m.group(1) if m else "2024"


def _clean_merchant(description: str) -> str:
    text = description or ""
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    prefixes = [
        r"^Inward CR\s*-\s*GIRO\s*",
        r"^Inward CR\s*",
        r"^Inward Credit-FAST\s*",
        r"^Inward DR\s*-\s*GIRO Cor\s*",
        r"^Inward DR\s*-\s*GIRO\s*",
        r"^Funds Trf\s*-\s*FAST\s*",
        r"^Funds Transfer-IB\s*",
        r"^Funds Transfer\s*",
        r"^PAYNOW-FAST\s*",
        r"^PAYNOW OTHR\s*",
        r"^PAYNOW\s*",
        r"^Cash Deposit-CDM\s*",
        r"^Cash Withdrawal-SATM\s*",
        r"^Cheque Deposit\s*",
        r"^Misc CR-Debit Card\s*",
        r"^Misc DR-Debit Card\s*",
        r"^Misc Credit\s*",
        r"^Misc Debit\s*",
        r"^SVC Chg\s*",
        r"^Service Charge\s*",
        r"^Payment to IRAS\s*",
        r"^IVPT Invoice Payment\s*",
        r"^SUPP SupplierPymt\s*",
        r"^Inward Credit-FAST\s*",
        r"^BEXP BizExpenses\s*",
    ]
    for p in prefixes:
        text = re.sub(p, "", text, flags=re.IGNORECASE)

    # Strip long reference codes
    text = re.sub(r"\b[A-Z0-9]{10,}\b", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip()

    if text and text == text.upper():
        text = text.title()

    return text if text else (description.split()[0].title() if description else "Unknown")


def _categorise(description: str) -> str:
    haystack = description.lower()
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw.lower() in haystack:
                return category
    return "Uncategorised"


def _resolve_debit_credit(df: pd.DataFrame) -> pd.DataFrame:
    """
    When OCR flattens debit/credit columns into one amount column,
    use the running balance delta to determine direction.
    
    Rule: If balance went DOWN → it's a debit; if UP → it's a credit.
    When withdrawals > 0 AND deposits > 0 → trust them as-is (3-col parse worked).
    When only withdrawals > 0 → use balance delta to reassign.
    """
    df = df.copy()

    prev_bal = None
    for idx in df.index:
        row = df.loc[idx]
        bal = row["balance"]
        has_both = row["withdrawals"] > 0 and row["deposits"] > 0

        if has_both or bal == 0:
            prev_bal = bal if bal != 0 else prev_bal
            continue

        # Use balance delta
        if prev_bal is not None and bal != 0:
            delta = bal - prev_bal
            amount = row["withdrawals"]  # the single captured amount

            if amount > 0:
                if delta < 0:
                    df.at[idx, "withdrawals"] = amount
                    df.at[idx, "deposits"]    = 0.0
                elif delta > 0:
                    df.at[idx, "deposits"]    = amount
                    df.at[idx, "withdrawals"] = 0.0

        if bal != 0:
            prev_bal = bal

    return df


def normalize(raw_df: pd.DataFrame, period_end: str) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame()

    year = _extract_year(period_end)
    df   = raw_df.copy()

    # Resolve debit vs credit using balance delta
    df = _resolve_debit_credit(df)

    # Dates
    df["transaction_date"] = df["raw_date"].apply(lambda d: _parse_date(d, year))

    # Clean merchant
    df["clean_merchant"] = df["description"].apply(_clean_merchant)

    # Category
    df["category"] = df["description"].apply(_categorise)

    # Rename
    df = df.rename(columns={
        "withdrawals": "debit",
        "deposits":    "credit",
        "balance":     "running_balance",
    })

    cols = ["transaction_date", "description", "clean_merchant",
            "category", "debit", "credit", "running_balance"]
    df = df[cols]

    for col in ["debit", "credit", "running_balance"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df = df.sort_values("transaction_date").reset_index(drop=True)
    return df
