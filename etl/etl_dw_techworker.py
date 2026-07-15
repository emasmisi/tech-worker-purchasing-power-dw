# ============================================================
# ETL — Il Potere d'Acquisto del Tech Worker
# Data Management A.A. 2025/26 — Emanuele Smisi, Fabrizio Pietrobono
#
# Pipeline: EXTRACT (kagglehub) -> TRANSFORM (regole R1-R6, Fase 1)
#           -> LOAD (star schema, Fase 3) -> QUALITY CHECK
# Idempotente: ogni esecuzione ricrea lo schema da zero.
#
# Prerequisiti:
#   - PostgreSQL in esecuzione su localhost:5432
#   - CREATE DATABASE dw_techworker;  (una tantum, via psql)
#   - pip install kagglehub pandas sqlalchemy psycopg2-binary
# ============================================================

import os, glob
import kagglehub
import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://emanuelesmisi@localhost:5432/dw_techworker"

# ------------------------------------------------------------
# 1. EXTRACT
# ------------------------------------------------------------
print("== EXTRACT ==")

def carica(folder, preferisci=()):
    csvs = glob.glob(os.path.join(folder, "*.csv"))
    scelta = next((c for c in csvs
                   if any(k in os.path.basename(c).lower() for k in preferisci)),
                  max(csvs, key=os.path.getsize))
    print("  carico:", os.path.basename(scelta))
    return pd.read_csv(scelta, low_memory=False)

so   = carica(kagglehub.dataset_download(
        "berkayalan/stack-overflow-annual-developer-survey-2024"), ("public",))
geo  = carica(kagglehub.dataset_download(
        "andradaolteanu/country-mapping-iso-continent-region"), ("continent",))
cost = carica(kagglehub.dataset_download(
        "myrios/cost-of-living-index-by-country-by-number-2024"), ("cost",))

# ------------------------------------------------------------
# 2. TRANSFORM
# ------------------------------------------------------------
print("\n== TRANSFORM ==")

# --- R6: correzione del master geografico (riga 'South Korea' ha codice PRK,
#     che e' la Corea del Nord; la Corea del Sud corretta e' KOR) ---
geo = geo.copy()
geo["name"] = geo["name"].astype(str).str.strip()
geo.loc[geo["alpha-3"] == "PRK", "name"] = "North Korea"

# --- Mapping di riconciliazione (Fase 1, §5): chiave canonica = nome GEO ---
MAP_SO_GEO = {
    "Bosnia and Herzegovina": "Bosnia And Herzegovina",
    "Cape Verde": "Cabo Verde",
    "Congo, Republic of the...": "Congo",
    "Côte d'Ivoire": "Côte D'Ivoire",
    "Democratic People's Republic of Korea": "North Korea",
    "Democratic Republic of the Congo": "Congo (Democratic Republic Of The)",
    "Hong Kong (S.A.R.)": "Hong Kong",
    "Iran, Islamic Republic of...": "Iran",
    "Lao People's Democratic Republic": "Laos",
    "Libyan Arab Jamahiriya": "Libya",
    "Palestine": "Palestine, State of",
    "Republic of Korea": "Korea, Republic of",
    "Republic of Moldova": "Moldova",
    "Republic of North Macedonia": "Macedonia",
    "Russian Federation": "Russia",
    "Syrian Arab Republic": "Syria",
    "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
    "United Republic of Tanzania": "Tanzania",
    "United States of America": "United States",
    "Venezuela, Bolivarian Republic of...": "Venezuela",
    "Viet Nam": "Vietnam",
}
ESCLUSI_SO = {"Nomadic", "Kosovo"}                       # R5
MAP_COSTO_GEO = {
    "Hong Kong (China)": "Hong Kong",
    "North Macedonia": "Macedonia",
    "Palestine": "Palestine, State of",
    "South Korea": "Korea, Republic of",                 # R6
    "Trinidad And Tobago": "Trinidad and Tobago",
}
ESCLUSI_COSTO = {"Kosovo (Disputed Territory)"}          # R5

# --- dim_geography: master GEO + indici Numbeo (D1: attributi descrittivi) ---
cost = cost.copy()
cost["country_canon"] = (cost["Country"].astype(str).str.strip()
                         .map(lambda s: MAP_COSTO_GEO.get(s, s)))
