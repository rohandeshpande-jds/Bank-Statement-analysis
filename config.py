# ─────────────────────────────────────────────
#  config.py  –  Bank Analyzer Configuration
# ─────────────────────────────────────────────

# SOP §3.3 – Anomaly Detection Thresholds
ANOMALY_THRESHOLD_PCT   = 0.20   # 20 % of average monthly spend
DUPLICATE_WINDOW_HOURS  = 24

# SOP §3.2 – Categorisation Rules
# Keys are category names; values are keyword lists (case-insensitive substring match)
CATEGORY_RULES = {
    "Income": [
        "inward cr", "inward credit", "giro cor", "misc credit",
        "cash deposit", "funds transfer-ib", "paynow othr",
        "cheque deposit", "bexp bizexpenses",
    ],
    "Financial": [
        "service charge", "svc chg", "payment to iras", "gst-iras",
        "payment iras", "misc debit", "cash withdrawal",
        "account annual service fee", "acct monthly service fee",
        "misc dr-debit card",
    ],
    "CPF / Govt": [
        "cpf", "iras", "gst", "sub court", "supreme court",
        "singapore land autho", "singapore telecommun",
    ],
    "Transfer Out": [
        "funds trf - fast", "funds transfer-ib", "paynow-fast",
        "funds trf-fast", "inward dr - giro",
    ],
    "Transfer In": [
        "inward cr - giro", "inward credit-fast",
    ],
    "Bank Fees": [
        "service charge", "svc chg",
    ],
}

# Category priority order (first match wins)
CATEGORY_PRIORITY = [
    "CPF / Govt",
    "Financial",
    "Income",
    "Transfer In",
    "Transfer Out",
    "Bank Fees",
    "Uncategorised",
]

# Merchant noise patterns to strip from descriptions
NOISE_PATTERNS = [
    r"GEBFT\d+",
    r"PMRSG\d+",
    r"PMRBUNDFR/\d+",
    r"PMRACCASC/\d+",
    r"PMRAMSVCFEE/\d+",
    r"FT\d+",
    r"GEB\w+",
    r"\b\d{10,}\b",          # long numeric strings
    r"OTHR\s+",
    r"PAYNOW\s+OTHR\s+",
]
