"""
harmonize.py
Standardise raw UIS and SDMX DataFrames into a common schema.

Operations
----------
1. Enforce column names and data types.
2. Validate and filter ISO 3166-1 alpha-3 country codes.
3. Enforce year range from config.
4. Attach region and income-group metadata.
5. Add a SOURCE column to track data provenance.

Location: src/integration/harmonize.py
"""

import logging
import pandas as pd

from src.utils.config import (
    DATA_PROCESSED_DIR,
    QA_CONFIG,
    LOG_FORMAT,
    LOG_DATE_FMT,
)

# ── Logger ────────────────────────────────────────────────────────────────────
logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FMT, level=logging.INFO)
log = logging.getLogger(__name__)

HARMONIZED_FILE = DATA_PROCESSED_DIR / "harmonized.csv"

# ── Region / income-group lookup ──────────────────────────────────────────────
# Source: World Bank country classification (simplified subset)
COUNTRY_META = {
    # ISO3 : (region, income_group)
    "MDG": ("Sub-Saharan Africa",        "Low income"),
    "GHA": ("Sub-Saharan Africa",        "Lower middle income"),
    "KEN": ("Sub-Saharan Africa",        "Lower middle income"),
    "ETH": ("Sub-Saharan Africa",        "Low income"),
    "NGA": ("Sub-Saharan Africa",        "Lower middle income"),
    "ZAF": ("Sub-Saharan Africa",        "Upper middle income"),
    "MAR": ("Middle East & North Africa","Lower middle income"),
    "EGY": ("Middle East & North Africa","Lower middle income"),
    "BRA": ("Latin America & Caribbean", "Upper middle income"),
    "MEX": ("Latin America & Caribbean", "Upper middle income"),
    "COL": ("Latin America & Caribbean", "Upper middle income"),
    "ARG": ("Latin America & Caribbean", "Upper middle income"),
    "IND": ("South Asia",                "Lower middle income"),
    "BGD": ("South Asia",                "Lower middle income"),
    "PAK": ("South Asia",                "Lower middle income"),
    "NPL": ("South Asia",                "Low income"),
    "FRA": ("Europe & Central Asia",     "High income"),
    "DEU": ("Europe & Central Asia",     "High income"),
    "GBR": ("Europe & Central Asia",     "High income"),
    "ITA": ("Europe & Central Asia",     "High income"),
    "ESP": ("Europe & Central Asia",     "High income"),
    "USA": ("North America",             "High income"),
    "CAN": ("North America",             "High income"),
    "AUS": ("East Asia & Pacific",       "High income"),
    "CHN": ("East Asia & Pacific",       "Upper middle income"),
    "JPN": ("East Asia & Pacific",       "High income"),
    "KOR": ("East Asia & Pacific",       "High income"),
    "IDN": ("East Asia & Pacific",       "Lower middle income"),
    "VNM": ("East Asia & Pacific",       "Lower middle income"),
    "THA": ("East Asia & Pacific",       "Upper middle income"),
}

# ── Required output schema ────────────────────────────────────────────────────
SCHEMA = {
    "INDICATOR_ID":    str,
    "INDICATOR_LABEL": str,
    "ISO3":            str,
    "YEAR":            "Int64",
    "VALUE":           float,
    "SOURCE":          str,
}