cost = cost[~cost["Country"].isin(ESCLUSI_COSTO)]
dim_geography = (
    geo[["name", "alpha-3", "sub-region", "region"]]
    .rename(columns={"name": "country_name", "alpha-3": "alpha3",
                     "sub-region": "sub_region", "region": "region"})
    .dropna(subset=["sub_region", "region"])
    .merge(cost.rename(columns={
        "Cost of Living Index": "col_index", "Rent Index": "rent_index",
        "Cost of Living Plus Rent Index": "col_rent_index",
        "Groceries Index": "groceries_index",
        "Restaurant Price Index": "restaurant_index",
        "Local Purchasing Power Index": "lpp_index"}),
        how="left", left_on="country_name", right_on="country_canon")
    [["country_name", "alpha3", "sub_region", "region", "col_index",
      "rent_index", "col_rent_index", "groceries_index",
      "restaurant_index", "lpp_index"]]
    .reset_index(drop=True))
dim_geography.insert(0, "geography_key", range(1, len(dim_geography) + 1))

# --- Fatti: R1 (compenso valido) + riconciliazione + R5 (esclusioni) ---
f = so[so["ConvertedCompYearly"].notna()].copy()
f["country_canon"] = (f["Country"].astype(str).str.strip()
                      .map(lambda s: MAP_SO_GEO.get(s, s)))
f = f[~f["Country"].isin(ESCLUSI_SO)]
f = f[f["country_canon"].isin(set(dim_geography["country_name"]))]

# --- R2: taglio outlier 1°-99° percentile ---
q01, q99 = f["ConvertedCompYearly"].quantile([0.01, 0.99])
prima = len(f)
f = f[f["ConvertedCompYearly"].between(q01, q99)]
print(f"  R2 outlier: soglie [{q01:.0f}, {q99:.0f}] USD -> {prima} -> {len(f)} fatti")

# --- D2: esperienza, anni -> fascia ---
def anni(v):
    if pd.isna(v): return None
    if v == "Less than 1 year": return 0
    if v == "More than 50 years": return 51
    return int(float(v))

def fascia(y):
    if y is None: return "Unknown"
    if y <= 2:  return "Junior (0-2)"
    if y <= 5:  return "Mid (3-5)"
    if y <= 10: return "Senior (6-10)"
    return "Expert (11+)"

f["years_code_pro"] = f["YearsCodePro"].map(anni)
f["experience_band"] = f["years_code_pro"].map(fascia)

# --- Dimensioni piccole: nulli -> membro 'Unknown' (R3) ---
SMALL_DIMS = [  # (tabella, chiave, attributo, colonna sorgente SO)
    ("dim_devtype",    "devtype_key",    "devtype_name",      "DevType"),
    ("dim_education",  "education_key",  "education_level",   "EdLevel"),
    ("dim_orgsize",    "orgsize_key",    "org_size",          "OrgSize"),
    ("dim_remotework", "remotework_key", "work_mode",         "RemoteWork"),
    ("dim_employment", "employment_key", "employment_status", "Employment"),
    ("dim_industry",   "industry_key",   "industry_name",     "Industry"),
    ("dim_age",        "age_key",        "age_band",          "Age"),
]
# Nota: Employment in SO e' multi-selezione; si tiene la combinazione come
# membro (scelta documentata: nessuna perdita, cardinalita' comunque bassa).

dims_small, lookups = {}, {}
for tab, key, attr, src in SMALL_DIMS:
    vals = sorted(f[src].fillna("Unknown").astype(str).str.strip().unique())
    vals = ["Unknown"] + [v for v in vals if v != "Unknown"]
    d = pd.DataFrame({key: range(len(vals)), attr: vals})   # Unknown -> key 0
    dims_small[tab] = d
    lookups[tab] = dict(zip(d[attr], d[key]))

# --- dim_experience: distinct (anni, fascia) + membro Unknown (key 0) ---
exp_pairs = (f[["years_code_pro", "experience_band"]].dropna()
             .drop_duplicates().sort_values("years_code_pro"))
dim_experience = pd.DataFrame(
    [{"years_code_pro": None, "experience_band": "Unknown"}]
    + exp_pairs.to_dict("records"))
