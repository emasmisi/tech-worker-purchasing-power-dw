# Progettazione Concettuale (DFM) — Fase 2

**Progetto:** Il Potere d'Acquisto del Tech Worker — Data Warehousing
**Corso:** Data Management A.A. 2025/26 — metodologia Golfarelli-Rizzi (slide del corso)
**Autori:** Emanuele Smisi, Fabrizio Pietrobono
**Data:** 13 luglio 2026
**Input:** Documento di Analisi delle Sorgenti (Fase 1)
**Diagramma:** `Fase2_DFM.svg`

---

## 1. Il fatto

| Elemento | Scelta | Motivazione |
|---|---|---|
| **Fatto** | RISPOSTA SURVEY | L'evento di interesse: la dichiarazione salariale/professionale di un singolo tech worker. |
| **Grana** | Una risposta al survey (~23.000 istanze dopo pulizia) | Grana più fine disponibile (raccomandazione della teoria): massima flessibilità di drill-down, mediane calcolabili, filtri analitici a valle (regola R4 di Fase 1). |

## 2. Le misure

| Misura | Definizione | Additività |
|---|---|---|
| `comp_usd` | ConvertedCompYearly (USD/anno, normalizzato da SO) | **Non additiva**: sommare stipendi non ha significato. Operatori validi: AVG, MEDIAN, MIN/MAX, COUNT, percentili. |
| `comp_adjusted` | `comp_usd / (col_index / 100)` — calcolata in ETL | Non additiva, come sopra. È la misura che risponde alla business question: "salario a parità di costo della vita" (base: New York = 100). |

**Decisione D1 — indici costo-vita.** Gli indici Numbeo hanno grana *paese*, non rispondente: concettualmente non sono misure del fatto ma proprietà del contesto geografico. Doppia rappresentazione: (a) attributi descrittivi del livello `country`; (b) misura derivata `comp_adjusted` pre-calcolata in ETL sul fatto. Vantaggi: le query OLAP centrali non richiedono join+divisione al volo; gli indici restano consultabili per analisi secondarie. Alternativa scartata: secondo fatto a grana paese (multi-fatto) — corretto in teoria ma sovradimensionato per lo scopo.

**Nota su `comp_adjusted`:** si usa il *Cost of Living Index* (esclude affitti). Il *Cost of Living Plus Rent Index* resta disponibile come attributo per analisi di sensibilità. Il *Local Purchasing Power Index* di Numbeo NON va usato nella formula: è già una misura di potere d'acquisto (ne risulterebbe un doppio aggiustamento); lo teniamo come attributo di confronto.

## 3. Le dimensioni

| # | Dimensione | Attributi (→ = gerarchia, roll-up) | Note |
|---|---|---|---|
| 1 | **Geografia** | country → sub_region → region | Descrittivi su country: alpha-3, col_index, rent_index, groceries_idx, restaurant_idx, lpp_index. Fonte: master GEO corretto (R6 Corea). |
| 2 | **Esperienza** | years_code_pro → fascia_esp | **D2**: Junior 0–2, Mid 3–5, Senior 6–10, Expert 11+. Gerarchia: dettaglio numerico conservato, banding modificabile senza rifare l'ETL dei fatti. ETL: convertire le stringhe "Less than 1 year" → 0 e "More than 50 years" → 51. |
| 3 | **Ruolo** | dev_type | 0,1% nulli → 'Unknown'. |
| 4 | **Istruzione** | ed_level | — |
| 5 | **Organizzazione** | org_size | — |
| 6 | **Modalità lavoro** | remote_work | Remote / Hybrid / In-person. |
| 7 | **Impiego** | employment | — |
| 8 | **Settore** | industry | 31,8% nulli → membro 'Unknown' (R3). |
| 9 | **Età** | age | Fasce già presenti nel dato SO. |
| 10 | **Linguaggio** | language | **Arco multiplo** (molti-a-molti): un rispondente conosce N linguaggi → bridge table nello schema logico. **D3**: solo `LanguageHaveWorkedWith` (competenze effettive, scope controllato); estensibile ad altre famiglie tech. |

