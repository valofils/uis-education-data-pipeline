"""
validate.py
Rules-based data quality assurance for harmonized education indicators.

Checks performed
----------------
1. Value range validation (rates: 0–100, GPI: 0–2.5).
2. Missing rate per indicator — flag if above threshold.
3. Duplicate (indicator, country, year) triplets.
4. Year range plausibility.
5. ISO3 presence check.

Outputs
-------
- QA report CSV  : outputs/reports/qa_report.csv
- Flagged rows   : outputs/reports/qa_flagged.csv

Location: src/quality/validate.py
"""

import logging
import pandas as pd

from src.utils.config import (
    DATA_PROCESSED_DIR,
    OUTPUTS_REPORTS_DIR,
    QA_CONFIG,
    SDG4_INDICATORS,
    LOG_FORMAT,
    LOG_DATE_FMT,
)

# ── Logger ────────────────────────────────────────────────────────────────────
logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FMT, level=logging.INFO)
log = logging.getLogger(__name__)

HARMONIZED_FILE = DATA_PROCESSED_DIR / "harmonized.csv"
QA_REPORT_FILE  = OUTPUTS_REPORTS_DIR / "qa_report.csv"
QA_FLAGGED_FILE = OUTPUTS_REPORTS_DIR / "qa_flagged.csv"

# GPI indicators — different valid range
GPI_INDICATORS = {k for k in SDG4_INDICATORS if "GPIA" in k}


