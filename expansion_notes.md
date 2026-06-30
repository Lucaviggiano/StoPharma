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

## Risultati delle Fasi 3-4-6-7-8 sul dataset unito

**Simulated Annealing (Fase 3):** 33 stati termodinamici generati, 100% con overlap medio-basso rispetto ai pattern di training — nessun trial ricaduto identicamente in una formulazione nota.

**Triage farmacologico (Fase 4):** 29 stati su 33 classificati come spuri genuini (overlap massimo osservato: 0.96). Tutti i candidati finali rispettano l'esclusività FANS. Le interazioni RxNorm risultano compatibili con profili terapeutici per sintomatologia influenzale acuta.
---

### Validazione ADMET — Fase 6 (PubChem API)

#### Rank 1 (5 principi attivi)
**Cocktail:** `acetaminophen, chlorpheniramine, dextromethorphan hydrobromide, guaifenesin, phenylephrine`

| Molecola                      | MW (Da)  | LogP   | HBD | HBA | Violazioni Lipinski |
|-------------------------------|----------|--------|-----|-----|---------------------|
| acetaminophen                 | 151.16   | 0.50   | 2   | 2   | 0 [OK]              |
| chlorpheniramine              | 274.79   | 3.40   | 0   | 2   | 0 [OK]              |
| dextromethorphan hydrobromide | 352.30   | 0.00   | 1   | 2   | 0 [OK]              |
| guaifenesin                   | 198.22   | 1.40   | 2   | 4   | 0 [OK]              |
| phenylephrine                 | 167.20   | -0.30  | 3   | 3   | 0 [OK]              |

**Carico metabolico totale:** 1143.67 Da — Ottima biodisponibilità orale.

#### Rank 2 (7 principi attivi)
**Cocktail:** `acetaminophen, chlorpheniramine, dextromethorphan hydrobromide, guaifenesin, hydrocodone, phenylephrine, pseudoephedrine`

| Molecola                      | MW (Da)  | LogP   | HBD | HBA | Violazioni Lipinski |
|-------------------------------|----------|--------|-----|-----|---------------------|
| acetaminophen                 | 151.16   | 0.50   | 2   | 2   | 0 [OK]              |
| chlorpheniramine              | 274.79   | 3.40   | 0   | 2   | 0 [OK]              |
| dextromethorphan hydrobromide | 352.30   | 0.00   | 1   | 2   | 0 [OK]              |
| guaifenesin                   | 198.22   | 1.40   | 2   | 4   | 0 [OK]              |
| hydrocodone                   | 299.40   | 2.20   | 0   | 4   | 0 [OK]              |
| phenylephrine                 | 167.20   | -0.30  | 3   | 3   | 0 [OK]              |
| pseudoephedrine               | 165.23   | 0.90   | 2   | 2   | 0 [OK]              |

**Carico metabolico totale:** 1608.30 Da — Ottima biodisponibilità orale.

#### Rank 3 (8 principi attivi)
**Cocktail:** `acetaminophen, chlorpheniramine, dextromethorphan hydrobromide, guaifenesin, hydrocodone, ibuprofen, phenylephrine, pseudoephedrine`

| Molecola                      | MW (Da)  | LogP   | HBD | HBA | Violazioni Lipinski |
|-------------------------------|----------|--------|-----|-----|---------------------|
| acetaminophen                 | 151.16   | 0.50   | 2   | 2   | 0 [OK]              |
| chlorpheniramine              | 274.79   | 3.40   | 0   | 2   | 0 [OK]              |
| dextromethorphan hydrobromide | 352.30   | 0.00   | 1   | 2   | 0 [OK]              |
| guaifenesin                   | 198.22   | 1.40   | 2   | 4   | 0 [OK]              |
| hydrocodone                   | 299.40   | 2.20   | 0   | 4   | 0 [OK]              |
| ibuprofen                     | 206.28   | 3.50   | 1   | 2   | 0 [OK]              |
| phenylephrine                 | 167.20   | -0.30  | 3   | 3   | 0 [OK]              |
| pseudoephedrine               | 165.23   | 0.90   | 2   | 2   | 0 [OK]              |

**Carico metabolico totale:** 1814.58 Da — Ottima biodisponibilità orale (sotto soglia 2000 Da).

**Conclusione ADMET:** 0 violazioni Lipinski su tutti e 3 i cocktail. Nessun candidato supera la soglia d'allerta del carico molecolare.

---

### Competizione Metabolica CYP450 — Fase 7 (KEGG API)

#### Rank 1 (5 principi attivi)

| Molecola                      | KEGG ID  | Enzimi CYP metabolizzanti       |
|-------------------------------|----------|----------------------------------|
| acetaminophen                 | D00217   | CYP1A2, CYP2E1, CYP3A4         |
| chlorpheniramine              | D00665   | CYP2D6                          |
| dextromethorphan hydrobromide | D00697   | CYP2D6, CYP3A4                  |
| guaifenesin                   | D00357   | Nessun CYP noto                 |
| phenylephrine                 | D00483   | Nessun CYP noto                 |

**Competizione rilevata:**
- CYP2D6: 2 substrati (chlorpheniramine, dextromethorphan) — [OK]
- CYP3A4: 2 substrati (acetaminophen, dextromethorphan) — [OK]
- **Nessuna competizione critica (≥3 substrati/CYP).**

#### Rank 2 (7 principi attivi)

