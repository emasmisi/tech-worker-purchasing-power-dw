# Demo Live — Scaletta minuto per minuto (5:00)

**Obiettivo:** dimostrare che il DW esiste, funziona, e risponde alla business question — usando i termini giusti (star schema, grana, roll-up, bridge, misura derivata). Il tutor deve vedere *cognizione di causa*, non velocità di digitazione.

**Regola d'oro:** niente digitazione live. Le query sono in `demo_live.sql`, già aperte nel client. Si seleziona, si esegue, si commenta. La dashboard (`demo_app.py`) è già in esecuzione in una scheda del browser.

---

## Divisione dei ruoli (il tutor valuta la cooperazione)

- **Chi guida** (tastiera): esegue le query, indica le righe col cursore.
- **Chi narra**: pronuncia il messaggio di ogni query PRIMA di eseguirla, poi legge il risultato.
- Scambiatevi i ruoli a metà (dopo D3): entrambi dovete toccare sia la tastiera sia la narrazione.

---

## Scena per scena

### D1 — Il data warehouse (0:00 – 0:40)
**Dire prima:** «Questo è lo star schema implementato su PostgreSQL: una fact table a grana singolo rispondente, dieci dimension table con chiavi surrogate, e una bridge table per l'attributo multi-valore dei linguaggi.»
**Eseguire D1.** Indicare: 22.909 fatti, 121.055 righe di bridge.
**Chiudere con:** «Tutto è caricato da uno script ETL Python idempotente che implementa le regole di pulizia documentate.»

### D2 — Un fatto, tutto lo schema (0:40 – 1:25)
**Dire prima:** «Vi mostro la join a stella completa su un caso concreto: la Georgia, terza al mondo per potere d'acquisto — lo vedremo tra poco.»
**Eseguire D2.** Indicare le colonne da sinistra a destra: «chiave naturale conservata come dimensione degenere → gerarchia geografica → fascia d'esperienza → e qui la misura derivata: comp_adjusted = salario / (indice costo vita / 100), calcolata in ETL.»

### D3 — La business question (1:25 – 2:15) ★ il cuore
**Dire prima:** «La domanda del progetto: quali paesi offrono il miglior potere d'acquisto reale a un tech worker? Mediana, non media: le misure salariali non sono additive e la mediana è robusta agli outlier.»
**Eseguire D3.** Leggere il podio: «USA primi anche in termini reali. Ma guardate il resto: Georgia terza, Polonia sesta — davanti a Canada e Regno Unito. Il confronto tra le due colonne è il valore del progetto.»

### D4 — Il roll-up (2:15 – 3:05) ★ il momento "teoria"
**Dire prima:** «Ora combino uno slice sull'Europa con un roll-up lungo la gerarchia del DFM: GROUP BY ROLLUP calcola in una sola query tutte le sub-region più il totale Europa.»
**Eseguire D4.** Indicare: «Est Europa 113.715, Ovest Europa 107.836: in termini reali l'Europa orientale ha superato quella occidentale. La riga "** TOTALE EUROPA **" è il subtotale generato da ROLLUP — la gerarchia progettata nel DFM che diventa SQL. Dettaglio da sapere: il WHERE agisce prima del ROLLUP, per questo il subtotale è correttamente "Europa" e non "mondo".»

### D5 — Il bridge (3:05 – 3:55)
**Dire prima:** «Infine l'attributo multi-valore: ogni rispondente conosce in media 5,3 linguaggi, quindi la relazione è molti-a-molti — risolta con la bridge table.»
**Eseguire D5.** Commentare: «In testa linguaggi di nicchia come Erlang ed Elixir: un premio di rarità. Nota metodologica: ogni rispondente contribuisce a tutti i suoi linguaggi — le mediane per gruppo sono legittime, sommarle tra linguaggi sarebbe doppio conteggio.»

### D6 — Il livello BI: la dashboard (3:55 – 4:45) ★ il finale
**Passare alla scheda del browser (già aperta su localhost:8501).**
**Dire prima:** «A warehouse ultimately serves analysts — so we built a thin BI layer on top of it. One SQL query drives everything you see.»
**Fare, in quest'ordine:**
1. Scheda *World map*: «This map is drawn from the ISO alpha-3 codes — it exists because we reconciled every source on the canonical key.»
2. **Muovere lo slider R4** da 30 a 50 e tornare alla scheda *Ranking*: «Watch Georgia leave the ranking: the slider only changes the HAVING clause. No reload, no ETL — the warehouse keeps full grain, analytical thresholds live at query time. This is rule R4, live.»
3. Aprire un attimo "SQL under the hood": «The dashboard doesn't hide the warehouse — it exhibits it.»
**Non indugiare oltre**: 50 secondi, poi chiudere.

