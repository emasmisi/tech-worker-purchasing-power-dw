# Risultati OLAP e Interpretazione — Fase 5

**Progetto:** Il Potere d'Acquisto del Tech Worker — DW su PostgreSQL
**Autori:** Emanuele Smisi, Fabrizio Pietrobono · **Data:** 13 luglio 2026
**Fonte:** `olap_queries.sql` eseguito su `dw_techworker` (22.909 fatti, Numbeo 2024)

---

## I 5 messaggi chiave (per le slide)

### 1. Gli USA vincono anche in termini reali — ma il podio sorprende (Q1)
Mediana aggiustata: **USA 198.864** (nominale 140.000), **Israele 180.756**, **Georgia 150.210**. Il costo della vita non scalfisce il primato USA; ma al 3° posto c'è la Georgia, davanti a Irlanda, Australia, Canada e UK. Polonia (6ª) e Lituania (11ª) battono la maggior parte dell'Europa occidentale.

### 2. I "vincitori nascosti": chi guadagna posizioni aggiustando (Q2)
Le scalate maggiori dal ranking nominale al reale: **Georgia +26, Cina +25, Argentina +25, Ucraina +25** (e con n=1.410 il dato ucraino è statisticamente solido), Sudafrica +21, Romania +19, Polonia +18. Il fenomeno non evidente dai dati grezzi: *salario medio-basso + costo della vita molto basso > salario alto + costo della vita alto*.

### 3. Il roll-up ribalta la geografia europea (Q3)
A livello di sub-region: Northern America 184.659, poi — dentro l'Europa — **l'Est (113.715) supera l'Ovest (107.836)** in termini reali. Mediana mondiale: 120.739. (Melanesia n=2: sotto soglia, si cita solo come esempio del perché serve R4.)

### 4. Il remoto paga, ovunque e tanto (Q6)
Differenziale mediano remote vs in-person: Americas 187.075 vs 119.318 (+57%), Europa +58%, **Asia +95%, Africa +134%**. Lettura: il lavoro remoto sgancia il salario dal mercato locale ma non dal costo della vita locale — è il moltiplicatore del potere d'acquisto nelle economie a basso costo.

### 5. Esperienza: stessa gerarchia, pendenze diverse (Q4)
Il gradiente junior→expert c'è ovunque, ma con pendenze molto diverse: in Asia un expert guadagna ~5,5× un junior (170.774 vs 31.150), in Africa ~9× (163.204 vs 18.024), nelle Americhe ~2,2× (213.068 vs 98.863). Nei mercati emergenti l'esperienza è il fattore più discriminante.

## Risultati di supporto

- **Q5 (slice full-stack):** stessa testa di classifica di Q1 → il pattern non dipende dal ruolo. Curiosità: il Giappone entra in top 5 per i full-stack.
- **Q7 (bridge linguaggi):** in testa linguaggi di nicchia/funzionali — Erlang 164.694, Elixir, Clojure, Scala, Ruby. Lettura: premio di rarità/seniority degli stack, non causalità. **Caveat anti doppio-conteggio** da dichiarare: ogni rispondente contribuisce a tutti i linguaggi che conosce (media 5,28); legittimo confrontare le mediane tra gruppi, vietato sommarle.
- **Q8 (robustezza, solo full-time):** top 10 sostanzialmente identica a Q1 (USA 205.966, Israele, Georgia...) → le conclusioni non dipendono dal mix di tipi di impiego.

## Caveat da dichiarare in presentazione (onestà = punti all'orale)

1. **Numerosità basse ai vertici:** Georgia n=46, Uruguay n=37, Cipro n=32 — sopra soglia R4 ma da leggere con cautela; i dati solidi (Polonia 581, Ucraina 1.410, UK 1.373) confermano comunque il pattern.
2. **Self-reported:** salari auto-dichiarati, mitigato da R2 (taglio 1°-99° percentile).
3. **Indici a grana paese:** il costo vita è nazionale (Tbilisi ≠ media Georgia; SF ≠ media USA).
4. **Correlazione, non causalità** (in particolare Q7): chi usa Erlang non guadagna di più *perché* usa Erlang.
5. **Snapshot 2024:** nessuna dimensione temporale; confronto tra paesi, non trend.

## Mappa query → operazione OLAP (per la demo)

| Query | Operazione OLAP dimostrata | Costrutto SQL |
|---|---|---|
| Q1 | Aggregazione con soglia (R4) | percentile_cont, HAVING |
| Q2 | Ranking analitico | window function RANK() OVER |
| Q3 | **Roll-up** sulla gerarchia del DFM | GROUP BY ROLLUP, GROUPING() |
| Q4 | Dice (2 dimensioni) / pivot | GROUP BY multiplo |
| Q5 | **Slice** + drill-down | WHERE su attributo dimensionale |
| Q6 | Aggregati condizionali affiancati | FILTER (WHERE ...) |
| Q7 | Interrogazione del **bridge** | join su tabella ponte |
| Q8 | Slice di robustezza | WHERE su employment |
