# Progettazione Logica — Star Schema (Fase 3)

**Progetto:** Il Potere d'Acquisto del Tech Worker — Data Warehousing
**Corso:** Data Management A.A. 2025/26
**Autori:** Emanuele Smisi, Fabrizio Pietrobono
**Data:** 13 luglio 2026
**Input:** DFM di Fase 2 · **Target:** PostgreSQL · **Diagramma:** `Fase3_Star_Schema.svg`

---

## 1. Decisioni di traduzione DFM → logico

| ID | Decisione | Motivazione |
|---|---|---|
| L1 | **Star schema** (no snowflake) | Le dimension table sono denormalizzate: l'intera gerarchia geografica sta in `dim_geography` (249 righe). Nel DW la ridondanza è innocua (scrittura una tantum in ETL controllato → niente anomalie di aggiornamento) e ripaga con meno join e query più semplici. Lo snowflake si giustifica solo con dimensioni molto grandi. |
| L2 | **Chiavi surrogate** intere per tutte le dimensioni | Indipendenza dalle sorgenti, join compatti, gestione uniforme del membro 'Unknown'. Le chiavi naturali (es. alpha-3) restano come attributi. |
| L3 | **Una dimension table per dimensione** (9 + linguaggi) | Schema da manuale, chiaro da presentare; join su tabelle piccolissime a costo nullo. Alternative scartate: attributi inline nel fatto (non è più uno star schema), junk dimension (pattern avanzato non necessario). |
| L4 | **Bridge diretto** fatto ↔ linguaggio | `bridge_response_language(fact_key, language_key)`: una riga per coppia rispondente-linguaggio (~150k righe attese). Trasparente e immediato. Alternativa scartata: group bridge di Kimball (deduplica i set di skill identici, ma aggiunge indirezione non necessaria a questa scala). |
| L5 | `response_id` come **dimensione degenere** nel fatto | Chiave naturale della sorgente conservata nella fact table senza dimension table propria: tracciabilità verso il CSV di origine (lineage), utile in demo e debug. |
| L6 | Paesi senza dato costo-vita: fatti **conservati**, `comp_adjusted = NULL` | Coerente con R4 (il DW non perde informazione). I 69 paesi rilevanti hanno tutti l'indice (verificato in Fase 1); i fatti dei paesi minori restano interrogabili su `comp_usd` e vengono naturalmente esclusi dalle analisi su `comp_adjusted`. |

## 2. Fact table

**`fact_survey_response`** — grana: una risposta al survey (~23.000 righe dopo pulizia R1-R2)

| Colonna | Tipo | Ruolo |
|---|---|---|
| fact_key | BIGSERIAL PK | Chiave surrogate del fatto |
| response_id | INTEGER | Dimensione degenere (ResponseId sorgente, lineage) |
| geography_key | INTEGER FK → dim_geography | |
| experience_key | INTEGER FK → dim_experience | |
| devtype_key | INTEGER FK → dim_devtype | |
| education_key | INTEGER FK → dim_education | |
| orgsize_key | INTEGER FK → dim_orgsize | |
| remotework_key | INTEGER FK → dim_remotework | |
| employment_key | INTEGER FK → dim_employment | |
| industry_key | INTEGER FK → dim_industry | |
| age_key | INTEGER FK → dim_age | |
| comp_usd | NUMERIC(12,2) | Misura (non additiva) |
| comp_adjusted | NUMERIC(12,2), NULL ammesso (L6) | Misura derivata = comp_usd / (col_index/100) |

## 3. Dimension table

**`dim_geography`** (~249 righe) — geografia + contesto economico (D1 di Fase 2)

| Colonna | Tipo | Note |
|---|---|---|
| geography_key | SERIAL PK | |
| country_name | TEXT | Nome canonico (post riconciliazione §5 Fase 1, correzione Corea R6) |
| alpha3 | CHAR(3) | Chiave naturale ISO |
| sub_region | TEXT | Livello gerarchia |
| region | TEXT | Livello gerarchia (continente) |
| col_index, rent_index, col_rent_index, groceries_index, restaurant_index, lpp_index | NUMERIC(6,1), NULL ammesso | Attributi descrittivi Numbeo 2024 (NULL per paesi non coperti) |

