"""
metadata_manager.py
Build, update, and query a structured metadata registry for SDG 4 indicators.

Aligned with SDMX 2.1 metadata concepts:
    - ConceptScheme  : indicator definitions and measurement units
    - CodeList       : valid values for categorical dimensions
    - DataStructure  : dimension and attribute descriptions
    - ProcessHistory : data lineage and processing steps

Output
------
data/processed/metadata_registry.json

Location: src/metadata/metadata_manager.py
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from src.utils.config import (
    METADATA_FILE,
    SDG4_INDICATORS,
    LOG_FORMAT,
    LOG_DATE_FMT,
)

# ── Logger ────────────────────────────────────────────────────────────────────
logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FMT, level=logging.INFO)
log = logging.getLogger(__name__)


# ── Metadata structures ───────────────────────────────────────────────────────
def build_concept_scheme() -> dict:
    """
    SDMX ConceptScheme: defines each indicator's concept, unit, and SDG target.
    """
    concepts = {}

    indicator_meta = {
        "CR.1": {
            "sdg_target":  "4.1",
            "unit":        "Percentage",
            "measurement": "Proportion of children who complete primary education",
            "disagg":      ["sex", "location", "wealth_quintile"],
            "source_org":  "UNESCO UIS",
        },
        "CR.2": {
            "sdg_target":  "4.1",
            "unit":        "Percentage",
            "measurement": "Proportion of youth who complete lower secondary education",
            "disagg":      ["sex", "location", "wealth_quintile"],
            "source_org":  "UNESCO UIS",
        },
        "CR.3": {
            "sdg_target":  "4.1",
            "unit":        "Percentage",
            "measurement": "Proportion of youth who complete upper secondary education",
            "disagg":      ["sex", "location", "wealth_quintile"],
            "source_org":  "UNESCO UIS",
        },
        "ROFST.1": {
            "sdg_target":  "4.1",
            "unit":        "Percentage",
            "measurement": "Proportion of primary-school-age children out of school",
            "disagg":      ["sex", "location"],
            "source_org":  "UNESCO UIS",
        },
        "ROFST.2": {
            "sdg_target":  "4.1",
            "unit":        "Percentage",
            "measurement": "Proportion of lower-secondary-age youth out of school",
            "disagg":      ["sex", "location"],
            "source_org":  "UNESCO UIS",
        },
        "ROFST.3": {
            "sdg_target":  "4.1",
            "unit":        "Percentage",
            "measurement": "Proportion of upper-secondary-age youth out of school",
            "disagg":      ["sex", "location"],
            "source_org":  "UNESCO UIS",
        },
        "PPPRT.1": {
            "sdg_target":  "4.2",
            "unit":        "Percentage",
            "measurement": "Gross enrolment ratio in pre-primary education",
            "disagg":      ["sex"],
            "source_org":  "UNESCO UIS",
        },
        "GPIA.CR.1": {
            "sdg_target":  "4.5",
            "unit":        "Index (0–2.5)",
            "measurement": "Gender Parity Index for primary completion rate",
            "disagg":      [],
            "source_org":  "UNESCO UIS",
            "note":        "GPI > 1 favours females; GPI < 1 favours males",
        },
        "GPIA.CR.2": {
            "sdg_target":  "4.5",
            "unit":        "Index (0–2.5)",
            "measurement": "Gender Parity Index for lower secondary completion rate",
            "disagg":      [],
            "source_org":  "UNESCO UIS",
            "note":        "GPI > 1 favours females; GPI < 1 favours males",
        },
        "TRTP.1": {
            "sdg_target":  "4.c",
            "unit":        "Percentage",
            "measurement": "Proportion of primary teachers who are trained",
            "disagg":      ["sex"],
            "source_org":  "UNESCO UIS",
        },
        "TRTP.2": {
            "sdg_target":  "4.c",
            "unit":        "Percentage",
            "measurement": "Proportion of lower secondary teachers who are trained",
            "disagg":      ["sex"],
            "source_org":  "UNESCO UIS",
        },
    }

    for ind_id, label in SDG4_INDICATORS.items():
        meta = indicator_meta.get(ind_id, {})
        concepts[ind_id] = {
            "id":          ind_id,
            "label":       label,
            "sdg_target":  meta.get("sdg_target", ""),
            "unit":        meta.get("unit", "Percentage"),
            "measurement": meta.get("measurement", ""),
            "disaggregations": meta.get("disagg", []),
            "source_organisation": meta.get("source_org", "UNESCO UIS"),
            "note":        meta.get("note", ""),
        }

    return {
        "id":          "UIS_SDG4_CONCEPTS",
        "name":        "UNESCO UIS SDG 4 Indicator Concept Scheme",
        "version":     "1.0",
        "agency":      "UNESCO UIS",
        "valid_from":  "2010-01-01",
        "concepts":    concepts,
    }


def build_codelists() -> dict:
    """
    SDMX CodeLists: valid codes for categorical dimensions.
    """
    return {
        "CL_AREA": {
            "id":          "CL_AREA",
            "name":        "Reference Area (ISO 3166-1 alpha-3)",
            "description": "Country codes used as the geographic dimension.",
            "codes": {
                "MDG": "Madagascar",
                "GHA": "Ghana",
                "KEN": "Kenya",
                "ETH": "Ethiopia",
                "NGA": "Nigeria",
                "ZAF": "South Africa",
                "MAR": "Morocco",
                "EGY": "Egypt",
                "BRA": "Brazil",
                "MEX": "Mexico",
                "COL": "Colombia",
                "IND": "India",
                "BGD": "Bangladesh",
                "PAK": "Pakistan",
                "NPL": "Nepal",
                "FRA": "France",
                "DEU": "Germany",
                "GBR": "United Kingdom",
                "USA": "United States",
                "CAN": "Canada",
                "CHN": "China",
                "JPN": "Japan",
                "IDN": "Indonesia",
                "VNM": "Viet Nam",
            },
        },
        "CL_OBS_STATUS": {
            "id":   "CL_OBS_STATUS",
            "name": "Observation Status",
            "codes": {
                "":  "Actual observation",
                "E": "Estimated",
                "P": "Provisional",
                "M": "Missing",
                "I": "Imputed (pipeline)",
            },
        },
        "CL_FREQ": {
            "id":   "CL_FREQ",
            "name": "Frequency",
            "codes": {
                "A": "Annual",
            },
        },
    }


def build_data_structure() -> dict:
    """
    SDMX DataStructureDefinition: dimensions and attributes.
    """
    return {
        "id":   "DSD_UIS_SDG4",
        "name": "Data Structure Definition — UIS SDG 4",
        "dimensions": [
            {"id": "INDICATOR_ID", "concept": "Indicator",      "codelist": "UIS_SDG4_CONCEPTS"},
            {"id": "REF_AREA",     "concept": "Reference Area",  "codelist": "CL_AREA"},
            {"id": "TIME_PERIOD",  "concept": "Time Period",      "codelist": None, "type": "integer"},
        ],
        "attributes": [
            {"id": "OBS_STATUS",   "concept": "Observation Status", "codelist": "CL_OBS_STATUS"},
            {"id": "UNIT_MEASURE", "concept": "Unit of Measure",    "codelist": None},
            {"id": "SOURCE",       "concept": "Data Source",        "codelist": None},
        ],
        "primary_measure": {
            "id":      "OBS_VALUE",
            "concept": "Observation Value",
            "type":    "float",
        },
    }


def build_process_history() -> list:
    """
    Data lineage: ordered list of processing steps applied in this pipeline.
    """
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    return [
        {
            "step":        1,
            "name":        "Data Ingestion — UIS API",
            "module":      "src.ingestion.fetch_uis",
            "description": "Attempted live fetch from UIS REST API; fell back to synthetic data.",
            "timestamp":   now,
        },
        {
            "step":        2,
            "name":        "Data Ingestion — SDMX",
            "module":      "src.ingestion.fetch_sdmx",
            "description": "Attempted SDMX 2.1 endpoint query; fell back to synthetic data.",
            "timestamp":   now,
        },
        {
            "step":        3,
            "name":        "Harmonization",
            "module":      "src.integration.harmonize",
            "description": "Schema alignment, ISO3 validation, year range enforcement, region enrichment.",
            "timestamp":   now,
        },
        {
            "step":        4,
            "name":        "Source Merge",
            "module":      "src.integration.merge_sources",
            "description": "Deduplication and pivot to wide analytical table; coverage statistics computed.",
            "timestamp":   now,
        },
        {
            "step":        5,
            "name":        "QA Validation",
            "module":      "src.quality.validate",
            "description": "Rules-based checks: value ranges, missing rates, duplicates, year plausibility.",
            "timestamp":   now,
        },
        {
            "step":        6,
            "name":        "Anomaly Detection",
            "module":      "src.quality.anomaly",
            "description": "IsolationForest applied per indicator; ~5% contamination rate.",
            "timestamp":   now,
        },
        {
            "step":        7,
            "name":        "Imputation",
            "module":      "src.imputation.impute",
            "description": "KNN imputation (k=5) applied to wide table; values clipped to valid ranges.",
            "timestamp":   now,
        },
    ]


def build_registry() -> dict:
    """Assemble the full metadata registry."""
    return {
        "registry_id":     "UIS_SDG4_METADATA",
        "version":         "1.0",
        "created":         datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "description":     (
            "SDMX-aligned metadata registry for the UIS Education Data Pipeline. "
            "Covers SDG 4 indicators: concept schemes, code lists, "
            "data structure definitions, and process history."
        ),
        "concept_scheme":  build_concept_scheme(),
        "codelists":       build_codelists(),
        "data_structure":  build_data_structure(),
        "process_history": build_process_history(),
    }


# ── Query helpers ─────────────────────────────────────────────────────────────
def get_indicator_meta(registry: dict, indicator_id: str) -> dict:
    """Return concept metadata for a single indicator."""
    return (
        registry
        .get("concept_scheme", {})
        .get("concepts", {})
        .get(indicator_id, {})
    )


def get_process_history(registry: dict) -> list:
    """Return the ordered list of processing steps."""
    return registry.get("process_history", [])


# ── Main entry ────────────────────────────────────────────────────────────────
def run() -> dict:
    """Build the metadata registry and save to JSON."""
    log.info("Building SDMX-aligned metadata registry ...")
    registry = build_registry()

    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    log.info("Metadata registry saved to: %s", METADATA_FILE)
    log.info("Concepts defined    : %s", len(registry["concept_scheme"]["concepts"]))
    log.info("Codelists defined   : %s", len(registry["codelists"]))
    log.info("Process steps logged: %s", len(registry["process_history"]))

    # ── Sample output ─────────────────────────────────────────────────────────
    sample = get_indicator_meta(registry, "CR.1")
    log.info("Sample — CR.1 metadata:")
    for k, v in sample.items():
        log.info("  %-22s: %s", k, v)

    return registry


if __name__ == "__main__":
    run()
