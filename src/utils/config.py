"""
config.py
Central configuration: paths, constants, UIS indicator catalogue.
Location: src/utils/config.py
"""

import os
from pathlib import Path

# ── Root ──────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parents[2]   # project root

# ── Data directories ──────────────────────────────────────────────────────────
DATA_RAW_DIR       = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"

# ── Output directories ────────────────────────────────────────────────────────
OUTPUTS_REPORTS_DIR = ROOT_DIR / "outputs" / "reports"
OUTPUTS_EXPORTS_DIR = ROOT_DIR / "outputs" / "exports"

# ── Ensure all directories exist on import ────────────────────────────────────
for _dir in [
    DATA_RAW_DIR,
    DATA_PROCESSED_DIR,
    OUTPUTS_REPORTS_DIR,
    OUTPUTS_EXPORTS_DIR,
]:
    _dir.mkdir(parents=True, exist_ok=True)

# ── UIS Bulk Data Download Base URL ──────────────────────────────────────────
# UIS publishes annual bulk CSV datasets at this endpoint.
UIS_BULK_BASE_URL = "https://uis.unesco.org/sites/default/files/documents/"

# ── SDMX endpoint (UNESCO UIS) ────────────────────────────────────────────────
# REST endpoint following SDMX 2.1 standard.
SDMX_BASE_URL = "https://sdmx.uis.unesco.org/ws/rest"

# ── SDG 4 Core Indicators ─────────────────────────────────────────────────────
# Each entry: indicator_id -> human-readable label
SDG4_INDICATORS = {
    # Target 4.1 — Free, equitable, quality primary and secondary education
    "CR.1":   "Completion rate — primary education",
    "CR.2":   "Completion rate — lower secondary education",
    "CR.3":   "Completion rate — upper secondary education",
    "ROFST.1": "Out-of-school rate — primary",
    "ROFST.2": "Out-of-school rate — lower secondary",
    "ROFST.3": "Out-of-school rate — upper secondary",

    # Target 4.2 — Early childhood development
    "PPPRT.1": "Pre-primary participation rate (gross)",

    # Target 4.5 — Gender parity and equity
    "GPIA.CR.1": "GPI — completion rate, primary",
    "GPIA.CR.2": "GPI — completion rate, lower secondary",

    # Target 4.c — Trained and qualified teachers
    "TRTP.1": "Proportion of trained teachers — primary",
    "TRTP.2": "Proportion of trained teachers — lower secondary",
}

# ── Data Quality Thresholds ───────────────────────────────────────────────────
QA_CONFIG = {
    "max_missing_pct":     30.0,   # flag indicator series with >30% missing
    "rate_min":             0.0,   # percentage indicators must be >= 0
    "rate_max":           100.0,   # percentage indicators must be <= 100
    "gpi_min":              0.0,   # gender parity index floor
    "gpi_max":              2.5,   # gender parity index ceiling
    "year_min":            2000,   # earliest plausible data year
    "year_max":            2030,   # latest plausible data year
    "anomaly_contamination": 0.05, # IsolationForest expected outlier fraction
}

# ── Imputation Settings ───────────────────────────────────────────────────────
IMPUTATION_CONFIG = {
    "method":      "knn",   # 'knn' | 'iterative'
    "knn_neighbors": 5,
    "max_iter":     10,     # for iterative imputer
    "random_state": 42,
}

# ── Metadata ──────────────────────────────────────────────────────────────────
METADATA_FILE = DATA_PROCESSED_DIR / "metadata_registry.json"

# ── Export formats ────────────────────────────────────────────────────────────
EXPORT_FORMATS = ["csv", "json", "xlsx"]

# ── ISO 3166-1 alpha-3 — small reference subset for validation ────────────────
# Full list loaded dynamically; this is used for fast smoke-tests.
KNOWN_ISO3 = {
    "MDG", "GHA", "KEN", "ETH", "NGA", "ZAF", "MAR", "EGY",
    "BRA", "MEX", "COL", "ARG", "IND", "BGD", "PAK", "NPL",
    "FRA", "DEU", "GBR", "ITA", "ESP", "USA", "CAN", "AUS",
    "CHN", "JPN", "KOR", "IDN", "VNM", "THA",
}

# ── Logging format ────────────────────────────────────────────────────────────
LOG_FORMAT  = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"