| Molecola                      | KEGG ID  | Enzimi CYP metabolizzanti       |
|-------------------------------|----------|----------------------------------|
| acetaminophen                 | D00217   | CYP1A2, CYP2E1, CYP3A4         |
| chlorpheniramine              | D00665   | CYP2D6                          |
| dextromethorphan hydrobromide | D00697   | CYP2D6, CYP3A4                  |
| guaifenesin                   | D00357   | Nessun CYP noto                 |
| hydrocodone                   | D08047   | CYP2D6, CYP3A4                  |
| phenylephrine                 | D00483   | Nessun CYP noto                 |
| pseudoephedrine               | D00489   | Nessun CYP noto                 |

**Competizione rilevata:**
- **CYP2D6: 3 substrati (chlorpheniramine, dextromethorphan, hydrocodone) — [!] COMPETIZIONE**
- **CYP3A4: 3 substrati (acetaminophen, dextromethorphan, hydrocodone) — [!] COMPETIZIONE**

> L'aggiunta di hydrocodone nel Rank 2 innesca la soglia critica su due isoenzimi contemporaneamente. Clinicamente, questo implica che il metabolismo di tutti e tre i substrati rallenterebbe per inibizione competitiva, con rischio di accumulo plasmatico degli oppioidi (hydrocodone) e dell'antitussivo (dextromethorphan).

#### Rank 3 (8 principi attivi)

Identico al Rank 2 per il profilo CYP, con l'aggiunta di ibuprofen che viene metabolizzato da CYP2C9 (isoenzima non condiviso con gli altri substrati).

**Competizione rilevata:** stesse 2 competizioni critiche del Rank 2 (CYP2D6 e CYP3A4), ibuprofen non aggiunge conflitto.

**Riepilogo CYP450:**

| Rank | Conflitti CYP | Isoenzimi critici | Verdetto |
|------|--------------|-------------------|----------|
| 1    | 0            | —                 | **OK**   |
| 2    | 2            | CYP2D6, CYP3A4   | **RISCHIO** |
| 3    | 2            | CYP2D6, CYP3A4   | **RISCHIO** |

---

### Network Pharmacology — Fase 8 (STRING + KEGG Pathway)

#### Rank 1 (5 principi attivi)

- **Target proteici trovati:** 10 (tutti via phenylephrine → GNB1, GNAQ, GNAO1, GNG2, GNA12, GNA11, GNA13, GNAS, GNB2, ADRA1A)
- **Target condivisi (2+ molecole):** 0
- **Pathway con convergenza critica (≥3 target):**
  - Hormone signaling: 4 target convergenti — **[!] CONVERGENZA**
  - Neuroactive ligand signaling: 3 target — **[!] CONVERGENZA**
  - cGMP-PKG signaling pathway: 3 target — **[!] CONVERGENZA**

#### Rank 2 (7 principi attivi)

- **Target proteici trovati:** 10 (phenylephrine domina il profilo target)
- **Target condivisi:** 0
- **Pathway con convergenza critica:**
  - Hormone signaling: 3 target — **[!] CONVERGENZA**
  - Neuroactive ligand signaling: 3 target — **[!] CONVERGENZA**
  - cGMP-PKG signaling pathway: 3 target — **[!] CONVERGENZA**

#### Rank 3 (8 principi attivi)

- **Target proteici trovati:** 11 (ibuprofen aggiunge SLC34A1)
- **Target condivisi:** 0
- **Pathway con convergenza critica:**
  - Hormone signaling: 3 target — **[!] CONVERGENZA**
  - cGMP-PKG signaling pathway: 3 target — **[!] CONVERGENZA**

**Riepilogo Network Pharmacology:**

| Rank | Target totali | Target condivisi | Pathway critici | Verdetto |
|------|--------------|-----------------|-----------------|----------|
| 1    | 10           | 0               | 3               | **CONVERGENZA** |
| 2    | 10           | 0               | 3               | **CONVERGENZA** |
| 3    | 11           | 0               | 2               | **CONVERGENZA** |

> **Nota interpretativa:** La convergenza pathway è guidata quasi interamente da phenylephrine (agonista adrenergico α1), che attiva molteplici proteine G (GNA11, GNA13, GNAQ, GNB1, GNAO1) coinvolte nei pathway di signaling ormonale e vascolare. Questo è un comportamento farmacologico atteso e ben documentato per i simpaticomimetici, non un artefatto. In contesto clinico, la convergenza segnala il rischio di vasocostrizione eccessiva e ipertensione — effetto collaterale noto della phenylephrine e motivo per cui i decongestionanti sono controindicati nei pazienti ipertesi. I target non sono condivisi tra molecole diverse del cocktail, il che indica che la convergenza è monofattoriale (un singolo farmaco, non una sinergia tossica tra farmaci).

---

## Osservazione qualitativa finale

La combinazione Rank 1 corrisponde, nella sostanza, alla formulazione tipica di un decongestionante multi-sintomo da banco. La rete l'ha prodotta come stato spurio partendo da correlazioni statistiche pure, senza che la categoria terapeutica "antinfluenzale multi-sintomo" fosse mai codificata esplicitamente nel sistema — un indizio che la matrice W cattura struttura farmacologica reale, non solo rumore.

Il Rank 1 emerge come il candidato più pulito: 0 violazioni Lipinski, 0 conflitti CYP450, e convergenze pathway monofattoriali (non sinergiche). I Rank 2 e 3, pur biologicamente validi (Lipinski OK), presentano competizione metabolica su CYP2D6 e CYP3A4 dovuta all'aggiunta di hydrocodone — un rischio clinicamente rilevante che le Fasi 6 e precedenti non avrebbero potuto identificare.
