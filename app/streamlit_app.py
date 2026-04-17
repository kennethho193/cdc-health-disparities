import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="CDC Health Disparities",
    page_icon="🏥",
    layout="wide"
)

@st.cache_data
def load_data():
    conn = sqlite3.connect("db/cdc_health.db")
    df = pd.read_sql_query("""
        SELECT c.countyfips, c.stateabbr, c.statedesc,
               c.countyname, c.totalpopulation,
               h.diabetes_adjprev, h.obesity_adjprev,
               h.bphigh_adjprev, h.depression_adjprev,
               h.csmoking_adjprev, h.lpa_adjprev,
               h.ghlth_adjprev,
               s.poverty_rate, s.median_household_income,
               s.uninsured_rate, s.bachelors_rate,
               s.unemployment_rate, s.pct_low_food_access,
               s.snap_participation_rate, s.food_insecurity_rate
        FROM counties c
        JOIN health_outcomes h ON c.countyfips = h.countyfips
        JOIN social_determinants s ON c.countyfips = s.countyfips
    """, conn)
    conn.close()
    return df

@st.cache_data
def load_shapes():
    gdf = gpd.read_file(
        "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_us_county_5m.zip"
    )
    gdf["countyfips"] = gdf["GEOID"]
    return gdf

@st.cache_data
def fit_model(df_json):
    df = pd.read_json(df_json)
    df = df.dropna(subset=[
        "diabetes_adjprev", "poverty_rate",
        "median_household_income", "uninsured_rate",
        "bachelors_rate", "unemployment_rate",
        "lpa_adjprev", "csmoking_adjprev"
    ]).copy()
    df["log_income"] = np.log(df["median_household_income"])
    model = smf.ols(
        """diabetes_adjprev ~ poverty_rate + log_income +
           uninsured_rate + bachelors_rate +
           unemployment_rate + lpa_adjprev + csmoking_adjprev""",
        data=df
    ).fit()
    return model

def search_counties(source_df, query):
    """
    Searches counties by name and state.
    Splits query into words and requires all to match.
    Works with or without commas.
    """
    if not query:
        return source_df.iloc[0:0]
    terms = [t.strip() for t in
             query.replace(",", " ").split() if t.strip()]
    mask = pd.Series([True] * len(source_df), index=source_df.index)
    for term in terms:
        mask = mask & (
            source_df["countyname"].str.contains(
                term, case=False, na=False) |
            source_df["stateabbr"].str.contains(
                term, case=False, na=False)
        )
    return source_df[mask]

#Header
st.title("🏥 CDC Health Disparities Dashboard")
st.markdown(
    "County-level analysis of social determinants and chronic disease "
    "prevalence across the US. Data: CDC PLACES 2025, Census ACS 2022, "
    "USDA Food Environment Atlas 2025."
)

#Load data and fit model
with st.spinner("Loading data..."):
    df  = load_data()
    gdf = load_shapes()

with st.spinner("Fitting regression model..."):
    model = fit_model(df.to_json())

#Sidebar settings
st.sidebar.title("Settings")

outcome_labels = {
    "diabetes_adjprev":   "Diabetes prevalence",
    "obesity_adjprev":    "Obesity prevalence",
    "bphigh_adjprev":     "High blood pressure",
    "depression_adjprev": "Depression",
    "lpa_adjprev":        "Physical inactivity",
    "csmoking_adjprev":   "Smoking rate",
    "ghlth_adjprev":      "Poor general health"
}

predictor_labels = {
    "poverty_rate":            "Poverty rate",
    "median_household_income": "Median household income",
    "uninsured_rate":          "Uninsured rate",
    "bachelors_rate":          "Bachelor's degree rate",
    "unemployment_rate":       "Unemployment rate",
    "pct_low_food_access":     "Low food access",
    "food_insecurity_rate":    "Food insecurity rate"
}

selected_outcome = st.sidebar.selectbox(
    "Health outcome",
    options=list(outcome_labels.keys()),
    format_func=lambda x: outcome_labels[x]
)

selected_predictor = st.sidebar.selectbox(
    "Social determinant",
    options=list(predictor_labels.keys()),
    format_func=lambda x: predictor_labels[x]
)

county_search = st.sidebar.text_input(
    "Search for a county",
    placeholder="e.g. Autauga or Fulton GA"
)

#Summary metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Counties analyzed",        f"{len(df):,}")
col2.metric("Mean diabetes prevalence", f"{df['diabetes_adjprev'].mean():.1f}%")
col3.metric("Mean poverty rate",        f"{df['poverty_rate'].mean():.1f}%")
col4.metric("Model R²",                 "0.840")

st.divider()

#Map and scatterplot
map_col, scatter_col = st.columns([1.6, 1])

