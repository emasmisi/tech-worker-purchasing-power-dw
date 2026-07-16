# ============================================================
# Live demo app — The Purchasing Power of the Tech Worker
# Streamlit + PostgreSQL (dw_techworker)
# Run:  streamlit run demo_app.py
# ============================================================
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Tech Worker DW — live", layout="wide")

DB_URL = "postgresql+psycopg2://emanuelesmisi@localhost:5432/dw_techworker"
BORDEAUX = "#8C1D2F"
GREY = "#B9B9B9"

@st.cache_resource
def get_engine():
    return create_engine(DB_URL)

# One SQL drives the whole app. The HAVING threshold is a parameter:
# rule R4 — the warehouse keeps full grain, thresholds live in queries.
SQL = """
WITH per_country AS (
    SELECT g.country_name, g.alpha3, g.region,
           count(*) AS n,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY f.comp_usd)      AS med_usd,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY f.comp_adjusted) AS med_adj
    FROM fact_survey_response f
    JOIN dim_geography g USING (geography_key)
    WHERE f.comp_adjusted IS NOT NULL
    GROUP BY g.country_name, g.alpha3, g.region
    HAVING count(*) >= :thr        -- <<< rule R4: threshold lives HERE, not in the ETL
)
SELECT country_name, alpha3, region, n,
       round(med_usd::numeric)  AS med_usd,
       round(med_adj::numeric)  AS med_adj,
       rank() OVER (ORDER BY med_usd DESC) AS rank_nominal,
       rank() OVER (ORDER BY med_adj DESC) AS rank_real
FROM per_country
ORDER BY med_adj DESC
"""

@st.cache_data(ttl=300)
def load(thr: int) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(SQL), conn, params={"thr": thr})

# ---------------- sidebar: the R4 rule, made tangible ----------------
st.sidebar.title("Tech Worker DW")
thr = st.sidebar.slider("Min respondents per country (rule R4)", 10, 200, 30, step=5)
st.sidebar.caption(
    "The warehouse stores **all** facts at the finest grain. "
    "This slider only changes the `HAVING` clause of the query — "
    "no reload, no ETL: analytical choices live at query time."
)

df = load(thr)
st.sidebar.metric("Countries above threshold", len(df))

st.title("The Purchasing Power of the Tech Worker")
st.caption("Live on PostgreSQL · star schema `dw_techworker` · every number below is one SQL query away")

tab_map, tab_rank, tab_focus = st.tabs(["World map", "Ranking", "Country focus"])

# ---------------- 1. world map: the ISO reconciliation, made visible ----------------
with tab_map:
    fig = px.choropleth(
        df, locations="alpha3", color="med_adj",
        hover_name="country_name",
        hover_data={"alpha3": False, "n": True, "med_usd": True, "med_adj": True},
        color_continuous_scale="Reds",
        labels={"med_adj": "median adj. $", "med_usd": "median nominal $", "n": "respondents"},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=520,
                      coloraxis_colorbar_title="median adj. $")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "This map is drawn directly from the **ISO alpha-3 codes** in `dim_geography` — "
        "it exists because every source was reconciled onto the canonical geographic master."
    )
    with st.expander("SQL under the hood"):
        st.code(SQL.replace(":thr", str(thr)), language="sql")

# ---------------- 2. ranking: nominal vs adjusted ----------------
with tab_rank:
    top = df.nlargest(15, "med_adj").sort_values("med_adj")
    fig = go.Figure()
    fig.add_bar(y=top["country_name"], x=top["med_usd"], orientation="h",
                name="Nominal USD (median)", marker_color=GREY)
    fig.add_bar(y=top["country_name"], x=top["med_adj"], orientation="h",
                name="Cost-of-living adjusted (median)", marker_color=BORDEAUX)
    fig.update_layout(barmode="group", height=560,
                      margin=dict(l=0, r=0, t=10, b=0),
                      legend=dict(orientation="h", y=-0.12),
                      xaxis_title="median yearly compensation ($)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Medians, never sums: the measures are **non-additive** and the distribution is right-skewed. "
        "Move the sidebar slider and watch small-sample countries enter and leave the top."
    )
    with st.expander("SQL under the hood"):
        st.code(SQL.replace(":thr", str(thr)), language="sql")

# ---------------- 3. country focus: nominal vs real, one country at a time ----------------
with tab_focus:
    country = st.selectbox("Country", df["country_name"].sort_values())
    row = df[df["country_name"] == country].iloc[0]
    gained = int(row["rank_nominal"] - row["rank_real"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Adjusted median", f"{int(row['med_adj']):,} $")
    c2.metric("Nominal median", f"{int(row['med_usd']):,} $")
    c3.metric("Real rank", f"#{int(row['rank_real'])}",
              delta=f"{gained:+d} vs nominal rank", delta_color="normal")
    c4.metric("Respondents", int(row["n"]))
    st.caption(
        f"{country} — {row['region']}. "
        "The rank delta is the whole project in one number: what cost of living gives or takes away."
    )
    with st.expander("SQL under the hood"):
        st.code(SQL.replace(":thr", str(thr)), language="sql")
