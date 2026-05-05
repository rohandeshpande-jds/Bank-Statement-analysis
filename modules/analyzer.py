# ─────────────────────────────────────────────
#  modules/analyzer.py  –  Phase 3: Analyse & Detect Anomalies
# ─────────────────────────────────────────────

import pandas as pd
from config import ANOMALY_THRESHOLD_PCT, DUPLICATE_WINDOW_HOURS


# ── Summary Statistics ────────────────────────────────────────────────────────

def compute_summary(df: pd.DataFrame) -> dict:
    """Compute high-level financial summary."""
    total_credits  = df["credit"].sum()
    total_debits   = df["debit"].sum()
    net_change     = total_credits - total_debits
    tx_count       = len(df)
    avg_debit      = df[df["debit"] > 0]["debit"].mean() if (df["debit"] > 0).any() else 0
    avg_credit     = df[df["credit"] > 0]["credit"].mean() if (df["credit"] > 0).any() else 0
    largest_debit  = df["debit"].max()
    largest_credit = df["credit"].max()

    return {
        "total_credits":   round(total_credits, 2),
        "total_debits":    round(total_debits, 2),
        "net_change":      round(net_change, 2),
        "transaction_count": tx_count,
        "avg_debit":       round(avg_debit, 2),
        "avg_credit":      round(avg_credit, 2),
        "largest_debit":   round(largest_debit, 2),
        "largest_credit":  round(largest_credit, 2),
    }


def category_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate debit/credit totals and transaction counts by category."""
    grp = df.groupby("category").agg(
        tx_count   = ("transaction_date", "count"),
        total_debit  = ("debit",  "sum"),
        total_credit = ("credit", "sum"),
    ).reset_index()
    grp["total_debit"]  = grp["total_debit"].round(2)
    grp["total_credit"] = grp["total_credit"].round(2)
    grp = grp.sort_values("total_debit", ascending=False)
    return grp


# ── Anomaly Detection ─────────────────────────────────────────────────────────

def _detect_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    SOP §3.3 – Flag transactions with same amount within DUPLICATE_WINDOW_HOURS.
    """
    flagged = []
    df_sorted = df.copy().sort_values(["transaction_date", "debit", "credit"])

    for i, row in df_sorted.iterrows():
        amount = row["debit"] if row["debit"] > 0 else row["credit"]
        if amount == 0:
            continue
        col = "debit" if row["debit"] > 0 else "credit"

        # Look for same date + same amount (simplified: same date window)
        same_date = df_sorted[df_sorted["transaction_date"] == row["transaction_date"]]
        matches   = same_date[same_date[col] == amount]

        if len(matches) > 1 and i == matches.index[0]:
            flagged.append({
                "anomaly_type": "Duplicate Transaction",
                "date":         row["transaction_date"],
                "description":  row["description"],
                "amount":       amount,
                "detail":       f"Appears {len(matches)}x on same date",
            })

    return pd.DataFrame(flagged)


def _detect_large_debits(df: pd.DataFrame, summary: dict) -> pd.DataFrame:
    """
    SOP §3.3 – Flag one-off debits exceeding 20% of average monthly spend.
    """
    avg_monthly = summary["total_debits"]  # single-month statement
    threshold   = avg_monthly * ANOMALY_THRESHOLD_PCT
    flagged     = []

    debits = df[df["debit"] > threshold]
    for _, row in debits.iterrows():
        flagged.append({
            "anomaly_type": "Large One-Off Debit",
            "date":         row["transaction_date"],
            "description":  row["description"],
            "amount":       row["debit"],
            "detail":       f"SGD {row['debit']:,.2f} > 20% of total debits (SGD {threshold:,.2f})",
        })

    return pd.DataFrame(flagged)


def _detect_subscription_spikes(df: pd.DataFrame) -> pd.DataFrame:
    """
    SOP §3.3 – Flag merchants with unexpected variation in recurring amounts.
    (Within a single statement, detect same merchant charging different amounts.)
    """
    flagged = []
    df_debits = df[df["debit"] > 0].copy()

    merchant_grp = df_debits.groupby("clean_merchant")["debit"]
    for merchant, amounts in merchant_grp:
        if len(amounts) < 2:
            continue
        mean_amt = amounts.mean()
        for idx, amt in amounts.items():
            if abs(amt - mean_amt) / mean_amt > 0.30:   # 30% spike threshold
                flagged.append({
                    "anomaly_type": "Subscription Spike",
                    "date":         df_debits.loc[idx, "transaction_date"],
                    "description":  merchant,
                    "amount":       amt,
                    "detail":       f"Avg charge SGD {mean_amt:,.2f}, this charge SGD {amt:,.2f}",
                })

    return pd.DataFrame(flagged)


def detect_anomalies(df: pd.DataFrame, summary: dict) -> pd.DataFrame:
    """
    Run all anomaly detectors and return a unified flags DataFrame.
    """
    parts = []

    dups   = _detect_duplicates(df)
    large  = _detect_large_debits(df, summary)
    spikes = _detect_subscription_spikes(df)

    for part in [dups, large, spikes]:
        if not part.empty:
            parts.append(part)

    if parts:
        all_flags = pd.concat(parts, ignore_index=True)
    else:
        all_flags = pd.DataFrame(
            columns=["anomaly_type", "date", "description", "amount", "detail"]
        )

    return all_flags


# ── Quality Gate ──────────────────────────────────────────────────────────────

def quality_gate(df: pd.DataFrame, validation: dict) -> dict:
    """
    SOP Final Quality Gate:
    Total Credits - Total Debits must match Net Change in account balance.
    """
    total_credits    = df["credit"].sum()
    total_debits     = df["debit"].sum()
    computed_net     = round(total_credits - total_debits, 2)
    stated_net       = round(validation["net_change"], 2)
    tolerance        = 0.10
    passed           = abs(computed_net - stated_net) <= tolerance

    return {
        "computed_net_change": computed_net,
        "stated_net_change":   stated_net,
        "difference":          round(abs(computed_net - stated_net), 2),
        "passed":              passed,
        "status":              "PASS ✓" if passed else "FAIL ✗",
    }


# ── Main Analyse Function ─────────────────────────────────────────────────────

def analyse(df: pd.DataFrame, validation: dict) -> dict:
    """
    Phase 3 main entry point.
    Returns a dict of all analytical results.
    """
    summary    = compute_summary(df)
    cat_df     = category_breakdown(df)
    anomalies  = detect_anomalies(df, summary)
    qg         = quality_gate(df, validation)

    return {
        "summary":            summary,
        "category_breakdown": cat_df,
        "anomalies":          anomalies,
        "quality_gate":       qg,
    }
