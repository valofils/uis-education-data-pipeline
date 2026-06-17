# UIS Education Data Pipeline

A modular Python pipeline for integrating, validating, and disseminating global education indicators aligned with **SDG 4**, built on UNESCO Institute for Statistics (UIS) public data.

---

## Overview

This project demonstrates end-to-end data engineering competencies for education statistics:

- **Multi-source data integration** from UIS bulk datasets and SDMX endpoints
- **Metadata governance** aligned with international standards (SDMX 2.1)
- **Data quality assurance** through rules-based validation and ML anomaly detection
- **Statistical imputation** for missing indicator values
- **Interactive dissemination** via a Streamlit dashboard
- **Structured exports** in CSV, JSON, and Excel formats

---

## Project Structure

```
uis-education-data-pipeline/
│
├── data/
│   ├── raw/                        # Downloaded source files (git-ignored)
│   └── processed/                  # Cleaned, integrated outputs (git-ignored)
│
├── src/
│   ├── ingestion/
│   │   ├── fetch_uis.py            # UIS bulk CSV downloader
│   │   └── fetch_sdmx.py           # SDMX endpoint parser
│   ├── integration/
│   │   ├── harmonize.py            # Country/year alignment, schema mapping
│   │   └── merge_sources.py        # Multi-source merge logic
│   ├── quality/
│   │   ├── validate.py             # Rules-based QA checks
│   │   └── anomaly.py              # ML anomaly detection (IsolationForest)
│   ├── imputation/
│   │   └── impute.py               # KNN / iterative imputation
│   ├── metadata/
│   │   └── metadata_manager.py     # SDMX-aligned metadata registry
│   ├── dissemination/
│   │   ├── dashboard.py            # Streamlit interactive dashboard
│   │   └── export.py               # CSV / JSON / Excel export
│   └── utils/
│       └── config.py               # Paths, constants, indicator catalogue
│
├── outputs/
│   ├── reports/                    # QA and processing reports (git-ignored)
│   └── exports/                    # Final data exports (git-ignored)
│
├── tests/
│   └── test_validate.py            # Unit tests for QA module
│
├── .gitignore
├── README.md
└── requirements.txt
```

---

## SDG 4 Indicators Covered

| Indicator ID   | Description                                      |
|----------------|--------------------------------------------------|
| CR.1–CR.3      | Completion rates — primary to upper secondary    |
| ROFST.1–3      | Out-of-school rates — primary to upper secondary |
| PPPRT.1        | Pre-primary participation rate (gross)           |
| GPIA.CR.1–2    | Gender Parity Index — completion rates           |
| TRTP.1–2       | Proportion of trained teachers                   |

---

## Setup

### Prerequisites

- Python 3.12
- Git

### Installation

```powershell
# Clone the repository
git clone https://github.com/valofils/uis-education-data-pipeline.git
cd uis-education-data-pipeline

# Create and activate virtual environment
python -m venv venv --without-pip
.\venv\Scripts\Activate.ps1
Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py
python get-pip.py
Remove-Item get-pip.py

# Install dependencies
python -m pip install -r requirements.txt
```

---

## Usage

### 1. Ingest UIS bulk data

```powershell
python -m src.ingestion.fetch_uis
```

### 2. Parse SDMX endpoint

```powershell
python -m src.ingestion.fetch_sdmx
```

### 3. Harmonize and merge sources

```powershell
python -m src.integration.harmonize
python -m src.integration.merge_sources
```

### 4. Run data quality checks

```powershell
python -m src.quality.validate
python -m src.quality.anomaly
```

### 5. Impute missing values

```powershell
python -m src.imputation.impute
```

### 6. Launch dissemination dashboard

```powershell
streamlit run src/dissemination/dashboard.py
```

### 7. Export data

```powershell
python -m src.dissemination.export
```

---

## Technical Stack

| Layer             | Tools                                         |
|-------------------|-----------------------------------------------|
| Language          | Python 3.12                                   |
| Data processing   | pandas, numpy                                 |
| SDMX integration  | pandaSDMX                                     |
| ML / QA           | scikit-learn (IsolationForest, KNNImputer)    |
| Dissemination     | Streamlit, Plotly                             |
| Export            | openpyxl, JSON, CSV                           |
| Testing           | pytest                                        |

---

## Data Source

All data originates from the **UNESCO Institute for Statistics (UIS)** public data portal:
[https://uis.unesco.org/en/bdds/education](https://uis.unesco.org/en/bdds/education)

Data is used strictly for non-commercial, analytical demonstration purposes in alignment with UIS open data policies.

---

## Author

**Mariel Andrianavalondrahona**
MSc Mathematics — AIMS Ghana, 2026
GitHub: [valofils](https://github.com/valofils)