**Gerarchie — il fondamento teorico.** Una gerarchia è valida se ogni attributo determina funzionalmente il successivo (dipendenza molti-a-uno): ogni country appartiene a una sola sub_region, ogni sub_region a una sola region. Verificato sul master GEO in Fase 1.

**Arco multiplo e doppio conteggio.** Aggregando per `language`, un rispondente con 5 linguaggi contribuisce a 5 gruppi: le query per linguaggio devono usare conteggi/medie *per gruppo* (corretto per "salario mediano di chi usa Python") e mai sommare tra linguaggi (doppio conteggio). Da dichiarare esplicitamente in presentazione — è la domanda d'orale più probabile sul bridge.

## 4. Workload preliminare (validazione dello schema)

La teoria richiede di validare lo schema concettuale contro le query attese. Tutte le seguenti sono esprimibili sul DFM:

1. **Q1** Top-N paesi per `comp_adjusted` mediano (soglia ≥30 rispondenti) — la business question.
2. **Q2** Confronto `comp_usd` vs `comp_adjusted` mediani per paese: chi guadagna/perde posizioni aggiustando per il costo della vita?
3. **Q3** Roll-up: potere d'acquisto mediano per sub_region e region.
4. **Q4** `comp_adjusted` per fascia_esp × region: dove conviene essere junior? E senior?
5. **Q5** Drill-down: per un ruolo (dev_type) fissato, classifica paesi per comp_adjusted.
6. **Q6** Remote vs in-person: differenziale di potere d'acquisto per paese/region.
7. **Q7** (bridge) Salario mediano aggiustato di chi usa un dato linguaggio, per region.
8. **Q8** Slice: solo full-time (employment) — robustezza di Q1.

## 5. Decisioni registrate in Fase 2

| ID | Decisione | Motivazione sintetica |
|---|---|---|
| D1 | Indici Numbeo = attributi di country + misura derivata `comp_adjusted` in ETL | Grana paese ≠ grana fatto; OLAP semplice sulla misura chiave |
| D2 | Esperienza come gerarchia anni → fascia (0–2 / 3–5 / 6–10 / 11+) | Dettaglio + leggibilità; banding modificabile |
| D3 | Bridge solo sui linguaggi | Scope controllato, pattern dimostrato, estensibile |

## 6. Preparazione all'orale — domande probabili su questa fase

1. *Perché la grana a singolo rispondente e non aggregata per paese?* → Grana più fine = massima flessibilità; aggregare in ETL distrugge informazione irreversibilmente; le dimensioni individuali (ruolo, esperienza...) esistono solo a questa grana.
2. *Le vostre misure sono additive?* → No: non additive. Il salario non si somma tra rispondenti/paesi; si usano AVG/MEDIAN/COUNT/percentili. (Distinguere: additiva / semi-additiva / non additiva.)
3. *Come gestite l'attributo multi-valore dei linguaggi?* → Arco multiplo nel DFM, bridge table nello schema logico; consapevolezza del doppio conteggio nelle aggregazioni per linguaggio.
4. *Perché gli indici costo-vita non sono misure del fatto?* → Hanno grana paese: sarebbero ridondanti su ~23k fatti e concettualmente sono proprietà del contesto geografico. La misura derivata li porta a grana fatto in modo controllato.
5. *Cosa garantisce la correttezza della gerarchia geografica?* → Dipendenze funzionali molti-a-uno verificate sul master ISO (country → sub_region → region).
6. *Perché non c'è la dimensione tempo?* → Tutte le sorgenti sono snapshot 2024: una dimensione temporale con un solo membro non abilita alcuna analisi. Scelta documentata, coerente con la business question (confronto tra paesi, non trend).

## 7. Prossimi passi (Fase 3 — progettazione logica)

- Traduzione DFM → **star schema**: tabella dei fatti + tabelle dimensione denormalizzate.
- Chiavi surrogate per tutte le dimensioni.
- Bridge table `fact ↔ language`.
- Scelte da discutere: dimensioni degeneri vs tabelle; star vs snowflake per la geografia (attesa: star, con motivazione).