with map_col:
    st.subheader(f"{outcome_labels[selected_outcome]} by county")

    merged      = gdf.merge(df, on="countyfips", how="left")
    continental = merged[~merged["STATEFP"].isin(["02", "15", "72"])]
    continental = continental.to_crs("EPSG:4326")

    fig, ax_main = plt.subplots(figsize=(12, 7))

    vmin = df[selected_outcome].quantile(0.05)
    vmax = df[selected_outcome].quantile(0.95)

    plot_kwargs = dict(
        column=selected_outcome,
        cmap="YlOrRd",
        linewidth=0.1,
        edgecolor="white",
        vmin=vmin,
        vmax=vmax,
        legend=False,
        missing_kwds={"color": "lightgrey"}
    )

    continental.plot(**plot_kwargs, ax=ax_main)
    ax_main.set_xlim(-125, -66)
    ax_main.set_ylim(24, 50)
    ax_main.set_axis_off()

    #Alaska inset
    ax_ak = fig.add_axes([0.10, 0.20, 0.18, 0.18])
    gdf[gdf["STATEFP"] == "02"].merge(
        df, on="countyfips", how="left"
    ).to_crs("EPSG:3338").plot(**plot_kwargs, ax=ax_ak)
    ax_ak.set_axis_off()
    ax_ak.set_title("Alaska", fontsize=8, pad=2)

    #Hawaii inset
    ax_hi = fig.add_axes([0.30, 0.22, 0.10, 0.10])
    gdf[gdf["STATEFP"] == "15"].merge(
        df, on="countyfips", how="left"
    ).to_crs("EPSG:4326").plot(**plot_kwargs, ax=ax_hi)
    ax_hi.set_axis_off()
    ax_hi.set_title("Hawaii", fontsize=8, pad=2)

    #Colorbar
    sm = plt.cm.ScalarMappable(
        cmap="YlOrRd",
        norm=plt.Normalize(vmin=vmin, vmax=vmax)
    )
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax_main,
                        orientation="vertical",
                        fraction=0.02, pad=0.02)
    cbar.set_label("Age-adjusted prevalence (%)", fontsize=10)

    st.pyplot(fig)

with scatter_col:
    st.subheader(
        f"{predictor_labels[selected_predictor]} vs "
        f"{outcome_labels[selected_outcome]}"
    )

    scatter_df = df.dropna(
        subset=[selected_predictor, selected_outcome])

    fig2, ax2 = plt.subplots(figsize=(7, 7))
    ax2.scatter(scatter_df[selected_predictor],
                scatter_df[selected_outcome],
                alpha=0.25, s=10, color="#1D9E75")

    #Highlight searched county
    if county_search:
        match = search_counties(scatter_df, county_search)
        if not match.empty:
            ax2.scatter(
                match[selected_predictor],
                match[selected_outcome],
                color="coral", s=60, zorder=5,
                label=f"{match.iloc[0]['countyname']}, "
                      f"{match.iloc[0]['stateabbr']}"
            )
            ax2.legend(fontsize=9)

    #Trend line
    z = np.polyfit(scatter_df[selected_predictor],
                   scatter_df[selected_outcome], 1)
    p = np.poly1d(z)
    x_line = np.linspace(scatter_df[selected_predictor].min(),
                         scatter_df[selected_predictor].max(), 100)
    ax2.plot(x_line, p(x_line), color="coral", linewidth=2)

    corr = scatter_df[selected_predictor].corr(
        scatter_df[selected_outcome])
    ax2.text(0.05, 0.95, f"r = {corr:.3f}",
             transform=ax2.transAxes, fontsize=12,
             verticalalignment="top",
             bbox=dict(boxstyle="round",
                       facecolor="white", alpha=0.8))

    ax2.set_xlabel(predictor_labels[selected_predictor], fontsize=11)
    ax2.set_ylabel(outcome_labels[selected_outcome],     fontsize=11)
    plt.tight_layout()
    st.pyplot(fig2)

st.divider()

#Regression results
st.subheader("Regression results — predictors of diabetes prevalence")
st.markdown("OLS regression, N = 2,956 counties, R² = 0.840")

coef_labels = {
    "poverty_rate":      "Poverty rate",
    "log_income":        "Log income",
    "uninsured_rate":    "Uninsured rate",
    "bachelors_rate":    "Bachelor's degree rate",
    "unemployment_rate": "Unemployment rate",
    "lpa_adjprev":       "Physical inactivity",
    "csmoking_adjprev":  "Smoking rate"
}

coef_df = pd.DataFrame({
    "Predictor":   [coef_labels.get(k, k) for k in
                    model.params.index if k != "Intercept"],
    "Coefficient": model.params.drop("Intercept").round(4).values,
    "p-value":     model.pvalues.drop("Intercept").round(4).values,
    "Significant": ["Yes" if p < 0.05 else "No"
                    for p in model.pvalues.drop("Intercept").values]
}).sort_values("Coefficient", ascending=False)

st.dataframe(coef_df, use_container_width=True, hide_index=True)

# County search results
if county_search:
    st.divider()
    st.subheader(f"County lookup — '{county_search}'")
    match = search_counties(df, county_search)
    if not match.empty:
        display_cols = [
            "countyname", "stateabbr",
            "diabetes_adjprev", "obesity_adjprev",
            "poverty_rate", "median_household_income",
            "uninsured_rate", "food_insecurity_rate"
        ]
        st.dataframe(
            match[display_cols].round(2),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning(
            "No counties found — try just the county name "
            "or state abbreviation e.g. 'Autauga' or 'Fulton GA'"
        )