dim_experience.insert(0, "experience_key", range(len(dim_experience)))
exp_lookup = {(None if pd.isna(y) else int(y)): k
              for k, y in zip(dim_experience["experience_key"],
                              dim_experience["years_code_pro"])}

# --- dim_language + bridge (D3/L4: arco multiplo -> bridge diretto) ---
langs = (f["LanguageHaveWorkedWith"].fillna("")
         .str.split(";").explode().str.strip())
langs = langs[langs != ""]
dim_language = pd.DataFrame({"language_name": sorted(langs.unique())})
dim_language.insert(0, "language_key", range(1, len(dim_language) + 1))
lang_lookup = dict(zip(dim_language["language_name"],
                       dim_language["language_key"]))

# --- Fact table: chiavi surrogate + misure ---
geo_lookup = dict(zip(dim_geography["country_name"],
                      dim_geography["geography_key"]))
col_lookup = dict(zip(dim_geography["country_name"],
                      dim_geography["col_index"]))

fact = pd.DataFrame({
    "fact_key":       range(1, len(f) + 1),
    "response_id":    f["ResponseId"].astype(int).values,           # L5
    "geography_key":  f["country_canon"].map(geo_lookup).values,
    "experience_key": [exp_lookup[None if pd.isna(y) else int(y)]
                       for y in f["years_code_pro"]],
    "comp_usd":       f["ConvertedCompYearly"].round(2).values,
})
for tab, key, attr, src in SMALL_DIMS:
    fact[key] = (f[src].fillna("Unknown").astype(str).str.strip()
                 .map(lookups[tab]).values)
# comp_adjusted = comp_usd / (col_index/100); NULL se indice assente (L6)
col = f["country_canon"].map(col_lookup)
fact["comp_adjusted"] = (f["ConvertedCompYearly"] / (col / 100)).round(2).values

# --- Bridge: una riga per coppia (fatto, linguaggio) ---
rid2key = dict(zip(fact["response_id"], fact["fact_key"]))
bl = (f[["ResponseId", "LanguageHaveWorkedWith"]].copy()
      .assign(language_name=lambda d: d["LanguageHaveWorkedWith"]
              .fillna("").str.split(";")).explode("language_name"))
bl["language_name"] = bl["language_name"].str.strip()
bl = bl[bl["language_name"] != ""]
bridge = pd.DataFrame({
    "fact_key":     bl["ResponseId"].astype(int).map(rid2key).values,
    "language_key": bl["language_name"].map(lang_lookup).values,
}).drop_duplicates()

print(f"  fatti: {len(fact)} | dim_geography: {len(dim_geography)} | "
      f"dim_language: {len(dim_language)} | bridge: {len(bridge)}")

# ------------------------------------------------------------
# 3. LOAD  (ordine: dimensioni -> fatti -> bridge)
# ------------------------------------------------------------
print("\n== LOAD ==")
engine = create_engine(DB_URL)

