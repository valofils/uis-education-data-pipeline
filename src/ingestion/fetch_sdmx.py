"""
fetch_sdmx.py
Query the UIS SDMX 2.1 REST endpoint and parse responses into a DataFrame.
Location: src/ingestion/fetch_sdmx.py

SDMX REST API standard:
    https://sdmx.uis.unesco.org/ws/rest
    Pattern: /data/{flowRef}/{key}/{provider}?startPeriod=&endPeriod=&format=
"""

import logging
import requests
import xml.etree.ElementTree as ET
import pandas as pd

from src.utils.config import (
    DATA_RAW_DIR,
    SDG4_INDICATORS,
    LOG_FORMAT,
    LOG_DATE_FMT,
)

# ── Logger ────────────────────────────────────────────────────────────────────
logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FMT, level=logging.INFO)
log = logging.getLogger(__name__)

# ── SDMX config ───────────────────────────────────────────────────────────────
SDMX_BASE       = "https://sdmx.uis.unesco.org/ws/rest"
DATAFLOW_ID     = "UIS,SDG4,1.0"          # UIS SDG 4 dataflow
SDMX_RAW_FILE   = DATA_RAW_DIR / "uis_sdmx_raw.csv"

# SDMX XML namespaces
NS = {
    "message": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message",
    "generic": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic",
    "common":  "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
}

# Sample countries for SDMX query (SDMX key uses + as OR separator)
SDMX_COUNTRIES  = "MDG+GHA+KEN+ETH+NGA+ZAF+BRA+MEX+IND+FRA+DEU+GBR+USA+CHN"
START_PERIOD    = "2010"
END_PERIOD      = "2023"


# ── SDMX fetch ────────────────────────────────────────────────────────────────
def build_sdmx_url(indicator_id: str) -> str:
    """
    Build a SDMX 2.1 REST data URL for one indicator.

    URL pattern:
        /data/{flowRef}/{key}?startPeriod=&endPeriod=&format=genericdata
    Key dimension order for UIS SDG4 flow: INDICATOR.COUNTRY
    """
    key = f"{indicator_id}.{SDMX_COUNTRIES}"
    url = (
        f"{SDMX_BASE}/data/{DATAFLOW_ID}/{key}"
        f"?startPeriod={START_PERIOD}&endPeriod={END_PERIOD}"
        f"&format=genericdata"
    )
    return url


