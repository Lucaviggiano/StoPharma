# fase4_validation.py — Triage farmacologico (FANS + RxNorm)
import numpy as np
import pandas as pd
import requests, time, json
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"

# ── Carica dati e risultati SA ────────────────────────────────────────────────
patterns  = np.load(DATA / "patterns.npy").astype(np.float64)
W         = np.load(DATA / "W.npy")
THETA     = float(np.load(DATA / "theta.npy"))
molecules = pd.read_csv(DATA / "molecules.csv")
names     = molecules["name"].tolist()
P, N      = patterns.shape

def overlap(S1, S2):
    return float(S1 @ S2) / len(S1)

def energy(W, S, theta):
    return -0.5 * S @ W @ S + theta * S.sum()

def decode(S):
    return [names[i] for i in range(N) if S[i] == 1]

# ── CARICA I RISULTATI DELLA FASE 3 ──────────────────────────────────────────
# Adatta questo al formato in cui hai salvato gli stati generati dal SA.
# Assumo che tu abbia salvato una lista di vettori S finali in results/sa_results.npy
# Se non li hai salvati, aggiungi alla fine di fase3_annealing.py:
#   np.save("results/sa_states.npy", np.array(final_states))

try:
    sa_states = np.load(RESULTS / "sa_states.npy")
    print(f"Caricati {len(sa_states)} stati dal SA")
except FileNotFoundError:
    print("[!] results/sa_states.npy non trovato.")
    print("   Aggiungi alla fine di fase3_annealing.py:")
    print("   np.save('results/sa_states.npy', np.array(final_states))")
    exit(1)

# ── STEP 1: FILTRA STATI GENUINAMENTE NUOVI ──────────────────────────────────
print("\n" + "="*60)
print("STEP 1 — Filtraggio stati genuini")
print("="*60)

candidates = []
for i, S in enumerate(sa_states):
    max_ov  = max(overlap(S, patterns[mu]) for mu in range(P))
    n_active = int((S == 1).sum())
    E = energy(W, S, THETA)
    candidates.append({
        "idx": i, "S": S, "overlap_max": max_ov,
        "n_active": n_active, "energy": E,
        "molecules": decode(S)
    })

# Ordina per overlap crescente (più originali prima) e poi energia
candidates.sort(key=lambda x: (x["overlap_max"], x["energy"]))

genuine = [c for c in candidates if c["overlap_max"] < 0.99 and c["n_active"] <= 12]
print(f"  Totale stati SA: {len(sa_states)}")
print(f"  Genuini (overlap<0.99 e <=12 attivi): {len(genuine)}")

# Deduplicazione: rimuovi stati identici
seen_keys = set()
unique_genuine = []
for c in genuine:
    key = frozenset(c["molecules"])
    if key not in seen_keys:
        seen_keys.add(key)
        unique_genuine.append(c)
print(f"  Unici dopo dedup: {len(unique_genuine)}")

# Mostra i top 10
print(f"\n  Top 10 candidati (più originali):")
for c in unique_genuine[:10]:
    print(f"  E={c['energy']:6.3f} | overlap={c['overlap_max']:.3f} | "
          f"n={c['n_active']} | {c['molecules']}")

# ── STEP 2: CHECK FANS AUTOMATICO ────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 2 — Check FANS exclusivity")
print("="*60)

FANS = {"ibuprofen","naproxen","diclofenac","meloxicam","ketorolac",
        "celecoxib","ketoprofen","indomethacin","piroxicam"}

def check_fans(mol_list):
    fans_present = [m for m in mol_list if m in FANS]
    if len(fans_present) > 1:
        return False, fans_present
    return True, fans_present

passed_fans = []
for c in unique_genuine:
    ok, fans_found = check_fans(c["molecules"])
    c["fans_ok"]    = ok
    c["fans_found"] = fans_found
    status = "[OK]" if ok else "[X]"
    if not ok:
        print(f"  {status} CONFLITTO: {c['molecules']} - FANS: {fans_found}")
    passed_fans.append(c) if ok else None

print(f"  Passano check FANS: {len(passed_fans)}/{len(unique_genuine)}")

# ── STEP 3: QUERY RXNORM ─────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 3 — Query RxNorm (interazioni note)")
print("="*60)

BASE = "https://rxnav.nlm.nih.gov/REST"

def get_rxcui(drug_name):
    """Cerca il codice RxCUI per un nome di farmaco."""
    try:
        r = requests.get(f"{BASE}/rxcui.json",
                         params={"name": drug_name, "search": 1},
                         timeout=5)
        ids = r.json().get("idGroup", {}).get("rxnormId", [])
        return ids[0] if ids else None
    except Exception:
        return None

