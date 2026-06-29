# StoPharma — Roadmap di Implementazione
> Progetto personale universitario · Hopfield Network per De Novo Drug Design  
> Ultimo aggiornamento: giugno 2026

---

## Come leggere questo documento

Ogni fase ha un **obiettivo unico e verificabile**. Non passi alla fase successiva finché non hai superato il checkpoint della fase corrente. Le fasi 0 e 1 sono interamente "a secco" (no codice, solo comprensione e dati) — è la parte che i tutorial saltano e che fa perdere settimane dopo.

---

## Fase 0 — Capire i Dati Prima di Toccare il Codice
**Durata stimata:** 2–3 giorni  
**Obiettivo:** Avere chiarissimo cosa rappresenta un "pattern di addestramento" nel tuo dominio.

### Il problema concettuale da risolvere subito

La rete di Hopfield impara da *esempi*. Nel tuo caso, un esempio non è un singolo farmaco — è una **combinazione terapeutica approvata** (es. "ibuprofene + codeina + caffeina" che esiste come Nurofen Plus).

Devi rispondere a queste domande prima di raccogliere dati:

- [ ] **Cosa è un pattern $\xi^\mu$?** → Una formulazione farmaceutica approvata contenente più principi attivi. Non un singolo farmaco.
- [ ] **Cosa è un nodo $i$?** → Un singolo principio attivo (INN — International Nonproprietary Name). Es. `ibuprofen`, `paracetamol`, `codeine`.
- [ ] **Quando un nodo vale +1?** → Il principio attivo è presente nella formulazione.
- [ ] **Quando un nodo vale −1?** → Il principio attivo è assente dalla formulazione (non: è controindicato, solo assente).
- [ ] **Cosa codifica un peso negativo $W_{ij} < 0$?** → Quella coppia di molecole non compare mai insieme nei pattern di training. Non necessariamente tossicità — potresti avere bias da dataset. **Questa distinzione è cruciale per la validazione.**

### Cosa leggere (30 min totali, non di più)

Non serve diventare farmacologi. Servono solo queste tre nozioni di base:

