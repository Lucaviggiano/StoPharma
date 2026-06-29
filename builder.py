# fase1_build_dataset_v2.py
import pandas as pd
import numpy as np
import zipfile, io, urllib.request, collections

# ── 1. CARICA IL FILE GIÀ SCARICATO (o riscarica) ────────────────────────────
# Se hai già il .zip scaricato, usalo direttamente:
# with zipfile.ZipFile("orange_book.zip") as z:
# Altrimenti:
print("Scaricando Orange Book...")
url = "https://www.fda.gov/media/76860/download"
with urllib.request.urlopen(url) as resp:
    zdata = io.BytesIO(resp.read())
with zipfile.ZipFile(zdata) as z:
    with z.open("products.txt") as f:
        df = pd.read_csv(f, sep="~", encoding="latin-1", low_memory=False)
df.columns = df.columns.str.strip()

def normalize(s):
    return {x.strip().lower() for x in str(s).split(";")}

df["ingredients_set"] = df["Ingredient"].apply(normalize)
df["n_ingredients"]   = df["ingredients_set"].apply(len)
combos_all = df[df["n_ingredients"] >= 2].copy()

# ── 2. KEYWORD SEED: molecole che ANCORANO il dominio terapeutico ─────────────
# Basta che UNA di queste sia presente → la combinazione è nel dominio
DOMAIN_SEEDS = {
    "ibuprofen", "naproxen", "naproxen sodium",
    "acetaminophen",
    "aspirin",
    "codeine", "codeine phosphate",
    "tramadol", "tramadol hydrochloride",
    "oxycodone", "oxycodone hydrochloride",
    "hydrocodone", "hydrocodone bitartrate",
    "diclofenac", "diclofenac sodium", "diclofenac potassium",
    "ketoprofen",
    "indomethacin",
    "piroxicam",
    "meloxicam",
    "ketorolac", "ketorolac tromethamine",
    "celecoxib",
    "morphine", "morphine sulfate",
    "buprenorphine", "buprenorphine hydrochloride",
    "caffeine",
    "orphenadrine", "orphenadrine citrate",
    "methocarbamol",
    "cyclobenzaprine", "cyclobenzaprine hydrochloride",
    "carisoprodol",
    "gabapentin",
    "pregabalin",
    "baclofen",
    "tizanidine", "tizanidine hydrochloride",
}

# ── 3. FILTRO overlap>=1: almeno una seed molecule presente ──────────────────
def has_domain_molecule(ingredient_set):
    return bool(ingredient_set & DOMAIN_SEEDS)

combos_domain = combos_all[combos_all["ingredients_set"].apply(has_domain_molecule)].copy()
print(f"Combinazioni nel dominio (overlap>=1): {len(combos_domain)}")

# ── 4. CONTA frequenza di TUTTI gli ingredienti nelle combo del dominio ───────
ingredient_freq = collections.Counter()
for s in combos_domain["ingredients_set"]:
    for ing in s:
        ingredient_freq[ing] += 1

print(f"\nIngredienti unici trovati nelle combo del dominio: {len(ingredient_freq)}")
print("\nTutti gli ingredienti con frequenza >= 2:")
for ing, cnt in sorted(ingredient_freq.items(), key=lambda x: -x[1]):
    if cnt >= 2:
        print(f"  {ing:50s}: {cnt}x")

# ── 5. NODI FINALI: tutti gli ingredienti con freq >= 2 ──────────────────────
# (freq=1 = probabilmente salt form rara o errore di nomenclatura)
MIN_FREQ = 2
NODES = {ing for ing, cnt in ingredient_freq.items() if cnt >= MIN_FREQ}

# ── ALIASES COMPLETO (salt forms -> nome canonico INN) ──────────────────────
# Il vecchio script cercava la forma base già nel set -> non funzionava.
# Qui mappiamo esplicitamente tutte le salt forms trovate nel dataset.
ALIASES = {
    # Oppioidi
    "hydrocodone bitartrate":           "hydrocodone",
    "codeine phosphate":                "codeine",
    "oxycodone hydrochloride":          "oxycodone",
    "oxycodone terephthalate":          "oxycodone",      # stessa molecola, salt diversa
    "morphine sulfate":                 "morphine",
    "buprenorphine hydrochloride":      "buprenorphine",
    "naloxone hydrochloride":           "naloxone",
    "naltrexone hydrochloride":         "naltrexone",
    "tramadol hydrochloride":           "tramadol",
    "propoxyphene napsylate":           "propoxyphene",
    "propoxyphene hydrochloride":       "propoxyphene",   # due salt della stessa molecola
    "pentazocine hydrochloride":        "pentazocine",
    "dihydrocodeine bitartrate":        "dihydrocodeine",
    "benzhydrocodone hydrochloride":    "benzhydrocodone",
    # FANS
    "diclofenac sodium":                "diclofenac",
    "naproxen sodium":                  "naproxen",
    "ketorolac tromethamine":           "ketorolac",
    # Gastroprotettori
    "esomeprazole magnesium":           "esomeprazole",
    # Antistaminici / decongestionanti
    "diphenhydramine hydrochloride":    "diphenhydramine",
    "diphenhydramine citrate":          "diphenhydramine", # stessa molecola
    "pseudoephedrine hydrochloride":    "pseudoephedrine",
    "promethazine hydrochloride":       "promethazine",
    "phenylephrine hydrochloride":      "phenylephrine",
    "chlorpheniramine maleate":         "chlorpheniramine",
    "triprolidine hydrochloride":       "triprolidine",
    "bromodiphenhydramine hydrochloride": "diphenhydramine", # isomero -> stessa classe
    # Miorilassanti / adiuvanti
    "orphenadrine citrate":             "orphenadrine",
    "ergotamine tartrate":              "ergotamine",
    "sumatriptan succinate":            "sumatriptan",
    "homatropine methylbromide":        "homatropine",
    "amlodipine besylate":              "amlodipine",
    "pravastatin sodium":               "pravastatin",
}

