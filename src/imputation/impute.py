"""
impute.py
Statistical imputation for missing SDG 4 indicator values.

Method
------
- Primary   : KNNImputer (scikit-learn) — imputes using k nearest neighbours
              in the feature space of all indicators for the same country-year.
- Fallback  : IterativeImputer — multivariate chained equations (MICE-style).
- Method selected via IMPUTATION_CONFIG in config.py.

Inputs
------
data/processed/analytical_wide.csv   (wide format from merge_sources)

Outputs
-------
data/processed/imputed_wide.csv      (wide table with filled values)
outputs/reports/imputation_report.csv (per-indicator imputation transparency)

Location: src/imputation/impute.py
"""

import logging
import pandas as pd
import numpy as np
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import KNNImputer, IterativeImputer

from src.utils.config import (
    DATA_PROCESSED_DIR,
    OUTPUTS_REPORTS_DIR,
    IMPUTATION_CONFIG,
    SDG4_INDICATORS,
    LOG_FORMAT,
    LOG_DATE_FMT,
)

# ── Logger ────────────────────────────────────────────────────────────────────
logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FMT, level=logging.INFO)
log = logging.getLogger(__name__)

WIDE_FILE        = DATA_PROCESSED_DIR / "analytical_wide.csv"
IMPUTED_FILE     = DATA_PROCESSED_DIR / "imputed_wide.csv"
IMPUTATION_REPORT = OUTPUTS_REPORTS_DIR / "imputation_report.csv"

# Indicator columns to impute
IND_COLS = list(SDG4_INDICATORS.keys())

# Meta columns kept but not imputed
META_COLS = ["ISO3", "YEAR", "REGION", "INCOME_GROUP"]


# ── Pre/post missingness audit ────────────────────────────────────────────────
def audit_missing(df: pd.DataFrame, label: str) -> dict:
    """Return per-indicator missing counts and percentages."""
    total = len(df)
    result = {}
    for col in IND_COLS:
        if col in df.columns:
            n_miss = int(df[col].isna().sum())
            result[col] = {
                "label":    label,
                "n_total":  total,
                "n_missing": n_miss,
                "pct_missing": round(n_miss / total * 100, 2) if total else 0,
            }
    return result


# ── Imputation ────────────────────────────────────────────────────────────────
def run_knn(X: np.ndarray) -> np.ndarray:
    """Apply KNNImputer to feature matrix X."""
    k = IMPUTATION_CONFIG["knn_neighbors"]
    log.info("KNN imputation — k=%s neighbours.", k)
    imp = KNNImputer(n_neighbors=k)
    return imp.fit_transform(X)


def run_iterative(X: np.ndarray) -> np.ndarray:
    """Apply IterativeImputer (MICE) to feature matrix X."""
    max_iter = IMPUTATION_CONFIG["max_iter"]
    rs       = IMPUTATION_CONFIG["random_state"]
    log.info("Iterative (MICE) imputation — max_iter=%s.", max_iter)
    imp = IterativeImputer(max_iter=max_iter, random_state=rs)
    return imp.fit_transform(X)


def impute_wide(df: pd.DataFrame) -> pd.DataFrame:
    """
    Impute missing values in the indicator columns of the wide table.

    Strategy
    --------
    1. Separate meta columns from indicator columns.
    2. Apply chosen imputer to the indicator matrix.
    3. Clip imputed values to valid ranges (0–100 for rates, 0–2.5 for GPI).
    4. Reassemble with meta columns.

    Returns imputed DataFrame.
    """
    df = df.copy()

    # Extract indicator matrix
    ind_present = [c for c in IND_COLS if c in df.columns]
    X = df[ind_present].values.astype(float)

    method = IMPUTATION_CONFIG.get("method", "knn")

    if method == "knn":
        X_imp = run_knn(X)
    elif method == "iterative":
        X_imp = run_iterative(X)
    else:
        log.warning("Unknown method '%s' — defaulting to KNN.", method)
        X_imp = run_knn(X)

    # ── Clip to valid ranges ──────────────────────────────────────────────────
    gpi_cols = [c for c in ind_present if "GPIA" in c]
    rate_cols = [c for c in ind_present if c not in gpi_cols]

    imp_df = pd.DataFrame(X_imp, columns=ind_present, index=df.index)

    for col in rate_cols:
        imp_df[col] = imp_df[col].clip(lower=0.0, upper=100.0)
    for col in gpi_cols:
        imp_df[col] = imp_df[col].clip(lower=0.0, upper=2.5)

    # Round to 4 decimal places
    imp_df = imp_df.round(4)

    # ── Reassemble ────────────────────────────────────────────────────────────
    meta_present = [c for c in META_COLS if c in df.columns]
    result = pd.concat([df[meta_present].reset_index(drop=True),
                        imp_df.reset_index(drop=True)], axis=1)

    return result


