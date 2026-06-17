"""
merge_sources.py
Merge harmonized long-format data into a wide analytical table.

Operations
----------
1. Load harmonized.csv from data/processed/.
2. Pivot: rows = (ISO3, YEAR), columns = INDICATOR_ID values.
3. Compute per-indicator coverage statistics.
4. Save both long and wide formats to data/processed/.

Location: src/integration/merge_sources.py
"""

import logging
import pandas as pd
import numpy as np

from src.utils.config import (
    DATA_PROCESSED_DIR,
    SDG4_INDICATORS,
    LOG_FORMAT,
    LOG_DATE_FMT,
)

# ── Logger ────────────────────────────────────────────────────────────────────
logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FMT, level=logging.INFO)
log = logging.getLogger(__name__)

HARMONIZED_FILE  = DATA_PROCESSED_DIR / "harmonized.csv"
WIDE_FILE        = DATA_PROCESSED_DIR / "analytical_wide.csv"
COVERAGE_FILE    = DATA_PROCESSED_DIR / "coverage_stats.csv"


# ── Coverage statistics ───────────────────────────────────────────────────────
def compute_coverage(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-indicator coverage statistics.

    Returns DataFrame with:
        INDICATOR_ID, INDICATOR_LABEL, N_COUNTRIES, N_YEARS,
        N_OBSERVATIONS, N_MISSING, COVERAGE_PCT, YEAR_MIN, YEAR_MAX
    """
    records = []

    # Full expected grid: all indicators × all countries × all years
    all_iso3  = df_long["ISO3"].unique()
    all_years = df_long["YEAR"].dropna().unique()
    total_possible = len(all_iso3) * len(all_years)

    for ind_id in SDG4_INDICATORS:
        subset = df_long[df_long["INDICATOR_ID"] == ind_id]

        n_obs      = subset["VALUE"].notna().sum()
        n_countries = subset["ISO3"].nunique()
        n_years     = subset["YEAR"].nunique()
        n_missing   = total_possible - n_obs
        coverage    = round(n_obs / total_possible * 100, 2) if total_possible else 0.0
        year_min    = int(subset["YEAR"].min()) if not subset.empty else None
        year_max    = int(subset["YEAR"].max()) if not subset.empty else None

        records.append({
            "INDICATOR_ID":    ind_id,
            "INDICATOR_LABEL": SDG4_INDICATORS[ind_id],
            "N_COUNTRIES":     n_countries,
            "N_YEARS":         n_years,
            "N_OBSERVATIONS":  n_obs,
            "N_MISSING":       max(n_missing, 0),
            "COVERAGE_PCT":    coverage,
            "YEAR_MIN":        year_min,
            "YEAR_MAX":        year_max,
        })

    return pd.DataFrame(records)


# ── Pivot to wide ─────────────────────────────────────────────────────────────
def pivot_wide(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot long-format data to wide format.

    Index  : ISO3, YEAR, REGION, INCOME_GROUP
    Columns: one per INDICATOR_ID
    """
    # Keep one value per (indicator, country, year) — prefer non-null
    df_long = df_long.sort_values("VALUE", ascending=False)
    df_dedup = df_long.drop_duplicates(
        subset=["INDICATOR_ID", "ISO3", "YEAR"], keep="first"
    )

    wide = df_dedup.pivot_table(
        index=["ISO3", "YEAR", "REGION", "INCOME_GROUP"],
        columns="INDICATOR_ID",
        values="VALUE",
        aggfunc="first",
    )

    # Flatten column index
    wide.columns = [str(c) for c in wide.columns]
    wide = wide.reset_index()

    # Ensure all SDG4 indicator columns are present (fill with NaN if absent)
    for ind_id in SDG4_INDICATORS:
        if ind_id not in wide.columns:
            wide[ind_id] = np.nan

    # Reorder columns
    meta_cols = ["ISO3", "YEAR", "REGION", "INCOME_GROUP"]
    ind_cols  = list(SDG4_INDICATORS.keys())
    wide = wide[meta_cols + ind_cols].sort_values(["ISO3", "YEAR"]).reset_index(drop=True)

    log.info("Wide table shape: %s rows × %s columns.", *wide.shape)
    return wide


# ── Summary report ────────────────────────────────────────────────────────────
def print_coverage_report(coverage: pd.DataFrame) -> None:
    """Log a formatted coverage summary to console."""
    log.info("=" * 60)
    log.info("INDICATOR COVERAGE REPORT")
    log.info("=" * 60)
    for _, row in coverage.iterrows():
        log.info(
            "%-12s | %s obs | %s%% coverage | %s–%s",
            row["INDICATOR_ID"],
            str(row["N_OBSERVATIONS"]).rjust(5),
            str(row["COVERAGE_PCT"]).rjust(5),
            row["YEAR_MIN"],
            row["YEAR_MAX"],
        )
    log.info("=" * 60)


# ── Main entry ────────────────────────────────────────────────────────────────
def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load harmonized data, produce wide table and coverage stats.

    Returns
    -------
    (wide_df, coverage_df)
    """
    if not HARMONIZED_FILE.exists():
        log.info("Harmonized file not found — running harmonize step first.")
        from src.integration.harmonize import run as harmonize_run
        harmonize_run()

    log.info("Loading: %s", HARMONIZED_FILE)
    df_long = pd.read_csv(HARMONIZED_FILE, dtype={"YEAR": "Int64"})
    log.info("Loaded: %s rows × %s columns.", *df_long.shape)

    # ── Coverage stats ────────────────────────────────────────────────────────
    coverage = compute_coverage(df_long)
    coverage.to_csv(COVERAGE_FILE, index=False)
    log.info("Coverage stats saved to: %s", COVERAGE_FILE)
    print_coverage_report(coverage)

    # ── Wide pivot ────────────────────────────────────────────────────────────
    wide = pivot_wide(df_long)
    wide.to_csv(WIDE_FILE, index=False)
    log.info("Wide table saved to: %s", WIDE_FILE)

    log.info(
        "Wide table sample:\n%s",
        wide.head(3).to_string(index=False),
    )

    return wide, coverage


if __name__ == "__main__":
    run()
