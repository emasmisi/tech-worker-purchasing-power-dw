# Demo Live — Scaletta minuto per minuto (5:00)

**Obiettivo:** dimostrare che il DW esiste, funziona, e risponde alla business question — usando i termini giusti (star schema, grana, roll-up, bridge, misura derivata). Il tutor deve vedere *cognizione di causa*, non velocità di digitazione.

**Regola d'oro:** niente digitazione live. Le query sono in `demo_live.sql`, già aperte nel client. Si seleziona, si esegue, si commenta.

---

## Divisione dei ruoli (il tutor valuta la cooperazione)

- **Chi guida** (tastiera): esegue le query, indica le righe col cursore.
- **Chi narra**: pronuncia il messaggio di ogni query PRIMA di eseguirla, poi legge il risultato.
- Scambiatevi i ruoli a metà (dopo D3): entrambi dovete toccare sia la tastiera sia la narrazione.

---

## Scena per scena

### D1 — Il data warehouse (0:00 – 0:45)
**Dire prima:** «Questo è lo star schema implementato su PostgreSQL: una fact table a grana singolo rispondente, dieci dimension table con chiavi surrogate, e una bridge table per l'attributo multi-valore dei linguaggi.»
**Eseguire D1.** Indicare: 22.909 fatti, 121.055 righe di bridge.
**Chiudere con:** «Tutto è caricato da uno script ETL Python idempotente che implementa le regole di pulizia documentate.»

### D2 — Un fatto, tutto lo schema (0:45 – 1:45)
**Dire prima:** «Vi mostro la join a stella completa su un caso concreto: la Georgia, terza al mondo per potere d'acquisto — lo vedremo tra poco.»
**Eseguire D2.** Indicare le colonne da sinistra a destra: «chiave naturale conservata come dimensione degenere → gerarchia geografica → fascia d'esperienza → e qui la misura derivata: comp_adjusted = salario / (indice costo vita / 100), calcolata in ETL.»
**Perché la Georgia:** prepara il colpo di scena di D3 e mostra salari georgiani nominali modesti con adjusted alto.

### D3 — La business question (1:45 – 2:45) ★ il cuore
**Dire prima:** «La domanda del progetto: quali paesi offrono il miglior potere d'acquisto reale a un tech worker? Mediana, non media: le misure salariali non sono additive e la mediana è robusta agli outlier.»
**Eseguire D3.** Leggere il podio: «USA primi anche in termini reali. Ma guardate il resto: Georgia terza, Polonia sesta — davanti a Canada e Regno Unito. Il confronto tra le due colonne è il valore del progetto: la colonna nominale da sola racconta un'altra storia, sbagliata.»

### D4 — Il roll-up (2:45 – 3:45) ★ il momento "teoria"
**Dire prima:** «Ora combino uno slice sull'Europa con un roll-up lungo la gerarchia del DFM: GROUP BY ROLLUP calcola in una sola query tutte le sub-region più il totale Europa.»
**Eseguire D4.** Indicare: «Est Europa 113.715, Ovest Europa 107.836: in termini reali l'Europa orientale ha superato quella occidentale. La riga "** TOTALE EUROPA **" è il subtotale generato da ROLLUP — la gerarchia progettata nel DFM che diventa SQL. Dettaglio da sapere: il WHERE agisce prima del ROLLUP, per questo il subtotale è correttamente "Europa" e non "mondo".»

### D5 — Il bridge (3:45 – 4:45)
**Dire prima:** «Infine l'attributo multi-valore: ogni rispondente conosce in media 5,3 linguaggi, quindi la relazione è molti-a-molti — risolta con la bridge table.»
**Eseguire D5.** Commentare: «In testa linguaggi di nicchia come Erlang ed Elixir: un premio di rarità. Nota metodologica: ogni rispondente contribuisce a tutti i suoi linguaggi — le mediane per gruppo sono legittime, sommarle tra linguaggi sarebbe doppio conteggio.»

### Chiusura (4:45 – 5:00)
«Il DW è interamente locale e riproducibile: un comando ricrea tutto da zero. Le regole di pulizia, i mapping di riconciliazione e ogni scelta di progetto sono documentati fase per fase. Domande?»

---

## Query bonus (solo su domanda o tempo extra)

| Se il tutor chiede... | Lancia |
|---|---|
| «E il lavoro remoto?» | B1 — remote vs in-person per region (+95% Asia, +134% Africa) |
| «Come avete integrato le sorgenti?» / dubbi ETL | B2 — il master ISO con l'errore Corea corretto (KOR/PRK): la prova che la riconciliazione va fatta sui codici, non sui nomi |
| «Chi ci guadagna dall'aggiustamento?» | B3 — window function: Georgia +26 posizioni, Ucraina +25 |

---

## Domande probabili DURANTE la demo (risposte pronte)

1. **«Perché la mediana e non la media?»** → Misure non additive e distribuzione con coda lunga; la media resterebbe sensibile agli outlier anche dopo il taglio 1°-99° percentile.
2. **«Perché n ≥ 30?»** → Soglia di significatività applicata a query time, non in ETL: il DW conserva la grana più fine e la soglia resta modificabile (regola R4).
3. **«La Georgia con 46 rispondenti è affidabile?»** → Sopra soglia ma dichiarata come dato da leggere con cautela; il pattern è confermato da paesi con campioni ampi (Polonia 581, Ucraina 1.410).
4. **«Cosa succede se rilanciate l'ETL?»** → Idempotente: DROP SCHEMA e ricostruzione completa; stesso risultato a ogni run.
5. **«Perché PostgreSQL?»** → Suggerito dalle slide del corso; percentile_cont, ROLLUP/CUBE e window function coprono tutte le esigenze OLAP del progetto.

---

## Checklist pre-demo (il giorno stesso, 30 minuti prima)

1. Postgres.app aperto e **Running** (verde).
2. Client aperto e connesso a `dw_techworker`, `demo_live.sql` caricato.
3. **Prova generale completa**: eseguire D1→D5 una volta (verifica anche che la vista `v_fact_geo` esista; se manca: rilanciare V0 da `olap_queries.sql`).
4. Font del client ingrandito (il tutor deve leggere da lontano / da schermo condiviso).
5. **Piano B**: `risultati_olap.txt` + screenshot di ogni risultato di demo in una cartella `backup_demo/` — se il DB non parte, si presenta dagli screenshot senza perdere punti sul contenuto.
6. Niente internet richiesto: tutto locale (punto di forza da menzionare se qualcosa va storto nella rete dell'aula).
7. Cronometro: prova generale sotto **4:30** per avere margine.

## Prove da fare con Fabrizio (prima della presentazione)

- 2 prove complete cronometrate, una a testa per ruolo.
- Ognuno deve saper rispondere a TUTTE le domande della sezione sopra e delle sezioni "orale" delle Fasi 2, 3 e 5 — il tutor può rivolgersi a chi vuole.
