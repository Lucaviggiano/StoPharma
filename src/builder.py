# builder.py — Fase 1: Parsing prescrizioni (Orange Book + openFDA) e codifica binaria
import pandas as pd
import numpy as np
import requests
import zipfile, io, urllib.request
import collections
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

parsed_products = []

# ── 1A. INGESTION DA ORANGE BOOK ─────────────────────────────────────────────
print("Scaricando Orange Book (ZIP)...")
ob_url = "https://www.fda.gov/media/76860/download"
try:
    with urllib.request.urlopen(ob_url) as resp:
        zdata = io.BytesIO(resp.read())
    with zipfile.ZipFile(zdata) as z:
        with z.open("products.txt") as f:
            df_ob = pd.read_csv(f, sep="~", encoding="latin-1", low_memory=False)
    df_ob.columns = df_ob.columns.str.strip()
    
    def normalize_ob(s):
        return {x.strip().lower() for x in str(s).split(";")}
    
    df_ob["ingredients_set"] = df_ob["Ingredient"].apply(normalize_ob)
    for _, row in df_ob.iterrows():
        ings = row["ingredients_set"]
        if len(ings) >= 2:
            parsed_products.append({
                "Trade_Name": str(row.get("Trade_Name", "UNKNOWN")),
                "ingredients_set": ings,
                "source": "orange_book"
            })
    print(f"  Trovate {len(df_ob[df_ob['ingredients_set'].apply(len) >= 2])} combo in Orange Book.")
except Exception as e:
    print(f"[!] Errore download Orange Book: {e}")

# ── 1B. INGESTION DA openFDA NDC API ─────────────────────────────────────────
print("\nScaricando combinazioni da openFDA NDC Directory...")
API_URL = "https://api.fda.gov/drug/ndc.json"
MAX_RECORDS = 15000
LIMIT_PER_REQ = 1000

def extract_ingredients_fda(product):
    return {ing.get("name", "").strip().lower() for ing in product.get("active_ingredients", []) if ing.get("name")}

n_fda_combos = 0
for skip in range(0, MAX_RECORDS, LIMIT_PER_REQ):
    print(f"  Fetch skip={skip} limit={LIMIT_PER_REQ}...")
    params = {
        "search": 'active_ingredients.name:* AND product_type:("HUMAN PRESCRIPTION DRUG" OR "HUMAN OTC DRUG")',
        "limit": LIMIT_PER_REQ,
        "skip": skip
    }
    try:
        r = requests.get(API_URL, params=params, timeout=10)
        r.raise_for_status()
        res = r.json().get('results', [])
        for p in res:
            ings = extract_ingredients_fda(p)
            if len(ings) >= 2:
                parsed_products.append({
                    "Trade_Name": p.get("brand_name", p.get("generic_name", "UNKNOWN")),
                    "ingredients_set": ings,
                    "source": "openfda"
                })
                n_fda_combos += 1
        if len(res) < LIMIT_PER_REQ:
            break
        time.sleep(0.5)
    except Exception as e:
        print(f"[!] Errore durante fetch a skip={skip}: {e}")
        break

print(f"  Trovate {n_fda_combos} combo in openFDA.")

df_all = pd.DataFrame(parsed_products)
if df_all.empty:
    print("[!] Nessun prodotto trovato.")
    exit(1)

combos_all = df_all.copy()

# ── 2. KEYWORD SEED: molecole che ANCORANO il dominio terapeutico ─────────────
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
print(f"\nCombinazioni totali nel dominio (overlap>=1): {len(combos_domain)}")

# ── 4. CONTA frequenza di TUTTI gli ingredienti nelle combo del dominio ───────
ingredient_freq = collections.Counter()
for s in combos_domain["ingredients_set"]:
    for ing in s:
        ingredient_freq[ing] += 1

print(f"Ingredienti unici trovati nelle combo del dominio: {len(ingredient_freq)}")

MIN_FREQ = 2
NODES = {ing for ing, cnt in ingredient_freq.items() if cnt >= MIN_FREQ}