DDL = """
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

CREATE TABLE dim_geography (
    geography_key    INTEGER PRIMARY KEY,
    country_name     TEXT NOT NULL UNIQUE,
    alpha3           CHAR(3) NOT NULL UNIQUE,
    sub_region       TEXT NOT NULL,
    region           TEXT NOT NULL,
    col_index        NUMERIC(6,1),
    rent_index       NUMERIC(6,1),
    col_rent_index   NUMERIC(6,1),
    groceries_index  NUMERIC(6,1),
    restaurant_index NUMERIC(6,1),
    lpp_index        NUMERIC(6,1)
);
CREATE TABLE dim_experience (
    experience_key   INTEGER PRIMARY KEY,
    years_code_pro   SMALLINT,
    experience_band  TEXT NOT NULL
);
CREATE TABLE dim_devtype    (devtype_key    INTEGER PRIMARY KEY, devtype_name      TEXT NOT NULL UNIQUE);
CREATE TABLE dim_education  (education_key  INTEGER PRIMARY KEY, education_level   TEXT NOT NULL UNIQUE);
CREATE TABLE dim_orgsize    (orgsize_key    INTEGER PRIMARY KEY, org_size          TEXT NOT NULL UNIQUE);
CREATE TABLE dim_remotework (remotework_key INTEGER PRIMARY KEY, work_mode         TEXT NOT NULL UNIQUE);
CREATE TABLE dim_employment (employment_key INTEGER PRIMARY KEY, employment_status TEXT NOT NULL UNIQUE);
CREATE TABLE dim_industry   (industry_key   INTEGER PRIMARY KEY, industry_name     TEXT NOT NULL UNIQUE);
CREATE TABLE dim_age        (age_key        INTEGER PRIMARY KEY, age_band          TEXT NOT NULL UNIQUE);
CREATE TABLE dim_language   (language_key   INTEGER PRIMARY KEY, language_name     TEXT NOT NULL UNIQUE);

CREATE TABLE fact_survey_response (
    fact_key        BIGINT PRIMARY KEY,
    response_id     INTEGER NOT NULL,
    geography_key   INTEGER NOT NULL REFERENCES dim_geography,
    experience_key  INTEGER NOT NULL REFERENCES dim_experience,
    devtype_key     INTEGER NOT NULL REFERENCES dim_devtype,
    education_key   INTEGER NOT NULL REFERENCES dim_education,
    orgsize_key     INTEGER NOT NULL REFERENCES dim_orgsize,
    remotework_key  INTEGER NOT NULL REFERENCES dim_remotework,
    employment_key  INTEGER NOT NULL REFERENCES dim_employment,
    industry_key    INTEGER NOT NULL REFERENCES dim_industry,
    age_key         INTEGER NOT NULL REFERENCES dim_age,
    comp_usd        NUMERIC(12,2) NOT NULL,
    comp_adjusted   NUMERIC(12,2)
);
CREATE TABLE bridge_response_language (
    fact_key      BIGINT  NOT NULL REFERENCES fact_survey_response,
    language_key  INTEGER NOT NULL REFERENCES dim_language,
    PRIMARY KEY (fact_key, language_key)
);
"""
with engine.begin() as conn:
    conn.execute(text(DDL))

def load(df, table):
    df.to_sql(table, engine, if_exists="append", index=False,
              method="multi", chunksize=5000)
    print(f"  {table}: {len(df)} righe")

load(dim_geography, "dim_geography")
load(dim_experience, "dim_experience")
for tab, *_ in SMALL_DIMS:
    load(dims_small[tab], tab)
load(dim_language, "dim_language")
load(fact[["fact_key", "response_id", "geography_key", "experience_key",
           "devtype_key", "education_key", "orgsize_key", "remotework_key",
           "employment_key", "industry_key", "age_key",
           "comp_usd", "comp_adjusted"]], "fact_survey_response")
load(bridge, "bridge_response_language")

# ------------------------------------------------------------
# 4. QUALITY CHECK post-load
# ------------------------------------------------------------
print("\n== QUALITY CHECK ==")
QC = {
 "Fatti caricati":
   "SELECT count(*) FROM fact_survey_response",
 "Fatti con comp_adjusted NULL (L6, attesi pochi)":
   "SELECT count(*) FROM fact_survey_response WHERE comp_adjusted IS NULL",
 "Paesi distinti nei fatti":
   "SELECT count(DISTINCT geography_key) FROM fact_survey_response",
 "Righe bridge":
   "SELECT count(*) FROM bridge_response_language",
 "Media linguaggi per rispondente":
   "SELECT round(count(*)::numeric / (SELECT count(*) FROM fact_survey_response), 2) "
   "FROM bridge_response_language",
}
with engine.connect() as conn:
    for label, q in QC.items():
        print(f"  {label}: {conn.execute(text(q)).scalar()}")

    print("\n  Smoke test — Top 10 paesi per comp_adjusted mediano (>=30 risp.):")
    smoke = pd.read_sql(text("""
        SELECT g.country_name,
               count(*)                                            AS n,
               round(percentile_cont(0.5) WITHIN GROUP
                     (ORDER BY f.comp_adjusted)::numeric, 0)       AS mediana_adj
        FROM fact_survey_response f
        JOIN dim_geography g USING (geography_key)
        WHERE f.comp_adjusted IS NOT NULL
        GROUP BY g.country_name
        HAVING count(*) >= 30
        ORDER BY mediana_adj DESC
        LIMIT 10"""), conn)
    print(smoke.to_string(index=False))

print("\nETL completato.")
