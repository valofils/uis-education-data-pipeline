"""
anomaly.py
ML-based anomaly detection for harmonized education indicator data.

Method
------
IsolationForest (scikit-learn) applied per indicator.
Features used: VALUE, YEAR, and one-hot encoded REGION.
Anomaly scores and binary flags are appended to the dataset.

Outputs
-------
- outputs/reports/anomaly_report.csv   : flagged anomalies with scores
- data/processed/harmonized_flagged.csv: full dataset with anomaly columns

Location: src/quality/anomaly.py
"""

import logging
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import OneHotEncoder

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

HARMONIZED_FILE  = DATA_PROCESSED_DIR / "harmonized.csv"
FLAGGED_FILE     = DATA_PROCESSED_DIR / "harmonized_flagged.csv"
ANOMALY_REPORT   = OUTPUTS_REPORTS_DIR / "anomaly_report.csv"

CONTAMINATION    = QA_CONFIG["anomaly_contamination"]   # 0.05
RANDOM_STATE     = 42
MIN_SAMPLES      = 20   # skip indicator if fewer observations


# ── Feature engineering ───────────────────────────────────────────────────────
def build_features(subset: pd.DataFrame) -> np.ndarray | None:
    """
    Build feature matrix for IsolationForest from one indicator's subset.

    Features
    --------
    - VALUE (normalised 0–1 within indicator)
    - YEAR  (normalised 0–1 within indicator)
    - REGION one-hot encoded

    Returns None if the subset is too small.
    """
    subset = subset.dropna(subset=["VALUE", "YEAR"]).copy()

    if len(subset) < MIN_SAMPLES:
        return None, None

    # Normalise VALUE and YEAR to [0, 1]
    for col in ["VALUE", "YEAR"]:
        col_min = subset[col].min()
        col_max = subset[col].max()
        rng     = col_max - col_min
        subset[f"{col}_NORM"] = (
            (subset[col] - col_min) / rng if rng > 0 else 0.0
        )

    numeric = subset[["VALUE_NORM", "YEAR_NORM"]].values

    # One-hot encode REGION if present
    if "REGION" in subset.columns and subset["REGION"].notna().any():
        enc = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
        region_encoded = enc.fit_transform(subset[["REGION"]])
        features = np.hstack([numeric, region_encoded])
    else:
        features = numeric

    return features, subset.index


# ── Anomaly detection per indicator ──────────────────────────────────────────
def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run IsolationForest on each SDG 4 indicator separately.

    Adds two columns to df:
        ANOMALY_SCORE : float  — lower = more anomalous
        IS_ANOMALY    : bool   — True if flagged as outlier
    """
    df = df.copy()
    df["ANOMALY_SCORE"] = np.nan
    df["IS_ANOMALY"]    = False

    summary = []

    for ind_id in SDG4_INDICATORS:
        subset = df[df["INDICATOR_ID"] == ind_id].copy()

        features, valid_idx = build_features(subset)

        if features is None:
            log.warning(
                "Skipping %s — fewer than %s valid observations.",
                ind_id, MIN_SAMPLES,
            )
            continue

        clf = IsolationForest(
            contamination=CONTAMINATION,
            random_state=RANDOM_STATE,
            n_estimators=100,
        )
        clf.fit(features)

        scores     = clf.score_samples(features)   # lower = more anomalous
        predictions = clf.predict(features)        # -1 = anomaly, 1 = normal

        df.loc[valid_idx, "ANOMALY_SCORE"] = np.round(scores, 6)
        df.loc[valid_idx, "IS_ANOMALY"]    = predictions == -1

        n_anomalies = int((predictions == -1).sum())
        n_total     = len(valid_idx)

        log.info(
            "%-12s | %s obs | %s anomalies (%.1f%%)",
            ind_id,
            n_total,
            n_anomalies,
            n_anomalies / n_total * 100,
        )

        summary.append({
            "INDICATOR_ID":    ind_id,
            "INDICATOR_LABEL": SDG4_INDICATORS[ind_id],
            "N_OBSERVATIONS":  n_total,
            "N_ANOMALIES":     n_anomalies,
            "ANOMALY_RATE_PCT": round(n_anomalies / n_total * 100, 2),
        })

    return df, pd.DataFrame(summary)


# ── Main entry ────────────────────────────────────────────────────────────────
def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load harmonized data, run anomaly detection, save outputs.

    Returns
    -------
    (full_df_with_flags, anomaly_summary)
    """
    if not HARMONIZED_FILE.exists():
        log.info("Harmonized file not found — running pipeline first.")
        from src.integration.harmonize import run as harmonize_run
        harmonize_run()

    log.info("Loading: %s", HARMONIZED_FILE)
    df = pd.read_csv(HARMONIZED_FILE, dtype={"YEAR": "Int64"})
    log.info("Loaded: %s rows × %s columns.", *df.shape)

    # ── Run detection ─────────────────────────────────────────────────────────
    log.info("Running IsolationForest anomaly detection ...")
    log.info("Contamination rate: %.2f", CONTAMINATION)
    log.info("=" * 58)

    df_flagged, summary = detect_anomalies(df)

    log.info("=" * 58)

    # ── Save full flagged dataset ─────────────────────────────────────────────
    df_flagged.to_csv(FLAGGED_FILE, index=False)
    log.info("Flagged dataset saved to: %s", FLAGGED_FILE)

    # ── Save anomaly report ───────────────────────────────────────────────────
    anomalies_only = df_flagged[df_flagged["IS_ANOMALY"] == True].copy()
    anomalies_only = anomalies_only.sort_values("ANOMALY_SCORE")

    report_cols = [
        "INDICATOR_ID", "INDICATOR_LABEL", "ISO3", "YEAR",
        "VALUE", "ANOMALY_SCORE", "REGION", "INCOME_GROUP",
    ]
    report_cols = [c for c in report_cols if c in anomalies_only.columns]
    anomalies_only[report_cols].to_csv(ANOMALY_REPORT, index=False)
    log.info("Anomaly report saved to: %s", ANOMALY_REPORT)

    # ── Print summary ─────────────────────────────────────────────────────────
    total_anomalies = int(df_flagged["IS_ANOMALY"].sum())
    log.info("=" * 58)
    log.info("ANOMALY DETECTION SUMMARY")
    log.info("=" * 58)
    for _, row in summary.iterrows():
        log.info(
            "%-12s | %s obs | %s anomalies | %.1f%%",
            row["INDICATOR_ID"],
            str(row["N_OBSERVATIONS"]).rjust(4),
            str(row["N_ANOMALIES"]).rjust(3),
            row["ANOMALY_RATE_PCT"],
        )
    log.info("=" * 58)
    log.info("Total anomalies flagged: %s", total_anomalies)

    return df_flagged, summary


if __name__ == "__main__":
    run()
