# Documento di Analisi delle Sorgenti — Fase 1

**Progetto:** Il Potere d'Acquisto del Tech Worker — Data Warehousing
**Corso:** Data Management A.A. 2025/26, Sapienza — Opzione 2 (progetto tipo [DW])
**Autori:** Emanuele Smisi, Fabrizio Pietrobono
**Data:** 13 luglio 2026
**Stato:** Fase 1 completata — proposta approvata dal tutor

---

## 1. Business question

*Quali paesi offrono il miglior potere d'acquisto reale per i lavoratori tech?*

Il salario nominale non basta: 60.000 USD a Zurigo e a Buenos Aires non sono la stessa cosa. Il DW integra i salari dichiarati dagli sviluppatori (Stack Overflow Survey 2024) con l'indice del costo della vita per paese (Numbeo 2024), tramite un master geografico ISO, per permettere analisi multidimensionali del potere d'acquisto per paese, ruolo, esperienza, modalità di lavoro, ecc.

---

## 2. Le tre sorgenti

### 2.1 Stack Overflow Annual Developer Survey 2024 (sorgente primaria — fatti)
- **Slug Kaggle:** `berkayalan/stack-overflow-annual-developer-survey-2024` (file `survey_results_public.csv`)
- **Dimensioni:** 65.437 righe × 114 colonne. Grana: singola risposta al survey.
- **Ruolo:** fornisce la misura (compenso) e gli attributi individuali che diventeranno dimensioni.

### 2.2 Country Mapping ISO/Continent/Region (master geografico)
- **Slug Kaggle:** `andradaolteanu/country-mapping-iso-continent-region` (file `continents2.csv`)
- **Dimensioni:** 249 righe. Grana: paese.
- **Ruolo:** chiave canonica di integrazione (codice ISO alpha-3) e gerarchia geografica Country → Sub-region → Region.

### 2.3 Cost of Living Index by Country 2024 (sorgente contestuale)
- **Slug Kaggle:** `myrios/cost-of-living-index-by-country-by-number-2024`
- **Dimensioni:** 121 righe × 8 colonne. Grana: paese. Indici Numbeo (base 100 = New York): Cost of Living, Rent, Groceries, Restaurant, Local Purchasing Power.
- **Ruolo:** contestualizza il salario nominale, abilita il calcolo del potere d'acquisto.

---

## 3. Selezione delle colonne (decisioni motivate)