# Blacklist: molecole off-domain da escludere dopo canonicalizzazione
BLACKLIST = {
    "pravastatin",   # statina - entra solo per combinazioni cardiologiche con aspirin
    "amlodipine",    # antipertensivo - stesso motivo
}

def canonicalize(ingredient_set):
    return frozenset(ALIASES.get(x, x) for x in ingredient_set)

# ── 7. RICOSTRUISCI combo con ingredienti canonici ───────────────────────────
combos_domain["canonical"] = combos_domain["ingredients_set"].apply(canonicalize)

# ── 5. NODI FINALI: escludi blacklist ────────────────────────────────────────
canonical_nodes = {ALIASES.get(n, n) for n in NODES} - BLACKLIST
combos_domain["n_canon_nodes"] = combos_domain["canonical"].apply(
    lambda s: len(s & canonical_nodes)
)
combos_valid = combos_domain[combos_domain["n_canon_nodes"] >= 2].copy()
print(f"\nCombinazioni valide (>=2 nodi canonici): {len(combos_valid)}")

# ── 8. DEDUPLICAZIONE ────────────────────────────────────────────────────────
combos_valid["canonical_key"] = combos_valid["canonical"].apply(
    lambda s: "|".join(sorted(s & canonical_nodes))
)
combos_dedup = combos_valid.drop_duplicates(subset="canonical_key").copy()
print(f"Combinazioni uniche dopo dedup: {len(combos_dedup)}")

# ── 9. NODI FINALI (solo quelli che appaiono in almeno 1 combo valida) ────────
active_nodes = set()
for key in combos_dedup["canonical_key"]:
    active_nodes.update(key.split("|"))
molecules_list = sorted(active_nodes)
N = len(molecules_list)
mol_index = {name: i for i, name in enumerate(molecules_list)}
print(f"\nN finale (nodi attivi): {N}")

# ── 10. SALVA molecules.csv e combinations.csv ───────────────────────────────
import os
os.makedirs("data", exist_ok=True)

pd.DataFrame({"id": range(N), "name": molecules_list}).to_csv("data/molecules.csv", index=False)

combos_out = combos_dedup[["Trade_Name", "canonical_key"]].copy()
combos_out.columns = ["product_name", "ingredients"]
combos_out.to_csv("data/combinations.csv", index=False)

# ── 11. COSTRUISCI patterns.npy ──────────────────────────────────────────────
P = len(combos_dedup)
patterns = np.full((P, N), -1, dtype=np.int8)
for row_idx, key in enumerate(combos_dedup["canonical_key"]):
    for mol in key.split("|"):
        if mol in mol_index:
            patterns[row_idx, mol_index[mol]] = +1
np.save("data/patterns.npy", patterns)

# ── 12. REPORT FINALE ────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  RIEPILOGO DATASET v2")
print(f"{'='*60}")
print(f"  N (nodi):             {N}")
print(f"  P (pattern):          {P}")
print(f"  Capacità teorica:     {0.14*N:.1f} pattern")
print(f"  Regime: SATURO (intenzionale - stati spuri = creativita')")
print(f"\n  Top 15 molecole più frequenti:")
freq_final = {molecules_list[i]: int((patterns[:, i] == 1).sum()) for i in range(N)}
for mol, cnt in sorted(freq_final.items(), key=lambda x: -x[1])[:15]:
    bar = "#" * cnt
    print(f"  {mol:35s} {cnt:3d} {bar}")

print(f"\n  Dimensione matrice W: {N}x{N} = {N*N} float64 ({N*N*8/1024:.1f} KB)")
print(f"\n  File salvati:")
print(f"  - data/molecules.csv")
print(f"  - data/combinations.csv")
print(f"  - data/patterns.npy")