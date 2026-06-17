"""
fetch_uis.py
Fetch UIS education indicator data via the UIS public REST API.
Falls back to synthetic sample data when the API is unreachable.
Location: src/ingestion/fetch_uis.py

UIS API reference:
    https://api.uis.unesco.org/api/public/documentation
"""

import logging
import time
import pandas as pd
import requests

from src.utils.config import (
    DATA_RAW_DIR,
    SDG4_INDICATORS,
    LOG_FORMAT,
    LOG_DATE_FMT,
)

# ── Logger ────────────────────────────────────────────────────────────────────
logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FMT, level=logging.INFO)
log = logging.getLogger(__name__)

# ── API config ────────────────────────────────────────────────────────────────
UIS_API_BASE    = "https://api.uis.unesco.org/api/public/data/indicators"
RAW_FILE        = DATA_RAW_DIR / "uis_sdg4_raw.csv"

# Countries to fetch (ISO3) — representative global sample
TARGET_COUNTRIES = [
    "MDG", "GHA", "KEN", "ETH", "NGA", "ZAF", "MAR", "EGY",
    "BRA", "MEX", "COL", "IND", "BGD", "PAK", "NPL",
    "FRA", "DEU", "GBR", "USA", "CAN",
    "CHN", "JPN", "IDN", "VNM",
]

START_YEAR = 2010
END_YEAR   = 2023


# ── API fetch ─────────────────────────────────────────────────────────────────
def fetch_indicator(indicator_id: str, session: requests.Session) -> pd.DataFrame:
    """
    Fetch one indicator for all target countries via UIS REST API.

    Returns a DataFrame with columns:
        INDICATOR_ID, ISO3, YEAR, VALUE, MAGNITUDE, QUALIFIER
    """
    params = {
        "indicator": indicator_id,
        "country":   ",".join(TARGET_COUNTRIES),
        "start":     START_YEAR,
        "end":       END_YEAR,
        "format":    "json",
    }

    try:
        r = session.get(UIS_API_BASE, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
    except requests.exceptions.RequestException as e:
        log.warning("API request failed for %s: %s", indicator_id, e)
        return pd.DataFrame()

    records = []
    # UIS API returns a list of observation objects
    for obs in payload.get("data", []):
        records.append({
            "INDICATOR_ID": indicator_id,
            "ISO3":         obs.get("countryId", obs.get("country_id", "")),
            "YEAR":         obs.get("year"),
            "VALUE":        obs.get("value"),
            "MAGNITUDE":    obs.get("magnitude", ""),
            "QUALIFIER":    obs.get("qualifier", ""),
        })

    return pd.DataFrame(records)


def fetch_all_indicators() -> pd.DataFrame:
    """Fetch all SDG 4 indicators and concatenate into one DataFrame."""
    frames = []
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    for ind_id, ind_label in SDG4_INDICATORS.items():
        log.info("Fetching indicator: %s — %s", ind_id, ind_label)
        df = fetch_indicator(ind_id, session)
        if not df.empty:
            df["INDICATOR_LABEL"] = ind_label
            frames.append(df)
        time.sleep(0.3)   # polite rate limiting

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    log.info("Total records fetched: %s", len(combined))
    return combined


# ── Synthetic fallback ────────────────────────────────────────────────────────
def generate_synthetic_data() -> pd.DataFrame:
    """
    Generate a realistic synthetic dataset for development and testing.
    Used when the UIS API is unreachable (e.g. offline, rate-limited).
    """
    import numpy as np
    rng = np.random.default_rng(seed=42)

    rows = []
    for ind_id, ind_label in SDG4_INDICATORS.items():
        is_gpi = "GPIA" in ind_id
        for iso3 in TARGET_COUNTRIES:
            for year in range(START_YEAR, END_YEAR + 1):
                if rng.random() < 0.15:   # ~15% missingness
                    continue
                if is_gpi:
                    value = round(rng.uniform(0.7, 1.3), 4)
                else:
                    value = round(rng.uniform(20.0, 99.0), 2)
                rows.append({
                    "INDICATOR_ID":    ind_id,
                    "INDICATOR_LABEL": ind_label,
                    "ISO3":            iso3,
                    "YEAR":            year,
                    "VALUE":           value,
                    "MAGNITUDE":       "",
                    "QUALIFIER":       "",
                })

    df = pd.DataFrame(rows)
    log.info("Synthetic dataset generated: %s rows", len(df))
    return df


# ── Main entry ────────────────────────────────────────────────────────────────
def run(force: bool = False, use_synthetic: bool = False) -> pd.DataFrame:
    """
    Download UIS data (or load from cache) and return clean DataFrame.

    Parameters
    ----------
    force         : Re-fetch even if cached file exists.
    use_synthetic : Skip API and use synthetic data (for offline dev/testing).
    """
    if RAW_FILE.exists() and not force and not use_synthetic:
        log.info("Loading cached raw file: %s", RAW_FILE)
        df = pd.read_csv(RAW_FILE, dtype={"YEAR": "Int64"})
        log.info("Cached shape: %s rows × %s columns", *df.shape)
        return df

    if use_synthetic:
        log.warning("Using SYNTHETIC data — not real UIS observations.")
        df = generate_synthetic_data()
    else:
        log.info("Fetching from UIS API ...")
        df = fetch_all_indicators()
        if df.empty:
            log.warning("API returned no data — falling back to synthetic data.")
            df = generate_synthetic_data()

    # ── Save to raw cache ─────────────────────────────────────────────────────
    df.to_csv(RAW_FILE, index=False)
    log.info("Saved to: %s", RAW_FILE)
    log.info("Sample:\n%s", df.head(3).to_string(index=False))
    return df


if __name__ == "__main__":
    # To use real API:    python -m src.ingestion.fetch_uis
    # To use synthetic:   python -m src.ingestion.fetch_uis --synthetic
    import sys
    synthetic = "--synthetic" in sys.argv
    run(use_synthetic=synthetic)
