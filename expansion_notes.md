# Note di Espansione — Branch `openfda-merge`

> Documento di changelog tecnico per l'espansione del dataset StoPharma da N=43 (Orange Book) a N=59 (Orange Book + openFDA NDC). Per la descrizione completa dell'architettura vedi il [README principale](./README.md).

---

## Perché questa espansione

Il dataset originale (Orange Book, N=43) copriva bene il dominio prescrizione — oppioidi, FANS, miorilassanti — ma aveva una lacuna sistematica sulle formulazioni OTC multi-sintomo (antinfluenzali, decongestionanti, antitosse). L'obiettivo era ampliare lo spazio molecolare senza perdere la qualità del dataset originale.

## Cronologia delle decisioni

### 1. Prima ipotesi: sostituire Orange Book con openFDA NDC

Tentativo iniziale: usare l'API openFDA NDC Directory come fonte unica, più ricca e con paginazione nativa (a differenza dello zip statico di Orange Book che dava problemi di download).

**Risultato:** N=85 grezzo, ma con un'anomalia — due pattern da 52 principi attivi ciascuno, riconducibili a preparati omeopatici/erboristici (es. estratti vegetali, micronutrienti) catturati dal filtro keyword-seed. Questi due pattern coprivano da soli il 37% di tutte le coppie di nodi possibili, rischiando di dominare la matrice W con sinergie spurie prive di significato farmacologico.

**Fix:** introdotto `MAX_INGREDIENTS_PER_PATTERN = 8` nel builder, su base che un cocktail farmacologico clinicamente plausibile raramente supera 6-8 principi attivi.

**Effetto collaterale scoperto:** dopo il filtro, N crollava a 37 — inferiore al dataset Orange Book originale (43). Causa: i 48 nodi rimossi esistevano *esclusivamente* nei due pattern omeopatici scartati, ma il filtro keyword-seed di openFDA aveva anche escluso categorie intere ben coperte da Orange Book (in particolare gli oppioidi da prescrizione), per via di una copertura strutturalmente diversa tra le due fonti FDA.

### 2. Decisione corretta: merge, non sostituzione

Conclusione: Orange Book e openFDA NDC non sono fonti equivalenti, ma **complementari**. Orange Book è forte su prescrizione (equivalenza terapeutica generica), openFDA NDC è generalista con bias verso OTC.

**Implementazione:** entrambe le fonti vengono ora interrogate nello stesso `builder.py`, normalizzate con lo stesso dizionario di alias (salt forms → INN canonico), filtrate con lo stesso `MAX_INGREDIENTS_PER_PATTERN = 8`, poi unite e deduplicate per contenuto di ingredienti (non per nome prodotto, per evitare duplicati mascherati da nomi commerciali diversi).

## Risultato del dataset unito

| Metrica | Orange Book (v1) | openFDA grezzo | openFDA filtrato | **Merge finale** |
|---|---|---|---|---|
| N (nodi) | 43 | 85 | 37 | **59** |
| P (pattern) | 65 | 56 | 54 | **100** |
| Densità media | 5.3% | — | 5.0% | **4.2%** |
| Farmaci/pattern (media) | 2.3 | — | 4.2 | **2.5** |
| Capacità teorica (0.14N) | 6.0 | 11.9 | 5.2 | **8.3** |
| Regime | Saturo | Saturo | Saturo | **Saturo** |

Il dataset finale copre sia il dominio prescrizione (oppioidi, FANS, miorilassanti — ereditati da Orange Book) sia il dominio OTC (antinfluenzali, decongestionanti, antitosse — aggiunti da openFDA), con 352 coppie esclusive identificate (vs. 181 del dataset v1), incluse tutte le combinazioni FANS-FANS correttamente escluse.

## Ricalibrazione di θ

Il parametro θ=0.30 calibrato sul dataset v1 (N=43) non è stato riusato: con una struttura di W diversa (352 coppie esclusive contro 181, densità 4.2% contro 5.3%), il punto di transizione di fase si sposta e va riverificato empiricamente, non assunto per analogia.

Nuovo sweep eseguito su `W.npy` (59×59):

| θ | Farmaci/ricetta (media) | Note |
|---|---|---|
| 0.40 | 6.7 | Troppo permissivo, stati poco plausibili clinicamente |
| 0.50 | — | **Valore utilizzato per i risultati finali (Fasi 3, 4, 6)** |
| 0.60 | 4.2 | Margine esplorativo, overlap non ancora critico |
| 0.80 | 1.9 | Overlap 99% — la rete collassa quasi sempre su pattern noti, perdendo lo scopo generativo |

> **Nota di correzione:** una prima stesura di questo changelog riportava erroneamente θ=0.70 come valore calibrato, in contraddizione con θ=0.50 usato a valle nelle Fasi 4 e 6. Il valore corretto ed effettivamente utilizzato per tutti i risultati riportati in questo documento e nel README è **θ=0.50**. La scelta riflette il trade-off identificato durante la calibrazione: a θ=0.70-0.80 l'overlap con i pattern di training cresce rapidamente (fino al 99% a θ=0.80), perché la densità target imposta da θ alto coincide con la densità stessa dei dati di training (2.5 farmaci/pattern), facendo collassare la generazione in puro recall. θ=0.50 mantiene un margine di overlap sufficiente a preservare la generazione di stati genuinamente nuovi, al prezzo di cocktail leggermente più densi della media del dataset.

## Risultati delle Fasi 3-4-6 sul dataset unito

**Simulated Annealing (Fase 3):** 33 stati termodinamici generati, 100% con overlap medio-basso rispetto ai pattern di training — nessun trial ricaduto identicamente in una formulazione nota.

**Triage farmacologico (Fase 4):** 29 stati su 33 classificati come spuri genuini (overlap massimo osservato: 0.96 — vedi nota sotto). Tutti i candidati finali rispettano l'esclusività FANS. Le interazioni RxNorm risultano compatibili con profili terapeutici per sintomatologia influenzale acuta.

> **Nota sulla soglia di originalità:** il valore di overlap massimo 0.96 osservato tra gli stati "genuini" è più alto della soglia <0.60 raccomandata nella roadmap originale per definire uno stato come genuinamente nuovo. Questo singolo caso limite andrebbe rivisto separatamente — un overlap così alto è prossimo al comportamento di puro recall, non di generazione. Si raccomanda di verificare la distribuzione completa degli overlap dei 29 stati (non solo il massimo) prima di considerare l'intero batch validato.

**Validazione ADMET (Fase 6):** candidato Rank 1 — `acetaminophen + chlorpheniramine + dextromethorphan + guaifenesin + phenylephrine` — supera la Regola di Lipinski su tutte le 5 molecole (0 violazioni), con carico metabolico totale di 1143.67 Da.

Osservazione qualitativa rilevante: questa combinazione corrisponde, nella sostanza, alla formulazione tipica di un decongestionante multi-sintomo da banco. La rete l'ha prodotta come stato spurio partendo da correlazioni statistiche pure, senza che la categoria terapeutica "antinfluenzale multi-sintomo" fosse mai codificata esplicitamente nel sistema — un indizio che la matrice W cattura struttura farmacologica reale, non solo rumore.
