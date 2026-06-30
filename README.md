# StoPharma
## Esplorazione dello Spazio Polifarmacologico con Reti di Hopfield e Termodinamica Statistica

---

## Introduzione

La polifarmacologia — la somministrazione contemporanea di più principi attivi per trattare patologie complesse — rappresenta oggi una delle frontiere più promettenti e al contempo più intricate della farmacologia moderna. Lo spazio combinatorio cresce esponenzialmente: dato un vocabolario di $N$ molecole, i possibili cocktail sono $2^N$. Per $N=43$ (il nostro caso), si tratta di circa $8.8 \times 10^{12}$ combinazioni — un numero che rende qualsiasi esplorazione brute-force computazionalmente proibitiva.

La domanda fondamentale che StoPharma si pone è: **è possibile far "sognare" una rete neurale artificiale, in modo che le sue allucinazioni siano farmacologicamente sensate?**

Per rispondere, il progetto prende in prestito strumenti dalla **meccanica statistica** e dalla **teoria delle reti neurali associative** (Hopfield, 1982). L'intuizione chiave è che le prescrizioni cliniche reali — i cocktail farmacologici che i medici prescrivono quotidianamente — possono essere codificate come *configurazioni di equilibrio* di un sistema di spin. In questo formalismo, ogni principio attivo è un neurone binario ($S_i = +1$ se il farmaco è presente, $S_i = -1$ se è assente) e le correlazioni apprese tra farmaci definiscono un paesaggio energetico.

I *minimi globali* di questo paesaggio corrispondono alle prescrizioni già note. Ma i *minimi locali spuri* — quelli che la letteratura classica delle reti di Hopfield considera artefatti da eliminare — diventano nel nostro contesto il vero obiettivo: **nuove combinazioni farmacologiche termodinamicamente stabili, mai prescritte prima, ma coerenti con la struttura relazionale profonda del dataset clinico**.

---

## Percorso del Progetto

> **Nota di Espansione (Branch `develop`)**: 
> La pipeline descritta di seguito si basa sull'architettura e sul dataset originale (*Orange Book*, $N=43$). Il sistema è stato successivamente espanso integrando il database **openFDA NDC** (raggiungendo $N=59$ molecole e 100 pattern) nel branch `develop`. Per tutti i dettagli tecnici sulle differenze, le calibrazioni termodinamiche e le analisi di biodisponibilità, consulta le [Note di Espansione](https://github.com/Lucaviggiano/StoPharma/blob/develop/expansion_notes.md) sul branch `develop`.

Il lavoro è organizzato in otto fasi sequenziali. Ciascuna fase produce artefatti che alimentano la successiva, creando una pipeline di scoperta farmacologica completamente riproducibile.

### Fase 1 — Costruzione del Dataset (`builder.py`, `fase1_validate.py`)

Il punto di partenza è un dataset di prescrizioni cliniche reali, estratto dal database FDA (*Drugs@FDA*). Ogni prescrizione è una lista di principi attivi co-formulati.

Lo script `builder.py` si occupa di:
- Estrarre le combinazioni uniche di principi attivi.
- Risolvere le *salt forms* (es. "hydrocodone bitartrate" → "hydrocodone", "morphine sulfate" → "morphine") tramite un dizionario di alias, aggregando le varianti sotto il nome canonico INN (*International Nonproprietary Name*).
- Codificare ciascuna prescrizione come vettore binario $\xi^\mu \in \{-1, +1\}^N$, dove $\xi^\mu_i = +1$ se la molecola $i$ è presente nella prescrizione $\mu$.

Il dataset risultante nel nostro esperimento contiene **$P = 65$ pattern** (prescrizioni) su un vocabolario di **$N = 43$ molecole**, con una densità di attivazione media di **2.3 farmaci per prescrizione** (sparsità del 5.3%).

`fase1_validate.py` esegue controlli di qualità: verifica la coerenza dimensionale, l'assenza di righe duplicate, e stampa statistiche descrittive sulla distribuzione delle co-occorrenze.

### Fase 2 — Apprendimento Hebbiano e Matrice dei Pesi (`fase2_hopfield.py`)

L'apprendimento della rete avviene tramite la **regola di Hebb nella variante centrata sulla covarianza**:

$$ W_{ij} = \frac{1}{P} \sum_{\mu=1}^{P} (\xi^\mu_i - \bar{\xi}_i)(\xi^\mu_j - \bar{\xi}_j), \quad W_{ii} = 0 $$

