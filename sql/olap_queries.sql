-- ============================================================
-- WORKLOAD OLAP — Il Potere d'Acquisto del Tech Worker
-- Data Management A.A. 2025/26 — Smisi, Pietrobono
-- Database: dw_techworker (star schema, Fase 3)
--
-- Ogni query indica l'operazione OLAP che dimostra.
-- Misure NON additive: aggregazione con mediana
-- (percentile_cont), mai SUM. Soglia n>=30 = regola R4.
-- ============================================================

-- ------------------------------------------------------------
-- V0. Vista di supporto: fatti analizzabili + dimensione geografica
--     (esclude i comp_adjusted NULL — regola L6)
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_fact_geo AS
SELECT f.*, g.country_name, g.sub_region, g.region, g.col_index
FROM fact_survey_response f
JOIN dim_geography g USING (geography_key)
WHERE f.comp_adjusted IS NOT NULL;


-- ------------------------------------------------------------
-- Q1. LA BUSINESS QUESTION  [aggregazione + slice implicito R4]
--     Top 15 paesi per potere d'acquisto mediano
-- ------------------------------------------------------------
SELECT country_name,
       count(*)                                                       AS n,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY comp_usd)::numeric, 0)      AS mediana_usd,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY comp_adjusted)::numeric, 0) AS mediana_adj
FROM v_fact_geo
GROUP BY country_name
HAVING count(*) >= 30
ORDER BY mediana_adj DESC
LIMIT 15;


-- ------------------------------------------------------------
-- Q2. NOMINALE vs REALE  [window function: RANK]
--     Chi guadagna/perde posizioni aggiustando per il costo della vita?
-- ------------------------------------------------------------
WITH per_paese AS (
    SELECT country_name,
           count(*) AS n,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY comp_usd)      AS med_usd,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY comp_adjusted) AS med_adj
    FROM v_fact_geo
    GROUP BY country_name
    HAVING count(*) >= 30
)
SELECT country_name, n,
       round(med_usd::numeric)  AS mediana_usd,
       round(med_adj::numeric)  AS mediana_adj,
       rank() OVER (ORDER BY med_usd  DESC) AS rank_nominale,
       rank() OVER (ORDER BY med_adj DESC)  AS rank_reale,
       rank() OVER (ORDER BY med_usd DESC)
         - rank() OVER (ORDER BY med_adj DESC) AS posizioni_guadagnate
FROM per_paese
ORDER BY posizioni_guadagnate DESC, mediana_adj DESC
LIMIT 20;


-- ------------------------------------------------------------
-- Q3. ROLL-UP sulla gerarchia geografica  [ROLLUP: country->sub_region->region]
--     Il GROUP BY ROLLUP produce tutti i livelli + totale generale;
--     GROUPING() distingue i subtotali.
-- ------------------------------------------------------------
SELECT CASE GROUPING(region)     WHEN 1 THEN '** MONDO **' ELSE region END     AS region,
       CASE GROUPING(sub_region) WHEN 1 THEN '(tutte)'     ELSE sub_region END AS sub_region,
       count(*) AS n,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY comp_adjusted)::numeric, 0) AS mediana_adj
FROM v_fact_geo
GROUP BY ROLLUP (region, sub_region)
ORDER BY GROUPING(region), region, GROUPING(sub_region), mediana_adj DESC;


-- ------------------------------------------------------------
-- Q4. PIVOT esperienza x region  [dice su due dimensioni]
--     Dove conviene essere junior? E senior?
-- ------------------------------------------------------------
SELECT e.experience_band,
       g.region,
       count(*) AS n,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.comp_adjusted)::numeric, 0) AS mediana_adj
FROM fact_survey_response f
JOIN dim_experience e USING (experience_key)
JOIN dim_geography  g USING (geography_key)
WHERE f.comp_adjusted IS NOT NULL
  AND e.experience_band <> 'Unknown'
GROUP BY e.experience_band, g.region
HAVING count(*) >= 30
ORDER BY e.experience_band, mediana_adj DESC;


-- ------------------------------------------------------------
-- Q5. SLICE + DRILL-DOWN  [slice su dev_type, dettaglio per paese]
--     Classifica paesi per gli sviluppatori full-stack
-- ------------------------------------------------------------
SELECT v.country_name,
       count(*) AS n,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY v.comp_adjusted)::numeric, 0) AS mediana_adj
FROM v_fact_geo v
JOIN dim_devtype d USING (devtype_key)
WHERE d.devtype_name = 'Developer, full-stack'          -- SLICE
GROUP BY v.country_name
HAVING count(*) >= 30
ORDER BY mediana_adj DESC
LIMIT 10;


-- ------------------------------------------------------------
-- Q6. REMOTE vs IN-PERSON  [FILTER: aggregati condizionali affiancati]
--     Differenziale di potere d'acquisto per region
-- ------------------------------------------------------------
SELECT g.region,
       count(*) FILTER (WHERE r.work_mode = 'Remote')    AS n_remote,
       count(*) FILTER (WHERE r.work_mode = 'In-person') AS n_inperson,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.comp_adjusted)
              FILTER (WHERE r.work_mode = 'Remote'))::numeric, 0)    AS med_adj_remote,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.comp_adjusted)
              FILTER (WHERE r.work_mode = 'In-person'))::numeric, 0) AS med_adj_inperson
FROM fact_survey_response f
JOIN dim_remotework r USING (remotework_key)
JOIN dim_geography  g USING (geography_key)
WHERE f.comp_adjusted IS NOT NULL
GROUP BY g.region
HAVING count(*) FILTER (WHERE r.work_mode = 'Remote') >= 30
   AND count(*) FILTER (WHERE r.work_mode = 'In-person') >= 30
ORDER BY med_adj_remote DESC;


-- ------------------------------------------------------------
-- Q7. BRIDGE: analisi per linguaggio  [arco multiplo]
--     Salario reale mediano di chi usa ciascun linguaggio.
--     NB anti doppio-conteggio: ogni fatto compare in N gruppi
--     (uno per linguaggio conosciuto). Legittimo aggregare
--     ENTRO il linguaggio; vietato sommare TRA linguaggi.
-- ------------------------------------------------------------
SELECT l.language_name,
       count(*) AS n_rispondenti,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY v.comp_adjusted)::numeric, 0) AS mediana_adj
FROM v_fact_geo v
JOIN bridge_response_language b USING (fact_key)
JOIN dim_language l USING (language_key)
GROUP BY l.language_name
HAVING count(*) >= 200
ORDER BY mediana_adj DESC
LIMIT 15;


-- ------------------------------------------------------------
-- Q8. ROBUSTEZZA  [slice su employment]
--     La Top 10 di Q1 regge considerando solo i full-time puri?
-- ------------------------------------------------------------
SELECT v.country_name,
       count(*) AS n,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY v.comp_adjusted)::numeric, 0) AS mediana_adj
FROM v_fact_geo v
JOIN dim_employment e USING (employment_key)
WHERE e.employment_status = 'Employed, full-time'       -- SLICE
GROUP BY v.country_name
HAVING count(*) >= 30
ORDER BY mediana_adj DESC
LIMIT 10;