### Chiusura (4:45 – 5:00)
«Il DW è interamente locale e riproducibile: un comando ricrea tutto da zero. Ogni scelta di progetto è documentata fase per fase. Domande?»

---

## Query bonus (solo su domanda o tempo extra)

| Se il tutor chiede... | Lancia |
|---|---|
| «E il lavoro remoto?» | B1 — remote vs in-person per region (+95% Asia, +134% Africa) |
| «Come avete integrato le sorgenti?» / dubbi ETL | B2 — il master ISO con l'errore Corea corretto (KOR/PRK) |
| «Chi ci guadagna dall'aggiustamento?» | B3 — window function: Georgia +26 posizioni, Ucraina +25 |

---

## Domande probabili DURANTE la demo (risposte pronte)

1. **«Perché la mediana e non la media?»** → Misure non additive e distribuzione right-skewed; la media resterebbe sensibile agli outlier anche dopo il taglio 1°-99° percentile.
2. **«Perché n ≥ 30?»** → Soglia di significatività applicata a query time, non in ETL: il DW conserva la grana più fine e la soglia resta modificabile (regola R4) — la dashboard lo dimostra dal vivo.
3. **«La Georgia con 46 rispondenti è affidabile?»** → Sopra soglia ma dichiarata come dato da leggere con cautela; il pattern è confermato da campioni ampi (Polonia 581, Ucraina 1.410).
4. **«Cosa succede se rilanciate l'ETL?»** → Idempotente: DROP SCHEMA e ricostruzione completa; stesso risultato a ogni run.
5. **«Perché PostgreSQL?»** → Suggerito dalle slide del corso; percentile_cont, ROLLUP/CUBE e window function coprono tutte le esigenze OLAP del progetto.

### Domande probabili sulla DASHBOARD

6. **«Cos'è questo strumento? Un prodotto BI?»** → «It's a ~150-line Python app we wrote with Streamlit, an open-source library. One parametrized SQL query — the same percentile_cont + RANK pattern of our workload — feeds all three views. We chose it over a BI product to keep the focus on the content, and because we wanted the SQL visible.»
7. **«Lo slider ricalcola il data warehouse?»** → «No: it only changes the HAVING threshold of the query. The warehouse is untouched — that's the point: full grain in storage, analytical choices at query time (rule R4).»
8. **«La mappa da dove prende la geografia?»** → «From dim_geography's ISO alpha-3 codes: the plotting library maps countries by ISO code natively. It works because reconciliation was done on codes, not names.»
9. **«I dati della dashboard sono pre-calcolati?»** → «No, live queries against PostgreSQL, with a short client-side cache (5 minutes) purely to avoid re-running the same query when switching tabs. Moving the slider always hits the database.»
10. **«Potevate usare Power BI / Tableau?»** → «Yes, and in a corporate setting we probably would. Here the didactic value was higher this way: we can show and defend every line, and no license is needed — the whole project runs on free software.»

---

## Checklist pre-demo (il giorno stesso, 30 minuti prima)

1. Postgres.app aperto e **Running** (verde).
2. Client SQL aperto e connesso a `dw_techworker`, `demo_live.sql` caricato.
3. **Dashboard avviata**: `python3 -m streamlit run demo_app.py` → scheda browser su localhost:8501 pronta, slider su 30.
4. **Prova generale completa**: D1→D6 una volta (se manca la vista `v_fact_geo`: rilanciare V0 da `olap_queries.sql`).
5. Font del client ingrandito; zoom del browser al 125% per la dashboard.
6. **Piano B**: screenshot di ogni risultato (incluse le 3 schede della dashboard) in `backup_demo/`. Se la dashboard non parte, la demo D1→D5 è completa da sola: D6 si salta senza drammi, è un bonus.
7. Niente internet richiesto: tutto locale.
8. Cronometro: prova generale sotto **4:40** per avere margine.

## Prove da fare con Fabrizio

- 2 prove complete cronometrate, una a testa per ruolo (lo scambio ora conviene dopo D3 o prima di D6).
- Ognuno deve saper rispondere a TUTTE le domande qui sopra — il tutor può rivolgersi a chi vuole.