# ── Imputation transparency report ────────────────────────────────────────────
def build_report(
    before: dict,
    after: dict,
    df_orig: pd.DataFrame,
    df_imp: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a per-indicator report showing how many values were imputed.
    """
    records = []
    for col in IND_COLS:
        if col not in before:
            continue
        b = before[col]
        a = after[col]
        n_imputed = b["n_missing"] - a["n_missing"]

        records.append({
            "INDICATOR_ID":      col,
            "INDICATOR_LABEL":   SDG4_INDICATORS.get(col, ""),
            "N_TOTAL":           b["n_total"],
            "N_MISSING_BEFORE":  b["n_missing"],
            "PCT_MISSING_BEFORE": b["pct_missing"],
            "N_MISSING_AFTER":   a["n_missing"],
            "PCT_MISSING_AFTER": a["pct_missing"],
            "N_IMPUTED":         max(n_imputed, 0),
            "METHOD":            IMPUTATION_CONFIG.get("method", "knn").upper(),
        })

    return pd.DataFrame(records)


# ── Main entry ────────────────────────────────────────────────────────────────
def run() -> pd.DataFrame:
    """
    Load wide table, impute missing values, save outputs.

    Returns
    -------
    Imputed wide DataFrame.
    """
    if not WIDE_FILE.exists():
        log.info("Wide file not found — running merge step first.")
        from src.integration.merge_sources import run as merge_run
        merge_run()

    log.info("Loading: %s", WIDE_FILE)
    df = pd.read_csv(WIDE_FILE, dtype={"YEAR": "Int64"})
    log.info("Loaded: %s rows × %s columns.", *df.shape)

    # ── Audit before ─────────────────────────────────────────────────────────
    before = audit_missing(df, label="before")
    log.info("=" * 58)
    log.info("MISSING VALUES BEFORE IMPUTATION")
    log.info("=" * 58)
    for col, stats in before.items():
        log.info(
            "%-12s | missing: %s / %s (%.1f%%)",
            col, stats["n_missing"], stats["n_total"], stats["pct_missing"],
        )

    # ── Impute ────────────────────────────────────────────────────────────────
    log.info("=" * 58)
    df_imp = impute_wide(df)

    # ── Audit after ──────────────────────────────────────────────────────────
    after = audit_missing(df_imp, label="after")
    log.info("=" * 58)
    log.info("MISSING VALUES AFTER IMPUTATION")
    log.info("=" * 58)
    for col, stats in after.items():
        log.info(
            "%-12s | missing: %s / %s (%.1f%%)",
            col, stats["n_missing"], stats["n_total"], stats["pct_missing"],
        )

    # ── Build and save report ─────────────────────────────────────────────────
    report = build_report(before, after, df, df_imp)
    report.to_csv(IMPUTATION_REPORT, index=False)
    log.info("Imputation report saved to: %s", IMPUTATION_REPORT)

    # ── Save imputed wide table ───────────────────────────────────────────────
    df_imp.to_csv(IMPUTED_FILE, index=False)
    log.info("Imputed wide table saved to: %s", IMPUTED_FILE)

    # ── Summary ───────────────────────────────────────────────────────────────
    total_imputed = int(report["N_IMPUTED"].sum())
    log.info("=" * 58)
    log.info("Total values imputed: %s", total_imputed)
    log.info("Method: %s", IMPUTATION_CONFIG.get("method", "knn").upper())
    log.info("Sample (first 3 rows):\n%s", df_imp.head(3).to_string(index=False))

    return df_imp


if __name__ == "__main__":
    run()