dove $`\bar{\xi}_i = \frac{1}{P}\sum_\mu \xi^\mu_i`$ è la media empirica di attivazione del neurone $i$ su tutti i pattern.

La centratura è un dettaglio tecnico cruciale per il nostro dominio. I dati farmacologici sono intrinsecamente sparsi: la media di attivazione è $\bar{\xi}_i \approx -0.89$ (un farmaco è "presente" solo nel ~5% delle prescrizioni). Senza centratura, la regola di Hebb standard produrrebbe pesi prevalentemente negativi, e la rete collasserebbe nello stato $S = (-1, -1, \ldots, -1)$ ("nessun farmaco attivo"), che è biologicamente triviale e privo di interesse.

![Heatmap dei Pesi Sinaptici](results/W_heatmap.png)

*Heatmap della matrice $`W`$ (43×43). Le isole rosse evidenziano cluster di sinergia terapeutica appresa (es. codeina-acetaminofene, comuni in formulazioni analgesiche combinate). Le regioni blu indicano repulsione o incompatibilità chimica.*

### Fase 2b — Calibrazione del Bias $\theta$: Matching the Data Statistics (`theta_sweep.py`)

Il parametro $\theta$ introduce un **campo esterno uniforme** nell'Hamiltoniana del sistema:

$$ E(S) = -\frac{1}{2} S^T W S + \theta \sum_{i} S_i $$

Il termine $+\theta \sum_i S_i$ penalizza energeticamente l'attivazione simultanea di molti neuroni, favorendo configurazioni sparse. In letteratura fisica, questa estensione è nota come **Rete di Hopfield con bias** ed è stata formalizzata per la prima volta da *Amit, Gutfreund e Sompolinsky* (1987) nel contesto delle reti con pattern biased.

La calibrazione di $\theta$ non è arbitraria. Si tratta formalmente di un problema di **matching the data statistics**: si cerca il valore del campo esterno per il quale la magnetizzazione media del sistema all'equilibrio termico coincide con la magnetizzazione empirica osservata nel dataset. Questo è esattamente lo stesso principio che governa l'addestramento delle **Restricted Boltzmann Machines** (RBM) e, più in generale, dei modelli di massima entropia in biofisica.

Lo sweep empirico condotto sui nostri dati reali ha prodotto i seguenti risultati:

| $\theta$ | Nodi attivi (media) | Range | Stati morti (%) | Overlap medio |
|----------|--------------------:|------:|----------------:|-------------:|
| 0.05     | 19.4               | 0–39  | 1.0%            | 0.241        |
| 0.10     | 16.1               | 4–39  | 0.0%            | 0.408        |
| 0.20     | 9.6                | 4–18  | 0.0%            | 0.710        |
| **0.30** | **8.1**             | **5–12** | **0.0%**     | **0.770**    |
| 0.40     | 6.9                | 5–8   | 0.0%            | 0.835        |
| 0.60     | 4.8                | 0–5   | 0.5%            | 0.894        |
| 0.80     | 1.8                | 1–4   | 0.0%            | 0.954        |
| ≥ 1.00   | 0.0                | 0–0   | 100.0%          | 0.000        |

Si osserva chiaramente la **transizione di fase** della rete. Per $\theta \geq 1.0$, il campo esterno è così intenso da spegnere completamente ogni neurone ("morte termica"). Per $\theta \leq 0.10$, la rete è troppo permissiva e genera cocktail da 16-19 farmaci, biologicamente irrealistici. L'intervallo ottimale $\theta \in [0.20, 0.40]$ bilancia creatività e parsimonia.

Per questo esperimento è stato scelto $\theta = 0.30$, che produce stati con **8-9 nodi attivi** in media e un overlap del 77% — abbastanza lontano dai pattern noti da garantire originalità, ma abbastanza vicino da rispettare la struttura profonda delle correlazioni farmacologiche.

### Fase 3 — Generazione Creativa via Simulated Annealing (`fase3_annealing.py`)

Se la rete fosse lasciata evolvere a temperatura $T=0$ (dinamica deterministica sincrona), collasserebbe inevitabilmente in uno dei 65 pattern memorizzati. È un risultato atteso: la rete è una macchina di memoria associativa, e a $T=0$ minimizza l'energia globale.

Per sfuggire ai bacini di attrazione delle memorie note e raggiungere i *minimi locali spuri*, StoPharma utilizza il **Simulated Annealing** con **Glauber Dynamics** (aggiornamento stocastico asincrono). La probabilità di transizione del neurone $i$ segue la distribuzione di Boltzmann:

$$ P(S_i = +1) = \frac{1}{1 + \exp\left(-2 h_i / T\right)}, \quad h_i = \sum_j W_{ij} S_j - \theta $$

La temperatura $T$ viene gradualmente abbassata secondo uno schedule geometrico ($T_{k+1} = \alpha \cdot T_k$, con $\alpha \in \{0.99, 0.995, 0.999\}$). A temperatura elevata il sistema esplora liberamente il paesaggio energetico; man mano che $T$ scende, la dinamica diventa sempre più deterministica e il sistema si "congela" nel minimo locale più vicino.

I risultati del Grid Search sulle tre velocità di raffreddamento confermano l'efficacia del metodo:

| Cooling Rate | Pattern Noti (Memoria) | Stati Spuri (Creatività) |
|:-------------|:----------------------:|:------------------------:|
| Veloce (α=0.99)  | 1/10 | **9/10** |
| Medio (α=0.995)  | 1/10 | **9/10** |
| Lento (α=0.999)  | 0/10 | **10/10** |

Il 90-100% delle traiettorie convergono in stati mai visti nel dataset originale: la rete "allucina" con successo.

![Curva di Simulated Annealing](results/sa_cooling_curve.png)

*Curva di raffreddamento T-vs-Energia. Si osserva la discesa termodinamica tipica del SA: a sinistra (alta T), l'energia oscilla liberamente; a destra (bassa T), il sistema si "congela" in un minimo locale stabile.*

### Fase 4 — Validazione Farmacologica e Triage (`fase4_validation.py`)

Gli stati spuri generati dal SA vengono filtrati attraverso una pipeline di validazione a tre stadi:

1. **Filtraggio per Sparsità e Originalità:** Si conservano solo gli stati con overlap $< 0.85$ (sufficientemente diversi dai pattern noti) e con un numero di nodi attivi $\leq 12$ (cocktail di dimensione clinicamente ragionevole).
2. **Check Esclusività FANS:** Regole logiche *hard-coded* che verificano l'assenza di FANS in competizione (es. ibuprofene + naprossene), la cui co-somministrazione è nota per causare tossicità gastrointestinale grave.
3. **Interrogazione RxNorm (FDA):** Per ogni candidato sopravvissuto, lo script interroga l'API REST del *National Library of Medicine* per verificare l'assenza di interazioni farmacologiche note nel database federale USA.

Nella nostra esecuzione, la Fase 4 ha processato 33 stati SA, identificato 31 candidati genuini, ridotti a 5 dopo deduplicazione, e di questi **ha scartato 3 per conflitto FANS** (ibuprofene + naprossene erano presenti simultaneamente). I 2 candidati sopravvissuti hanno superato il check RxNorm senza interazioni note.

### Fase 6 — Validazione Biologica ADMET (`fase6_biology.py`)

I candidati finali vengono sottoposti a un ultimo esame: la verifica della biodisponibilità orale tramite la **Regola del 5 di Lipinski** (1997). Per ciascun principio attivo nel cocktail, lo script interroga l'API di **PubChem** (NCBI) per recuperare le proprietà fisico-chimiche e verificare quattro criteri:

- Peso molecolare ≤ 500 Da
- Lipofilia (LogP) ≤ 5
- Donatori di legami idrogeno (HBD) ≤ 5
- Accettori di legami idrogeno (HBA) ≤ 10

Inoltre viene calcolato il **carico metabolico totale** (somma dei pesi molecolari), come indicatore grezzo del carico epatico-renale.

### Fase 7 — Check Competizione Metabolica CYP450 (`fase7_cyp450.py`)

La Fase 6 valuta ciascun farmaco *singolarmente* (Lipinski). Ma in un cocktail, il rischio principale è la **competizione metabolica**: più molecole processate dallo stesso enzima epatico del citocromo P450 (es. CYP3A4, CYP2D6) rallentano reciprocamente il proprio smaltimento, causando accumulo plasmatico e potenziale tossicità.

Lo script interroga l'API REST di **KEGG Drug** per ogni principio attivo:
1. Cerca l'ID KEGG del farmaco.
2. Recupera dal record farmacologico gli isoenzimi CYP coinvolti nel metabolismo.
3. Costruisce una matrice di competizione: se $\geq 3$ molecole del cocktail sono substrati dello stesso CYP, viene segnalato un **flag di competizione critica**.

### Fase 8 — Network Pharmacology (`fase8_network.py`)

L'ultimo livello di validazione analizza i **bersagli proteici** del cocktail per identificare convergenze farmaco-dinamiche potenzialmente pericolose. Lo script opera in tre step:

1. **Target Discovery (STRING DB):** Per ogni principio attivo, interroga STRING per recuperare le proteine bersaglio umane ($\text{score} \geq 700$, alta confidenza).
2. **Convergence Analysis:** Identifica proteine colpite da $\geq 2$ molecole del cocktail — potenziali punti di sinergia tossica.
3. **Pathway Mapping (KEGG Pathway):** Per i target condivisi, risale ai pathway biochimici (es. metabolismo epatico, trasduzione del segnale) e segnala convergenze critiche ($\geq 3$ target sullo stesso pathway).

---

## Risultati Ottenuti

### Candidato Rank 1 — Cocktail "StoPharma-01"

| Proprietà | Valore |
|:-----------|:-------|
| **Molecole** | acetaminophen, aspirin, butalbital, caffeine, carisoprodol, codeine, dihydrocodeine, propoxyphene |
| **Nodi attivi** | 8 su 43 |
| **Energia** | $E = -14.046$ |
| **Overlap max** | 0.814 (originalità ~19%) |
| **Check FANS** | Superato |
| **Check RxNorm** | 0 interazioni note |
| **Lipinski** | 0 violazioni su 8 molecole |
| **Carico metabolico** | 1950 Da (entro soglia di sicurezza) |
| **Competizione CYP450** | 1 conflitto (CYP3A4) |
| **Network Pharmacology**| 1 target, 0 convergenze pathway |

### Candidato Rank 2 — Cocktail "StoPharma-02"

| Proprietà | Valore |
|:-----------|:-------|
| **Molecole** | acetaminophen, aspirin, butalbital, caffeine, carisoprodol, codeine, dihydrocodeine, pentazocine, propoxyphene |
| **Nodi attivi** | 9 su 43 |
| **Energia** | $E = -13.904$ |
| **Overlap max** | 0.767 (originalità ~23%) |
| **Check FANS** | Superato |
| **Check RxNorm** | 0 interazioni note |
| **Lipinski** | 0 violazioni su 9 molecole |
| **Competizione CYP450** | 1 conflitto (CYP3A4) |
| **Network Pharmacology**| 1 target, 0 convergenze pathway |

### Dettaglio CYP450 del Candidato Rank 1

```
Molecola                       | KEGG ID    | Enzimi CYP metabolizzanti
--------------------------------------------------------------------------------
acetaminophen                  | D00217     | Nessun CYP noto
aspirin                        | D00109     | Nessun CYP noto
butalbital                     | D03182     | Nessun CYP noto
caffeine                       | D00528     | CYP1A2, CYP2E1, CYP3A4
carisoprodol                   | D00768     | CYP2C19
codeine                        | D00195     | CYP2D6, CYP3A4
dihydrocodeine                 | D01481     | CYP2D6, CYP3A4
propoxyphene                   | D00482     | Nessun CYP noto

-> CYP3A4: 3 substrati (caffeine, codeine, dihydrocodeine)  [!] COMPETIZIONE
-> Tutti gli altri CYP: nessuna competizione critica          [OK]
```

> **Nota clinica:** La competizione su CYP3A4 è un risultato atteso e clinicamente rilevante. In un contesto terapeutico reale, il dosaggio di caffeina e degli oppioidi andrebbe aggiustato per compensare il rallentamento metabolico reciproco. Questo flag — che la Fase 6 (Lipinski) non poteva catturare — dimostra il valore aggiunto del check CYP450.

---

## Struttura del Progetto

```
StoPharma/
├── run_pipeline.py          # Entry point: esegue l'intera pipeline
├── requirements.txt         # Dipendenze Python
├── README.md
├── demo.ipynb               # Notebook interattivo end-to-end
├── src/
│   ├── __init__.py
│   ├── hopfield_core.py     # Libreria condivisa: energy, update_sync, glauber_step, overlap
│   ├── builder.py           # Fase 1: Parsing prescrizioni FDA e codifica binaria
│   ├── fase1_validate.py    # Fase 1: Quality Assurance del dataset
│   ├── fase2_hopfield.py    # Fase 2: Hebbian Learning (W) e test di recall
│   ├── theta_sweep.py       # Fase 2b: Sweep empirico per calibrazione θ
│   ├── fase3_annealing.py   # Fase 3: Simulated Annealing (generazione creativa)
│   ├── fase4_validation.py  # Fase 4: Triage FANS + RxNorm
│   ├── fase6_biology.py     # Fase 6: Check ADMET e Lipinski via PubChem
│   ├── fase7_cyp450.py      # Fase 7: Check competizione metabolica CYP450 via KEGG
│   └── fase8_network.py     # Fase 8: Network Pharmacology via STRING + KEGG Pathway
├── data/
│   ├── molecules.csv        # Vocabolario dei 43 principi attivi
│   ├── combinations.csv     # 65 prescrizioni cliniche reali
│   ├── patterns.npy         # Matrice binaria P×N dei pattern
│   ├── W.npy                # Matrice dei pesi sinaptici N×N
│   └── theta.npy            # Bias ottimale calibrato (θ = 0.30)
└── results/
    ├── W_heatmap.png         # Heatmap della matrice W
    ├── sa_cooling_curve.png  # Curva termodinamica del SA
    ├── sa_states.npy         # Vettori S finali del SA
    └── validated_combinations.csv  # Report finale candidati
```

