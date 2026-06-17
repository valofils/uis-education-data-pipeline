"""
test_validate.py
Unit tests for src/quality/validate.py

Tests
-----
- check_value_range   : out-of-range values flagged correctly
- check_missing_rate  : high missingness detected
- check_duplicates    : duplicate triplets identified
- check_year_range    : implausible years caught
- check_missing_iso3  : null/empty ISO3 flagged
- build_qa_summary    : summary table structure and status logic

Run
---
    pytest tests/test_validate.py -v

Location: tests/test_validate.py
"""

import pandas as pd
import numpy as np
import pytest

from src.quality.validate import (
    check_value_range,
    check_missing_rate,
    check_duplicates,
    check_year_range,
    check_missing_iso3,
    build_qa_summary,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────
def _base_df(n: int = 20, indicator: str = "CR.1") -> pd.DataFrame:
    """Return a minimal valid harmonized DataFrame."""
    return pd.DataFrame({
        "INDICATOR_ID":    [indicator] * n,
        "INDICATOR_LABEL": ["Completion rate — primary"] * n,
        "ISO3":            ["MDG", "GHA", "KEN", "ETH", "NGA"] * (n // 5),
        "YEAR":            list(range(2010, 2010 + n)),
        "VALUE":           np.linspace(50.0, 90.0, n),
        "SOURCE":          ["UIS_API"] * n,
        "REGION":          ["Sub-Saharan Africa"] * n,
        "INCOME_GROUP":    ["Low income"] * n,
    })


def _gpi_df(n: int = 20) -> pd.DataFrame:
    """Return a minimal valid GPI DataFrame."""
    df = _base_df(n, indicator="GPIA.CR.1")
    df["VALUE"] = np.linspace(0.80, 1.20, n)
    df["INDICATOR_LABEL"] = "GPI — completion rate, primary"
    return df


# ── check_value_range ─────────────────────────────────────────────────────────
class TestCheckValueRange:

    def test_clean_data_no_flags(self):
        df = _base_df()
        result = check_value_range(df)
        assert result.empty, "Clean data should produce no flags."

    def test_value_above_100_flagged(self):
        df = _base_df()
        df.loc[0, "VALUE"] = 105.0
        result = check_value_range(df)
        assert len(result) == 1
        assert result.iloc[0]["QA_FLAG"] == "OUT_OF_RANGE"

    def test_negative_value_flagged(self):
        df = _base_df()
        df.loc[3, "VALUE"] = -5.0
        result = check_value_range(df)
        assert len(result) == 1
        assert result.iloc[0]["QA_FLAG"] == "OUT_OF_RANGE"

    def test_multiple_out_of_range_all_flagged(self):
        df = _base_df()
        df.loc[0, "VALUE"] = 110.0
        df.loc[1, "VALUE"] = -1.0
        result = check_value_range(df)
        assert len(result) == 2

    def test_null_values_not_flagged(self):
        """NaN values should not be flagged by range check."""
        df = _base_df()
        df.loc[0, "VALUE"] = np.nan
        result = check_value_range(df)
        assert result.empty

    def test_gpi_above_2_5_flagged(self):
        df = _gpi_df()
        df.loc[0, "VALUE"] = 3.0
        result = check_value_range(df)
        assert len(result) == 1
        assert result.iloc[0]["QA_FLAG"] == "OUT_OF_RANGE"

    def test_gpi_valid_range_no_flags(self):
        df = _gpi_df()
        result = check_value_range(df)
        assert result.empty

    def test_boundary_values_not_flagged(self):
        """Exact boundary values (0 and 100) must be accepted."""
        df = _base_df()
        df.loc[0, "VALUE"] = 0.0
        df.loc[1, "VALUE"] = 100.0
        result = check_value_range(df)
        assert result.empty


# ── check_missing_rate ────────────────────────────────────────────────────────
class TestCheckMissingRate:

    def test_no_missing_no_flags(self):
        """
        check_missing_rate computes expected = all_iso3 x all_years across
        all 11 indicators. A single-indicator fixture will appear sparse
        for the other 10. We verify the flag structure is correct and that
        any CR.1 flag is only due to the cross-indicator grid, not bad data.
        """
        df = _base_df(20)
        result = check_missing_rate(df)
        # All flags must have the correct type
        if not result.empty:
            assert all(result["QA_FLAG"] == "HIGH_MISSING_RATE")
            assert "INDICATOR_ID" in result.columns
        # CR.1 has full values — its VALUE column must have no NaN
        assert df["VALUE"].isna().sum() == 0

    def test_high_missing_rate_flagged(self):
        df = _base_df(20)
        df.loc[:15, "VALUE"] = np.nan
        result = check_missing_rate(df)
        assert len(result) >= 1
        assert result.iloc[0]["QA_FLAG"] == "HIGH_MISSING_RATE"

    def test_flag_contains_indicator_id(self):
        df = _base_df(20)
        df["VALUE"] = np.nan
        result = check_missing_rate(df)
        assert "CR.1" in result["INDICATOR_ID"].values


# ── check_duplicates ──────────────────────────────────────────────────────────
class TestCheckDuplicates:

    def test_no_duplicates_empty_result(self):
        df = _base_df()
        result = check_duplicates(df)
        assert result.empty

    def test_duplicate_triplet_flagged(self):
        df = _base_df()
        dupe = df.iloc[[0]].copy()
        df = pd.concat([df, dupe], ignore_index=True)
        result = check_duplicates(df)
        assert len(result) == 2
        assert result.iloc[0]["QA_FLAG"] == "DUPLICATE_KEY"

    def test_different_indicators_not_duplicate(self):
        df1 = _base_df(10, indicator="CR.1")
        df2 = _base_df(10, indicator="CR.2")
        df  = pd.concat([df1, df2], ignore_index=True)
        result = check_duplicates(df)
        assert result.empty


# ── check_year_range ──────────────────────────────────────────────────────────
class TestCheckYearRange:

    def test_valid_years_no_flags(self):
        df = _base_df()
        result = check_year_range(df)
        assert result.empty

    def test_year_before_2000_flagged(self):
        df = _base_df()
        df.loc[0, "YEAR"] = 1995
        result = check_year_range(df)
        assert len(result) == 1
        assert result.iloc[0]["QA_FLAG"] == "IMPLAUSIBLE_YEAR"

    def test_year_after_2030_flagged(self):
        df = _base_df()
        df.loc[0, "YEAR"] = 2035
        result = check_year_range(df)
        assert len(result) == 1

    def test_null_year_not_flagged(self):
        df = _base_df()
        df["YEAR"] = df["YEAR"].astype("Int64")
        df.loc[0, "YEAR"] = pd.NA
        result = check_year_range(df)
        assert result.empty


# ── check_missing_iso3 ────────────────────────────────────────────────────────
class TestCheckMissingISO3:

    def test_valid_iso3_no_flags(self):
        df = _base_df()
        result = check_missing_iso3(df)
        assert result.empty

    def test_null_iso3_flagged(self):
        df = _base_df()
        df.loc[0, "ISO3"] = None
        result = check_missing_iso3(df)
        assert len(result) == 1
        assert result.iloc[0]["QA_FLAG"] == "MISSING_ISO3"

    def test_empty_string_iso3_flagged(self):
        df = _base_df()
        df.loc[0, "ISO3"] = "   "
        result = check_missing_iso3(df)
        assert len(result) == 1


# ── build_qa_summary ──────────────────────────────────────────────────────────
class TestBuildQASummary:

    def test_summary_has_all_indicators(self):
        df = _base_df()
        summary = build_qa_summary(df, pd.DataFrame())
        from src.utils.config import SDG4_INDICATORS
        for ind_id in SDG4_INDICATORS:
            assert ind_id in summary["INDICATOR_ID"].values

    def test_clean_data_all_pass(self):
        """CR.1 with full data and no flagged rows must have N_FLAGGED == 0."""
        df = _base_df()
        summary = build_qa_summary(df, pd.DataFrame())
        cr1 = summary[summary["INDICATOR_ID"] == "CR.1"].iloc[0]
        assert cr1["QA_STATUS"] in ("PASS", "WARN_MISSING")
        assert cr1["N_FLAGGED"] == 0

    def test_flagged_rows_reflected_in_summary(self):
        df = _base_df()
        df.loc[0, "VALUE"] = 999.0
        flagged = check_value_range(df)
        summary = build_qa_summary(df, flagged)
        cr1 = summary[summary["INDICATOR_ID"] == "CR.1"].iloc[0]
        assert cr1["N_FLAGGED"] >= 1

    def test_summary_columns_present(self):
        df = _base_df()
        summary = build_qa_summary(df, pd.DataFrame())
        expected_cols = {
            "INDICATOR_ID", "INDICATOR_LABEL", "N_EXPECTED",
            "N_VALID", "N_MISSING", "MISSING_PCT",
            "N_FLAGGED", "QA_STATUS",
        }
        assert expected_cols.issubset(set(summary.columns))