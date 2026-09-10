# Design rules reference

Every rule cited by its code (`R1`, `D2`, `L6`, ...) in the ETL script, the SQL workload, and the README is defined here. This is the single lookup point for all of them.

## R1–R6 — data cleaning rules (source profiling, `etl/etl_dw_techworker.py`)

| Rule | What it does | Why |
|---|---|---|
| **R1** | Keep only respondents with a non-null `ConvertedCompYearly` (23,435 of 65,437, 35.8%). | A fact without a measure contributes nothing to the analysis. |
| **R2** | Trim compensation at the 1st–99th percentile (raw range: 1 to 16.2M USD/year). | Standard, reproducible way to remove the most implausible self-reported values without hand-picking a cutoff. |
| **R3** | Nulls in `Industry` (31.8%) become an explicit `'Unknown'` dimension member instead of being dropped. | Standard DW practice: no fact is discarded for a secondary dimension, and the dimension stays queryable. |
| **R4** | The minimum-respondents-per-country threshold (e.g. `n ≥ 30`) is enforced in OLAP queries (`HAVING`), never in the ETL. | The warehouse keeps full grain and never loses information; analytical thresholds are a query-time choice and stay changeable without reloading. |
| **R5** | Documented exclusions: `Nomadic` (4 respondents, not a country) and `Kosovo` (4 respondents, no official ISO 3166 code, absent from the geographic master). | Both fall outside what the ISO master can represent; excluding them is explicit and small in scope. |
| **R6** | Fix a bug in the geographic master (`continents2.csv`): the row named "South Korea" carried North Korea's ISO code (`PRK`). Fixed in ETL — that row is renamed "North Korea", and South Korea mappings point to `KOR`. | Demonstrates why integration must join on ISO codes, not names: even the master needs validation. |

## D1–D3 — conceptual design decisions (DFM, Fase 2)

| Decision | What it does | Why |
|---|---|---|
| **D1** | Numbeo cost-of-living indices live as descriptive attributes of `country`, *and* as the pre-computed derived measure `comp_adjusted` on the fact. | The indices are country-grain, not respondent-grain — conceptually context, not a fact measure. Pre-computing `comp_adjusted` in ETL keeps the core OLAP queries free of join+divide logic; the raw indices stay available for secondary analysis. |
| **D2** | Experience is banded (Junior 0–2, Mid 3–5, Senior 6–10, Expert 11+) from `YearsCodePro`. | The numeric detail is kept upstream; banding is a documented, changeable rule that doesn't require re-running the ETL over facts. |
| **D3** | The language bridge only covers `LanguageHaveWorkedWith` (languages actually used), not related but broader Stack Overflow fields. | Keeps the many-to-many relationship scoped and unambiguous; the same bridge pattern could extend to other tech-stack fields later. |

## L1–L6 — logical design decisions (star schema, Fase 3)

| Decision | What it does | Why |
|---|---|---|
| **L1** | Star schema, not snowflake: hierarchies are denormalized inside each dimension table (e.g. the full geographic hierarchy lives in `dim_geography`). | The warehouse is written once by a controlled ETL and read many times — redundancy causes no update anomalies here, and it means fewer joins and simpler queries. Snowflaking only pays off for much larger dimensions. |
| **L2** | Every dimension uses an integer surrogate key. | Source-independent joins, uniform handling of the `'Unknown'` member, and natural keys (like ISO alpha-3) are kept as plain attributes rather than join keys. |
| **L3** | One dimension table per dimension (9 conformed dimensions + languages), no inline attributes or junk dimensions. | Textbook-clear schema; joins on tables this small cost nothing. Both alternatives (fact-inline attributes, junk dimension) were considered and rejected as unnecessary at this scale. |
| **L4** | Direct bridge table `bridge_response_language(fact_key, language_key)` — one row per respondent–language pair (~121k rows). | Transparent and immediate. Kimball's "group bridge" (deduplicating identical skill sets) was considered and rejected as unneeded indirection at this scale. |
| **L5** | `response_id` is kept in the fact table as a degenerate dimension (no separate dimension table). | Preserves lineage back to the source CSV row — useful for debugging and for the live demo. |
| **L6** | Countries without a cost-of-living index keep their facts, with `comp_adjusted = NULL`. | Consistent with R4: the warehouse never silently loses information. All 69 countries relevant to the analysis do have the index (verified in Fase 1); the few facts from smaller countries remain queryable on `comp_usd` and are naturally excluded from `comp_adjusted`-based analyses. |
