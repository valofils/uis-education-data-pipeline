"""
dashboard.py
Interactive Streamlit dashboard for SDG 4 education indicator dissemination.

Sections
--------
1. Overview     : key metrics and dataset summary
2. Trends       : time-series line charts per indicator and country
3. Equity       : gender parity index visualisation by region
4. Coverage Map : data coverage heatmap by indicator and country
5. Data Table   : filterable, downloadable data table
6. QA & Process : quality report and pipeline process history

Run
---
    streamlit run src/dissemination/dashboard.py

Location: src/dissemination/dashboard.py
"""

import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT            = Path(__file__).resolve().parents[2]
IMPUTED_FILE    = ROOT / "data"    / "processed" / "imputed_wide.csv"
HARMONIZED_FILE = ROOT / "data"    / "processed" / "harmonized.csv"
COVERAGE_FILE   = ROOT / "outputs" / "reports"   / "coverage_stats.csv"
QA_REPORT_FILE  = ROOT / "outputs" / "reports"   / "qa_report.csv"
ANOMALY_FILE    = ROOT / "outputs" / "reports"   / "anomaly_report.csv"
METADATA_FILE   = ROOT / "data"    / "processed" / "metadata_registry.json"

# ── Indicator catalogue ───────────────────────────────────────────────────────
SDG4_INDICATORS = {
    "CR.1":      "Completion rate — primary",
    "CR.2":      "Completion rate — lower secondary",
    "CR.3":      "Completion rate — upper secondary",
    "ROFST.1":   "Out-of-school rate — primary",
    "ROFST.2":   "Out-of-school rate — lower secondary",
    "ROFST.3":   "Out-of-school rate — upper secondary",
    "PPPRT.1":   "Pre-primary participation rate",
    "GPIA.CR.1": "GPI — completion rate, primary",
    "GPIA.CR.2": "GPI — completion rate, lower secondary",
    "TRTP.1":    "Trained teachers — primary (%)",
    "TRTP.2":    "Trained teachers — lower secondary (%)",
}

GPI_INDICATORS = {"GPIA.CR.1", "GPIA.CR.2"}

# ── UIS brand colours ─────────────────────────────────────────────────────────
C_BLUE    = "#0072BC"
C_TEAL    = "#009EDB"
C_ORANGE  = "#E5843A"
C_GREEN   = "#00A651"
C_RED     = "#CC0000"
C_GREY    = "#6C757D"


# ── Data loaders ──────────────────────────────────────────────────────────────
@st.cache_data
def load_wide() -> pd.DataFrame:
    if not IMPUTED_FILE.exists():
        st.error("Imputed data not found. Run the pipeline first.")
        st.stop()
    return pd.read_csv(IMPUTED_FILE, dtype={"YEAR": int})


@st.cache_data
def load_long() -> pd.DataFrame:
    if not HARMONIZED_FILE.exists():
        st.error("Harmonized data not found. Run the pipeline first.")
        st.stop()
    df = pd.read_csv(HARMONIZED_FILE, dtype={"YEAR": int})
    df["INDICATOR_LABEL"] = df["INDICATOR_ID"].map(SDG4_INDICATORS)
    return df


@st.cache_data
def load_coverage() -> pd.DataFrame:
    return pd.read_csv(COVERAGE_FILE) if COVERAGE_FILE.exists() else pd.DataFrame()


@st.cache_data
def load_qa() -> pd.DataFrame:
    return pd.read_csv(QA_REPORT_FILE) if QA_REPORT_FILE.exists() else pd.DataFrame()


@st.cache_data
def load_anomalies() -> pd.DataFrame:
    return pd.read_csv(ANOMALY_FILE) if ANOMALY_FILE.exists() else pd.DataFrame()