def _enforce_schema(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """
    Align a raw DataFrame to the common schema.
    Adds SOURCE column; fills missing optional columns with None.
    """
    df = df.copy()
    df["SOURCE"] = source_name

    # Ensure required columns exist
    for col, dtype in SCHEMA.items():
        if col not in df.columns:
            df[col] = pd.NA

    # Cast types
    df["INDICATOR_ID"]    = df["INDICATOR_ID"].astype(str).str.strip()
    df["INDICATOR_LABEL"] = df["INDICATOR_LABEL"].astype(str).str.strip()
    df["ISO3"]            = df["ISO3"].astype(str).str.strip().str.upper()
    df["YEAR"]            = pd.to_numeric(df["YEAR"],  errors="coerce").astype("Int64")
    df["VALUE"]           = pd.to_numeric(df["VALUE"], errors="coerce")

    return df[list(SCHEMA.keys())]


def _validate_iso3(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows whose ISO3 code is in the known country metadata."""
    valid = set(COUNTRY_META.keys())
    before = len(df)
    df = df[df["ISO3"].isin(valid)].copy()
    dropped = before - len(df)
    if dropped:
        log.info("ISO3 filter: dropped %s rows with unknown country codes.", dropped)
    return df


def _enforce_year_range(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows outside the plausible year range defined in QA_CONFIG."""
    yr_min = QA_CONFIG["year_min"]
    yr_max = QA_CONFIG["year_max"]
    before = len(df)
    df = df[df["YEAR"].between(yr_min, yr_max)].copy()
    dropped = before - len(df)
    if dropped:
        log.info("Year filter: dropped %s rows outside [%s, %s].", dropped, yr_min, yr_max)
    return df


def _attach_country_meta(df: pd.DataFrame) -> pd.DataFrame:
    """Add REGION and INCOME_GROUP columns from the lookup table."""
    meta_df = pd.DataFrame.from_dict(
        COUNTRY_META,
        orient="index",
        columns=["REGION", "INCOME_GROUP"],
    ).rename_axis("ISO3").reset_index()

    df = df.merge(meta_df, on="ISO3", how="left")
    return df


def harmonize(
    df_uis: pd.DataFrame,
    df_sdmx: pd.DataFrame,
) -> pd.DataFrame:
    """
    Harmonize and combine UIS and SDMX DataFrames into a single clean table.

    Parameters
    ----------
    df_uis  : Raw DataFrame from fetch_uis.run()
    df_sdmx : Raw DataFrame from fetch_sdmx.run()

    Returns
    -------
    Harmonized pd.DataFrame with unified schema + region metadata.
    """
    log.info("Harmonizing UIS source  (%s rows) ...", len(df_uis))
    uis  = _enforce_schema(df_uis,  source_name="UIS_API")

    log.info("Harmonizing SDMX source (%s rows) ...", len(df_sdmx))
    sdmx = _enforce_schema(df_sdmx, source_name="UIS_SDMX")

    # ── Combine ───────────────────────────────────────────────────────────────
    combined = pd.concat([uis, sdmx], ignore_index=True)
    log.info("Combined: %s rows before deduplication.", len(combined))

    # ── Deduplicate: keep UIS_API value where both sources agree on key ───────
    combined = combined.sort_values(
        by=["INDICATOR_ID", "ISO3", "YEAR", "SOURCE"],
        ascending=[True, True, True, True],
    )
    combined = combined.drop_duplicates(
        subset=["INDICATOR_ID", "ISO3", "YEAR"],
        keep="first",
    )
    log.info("After deduplication: %s rows.", len(combined))

    # ── Validate ──────────────────────────────────────────────────────────────
    combined = _validate_iso3(combined)
    combined = _enforce_year_range(combined)

    # ── Enrich ────────────────────────────────────────────────────────────────
    combined = _attach_country_meta(combined)

    # ── Sort ──────────────────────────────────────────────────────────────────
    combined = combined.sort_values(
        ["INDICATOR_ID", "ISO3", "YEAR"]
    ).reset_index(drop=True)

    log.info("Harmonized shape: %s rows × %s columns.", *combined.shape)
    return combined


def run() -> pd.DataFrame:
    """Load raw cached files, harmonize, and save to data/processed/."""
    from src.ingestion.fetch_uis  import run as uis_run
    from src.ingestion.fetch_sdmx import run as sdmx_run

    df_uis  = uis_run()
    df_sdmx = sdmx_run()

    df = harmonize(df_uis, df_sdmx)

    df.to_csv(HARMONIZED_FILE, index=False)
    log.info("Saved harmonized data to: %s", HARMONIZED_FILE)
    log.info("Sample:\n%s", df.head(4).to_string(index=False))
    return df


if __name__ == "__main__":
    run()