| Scelta                                 | Alternativa scartata     | Motivazione                                                                                                                                                                                                                                                                      |
| -------------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ConvertedCompYearly` come misura      | `CompTotal`              | ConvertedCompYearly è il compenso annuo **normalizzato in USD** da Stack Overflow; CompTotal è in valuta locale, non confrontabile tra paesi (essenza della business question). Con CompTotal i "validi" erano 33.740, ma inquinati; con la colonna corretta sono 23.435 puliti. |
| `YearsCodePro` per l'esperienza        | `YearsCode`              | L'analisi riguarda i *tech worker*: conta l'esperienza professionale, non quella hobbistica.                                                                                                                                                                                     |
| `LanguageHaveWorkedWith` per gli skill | `LanguageWantToWorkWith` | Competenze effettive, non aspirazioni. Attributo multi-valore (separatore `;`) → bridge table.                                                                                                                                                                                   |

**Lezione metodologica:** la selezione per substring aveva inizialmente scelto CompTotal (match prima di ConvertedCompYearly). Verificare sempre la semantica della colonna, non solo il nome.

---

## 4. Qualità dei dati e regole di pulizia

Tutte le regole sono esplicite, motivate e applicate in ETL (mai pulizia silenziosa).

**R1 — Compenso valido.** Si tengono solo i rispondenti con `ConvertedCompYearly` non nullo: 23.435 su 65.437 (35,8%). Un fatto senza misura non contribuisce all'analisi.

**R2 — Outlier: taglio 1°–99° percentile.** La distribuzione presenta valori implausibili (min 1 USD/anno, max 16,2 M USD/anno; mediana 65.000). Si escludono i valori sotto il 1° percentile (~208 USD) e sopra il 99° (~394.000 USD). Regola statistica standard, riproducibile, elimina il 2% più implausibile delle auto-dichiarazioni.

**R3 — Industry: membro 'Unknown'.** La colonna ha 31,8% di nulli. Pratica DW standard: i nulli diventano un membro esplicito della dimensione. Non si buttano fatti per una dimensione secondaria e la dimensione resta interrogabile.

**R4 — Soglia minima rispondenti per paese: applicata in OLAP, non in ETL.** Il DW carica tutti i fatti puliti alla grana più fine; la soglia (es. ≥30 rispondenti/paese) è un filtro nelle query analitiche. Principio: il DW non perde informazione, le scelte analitiche stanno a valle e restano modificabili senza ricaricare.

**R5 — Esclusioni documentate (SO):** `Nomadic` (4 risp.: non è un paese) e `Kosovo` (4 risp.: privo di codice ISO 3166 ufficiale, assente dal master geografico).

**R6 — Correzione del master geografico (Corea).** Il CSV `continents2.csv` contiene un errore: la riga con nome "South Korea" ha codice alpha-3 **PRK** (Corea del Nord); la Corea del Sud corretta è "Korea, Republic of" (KOR). Correzione in ETL: la riga PRK viene rinominata "North Korea"; i mapping puntano a KOR per la Corea del Sud. Dimostra perché l'integrazione si fa sui codici ISO e non sui nomi: anche il master va validato.

**Nulli sulle altre dimensioni candidate:** trascurabili (0–0,4%) → gestiti con membro 'Unknown' senza impatto.

---

## 5. Riconciliazione dei nomi paese (sfida ETL centrale)

**Strategia:** chiave canonica = codice **ISO alpha-3** del master geografico. Nessuna join diretta SO↔COSTO: entrambe le sorgenti convergono sul master (SO→GEO, COSTO→GEO), poi le join avvengono sui codici.

Match esatti senza pulizia: SO↔GEO 158/185; SO↔COSTO 105/185. I mismatch includevano i paesi a maggior peso statistico (USA: 4.677 risp.; UK: 1.391; Russia: 258) — senza riconciliazione l'analisi sarebbe stata inutilizzabile.

### 5.1 Mapping SO → GEO (21 voci)

| Nome in Stack Overflow                               | Nome canonico (GEO)                    |
| ---------------------------------------------------- | -------------------------------------- |
| Bosnia and Herzegovina                               | Bosnia And Herzegovina                 |
| Cape Verde                                           | Cabo Verde                             |
| Congo, Republic of the...                            | Congo                                  |
| Côte d'Ivoire                                        | Côte D'Ivoire                          |
| Democratic People's Republic of Korea                | North Korea (riga PRK corretta, v. R6) |
| Democratic Republic of the Congo                     | Congo (Democratic Republic Of The)     |
| Hong Kong (S.A.R.)                                   | Hong Kong                              |
| Iran, Islamic Republic of...                         | Iran                                   |
| Lao People's Democratic Republic                     | Laos                                   |
| Libyan Arab Jamahiriya                               | Libya                                  |
| Palestine                                            | Palestine, State of                    |
| Republic of Korea                                    | Korea, Republic of (KOR — v. R6)       |
| Republic of Moldova                                  | Moldova                                |
| Republic of North Macedonia                          | Macedonia                              |
| Russian Federation                                   | Russia                                 |
| Syrian Arab Republic                                 | Syria                                  |
| United Kingdom of Great Britain and Northern Ireland | United Kingdom                         |
| United Republic of Tanzania                          | Tanzania                               |
| United States of America                             | United States                          |
| Venezuela, Bolivarian Republic of...                 | Venezuela                              |
| Viet Nam                                             | Vietnam                                |

### 5.2 Mapping COSTO → GEO (5 voci)

| Nome nel Cost of Living | Nome canonico (GEO) |
|---|---|
| Hong Kong (China) | Hong Kong |
| Kosovo (Disputed Territory) | — escluso (v. R5) |
| North Macedonia | Macedonia |
| Palestine | Palestine, State of |
| South Korea | Korea, Republic of (KOR — v. R6) |
| Trinidad And Tobago | Trinidad and Tobago |

### 5.3 Copertura post-riconciliazione (verificata)

- Fatti validi: **23.435**
- Paesi rilevanti (≥30 rispondenti validi): **69** — copertura ≥50: 58 paesi; ≥100: 39; ≥200: 22
- Paesi rilevanti con dato costo-vita: **69/69 (100%)**
- Residui non riconciliati: solo il singolo rispondente "North Korea" (sotto soglia, irrilevante)

---

## 6. Grana del fatto e candidati per il DFM (input Fase 2)

**Grana scelta: singola risposta al survey** (un fatto = un rispondente, ~23.000 fatti dopo pulizia). Motivazione: la teoria raccomanda la grana più fine disponibile; massima flessibilità OLAP (drill-down su ogni dimensione, mediane calcolabili); coerente con R4.

**Misure candidate:**
- `ConvertedCompYearly` (USD/anno) — misura base
- *Potere d'acquisto* = compenso / (Cost of Living Index / 100) — misura derivata, cuore della business question (da definire in Fase 2 se calcolata in ETL o a query time; gli indici Numbeo sono a grana paese)

**Dimensioni candidate e gerarchie:**

| Dimensione | Attributi / gerarchia | Note |
|---|---|---|
| Geografia | Country → Sub-region → Region (continente) | Da GEO; include gli indici costo-vita come attributi del paese (da discutere in Fase 2) |
| Ruolo | DevType | 0,1% nulli |
| Istruzione | EdLevel | pulita |
| Esperienza | YearsCodePro → fasce (es. junior/mid/senior) | banding da definire in Fase 2 |
| Organizzazione | OrgSize | pulita |
| Modalità lavoro | RemoteWork | pulita |
| Impiego | Employment | pulita |
| Settore | Industry (con 'Unknown') | 31,8% nulli → R3 |
| Età | Age (fasce già nel dato) | pulita |
| Tecnologie | LanguageHaveWorkedWith | **multi-valore → bridge table** |

---

## 7. Limiti documentati

1. **Dati auto-dichiarati:** i salari sono self-reported; mitigato da R2, resta un limite intrinseco della sorgente.
2. **Skew geografico residuo:** USA e Europa sovrarappresentati; mitigato dalla soglia R4 e dall'uso di statistiche robuste (mediana) nelle analisi.
3. **Fotografia singola (2024):** tutte le sorgenti sono snapshot 2024 → il DW non ha dimensione temporale significativa. Scelta consapevole, coerente con la business question (confronto tra paesi, non trend).
4. **Indici a grana paese:** il costo della vita è nazionale, non cittadino (Zurigo ≠ media svizzera). Limite della sorgente, da citare in presentazione.

---

## 8. Prossimi passi

- **Fase 2 — Progettazione concettuale (DFM):** fatto, misure, dimensioni, gerarchie, bridge table per le tecnologie, gestione degli indici costo-vita (attributi dimensionali vs misure a grana paese).
- **Fase 3 — Progettazione logica:** star schema, chiavi surrogate.
- **Fase 4 — ETL** (Python → PostgreSQL): implementazione delle regole R1–R6 e dei mapping §5.
- **Fase 5 — OLAP:** query che rispondono alla business question.
- **Fase 6 — Presentazione** (10–15 min + demo 5 min) e preparazione orale.