# ── Individual checks ─────────────────────────────────────────────────────────
def check_value_range(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flag rows where VALUE is outside the valid range for the indicator type.
    - Rate indicators : 0 – 100
    - GPI indicators  : 0 – 2.5
    """
    flagged = []

    for ind_id in df["INDICATOR_ID"].unique():
        subset = df[df["INDICATOR_ID"] == ind_id].copy()
        vals   = subset["VALUE"].dropna()

        if ind_id in GPI_INDICATORS:
            lo, hi = QA_CONFIG["gpi_min"], QA_CONFIG["gpi_max"]
        else:
            lo, hi = QA_CONFIG["rate_min"], QA_CONFIG["rate_max"]

        out = subset[
            subset["VALUE"].notna() &
            ((subset["VALUE"] < lo) | (subset["VALUE"] > hi))
        ].copy()

        if not out.empty:
            out["QA_FLAG"]   = "OUT_OF_RANGE"
            out["QA_DETAIL"] = f"VALUE outside [{lo}, {hi}] for {ind_id}"
            flagged.append(out)

    return pd.concat(flagged, ignore_index=True) if flagged else pd.DataFrame()


def check_missing_rate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flag indicators whose missing value rate exceeds QA_CONFIG threshold.
    Returns a summary DataFrame (one row per flagged indicator).
    """
    threshold = QA_CONFIG["max_missing_pct"]
    records   = []

    all_iso3  = df["ISO3"].nunique()
    all_years = df["YEAR"].nunique()
    expected  = all_iso3 * all_years

    for ind_id in SDG4_INDICATORS:
        subset   = df[df["INDICATOR_ID"] == ind_id]
        n_obs    = subset["VALUE"].notna().sum()
        miss_pct = (1 - n_obs / expected) * 100 if expected else 0

        if miss_pct > threshold:
            records.append({
                "INDICATOR_ID": ind_id,
                "QA_FLAG":      "HIGH_MISSING_RATE",
                "QA_DETAIL":    f"{miss_pct:.1f}% missing (threshold {threshold}%)",
                "ISO3":         "ALL",
                "YEAR":         pd.NA,
                "VALUE":        pd.NA,
            })

    return pd.DataFrame(records)


def check_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Flag duplicate (INDICATOR_ID, ISO3, YEAR) triplets."""
    dupes = df[
        df.duplicated(subset=["INDICATOR_ID", "ISO3", "YEAR"], keep=False)
    ].copy()

    if not dupes.empty:
        dupes["QA_FLAG"]   = "DUPLICATE_KEY"
        dupes["QA_DETAIL"] = "Duplicate (INDICATOR_ID, ISO3, YEAR) triplet"
        log.warning("Duplicates found: %s rows.", len(dupes))

    return dupes


def check_year_range(df: pd.DataFrame) -> pd.DataFrame:
    """Flag rows with implausible year values."""
    yr_min = QA_CONFIG["year_min"]
    yr_max = QA_CONFIG["year_max"]

    out = df[
        df["YEAR"].notna() &
        (~df["YEAR"].between(yr_min, yr_max))
    ].copy()

    if not out.empty:
        out["QA_FLAG"]   = "IMPLAUSIBLE_YEAR"
        out["QA_DETAIL"] = f"YEAR outside [{yr_min}, {yr_max}]"

    return out


def check_missing_iso3(df: pd.DataFrame) -> pd.DataFrame:
    """Flag rows with null or empty ISO3."""
    out = df[df["ISO3"].isna() | (df["ISO3"].str.strip() == "")].copy()

    if not out.empty:
        out["QA_FLAG"]   = "MISSING_ISO3"
        out["QA_DETAIL"] = "ISO3 is null or empty"

    return out


# ── QA summary report ─────────────────────────────────────────────────────────
def build_qa_summary(df: pd.DataFrame, flagged: pd.DataFrame) -> pd.DataFrame:
    """
    Build a per-indicator QA summary table.

    Columns: INDICATOR_ID, N_TOTAL, N_VALID, N_MISSING,
             MISSING_PCT, N_FLAGGED, QA_STATUS
    """
    records = []
    all_iso3  = df["ISO3"].nunique()
    all_years = df["YEAR"].nunique()
    expected  = all_iso3 * all_years

    for ind_id in SDG4_INDICATORS:
        subset   = df[df["INDICATOR_ID"] == ind_id]
        n_valid  = int(subset["VALUE"].notna().sum())
        n_miss   = expected - n_valid
        miss_pct = round((n_miss / expected) * 100, 2) if expected else 0

        n_flagged = 0
        if not flagged.empty and "INDICATOR_ID" in flagged.columns:
            n_flagged = int(
                (flagged["INDICATOR_ID"] == ind_id).sum()
            )

        status = "PASS"
        if miss_pct > QA_CONFIG["max_missing_pct"]:
            status = "WARN_MISSING"
        if n_flagged > 0:
            status = "FAIL" if status == "PASS" else status + "|FAIL"

        records.append({
            "INDICATOR_ID":    ind_id,
            "INDICATOR_LABEL": SDG4_INDICATORS[ind_id],
            "N_EXPECTED":      expected,
            "N_VALID":         n_valid,
            "N_MISSING":       max(n_miss, 0),
            "MISSING_PCT":     miss_pct,
            "N_FLAGGED":       n_flagged,
            "QA_STATUS":       status,
        })

    return pd.DataFrame(records)


# ── Main entry ────────────────────────────────────────────────────────────────
def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run all QA checks on harmonized data.

    Returns
    -------
    (qa_summary, flagged_rows)
    """
    if not HARMONIZED_FILE.exists():
        log.info("Harmonized file not found — running pipeline first.")
        from src.integration.harmonize import run as harmonize_run
        harmonize_run()

    log.info("Loading: %s", HARMONIZED_FILE)
    df = pd.read_csv(HARMONIZED_FILE, dtype={"YEAR": "Int64"})
    log.info("Loaded: %s rows.", len(df))

    # ── Run all checks ────────────────────────────────────────────────────────
    log.info("Running QA checks ...")
    all_flagged = []

    range_flags = check_value_range(df)
    if not range_flags.empty:
        log.warning("Range flags: %s rows.", len(range_flags))
        all_flagged.append(range_flags)

    miss_flags = check_missing_rate(df)
    if not miss_flags.empty:
        log.warning("High missing rate flags: %s indicators.", len(miss_flags))
        all_flagged.append(miss_flags)

    dupe_flags = check_duplicates(df)
    if not dupe_flags.empty:
        all_flagged.append(dupe_flags)

    year_flags = check_year_range(df)
    if not year_flags.empty:
        log.warning("Year range flags: %s rows.", len(year_flags))
        all_flagged.append(year_flags)

    iso3_flags = check_missing_iso3(df)
    if not iso3_flags.empty:
        log.warning("Missing ISO3 flags: %s rows.", len(iso3_flags))
        all_flagged.append(iso3_flags)

    # ── Combine flagged rows ──────────────────────────────────────────────────
    flagged = (
        pd.concat(all_flagged, ignore_index=True)
        if all_flagged else pd.DataFrame()
    )

    # ── Build and save QA summary ─────────────────────────────────────────────
    summary = build_qa_summary(df, flagged)
    summary.to_csv(QA_REPORT_FILE, index=False)
    log.info("QA report saved to: %s", QA_REPORT_FILE)

    if not flagged.empty:
        flagged.to_csv(QA_FLAGGED_FILE, index=False)
        log.info("Flagged rows saved to: %s", QA_FLAGGED_FILE)

    # ── Print summary ─────────────────────────────────────────────────────────
    log.info("=" * 62)
    log.info("QA SUMMARY")
    log.info("=" * 62)
    for _, row in summary.iterrows():
        log.info(
            "%-12s | valid: %s | missing: %s%% | flagged: %s | %s",
            row["INDICATOR_ID"],
            str(row["N_VALID"]).rjust(4),
            str(row["MISSING_PCT"]).rjust(5),
            str(row["N_FLAGGED"]).rjust(3),
            row["QA_STATUS"],
        )
    log.info("=" * 62)

    pass_count = (summary["QA_STATUS"] == "PASS").sum()
    log.info(
        "Result: %s/%s indicators PASS | %s total flagged rows.",
        pass_count, len(summary), len(flagged),
    )

    return summary, flagged


if __name__ == "__main__":
    run()