def get_interactions(rxcui_list):
    """Cerca interazioni tra una lista di RxCUI."""
    if len(rxcui_list) < 2:
        return []
    try:
        ids_str = "+".join(rxcui_list)
        r = requests.get(f"{BASE}/interaction/list.json",
                         params={"rxcuis": ids_str},
                         timeout=8)
        data = r.json()
        interactions = []
        for pair in data.get("fullInteractionTypeGroup", []):
            for itype in pair.get("fullInteractionType", []):
                desc = itype.get("comment", "")
                drugs = [c["minConceptItem"]["name"]
                         for c in itype.get("interactionPair", [{}])[0]
                                       .get("interactionConcept", [])]
                interactions.append({"drugs": drugs, "description": desc})
        return interactions
    except Exception:
        return []

# Cache RxCUI per non rifarlo ogni volta
rxcui_cache = {}

def lookup_combination(mol_list, verbose=True):
    """Lookup RxNorm completo per una combinazione."""
    rxcuis = []
    not_found = []
    for mol in mol_list:
        if mol not in rxcui_cache:
            rxcui_cache[mol] = get_rxcui(mol)
            time.sleep(0.15)  # rate limit gentile
        cid = rxcui_cache[mol]
        if cid:
            rxcuis.append(cid)
        else:
            not_found.append(mol)

    interactions = get_interactions(rxcuis) if len(rxcuis) >= 2 else []

    if verbose:
        print(f"\n  Molecole: {mol_list}")
        for mol in not_found:
            print(f"    [!] '{mol}' non trovato in RxNorm")
        if not interactions:
            print(f"    [OK] Nessuna interazione nota trovata in RxNorm")
        else:
            print(f"    [!] {len(interactions)} interazione/i trovata/e:")
            for ix in interactions[:3]:
                print(f"       - {ix['description'][:120]}")
    return {"rxcuis": rxcuis, "not_found": not_found,
            "interactions": interactions}

# Interroga i top 5 candidati
print("  (Interrogazione RxNorm — richiede connessione internet)")
TOP_N = min(5, len(passed_fans))
rxnorm_results = []

for c in passed_fans[:TOP_N]:
    result = lookup_combination(c["molecules"])
    c["rxnorm"] = result
    rxnorm_results.append(c)

# ── STEP 4: REPORT FINALE ─────────────────────────────────────────────────────
print("\n" + "="*60)
print("REPORT FINALE — Candidati validati")
print("="*60)

# Classifica i candidati
def score_candidate(c):
    """
    Score composito (più basso = migliore candidato):
    - overlap basso = più originale
    - poche interazioni RxNorm = più sicuro
    - n_active ragionevole (2-4) = più credibile clinicamente
    """
    n_interactions = len(c.get("rxnorm", {}).get("interactions", []))
    dist_from_ideal = abs(c["n_active"] - 3)  # ideale: 3 molecole
    return c["overlap_max"] + 0.5 * n_interactions + 0.1 * dist_from_ideal

rxnorm_results.sort(key=score_candidate)

print(f"\n{'Rank':<5} {'Energia':>8} {'Overlap':>8} {'N':>4} "
      f"{'FANS':>6} {'RxNorm':>8}  Molecole")
print("-"*90)
for rank, c in enumerate(rxnorm_results, 1):
    n_ix = len(c.get("rxnorm", {}).get("interactions", []))
    fans_str = "[OK]" if c["fans_ok"] else "[X]"
    rxnorm_str = f"[OK] ({n_ix}ix)" if n_ix == 0 else f"[!] ({n_ix}ix)"
    mols_str = ", ".join(c["molecules"])
    print(f"{rank:<5} {c['energy']:>8.3f} {c['overlap_max']:>8.3f} "
          f"{c['n_active']:>4} {fans_str:>6} {rxnorm_str:>8}  {mols_str}")

# Salva risultati
output = []
for c in rxnorm_results:
    output.append({
        "rank": rxnorm_results.index(c)+1,
        "molecules": c["molecules"],
        "energy": round(c["energy"], 4),
        "overlap_max": round(c["overlap_max"], 4),
        "n_active": c["n_active"],
        "fans_ok": c["fans_ok"],
        "rxnorm_interactions": len(c.get("rxnorm", {}).get("interactions", [])),
        "rxnorm_not_found": c.get("rxnorm", {}).get("not_found", []),
    })

pd.DataFrame(output).to_csv(RESULTS / "validated_combinations.csv", index=False)
print(f"\nSalvato results/validated_combinations.csv")
print("\n-> Per i candidati top, cerca su PubMed:")
for c in rxnorm_results[:3]:
    query = " AND ".join(f'"{m}"' for m in c["molecules"])
    print(f"  https://pubmed.ncbi.nlm.nih.gov/?term={query.replace(' ','+')}+combination")