# ── 5. ALIASES COMPLETO (salt forms -> nome canonico INN) ──────────────────────
ALIASES = {
    # Oppioidi
    "hydrocodone bitartrate":           "hydrocodone",
    "codeine phosphate":                "codeine",
    "oxycodone hydrochloride":          "oxycodone",
    "oxycodone terephthalate":          "oxycodone",
    "morphine sulfate":                 "morphine",
    "buprenorphine hydrochloride":      "buprenorphine",
    "naloxone hydrochloride":           "naloxone",
    "naltrexone hydrochloride":         "naltrexone",
    "tramadol hydrochloride":           "tramadol",
    "propoxyphene napsylate":           "propoxyphene",
    "propoxyphene hydrochloride":       "propoxyphene",
    "pentazocine hydrochloride":        "pentazocine",
    "dihydrocodeine bitartrate":        "dihydrocodeine",
    "benzhydrocodone hydrochloride":    "benzhydrocodone",
    # FANS
    "diclofenac sodium":                "diclofenac",
    "diclofenac potassium":             "diclofenac",
    "naproxen sodium":                  "naproxen",
    "ketorolac tromethamine":           "ketorolac",
    # Gastroprotettori
    "esomeprazole magnesium":           "esomeprazole",
    # Antistaminici / decongestionanti
    "diphenhydramine hydrochloride":    "diphenhydramine",
    "diphenhydramine citrate":          "diphenhydramine",
    "pseudoephedrine hydrochloride":    "pseudoephedrine",
    "promethazine hydrochloride":       "promethazine",
    "phenylephrine hydrochloride":      "phenylephrine",
    "chlorpheniramine maleate":         "chlorpheniramine",
    "triprolidine hydrochloride":       "triprolidine",
    "bromodiphenhydramine hydrochloride": "diphenhydramine",
    # Miorilassanti / adiuvanti
    "orphenadrine citrate":             "orphenadrine",
    "ergotamine tartrate":              "ergotamine",
    "sumatriptan succinate":            "sumatriptan",
    "homatropine methylbromide":        "homatropine",
    "amlodipine besylate":              "amlodipine",
    "pravastatin sodium":               "pravastatin",
}

BLACKLIST = {
    "pravastatin",   # statina
    "amlodipine",    # antipertensivo
}

def canonicalize(ingredient_set):
    return frozenset(ALIASES.get(x, x) for x in ingredient_set)

# ── 6. RICOSTRUISCI combo con ingredienti canonici ───────────────────────────
combos_domain["canonical"] = combos_domain["ingredients_set"].apply(canonicalize)

# ── 7. NODI FINALI: escludi blacklist ────────────────────────────────────────
canonical_nodes = {ALIASES.get(n, n) for n in NODES} - BLACKLIST
combos_domain["n_canon_nodes"] = combos_domain["canonical"].apply(
    lambda s: len(s & canonical_nodes)
)
combos_valid = combos_domain[combos_domain["n_canon_nodes"] >= 2].copy()
print(f"Combinazioni valide (>=2 nodi canonici): {len(combos_valid)}")

# ── 8. DEDUPLICAZIONE E FILTRO SANITA' ───────────────────────────────────────
combos_valid["canonical_key"] = combos_valid["canonical"].apply(
    lambda s: "|".join(sorted(s & canonical_nodes))
)
combos_dedup = combos_valid.drop_duplicates(subset="canonical_key").copy()

MAX_INGREDIENTS_PER_PATTERN = 8
combos_dedup["n_canon"] = combos_dedup["canonical_key"].apply(lambda s: len(s.split("|")))

n_outliers = (combos_dedup["n_canon"] > MAX_INGREDIENTS_PER_PATTERN).sum()
combos_dedup = combos_dedup[combos_dedup["n_canon"] <= MAX_INGREDIENTS_PER_PATTERN].copy()

print(f"\nCombinazioni uniche prima del filtro sanità: {len(combos_dedup) + n_outliers}")
print(f"Scartati {n_outliers} pattern oltre soglia ({MAX_INGREDIENTS_PER_PATTERN} ingredienti massimi)")
print(f"Combinazioni uniche valide finali: {len(combos_dedup)}")

# ── 9. NODI FINALI (solo quelli che appaiono in almeno 1 combo valida) ────────
active_nodes = set()
for key in combos_dedup["canonical_key"]:
    active_nodes.update(key.split("|"))
molecules_list = sorted(active_nodes)
N = len(molecules_list)
mol_index = {name: i for i, name in enumerate(molecules_list)}
print(f"\nN finale (nodi attivi): {N}")

# ── 10. SALVA molecules.csv e combinations.csv ───────────────────────────────
pd.DataFrame({"id": range(N), "name": molecules_list}).to_csv(DATA / "molecules.csv", index=False)

combos_out = combos_dedup[["Trade_Name", "canonical_key"]].copy()
combos_out.columns = ["product_name", "ingredients"]
combos_out.to_csv(DATA / "combinations.csv", index=False)

# ── 11. COSTRUISCI patterns.npy ──────────────────────────────────────────────
P = len(combos_dedup)
patterns = np.full((P, N), -1, dtype=np.int8)
for row_idx, key in enumerate(combos_dedup["canonical_key"]):
    for mol in key.split("|"):
        if mol in mol_index:
            patterns[row_idx, mol_index[mol]] = +1
np.save(DATA / "patterns.npy", patterns)

# ── 12. REPORT FINALE ────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  RIEPILOGO DATASET v4 (Orange Book + openFDA NDC)")
print(f"{'='*60}")
print(f"  N (nodi):             {N}")
print(f"  P (pattern):          {P}")
print(f"  Capacità teorica:     {0.14*N:.1f} pattern")
print(f"  Regime: {'SATURO (stati spuri attivi)' if P > 0.14*N else 'OTTIMALE (memory phase)'}")
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