def parse_sdmx_xml(xml_bytes: bytes, indicator_id: str) -> pd.DataFrame:
    """
    Parse SDMX Generic Data XML response into a flat DataFrame.

    Returns DataFrame with columns:
        INDICATOR_ID, ISO3, YEAR, VALUE, OBS_STATUS
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        log.error("XML parse error for %s: %s", indicator_id, e)
        return pd.DataFrame()

    records = []

    # Iterate over Series elements
    for series in root.iter("{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}Series"):
        # Extract series-level keys (COUNTRY, INDICATOR, etc.)
        series_keys = {}
        for key_val in series.iter(
            "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}Value"
        ):
            id_attr  = key_val.get("id", "")
            val_attr = key_val.get("value", "")
            series_keys[id_attr] = val_attr

        country = series_keys.get("REF_AREA", series_keys.get("COUNTRY", ""))

        # Extract observations
        for obs in series.iter(
            "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}Obs"
        ):
            obs_dict = {}
            for child in obs:
                tag = child.tag.split("}")[-1]   # strip namespace
                if tag == "ObsDimension":
                    obs_dict["YEAR"] = child.get("value", "")
                elif tag == "ObsValue":
                    obs_dict["VALUE"] = child.get("value", "")
                elif tag == "Attributes":
                    for attr in child:
                        obs_dict[attr.get("id", "")] = attr.get("value", "")

            records.append({
                "INDICATOR_ID": indicator_id,
                "ISO3":         country,
                "YEAR":         obs_dict.get("YEAR", ""),
                "VALUE":        obs_dict.get("VALUE", ""),
                "OBS_STATUS":   obs_dict.get("OBS_STATUS", ""),
            })

    df = pd.DataFrame(records)
    if not df.empty:
        df["YEAR"]  = pd.to_numeric(df["YEAR"],  errors="coerce").astype("Int64")
        df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")

    return df


def fetch_sdmx_indicator(
    indicator_id: str,
    session: requests.Session,
) -> pd.DataFrame:
    """Fetch and parse one SDMX indicator. Returns empty DataFrame on failure."""
    url = build_sdmx_url(indicator_id)
    log.info("SDMX request: %s", indicator_id)

    try:
        r = session.get(url, timeout=40)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.warning("SDMX request failed for %s: %s", indicator_id, e)
        return pd.DataFrame()

    content_type = r.headers.get("Content-Type", "")
    if "xml" not in content_type.lower() and len(r.content) < 200:
        log.warning("Unexpected response for %s (Content-Type: %s)", indicator_id, content_type)
        return pd.DataFrame()

    return parse_sdmx_xml(r.content, indicator_id)


# ── Synthetic fallback ────────────────────────────────────────────────────────
def generate_sdmx_synthetic() -> pd.DataFrame:
    """
    Synthetic SDMX-structured data for offline development.
    Mirrors real SDMX output schema with OBS_STATUS codes.
    """
    import numpy as np
    rng = np.random.default_rng(seed=99)

    obs_statuses = ["", "E", "P", ""]   # actual, estimated, provisional
    countries = SDMX_COUNTRIES.split("+")
    rows = []

    for ind_id, ind_label in SDG4_INDICATORS.items():
        is_gpi = "GPIA" in ind_id
        for iso3 in countries:
            for year in range(int(START_PERIOD), int(END_PERIOD) + 1):
                if rng.random() < 0.18:
                    continue
                value = (
                    round(rng.uniform(0.75, 1.25), 4) if is_gpi
                    else round(rng.uniform(25.0, 98.0), 2)
                )
                rows.append({
                    "INDICATOR_ID":    ind_id,
                    "INDICATOR_LABEL": ind_label,
                    "ISO3":            iso3,
                    "YEAR":            year,
                    "VALUE":           value,
                    "OBS_STATUS":      rng.choice(obs_statuses),
                })

    df = pd.DataFrame(rows)
    log.info("Synthetic SDMX dataset: %s rows", len(df))
    return df


# ── Main entry ────────────────────────────────────────────────────────────────
def run(force: bool = False, use_synthetic: bool = False) -> pd.DataFrame:
    """
    Fetch SDMX data for all SDG 4 indicators (or load from cache).

    Parameters
    ----------
    force         : Re-fetch even if cached file exists.
    use_synthetic : Use synthetic data for offline development.
    """
    if SDMX_RAW_FILE.exists() and not force and not use_synthetic:
        log.info("Loading cached SDMX file: %s", SDMX_RAW_FILE)
        df = pd.read_csv(SDMX_RAW_FILE, dtype={"YEAR": "Int64"})
        log.info("Cached shape: %s rows × %s columns", *df.shape)
        return df

    if use_synthetic:
        log.warning("Using SYNTHETIC SDMX data — not real observations.")
        df = generate_sdmx_synthetic()
    else:
        session = requests.Session()
        session.headers.update({
            "Accept":     "application/vnd.sdmx.genericdata+xml;version=2.1",
            "User-Agent": "uis-education-data-pipeline/1.0",
        })

        frames = []
        for ind_id, ind_label in SDG4_INDICATORS.items():
            df_ind = fetch_sdmx_indicator(ind_id, session)
            if not df_ind.empty:
                df_ind["INDICATOR_LABEL"] = ind_label
                frames.append(df_ind)

        if frames:
            df = pd.concat(frames, ignore_index=True)
            log.info("SDMX total records: %s", len(df))
        else:
            log.warning("SDMX API returned no data — falling back to synthetic.")
            df = generate_sdmx_synthetic()

    # ── Save cache ────────────────────────────────────────────────────────────
    df.to_csv(SDMX_RAW_FILE, index=False)
    log.info("Saved to: %s", SDMX_RAW_FILE)
    log.info("Sample:\n%s", df.head(3).to_string(index=False))
    return df


if __name__ == "__main__":
    import sys
    synthetic = "--synthetic" in sys.argv
    run(use_synthetic=synthetic)