**`dim_experience`** (~53 righe) — gerarchia anni → fascia (D2)

| Colonna | Tipo | Note |
|---|---|---|
| experience_key | SERIAL PK | |
| years_code_pro | SMALLINT, NULL per 'Unknown' | ETL: "Less than 1 year"→0, "More than 50 years"→51 |
| experience_band | TEXT | Junior 0–2 · Mid 3–5 · Senior 6–10 · Expert 11+ · Unknown |

**Dimensioni piccole** (stessa struttura: `<nome>_key SERIAL PK`, `<attributo> TEXT NOT NULL`, membro **'Unknown'** con chiave riservata = 0):

| Tabella | Attributo | Cardinalità attesa |
|---|---|---|
| dim_devtype | devtype_name | ~35 |
| dim_education | education_level | ~8 |
| dim_orgsize | org_size | ~10 |
| dim_remotework | work_mode | 3-4 |
| dim_employment | employment_status | ~10 |
| dim_industry | industry_name | ~15 (incl. 'Unknown', R3) |
| dim_age | age_band | ~8 (fasce native SO) |
| dim_language | language_name | ~50 |

## 4. Bridge table

**`bridge_response_language`** (~150.000 righe attese)

| Colonna | Tipo |
|---|---|
| fact_key | BIGINT FK → fact_survey_response |
| language_key | INTEGER FK → dim_language |
| **PK** | (fact_key, language_key) |

ETL: split di `LanguageHaveWorkedWith` sul separatore `;`, deduplica, lookup della chiave surrogate. Guardia anti doppio conteggio: nelle query per linguaggio si aggregano i fatti *entro* ciascun linguaggio, mai somme *tra* linguaggi.

## 5. DDL rappresentativo (PostgreSQL)

```sql
CREATE TABLE dim_geography (
    geography_key    SERIAL PRIMARY KEY,
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

CREATE TABLE dim_language (
    language_key   SERIAL PRIMARY KEY,
    language_name  TEXT NOT NULL UNIQUE
);
-- dim_devtype, dim_education, ... : struttura analoga

CREATE TABLE fact_survey_response (
    fact_key        BIGSERIAL PRIMARY KEY,
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
```

Le FK sono dichiarate: in un DW reale spesso si omettono per velocizzare il load, ma a questa scala documentano l'integrità e sono un plus in demo (violazioni ETL impossibili).

## 6. Preparazione all'orale — domande probabili su questa fase

1. *Perché star e non snowflake?* → Ridondanza innocua in un DB read-only caricato da ETL controllato; meno join; snowflake giustificato solo da dimensioni enormi. Saper citare il trade-off normalizzazione vs prestazioni.
2. *Perché chiavi surrogate invece di alpha-3?* → Indipendenza dalle sorgenti, join su interi, gestione di 'Unknown'; la naturale resta come attributo (e vincolo UNIQUE).
3. *Cos'è response_id nel fatto?* → Dimensione degenere: chiave naturale conservata per lineage, senza dimension table.
4. *Quante righe ha il bridge e perché?* → ~150k: media ~6-7 linguaggi per rispondente × ~23k fatti. Molti-a-molti irriducibile a FK singola.
5. *Perché comp_adjusted può essere NULL?* → Paesi senza indice Numbeo: fatto conservato (principio: il DW non perde dati), misura derivata non calcolabile, esclusione naturale dalle query sul potere d'acquisto.
6. *La gerarchia geografica dove sta?* → Dentro dim_geography, denormalizzata (star): country → sub_region → region come colonne, dipendenze funzionali garantite dall'ETL a monte.

## 7. Prossimi passi (Fase 4 — ETL)

1. Setup PostgreSQL locale + database `dw_techworker`.
2. Script ETL Python (dal notebook): extract (kagglehub) → transform (R1-R6, mapping §5 Fase 1, split linguaggi, banding esperienza, calcolo comp_adjusted) → load (dimensioni prima, poi fatti, poi bridge).
3. Controlli di qualità post-load: conteggi attesi, FK coperte, spot-check su paesi campione.