1. **Sinergia farmacologica:** due farmaci producono un effetto maggiore della somma. Esempio classico: paracetamolo + ibuprofene per il dolore acuto (meccanismi d'azione diversi, COX vs centrale).
2. **Interazione farmacologica avversa:** una coppia aumenta la tossicità. Esempio: FANS + anticoagulanti → rischio emorragico. Queste coppie NON devono mai apparire insieme nei tuoi pattern di addestramento, oppure se appaiono il peso $W_{ij}$ sarà correttamente negativo.
3. **Profilo FANS:** ibuprofene, naprossene, ketoprofene, diclofenac, indometacina agiscono tutti inibendo le COX. Sono intercambiabili terapeuticamente ma non combinabili (stesso meccanismo + tossicità additiva). Questo significa che nella tua matrice non vedrai mai due FANS insieme → pesi fortemente negativi tra di loro = **segnale corretto**.

**Fonti consigliate (non farmacologia, solo reference):**
- Wikipedia "NSAID combinations" per orientarti
- DrugBank entry per ibuprofene: guarda il campo `drug_interactions` per capire la struttura dei dati

---

## Fase 1 — Costruzione del Dataset
**Durata stimata:** 3–5 giorni  
**Obiettivo:** Una matrice `patterns.npy` di shape `(P, N)` con valori in `{-1, +1}`.

### Step 1.1 — Scegliere le 60–80 molecole (i tuoi nodi)

Non usare un'API automatica qui. Fallo a mano la prima volta. Ecco una lista di partenza ragionevole per i FANS + analgesici:

**Analgesici puri:**
`paracetamol (acetaminophen)`, `codeine`, `tramadol`, `morphine`, `oxycodone`, `hydrocodone`, `buprenorphine`, `fentanyl`, `nalbuphine`, `pethidine (meperidine)`

**FANS (COX non-selettivi):**
`ibuprofen`, `naproxen`, `diclofenac`, `ketoprofen`, `indomethacin`, `piroxicam`, `meloxicam`, `nimesulide`, `ketorolac`, `sulindac`

**COX-2 selettivi:**
`celecoxib`, `etoricoxib`, `parecoxib`

**Adiuvanti analgesici (spesso in combinazione):**
`caffeine`, `orphenadrine`, `methocarbamol`, `cyclobenzaprine`, `gabapentin`, `pregabalin`, `amitriptyline`, `duloxetine`, `capsaicin`

**Gastroprotettori (spesso co-prescritta con FANS):**
`omeprazole`, `esomeprazole`, `lansoprazole`, `misoprostol`, `ranitidine`

**Antispastici / Miorilassanti:**
`baclofen`, `tizanidine`, `diazepam`, `carisoprodol`

**Altro spesso co-prescritta:**
`diphenhydramine`, `doxylamine`, `pseudoephedrine`, `phenylephrine`, `guaifenesin`, `dextromethorphan`

Totale: ~55 molecole. Aggiungi o rimuovi a piacere per arrivare a N=60–70. **Salva questa lista in `molecules.csv` con colonne `id, name, class`.**

### Step 1.2 — Raccogliere i pattern (le combinazioni approvate)

**Fonte primaria: DrugBank Open Data**
- Scarica il file `drugbank_open_structures.sdf` o il database XML da [drugbank.com/releases/latest](https://go.drugbank.com/releases/latest) (richiede registrazione gratuita come ricercatore)
- Cerca `<combination-products>` nel XML — sono le combinazioni approvate

**Fonte alternativa più rapida: FDA Orange Book**
- [fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files](https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files)
- Scarica `products.txt`. Ogni riga è un prodotto, la colonna `Ingredient` lista i principi attivi separati da `;`
- Filtra per i tuoi 60+ nodi. **Questo è il metodo più diretto e non richiede API.**

**Alternativa ancora più rapida per iniziare (raccolta manuale):**
Cerca su Wikipedia "combination analgesic" e costruisci ~30 vettori a mano in un CSV. È sufficiente per validare la matematica nelle fasi successive. Esempi reali:

| Prodotto commerciale | Ingredienti | Note |
|---|---|---|
| Nurofen Plus | ibuprofen + codeine | approvato UK |
| Cocodamol | paracetamol + codeine | approvato UK |
| Excedrin | paracetamol + aspirin + caffeine | approvato USA |
| Percocet | oxycodone + paracetamol | approvato USA |
| Voltaren Plus | diclofenac + codeine | approvato EU |

Punta a **P = 40–60 combinazioni** per N = 60–70 molecole. Stai ben sotto il limite di capacità $0.14N \approx 9$ — attenzione, con N=70 il limite è ~10 pattern per la Hopfield classica! Vedi nota sotto.

> ⚠️ **Nota critica sulla capacità:**  
> La Hopfield Network classica memorizza al massimo $P \approx 0.14N$ pattern senza errori. Con N=70, sono **~10 pattern**. Se ne hai 50, la rete è **satura** e i risultati deterministici (Fase 2) non sono affidabili come "memoria". Questo va bene per il tuo scopo — gli stati spuri sono la tua creatività — ma devi dichiararlo esplicitamente. Alternativa: usa la **Modern Hopfield Network** (Ramsauer et al. 2020) che ha capacità esponenziale, ma è più complessa da implementare. Per ora, procedi con la classica e documenta il limite.

### Step 1.3 — Costruire la matrice `patterns.npy`

```python
# build_dataset.py
import numpy as np
import pandas as pd

molecules = pd.read_csv('molecules.csv')  # colonne: id, name, class
combinations = pd.read_csv('combinations.csv')  # colonne: product_name, ingredients (separati da '|')

N = len(molecules)
mol_index = {name: i for i, name in enumerate(molecules['name'])}

patterns = []
for _, row in combinations.iterrows():
    vec = np.full(N, -1)  # tutto assente di default
    for ingredient in row['ingredients'].split('|'):
        ingredient = ingredient.strip()
        if ingredient in mol_index:
            vec[mol_index[ingredient]] = +1
    patterns.append(vec)

patterns = np.array(patterns)  # shape (P, N)
np.save('patterns.npy', patterns)
print(f"Dataset: {patterns.shape[0]} pattern, {patterns.shape[1]} nodi")
print(f"Capacità teorica: {0.14 * N:.1f} pattern — attuale: {patterns.shape[0]}")
```

**Checkpoint Fase 1 ✓**
- [ ] `molecules.csv` con N ≥ 50 molecole
- [ ] `combinations.csv` con P ≥ 20 combinazioni verificate
- [ ] `patterns.npy` caricabile e shape corretta
- [ ] Stampato il rapporto P/0.14N e documentato se siete in regime saturo

---

## Fase 2 — Motore Deterministico (Hopfield Classica)
**Durata stimata:** 2–3 giorni  
**Obiettivo:** La rete corregge un pattern "corrotto" e torna al pattern originale.

### Step 2.1 — Apprendimento (Regola di Hebb)

```python
# hopfield.py
import numpy as np

def hebbian_weights(patterns: np.ndarray) -> np.ndarray:
    """
    patterns: shape (P, N), valori in {-1, +1}
    ritorna W: shape (N, N), simmetrica, diagonale zero
    """
    P, N = patterns.shape
    W = (patterns.T @ patterns) / N
    np.fill_diagonal(W, 0)
    return W

def energy(W: np.ndarray, S: np.ndarray) -> float:
    return -0.5 * S @ W @ S

def update_sync(W: np.ndarray, S: np.ndarray) -> np.ndarray:
    """Aggiornamento sincrono (tutti i nodi insieme)"""
    return np.sign(W @ S)
```

### Step 2.2 — Test di recall (il test più importante)

```python
def corrupt_pattern(pattern: np.ndarray, noise_fraction: float = 0.2) -> np.ndarray:
    """Flip casuale del noise_fraction dei nodi"""
    corrupted = pattern.copy()
    n_flip = int(noise_fraction * len(pattern))
    flip_idx = np.random.choice(len(pattern), n_flip, replace=False)
    corrupted[flip_idx] *= -1
    return corrupted

def recall(W, S_init, max_iter=100):
    S = S_init.copy()
    for _ in range(max_iter):
        S_new = update_sync(W, S)
        if np.array_equal(S_new, S):
            break
        S = S_new
    return S

def overlap(S1, S2):
    """Misura di similarità tra due stati: 1.0 = identici, -1.0 = opposti"""
    return (S1 @ S2) / len(S1)
```

**Test da eseguire:**
```python
patterns = np.load('patterns.npy')
W = hebbian_weights(patterns)

for idx in range(len(patterns)):
    original = patterns[idx]
    corrupted = corrupt_pattern(original, noise_fraction=0.15)
    recalled = recall(W, corrupted)
    ov = overlap(original, recalled)
    print(f"Pattern {idx}: overlap recall={ov:.3f} {'✓' if ov > 0.9 else '✗ (stato spurio)'}")
```

Se il recall funziona su almeno il 70% dei pattern con 15% di rumore → la matrice W è ben costruita e puoi andare alla Fase 3.

**Checkpoint Fase 2 ✓**
- [ ] Matrice W calcolata e verificata (simmetrica, diagonale zero)
- [ ] Test di recall su tutti i pattern con noise=15%: tasso successo documentato
- [ ] Energia calcolata su ciascun pattern di training (devono essere tutti minimi locali)

---

## Fase 3 — Motore Creativo (Simulated Annealing)
**Durata stimata:** 3–4 giorni  
**Obiettivo:** Generare uno stato `S_new` con overlap < 0.85 rispetto a qualsiasi pattern di training.

### Step 3.1 — Aggiornamento di Glauber (asincrono, temperature-driven)

```python
def glauber_step(W: np.ndarray, S: np.ndarray, T: float) -> np.ndarray:
    """
    Un singolo step di aggiornamento stocastico (un nodo random).
    T: temperatura (noise). T→0 = deterministico. T→∞ = random.
    """
    i = np.random.randint(len(S))
    local_field = W[i] @ S  # campo locale sul nodo i
    prob_up = 1.0 / (1.0 + np.exp(-2.0 * local_field / T))
    S = S.copy()
    S[i] = +1 if np.random.rand() < prob_up else -1
    return S

def simulated_annealing(W, S_init, T_start=2.0, T_end=0.05,
                         cooling=0.995, steps_per_T=50):
    S = S_init.copy()
    T = T_start
    history = []

    while T > T_end:
        for _ in range(steps_per_T):
            S = glauber_step(W, S, T)
        history.append({
            'T': T,
            'energy': energy(W, S),
            'S': S.copy()
        })
        T *= cooling

    return S, history
```

### Step 3.2 — Strategia di inizializzazione

Hai tre opzioni, usale tutte e tre in run separate per confrontare:

| Init | Descrizione | Quando usarla |
|---|---|---|
| **Random** | `S = np.random.choice([-1,1], N)` | Esplorazione massima, spesso stati spuri |
| **Pattern corrotto** | Parti da un pattern noto con 40% rumore | Esplorazione vicino a un minimo noto |
| **Complementare** | Inverti un pattern noto (`S *= -1`) | Forza l'uscita dai minimi noti |

### Step 3.3 — Parametri di cooling da testare

Esegui una **grid search manuale** su questi parametri e salva i risultati:

```python
configs = [
    {'T_start': 3.0, 'T_end': 0.05, 'cooling': 0.99},   # lento
    {'T_start': 2.0, 'T_end': 0.05, 'cooling': 0.995},  # medio (default)
    {'T_start': 1.0, 'T_end': 0.01, 'cooling': 0.999},  # molto lento
]
```

Per ogni config, esegui 10 run con seed diversi e misura quante convergono a stati spuri vs. pattern noti.

**Checkpoint Fase 3 ✓**
- [ ] Almeno un run che converge a uno stato con overlap < 0.85 rispetto a tutti i pattern
- [ ] Curva energia vs. temperatura salvata per almeno una run (per il plot)
- [ ] Grid dei parametri di cooling documentata

---

## Fase 4 — Interprete e Validazione
**Durata stimata:** 3–4 giorni  
**Obiettivo:** Rispondere alla domanda "il cocktail generato ha senso farmacologico?"

### Step 4.1 — Decodifica del vettore output

```python
def decode_state(S: np.ndarray, molecules_df: pd.DataFrame,
                 threshold: float = 1.0) -> list[str]:
    """
    Ritorna i nomi delle molecole con S_i = +1.
    threshold: usa 0.0 se vuoi includere i nodi incerti (se usi valori continui).
    """
    active_idx = np.where(S >= threshold)[0]
    return molecules_df.iloc[active_idx]['name'].tolist()

# Esempio di output report
def print_report(S, W, patterns, molecules_df):
    active = decode_state(S, molecules_df)
    E = energy(W, S)
    overlaps = [(i, overlap(S, patterns[i])) for i in range(len(patterns))]
    best_match_idx, best_overlap = max(overlaps, key=lambda x: x[1])

    print("="*50)
    print(f"COMBINAZIONE GENERATA ({len(active)} principi attivi):")
    for mol in active: print(f"  + {mol}")
    print(f"\nEnergia: {E:.4f}")
    print(f"Overlap max con pattern noti: {best_overlap:.3f} (pattern #{best_match_idx})")
    if best_overlap > 0.85:
        print("⚠️  Molto simile a un pattern noto — probabilmente recall, non creatività")
    else:
        print("✓  Stato genuinamente nuovo")
```

### Step 4.2 — Validazione farmacologica (senza essere farmacologi)

Esegui questi controlli **in quest'ordine**, dal più facile al più elaborato.

#### Check 1 — Regola di esclusività FANS (automatizzabile)
Due FANS non devono mai coesistere nella stessa combinazione. Definisci la lista dei FANS e verifica:

```python
FANS_list = ['ibuprofen', 'naproxen', 'diclofenac', 'ketoprofen',
             'indomethacin', 'piroxicam', 'meloxicam', 'nimesulide',
             'ketorolac', 'celecoxib', 'etoricoxib']

def check_fans_exclusivity(active_molecules: list[str]) -> bool:
    fans_present = [m for m in active_molecules if m in FANS_list]
    if len(fans_present) > 1:
        print(f"❌ FANS conflict: {fans_present}")
        return False
    return True
```

#### Check 2 — Query sull'API di DrugBank o RxNorm (semi-automatizzabile)
RxNorm ha un'API pubblica gratuita. Per ogni coppia di molecole attive, puoi interrogare le interazioni note:

```python
import requests

def check_rxnorm_interaction(drug1: str, drug2: str) -> dict:
    """
    Usa l'API di RxNorm per cercare interazioni.
    Non richiede autenticazione.
    """
    base = "https://rxnav.nlm.nih.gov/REST"
    # Step 1: trova RxCUI per drug1
    r1 = requests.get(f"{base}/rxcui.json?name={drug1}&search=1")
    rxcui1 = r1.json()['idGroup'].get('rxnormId', [None])[0]
    # Step 2: trova RxCUI per drug2
    r2 = requests.get(f"{base}/rxcui.json?name={drug2}&search=1")
    rxcui2 = r2.json()['idGroup'].get('rxnormId', [None])[0]

    if not rxcui1 or not rxcui2:
        return {'status': 'not_found'}

    # Step 3: controlla interazioni
    r3 = requests.get(f"{base}/interaction/list.json?rxcuis={rxcui1}+{rxcui2}")
    return r3.json()
```

> **Nota:** RxNorm copre principalmente farmaci USA. Se una molecola non viene trovata, segna `not_found` e passa oltre — non è un errore del tuo sistema.

#### Check 3 — Validazione manuale su letteratura (non automatizzabile, ma veloce)
Per le combinazioni genuinamente nuove (quelle con overlap < 0.7), fai una ricerca su:
- **PubMed** ([pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov)): cerca `"drug1" AND "drug2" AND "combination"`
- **Google Scholar**: `"drug1 drug2 synergy analgesic"`

Documenta per ogni combinazione nuova:
- Trovato/non trovato in letteratura
- Se trovato: supporta o smentisce la combinazione?
- Giudizio: `plausibile` / `problematica` / `sconosciuta`

### Step 4.3 — Visualizzazione del paesaggio energetico

```python
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

def plot_energy_landscape(patterns, generated_states, W, molecules_df):
    all_states = np.vstack([patterns, np.array(generated_states)])
    pca = PCA(n_components=2)
    coords = pca.fit_transform(all_states)

    energies_train = [energy(W, p) for p in patterns]
    energies_gen = [energy(W, s) for s in generated_states]

    plt.figure(figsize=(10, 7))
    plt.scatter(coords[:len(patterns), 0], coords[:len(patterns), 1],
                c=energies_train, cmap='Blues', s=100, label='Pattern noti', zorder=3)
    plt.scatter(coords[len(patterns):, 0], coords[len(patterns):, 1],
                c=energies_gen, cmap='Reds', s=80, marker='*',
                label='Combinazioni generate', zorder=4)
    plt.colorbar(label='Energia')
    plt.xlabel('PC1'); plt.ylabel('PC2')
    plt.title('Paesaggio energetico — PCA degli stati')
    plt.legend()
    plt.savefig('energy_landscape.png', dpi=150)
```

**Checkpoint Fase 4 ✓**
- [ ] Script di decodifica funzionante con report leggibile
- [ ] Check FANS automatico integrato nel report
- [ ] Almeno 3 combinazioni interrogate su RxNorm
- [ ] Almeno 1 combinazione genuinamente nuova cercata su PubMed
- [ ] Plot PCA del paesaggio energetico salvato

---

## Fase 5 (Bonus) — Presentazione e Portfolio
**Durata stimata:** 1–2 giorni  
**Obiettivo:** Rendere il progetto comunicabile.

### Cosa produrre

1. **`README.md`** con: motivazione, architettura in 5 righe, istruzioni di setup, esempio di output
2. **Notebook Jupyter `demo.ipynb`** che esegue end-to-end: carica dataset → addestramento → SA → report → plot. Eseguibile in un click.
3. **Plot da includere:**
   - Heatmap della matrice W (mostra le correlazioni apprese)
   - Curva energia vs. temperatura per una run di SA
   - PCA del paesaggio energetico
4. **Tabella di risultati** con le migliori combinazioni generate e il loro giudizio di validazione

### Struttura finale del repository

```
stopharma/
├── data/
│   ├── molecules.csv          # lista nodi
│   ├── combinations.csv       # pattern di training
│   └── patterns.npy           # matrice binaria
├── src/
│   ├── hopfield.py            # motore matematico
│   ├── annealing.py           # Simulated Annealing
│   ├── validation.py          # check farmacologici
│   └── visualize.py           # plot
├── demo.ipynb                 # notebook end-to-end
├── results/
│   ├── energy_landscape.png
│   └── generated_combinations.csv
└── README.md
```

---

## Riepilogo checkpoint e sequenza consigliata

| Fase | Durata | Deliverable | Bloccante? |
|---|---|---|---|
| 0 — Comprensione dominio | 2–3 gg | Risposte alle 5 domande concettuali | ✅ Sì |
| 1 — Dataset | 3–5 gg | `patterns.npy` validata | ✅ Sì |
| 2 — Motore deterministico | 2–3 gg | Test recall > 70% | ✅ Sì |
| 3 — Simulated Annealing | 3–4 gg | Stato spurio genuino trovato | ✅ Sì |
| 4 — Validazione | 3–4 gg | Report con check FANS + RxNorm | ✅ Sì |
| 5 — Portfolio | 1–2 gg | Notebook + README + plots | ❌ No (ma consigliato) |

**Tempo totale realistico: 2–3 settimane part-time.**

---

## Cosa non fare (errori comuni)

- ❌ **Non iniziare dalla Fase 3 perché "è la più interessante"** — senza una W corretta il SA esplora spazzatura
- ❌ **Non usare i 100 nodi subito** — inizia con 50 molecole e 20 pattern, scala dopo
- ❌ **Non fidarti degli stati spuri come risultati senza la validazione della Fase 4** — il 90% saranno combinazioni farmacologicamente assurde (troppi oppioidi insieme, o FANS in conflitto)
- ❌ **Non cercare di automatizzare tutto il dataset dalla Fase 1** — 30 vettori costruiti a mano correttamente valgono più di 200 scaricati con un'API che non capisci

---

*StoPharma — documento interno di progetto. Non costituisce consulenza medica o farmacologica.*