@st.cache_data
def load_metadata() -> dict:
    if not METADATA_FILE.exists():
        return {}
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UIS SDG 4 Dashboard",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f0f4f8;
        border-left: 4px solid #0072BC;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .metric-card h3 { margin: 0; font-size: 1.6rem; color: #0072BC; }
    .metric-card p  { margin: 0; font-size: 0.85rem; color: #555; }
    .section-title  { color: #0072BC; border-bottom: 2px solid #0072BC;
                      padding-bottom: 4px; margin-top: 24px; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://uis.unesco.org/sites/default/files/uis_logo.png",
        width=180,
    )
    st.markdown("### UIS SDG 4 Data Pipeline")
    st.markdown(
        "Interactive dashboard for global education indicator "
        "dissemination aligned with SDG 4 monitoring."
    )
    st.divider()

    section = st.radio(
        "Navigate",
        ["📊 Overview", "📈 Trends", "⚖️ Equity (GPI)",
         "🗺️ Coverage", "📋 Data Table", "🔍 QA & Process"],
    )
    st.divider()
    st.caption("Data: UNESCO UIS (synthetic demo)")
    st.caption("Pipeline: UIS Education Data Pipeline v1.0")


# ── Load data ─────────────────────────────────────────────────────────────────
df_wide  = load_wide()
df_long  = load_long()
coverage = load_coverage()
qa       = load_qa()
anomalies = load_anomalies()
metadata  = load_metadata()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if section == "📊 Overview":
    st.title("📚 SDG 4 Education Indicators — Global Dashboard")
    st.markdown(
        "Monitoring progress toward **Sustainable Development Goal 4**: "
        "Ensure inclusive and equitable quality education and promote "
        "lifelong learning opportunities for all."
    )

    # ── Key metrics ───────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""<div class="metric-card">
            <h3>{df_wide['ISO3'].nunique()}</h3>
            <p>Countries covered</p></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card">
            <h3>{len(SDG4_INDICATORS)}</h3>
            <p>SDG 4 indicators</p></div>""", unsafe_allow_html=True)
    with col3:
        yr_range = f"{int(df_wide['YEAR'].min())}–{int(df_wide['YEAR'].max())}"
        st.markdown(f"""<div class="metric-card">
            <h3>{yr_range}</h3>
            <p>Time period</p></div>""", unsafe_allow_html=True)
    with col4:
        n_obs = df_long["VALUE"].notna().sum()
        st.markdown(f"""<div class="metric-card">
            <h3>{n_obs:,}</h3>
            <p>Observations</p></div>""", unsafe_allow_html=True)

    st.divider()

    # ── Coverage bar chart ────────────────────────────────────────────────────
    st.markdown('<h3 class="section-title">Indicator Coverage</h3>',
                unsafe_allow_html=True)

    if not coverage.empty:
        fig = px.bar(
            coverage,
            x="INDICATOR_ID",
            y="COVERAGE_PCT",
            color="COVERAGE_PCT",
            color_continuous_scale=[[0, C_RED], [0.7, C_ORANGE], [1, C_GREEN]],
            labels={"COVERAGE_PCT": "Coverage (%)", "INDICATOR_ID": "Indicator"},
            text="COVERAGE_PCT",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(
            height=380, showlegend=False,
            coloraxis_showscale=False,
            plot_bgcolor="white",
            yaxis=dict(range=[0, 110], gridcolor="#eee"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Region breakdown ──────────────────────────────────────────────────────
    st.markdown('<h3 class="section-title">Countries by Region</h3>',
                unsafe_allow_html=True)

    region_counts = (
        df_wide.drop_duplicates("ISO3")["REGION"]
        .value_counts()
        .reset_index()
        .rename(columns={"count": "N_COUNTRIES"})
    )
    fig2 = px.pie(
        region_counts, names="REGION", values="N_COUNTRIES",
        color_discrete_sequence=px.colors.qualitative.Safe,
        hole=0.4,
    )
    fig2.update_layout(height=340)
    st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — TRENDS
# ══════════════════════════════════════════════════════════════════════════════
elif section == "📈 Trends":
    st.title("📈 Indicator Trends Over Time")

    col1, col2 = st.columns(2)
    with col1:
        ind_choice = st.selectbox(
            "Indicator",
            options=list(SDG4_INDICATORS.keys()),
            format_func=lambda x: f"{x} — {SDG4_INDICATORS[x]}",
        )
    with col2:
        all_countries = sorted(df_wide["ISO3"].unique().tolist())
        country_choice = st.multiselect(
            "Countries", all_countries,
            default=["MDG", "GHA", "IND", "BRA", "FRA"],
        )

    if not country_choice:
        st.info("Select at least one country.")
    else:
        plot_df = df_wide[df_wide["ISO3"].isin(country_choice)][
            ["ISO3", "YEAR", "REGION", ind_choice]
        ].dropna(subset=[ind_choice])

        is_gpi = ind_choice in GPI_INDICATORS
        y_label = "Index value" if is_gpi else "Percentage (%)"

        fig = px.line(
            plot_df, x="YEAR", y=ind_choice,
            color="ISO3", markers=True,
            labels={"YEAR": "Year", ind_choice: y_label, "ISO3": "Country"},
            title=f"{ind_choice} — {SDG4_INDICATORS[ind_choice]}",
            color_discrete_sequence=px.colors.qualitative.Plotly,
        )

        if is_gpi:
            fig.add_hline(
                y=1.0, line_dash="dash", line_color=C_GREY,
                annotation_text="Parity (GPI = 1)",
                annotation_position="bottom right",
            )

        fig.update_layout(
            height=460, plot_bgcolor="white",
            xaxis=dict(gridcolor="#eee", dtick=1),
            yaxis=dict(gridcolor="#eee"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── Regional average ──────────────────────────────────────────────────
        st.markdown("##### Regional average trend")
        reg_avg = (
            df_wide.groupby(["REGION", "YEAR"])[ind_choice]
            .mean().reset_index()
        )
        fig2 = px.line(
            reg_avg, x="YEAR", y=ind_choice, color="REGION",
            labels={"YEAR": "Year", ind_choice: y_label},
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig2.update_layout(
            height=360, plot_bgcolor="white",
            xaxis=dict(gridcolor="#eee"), yaxis=dict(gridcolor="#eee"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — EQUITY (GPI)
# ══════════════════════════════════════════════════════════════════════════════
elif section == "⚖️ Equity (GPI)":
    st.title("⚖️ Gender Parity in Education")
    st.markdown(
        "The **Gender Parity Index (GPI)** measures female-to-male ratio. "
        "GPI = 1 indicates parity; < 1 favours males; > 1 favours females."
    )

    year_sel = st.slider(
        "Select year", int(df_wide["YEAR"].min()),
        int(df_wide["YEAR"].max()), int(df_wide["YEAR"].max()),
    )

    gpi_df = df_wide[df_wide["YEAR"] == year_sel][
        ["ISO3", "REGION", "INCOME_GROUP", "GPIA.CR.1", "GPIA.CR.2"]
    ].dropna(subset=["GPIA.CR.1"])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**GPI — Primary Completion ({year_sel})**")
        fig = px.bar(
            gpi_df.sort_values("GPIA.CR.1"),
            x="GPIA.CR.1", y="ISO3", orientation="h",
            color="GPIA.CR.1",
            color_continuous_scale=[
                [0, C_RED], [0.5, C_ORANGE], [0.85, C_TEAL], [1, C_GREEN]
            ],
            range_color=[0.5, 1.5],
            labels={"GPIA.CR.1": "GPI", "ISO3": "Country"},
        )
        fig.add_vline(x=1.0, line_dash="dash", line_color=C_GREY)
        fig.update_layout(
            height=500, plot_bgcolor="white",
            coloraxis_showscale=False,
            xaxis=dict(gridcolor="#eee"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(f"**GPI by Region — Primary ({year_sel})**")
        reg_gpi = gpi_df.groupby("REGION")["GPIA.CR.1"].mean().reset_index()
        fig2 = px.bar(
            reg_gpi.sort_values("GPIA.CR.1"),
            x="REGION", y="GPIA.CR.1",
            color="GPIA.CR.1",
            color_continuous_scale=[[0, C_RED], [0.85, C_TEAL], [1, C_GREEN]],
            range_color=[0.5, 1.5],
            labels={"GPIA.CR.1": "Mean GPI", "REGION": "Region"},
        )
        fig2.add_hline(y=1.0, line_dash="dash", line_color=C_GREY)
        fig2.update_layout(
            height=500, plot_bgcolor="white",
            coloraxis_showscale=False,
            xaxis_tickangle=-30,
            yaxis=dict(gridcolor="#eee"),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — COVERAGE HEATMAP
# ══════════════════════════════════════════════════════════════════════════════
elif section == "🗺️ Coverage":
    st.title("🗺️ Data Coverage Heatmap")
    st.markdown(
        "Availability of observations per indicator and country "
        "across the full time series (2010–2023)."
    )

    ind_cols = list(SDG4_INDICATORS.keys())
    pivot = df_wide.set_index("ISO3")[ind_cols].notna().astype(int)

    # Count non-null years per country-indicator
    counts = df_wide.groupby("ISO3")[ind_cols].count().reset_index()
    counts = counts.set_index("ISO3")

    fig = px.imshow(
        counts,
        color_continuous_scale=[[0, "#f0f0f0"], [0.4, C_ORANGE], [1, C_BLUE]],
        labels=dict(x="Indicator", y="Country", color="Years of data"),
        aspect="auto",
        title="Number of available years per country-indicator",
    )
    fig.update_layout(height=600, xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

    if not coverage.empty:
        st.markdown("##### Summary coverage table")
        st.dataframe(
            coverage[["INDICATOR_ID", "INDICATOR_LABEL",
                       "N_OBSERVATIONS", "COVERAGE_PCT", "YEAR_MIN", "YEAR_MAX"]]
            .style.background_gradient(subset=["COVERAGE_PCT"], cmap="YlGn"),
            use_container_width=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — DATA TABLE
# ══════════════════════════════════════════════════════════════════════════════
elif section == "📋 Data Table":
    st.title("📋 Filterable Data Table")

    col1, col2, col3 = st.columns(3)
    with col1:
        regions = ["All"] + sorted(df_wide["REGION"].dropna().unique().tolist())
        reg_filter = st.selectbox("Region", regions)
    with col2:
        income_groups = ["All"] + sorted(df_wide["INCOME_GROUP"].dropna().unique().tolist())
        inc_filter = st.selectbox("Income group", income_groups)
    with col3:
        year_range = st.slider(
            "Year range",
            int(df_wide["YEAR"].min()), int(df_wide["YEAR"].max()),
            (int(df_wide["YEAR"].min()), int(df_wide["YEAR"].max())),
        )

    filtered = df_wide.copy()
    if reg_filter != "All":
        filtered = filtered[filtered["REGION"] == reg_filter]
    if inc_filter != "All":
        filtered = filtered[filtered["INCOME_GROUP"] == inc_filter]
    filtered = filtered[
        filtered["YEAR"].between(year_range[0], year_range[1])
    ]

    st.markdown(f"**{len(filtered):,} rows** matching filters.")
    st.dataframe(filtered, use_container_width=True, height=440)

    csv_bytes = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download filtered data (CSV)",
        data=csv_bytes,
        file_name="uis_sdg4_filtered.csv",
        mime="text/csv",
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — QA & PROCESS
# ══════════════════════════════════════════════════════════════════════════════
elif section == "🔍 QA & Process":
    st.title("🔍 Data Quality & Pipeline Process")

    tab1, tab2, tab3 = st.tabs(["QA Report", "Anomalies", "Process History"])

    with tab1:
        st.markdown("##### Rules-based QA summary")
        if not qa.empty:
            def colour_status(val):
                if val == "PASS":
                    return "background-color: #d4edda; color: #155724"
                elif "WARN" in str(val):
                    return "background-color: #fff3cd; color: #856404"
                return "background-color: #f8d7da; color: #721c24"

            st.dataframe(
                qa.style.applymap(colour_status, subset=["QA_STATUS"]),
                use_container_width=True,
            )

    with tab2:
        st.markdown("##### IsolationForest anomaly flags")
        if not anomalies.empty:
            st.markdown(f"**{len(anomalies)}** anomalous observations flagged.")
            ind_sel = st.selectbox(
                "Filter by indicator",
                ["All"] + sorted(anomalies["INDICATOR_ID"].unique().tolist()),
            )
            anom_view = (
                anomalies if ind_sel == "All"
                else anomalies[anomalies["INDICATOR_ID"] == ind_sel]
            )
            st.dataframe(anom_view, use_container_width=True, height=380)
        else:
            st.info("No anomaly report found.")

    with tab3:
        st.markdown("##### Pipeline process history")
        history = metadata.get("process_history", [])
        if history:
            for step in history:
                with st.expander(f"Step {step['step']} — {step['name']}"):
                    st.markdown(f"**Module:** `{step['module']}`")
                    st.markdown(f"**Description:** {step['description']}")
                    st.markdown(f"**Timestamp:** {step['timestamp']}")
        else:
            st.info("Metadata registry not found. Run step 9 first.")