## Installazione e Avvio Rapido

### Requisiti
- Python 3.10+

```bash
pip install -r requirements.txt
```

### Esecuzione della Pipeline Completa
```bash
# Metodo 1: entry point unico (consigliato)
python run_pipeline.py                # Tutte le fasi (1-8)
python run_pipeline.py 3 4 6          # Solo fasi selezionate

# Metodo 2: esecuzione manuale fase per fase
python src/builder.py                 # 1. Parsing prescrizioni e codifica binaria
python src/fase1_validate.py          # 2. QA e statistiche del dataset
python src/fase2_hopfield.py          # 3. Apprendimento matrice W + test recall
python src/theta_sweep.py             # 4. Matching the data statistics
python src/fase3_annealing.py         # 5. Generazione entropica (Simulated Annealing)
python src/fase4_validation.py        # 6. Triage interazioni (FANS + RxNorm)
python src/fase6_biology.py           # 7. Check ADMET e biodisponibilità orale
python src/fase7_cyp450.py            # 8. Check competizione CYP450 (KEGG)
python src/fase8_network.py           # 9. Network Pharmacology (STRING + KEGG)
```

---

## Prospettive Future

### Ampliamento dello Spazio dei Principi Attivi

L'architettura del sistema è stata progettata per scalare. La complessità dell'apprendimento Hebbiano è $O(N^2 \cdot P)$, il che rende il passaggio da $N = 43$ a $N = 500$ o $N = 1000$ molecole computazionalmente triviale anche su hardware consumer. Il vincolo matematico della capacità della rete di Hopfield ($P_{\max} \approx 0.14N$) implica che aumentando il vocabolario $N$ si *aumenta* anche il numero di pattern memorizzabili senza saturazione (regime spin-glass). Il vincolo reale è la **copertura dati**: ogni molecola aggiunta deve apparire in un numero sufficiente di pattern ($\geq 5$) affinché i pesi Hebbiani siano statisticamente informativi.

### Simulazioni PBPK e Docking Molecolare

Per validare ulteriormente i candidati generati da StoPharma in un contesto pre-clinico, il passo successivo sarebbe l'integrazione con software di farmacocinetica fisiologica (PBPK Modeling, es. *Simcyp*, *GastroPlus*) o di Docking Molecolare (es. *AutoDock Vina*, *Schrödinger Suite*), che modellano rispettivamente l'assorbimento/distribuzione/metabolismo/escrezione (ADME) e l'interazione tridimensionale farmaco-recettore. Questi strumenti richiedono software specialistico e competenze bioinformatiche dedicate, e rappresentano il naturale passo successivo rispetto alla validazione API-based implementata nelle Fasi 6-8.

---

## Riferimenti

- Hopfield, J.J. (1982). *"Neural networks and physical systems with emergent collective computational abilities."* PNAS 79(8), 2554–2558.
- Amit, D.J., Gutfreund, H., Sompolinsky, H. (1987). *"Statistical mechanics of neural networks near saturation."* Annals of Physics, 173(1), 30–67.
- Hinton, G.E. (2002). *"Training products of experts by minimizing contrastive divergence."* Neural Computation 14(8), 1771–1800.
- Lipinski, C.A. et al. (1997). *"Experimental and computational approaches to estimate solubility and permeability in drug discovery."* Advanced Drug Delivery Reviews, 23(1-3), 3–25.
- Kirkpatrick, S., Gelatt, C.D., Vecchi, M.P. (1983). *"Optimization by Simulated Annealing."* Science 220(4598), 671–680.

---

*Disclaimer: StoPharma è un proof-of-concept di biologia computazionale. Le combinazioni farmaceutiche generate dall'intelligenza artificiale non sostituiscono in alcun modo protocolli clinici (trial in-vivo, studi PBPK) né il parere di un medico.*
