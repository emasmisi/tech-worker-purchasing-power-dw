-- ============================================================
-- DEMO LIVE (5 minuti) — Il Potere d'Acquisto del Tech Worker
-- Smisi, Pietrobono — Data Management A.A. 2025/26
-- Eseguire in ordine D1 -> D5. Ogni query e' autonoma.
-- Prerequisito: vista v_fact_geo gia' creata (olap_queries.sql, V0)
-- ============================================================

-- ------------------------------------------------------------
-- D1 (0:00-0:45) — "Questo e' il data warehouse"
-- Star schema popolato: fatto, 10 dimensioni, bridge
-- ------------------------------------------------------------
SELECT 'fact_survey_response' AS tabella, count(*) AS righe, 'fatti (1 riga = 1 rispondente)' AS ruolo FROM fact_survey_response
UNION ALL SELECT 'bridge_response_language', count(*), 'molti-a-molti linguaggi'  FROM bridge_response_language
UNION ALL SELECT 'dim_geography',  count(*), 'gerarchia country->sub_region->region + indici Numbeo' FROM dim_geography
UNION ALL SELECT 'dim_experience', count(*), 'gerarchia anni->fascia'   FROM dim_experience
UNION ALL SELECT 'dim_language',   count(*), 'dimensione del bridge'    FROM dim_language
ORDER BY righe DESC;


-- ------------------------------------------------------------
-- D2 (0:45-1:45) — "Un fatto, tutto lo schema": join a stella
-- + la misura derivata comp_adjusted calcolata in ETL
-- ------------------------------------------------------------
SELECT f.response_id,
       g.country_name, g.sub_region,
       e.experience_band,
       d.devtype_name,
       r.work_mode,
       f.comp_usd,
       g.col_index,
       f.comp_adjusted            -- = comp_usd / (col_index/100)
FROM fact_survey_response f
JOIN dim_geography  g USING (geography_key)
JOIN dim_experience e USING (experience_key)
JOIN dim_devtype    d USING (devtype_key)
JOIN dim_remotework r USING (remotework_key)
WHERE g.country_name = 'Georgia'
ORDER BY f.comp_adjusted DESC
LIMIT 5;


-- ------------------------------------------------------------
-- D3 (1:45-2:45) — LA BUSINESS QUESTION
-- Top 10 paesi per potere d'acquisto mediano (soglia n>=30)
-- ------------------------------------------------------------
SELECT country_name,
       count(*) AS n,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY comp_usd)::numeric, 0)      AS mediana_usd,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY comp_adjusted)::numeric, 0) AS mediana_reale
FROM v_fact_geo
GROUP BY country_name
HAVING count(*) >= 30
ORDER BY mediana_reale DESC
LIMIT 10;


-- ------------------------------------------------------------
-- D4 (2:45-3:45) — ROLL-UP sulla gerarchia del DFM
-- GROUP BY ROLLUP = tutti i livelli di aggregazione in una query
-- (Est Europa > Ovest Europa in termini reali)
-- ------------------------------------------------------------
-- NB: il WHERE agisce PRIMA del ROLLUP, quindi il subtotale
--     e' correttamente "totale Europa" (non "mondo").
SELECT COALESCE(sub_region, '** TOTALE EUROPA **') AS sub_region,
       count(*) AS n,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY comp_adjusted)::numeric, 0) AS mediana_reale
FROM v_fact_geo
WHERE region = 'Europe'                      -- slice + roll-up insieme
GROUP BY ROLLUP (sub_region)
ORDER BY GROUPING(sub_region), mediana_reale DESC;


-- ------------------------------------------------------------
-- D5 (3:45-4:45) — IL BRIDGE: attributo multi-valore
-- Salario reale mediano per linguaggio (>=200 rispondenti)
-- ------------------------------------------------------------
SELECT l.language_name,
       count(*) AS n,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY v.comp_adjusted)::numeric, 0) AS mediana_reale
FROM v_fact_geo v
JOIN bridge_response_language b USING (fact_key)
JOIN dim_language l USING (language_key)
GROUP BY l.language_name
HAVING count(*) >= 200
ORDER BY mediana_reale DESC
LIMIT 10;


-- ============================================================
-- BONUS (solo se avanzano tempo o su domanda del tutor)
-- ============================================================

-- B1 — Remote vs in-person per region (FILTER)
SELECT g.region,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.comp_adjusted)
              FILTER (WHERE r.work_mode = 'Remote'))::numeric, 0)    AS med_remote,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.comp_adjusted)
              FILTER (WHERE r.work_mode = 'In-person'))::numeric, 0) AS med_inperson
FROM fact_survey_response f
JOIN dim_remotework r USING (remotework_key)
JOIN dim_geography  g USING (geography_key)
WHERE f.comp_adjusted IS NOT NULL
GROUP BY g.region
ORDER BY med_remote DESC;

-- B2 — La prova della riconciliazione ETL (errore Corea nel master)
SELECT country_name, alpha3, sub_region, region, col_index
FROM dim_geography
WHERE alpha3 IN ('KOR', 'PRK', 'USA', 'GBR', 'GEO')
ORDER BY country_name;

-- B3 — Chi scala il ranking aggiustando per il costo della vita (window)
WITH per_paese AS (
    SELECT country_name, count(*) AS n,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY comp_usd)      AS med_usd,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY comp_adjusted) AS med_adj
    FROM v_fact_geo GROUP BY country_name HAVING count(*) >= 30)
SELECT country_name, n,
       rank() OVER (ORDER BY med_usd DESC)  AS rank_nominale,
       rank() OVER (ORDER BY med_adj DESC)  AS rank_reale,
       rank() OVER (ORDER BY med_usd DESC)
         - rank() OVER (ORDER BY med_adj DESC) AS posizioni_guadagnate
FROM per_paese
ORDER BY posizioni_guadagnate DESC
LIMIT 8;
