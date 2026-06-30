# fase7_cyp450.py — Check competizione metabolica CYP450 via KEGG REST API
"""
Per ogni cocktail candidato, interroga KEGG Drug per recuperare gli enzimi
del citocromo P450 che metabolizzano ciascun principio attivo.
Se 3+ molecole del cocktail competono sullo stesso isoenzima CYP,
il cocktail viene segnalato come a rischio di interazione farmacocinetica.

Soglia clinica: >= 3 substrati sullo stesso CYP e' il limite convenzionale
oltre il quale la competizione metabolica diventa clinicamente rilevante
(inibizione competitiva -> accumulo plasmatico -> tossicita').
"""
import pandas as pd
import requests
import time
import ast
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

# ---------- Soglia di allarme ----------
MAX_SUBSTRATES_PER_CYP = 3  # >= 3 molecole sullo stesso CYP = flag rosso

# ---------- Mapping nomi comuni -> KEGG Drug ID ----------
# KEGG usa nomi canonici lowercase; per le molecole piu' comuni
# manteniamo un dizionario di fallback per casi ambigui
KEGG_ALIAS = {
    "acetaminophen": "paracetamol",
    "dextromethorphan hydrobromide": "dextromethorphan",
    "pseudoephedrine hydrochloride": "pseudoephedrine",
    "phenylephrine hydrochloride": "phenylephrine",
    "chlorpheniramine maleate": "chlorpheniramine",
}

# I principali isoenzimi CYP monitorati in clinica
CYP_ENZYMES = [
    "CYP1A2", "CYP2B6", "CYP2C8", "CYP2C9", "CYP2C19",
    "CYP2D6", "CYP2E1", "CYP3A4", "CYP3A5",
]


def search_kegg_drug(drug_name: str) -> str | None:
    """Cerca un farmaco nel database KEGG e restituisce il primo Drug ID."""
    canonical = KEGG_ALIAS.get(drug_name.lower(), drug_name.lower())
    url = f"https://rest.kegg.jp/find/drug/{canonical}"
    try:
        time.sleep(0.3)  # Rate limiting (KEGG tollera ~10 req/s)
        r = requests.get(url, timeout=10)
        if r.status_code != 200 or not r.text.strip():
            return None
        # Ogni riga: "dr:D00001\tParacetamol (JAN/INN); ..."
        first_line = r.text.strip().split("\n")[0]
        drug_id = first_line.split("\t")[0].replace("dr:", "")
        return drug_id
    except Exception:
        return None


def get_kegg_drug_enzymes(drug_id: str) -> list[str]:
    """Recupera gli enzimi metabolizzanti di un farmaco da KEGG Drug."""
    url = f"https://rest.kegg.jp/get/drug:{drug_id}"
    try:
        time.sleep(0.3)
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []

        text = r.text
        enzymes = []

        # Cerca nella sezione METABOLISM o nell'intero testo i pattern CYPxxx
        for cyp in CYP_ENZYMES:
            # Match case-insensitive per CYP2D6, cyp2d6, CYP 2D6, etc.
            pattern = re.compile(re.escape(cyp), re.IGNORECASE)
            if pattern.search(text):
                enzymes.append(cyp)

        return enzymes
    except Exception:
        return []


def analyze_cocktail(molecules: list[str], rank: int) -> dict:
    """Analizza un cocktail per competizione CYP450. Restituisce il report."""
    print(f"\nAnalisi CYP450 del Rank {rank} Cocktail ({len(molecules)} principi attivi):")
    print(f"-> {molecules}\n")

    drug_cyp_map = {}  # {molecola: [CYP...]}
    cyp_drug_map = {}  # {CYP: [molecole...]}

    header = f"{'Molecola':<30} | {'KEGG ID':<10} | {'Enzimi CYP metabolizzanti'}"
    print(header)
    print("-" * 80)

    for mol in molecules:
        drug_id = search_kegg_drug(mol)
        if not drug_id:
            print(f"{mol:<30} | {'---':<10} | NON TROVATO SU KEGG")
            drug_cyp_map[mol] = []
            continue

        enzymes = get_kegg_drug_enzymes(drug_id)
        drug_cyp_map[mol] = enzymes

        for cyp in enzymes:
            cyp_drug_map.setdefault(cyp, []).append(mol)

        cyp_str = ", ".join(enzymes) if enzymes else "Nessun CYP noto"
        print(f"{mol:<30} | {drug_id:<10} | {cyp_str}")

    print("-" * 80)

    # ---------- Analisi della competizione ----------
    print(f"\n[REPORT COMPETIZIONE METABOLICA - RANK {rank}]")

    conflicts = {}
    for cyp, drugs in sorted(cyp_drug_map.items()):
        n = len(drugs)
        status = "[!] COMPETIZIONE" if n >= MAX_SUBSTRATES_PER_CYP else "[OK]"
        print(f"  {cyp}: {n} substrati -> {', '.join(drugs)}  {status}")
        if n >= MAX_SUBSTRATES_PER_CYP:
            conflicts[cyp] = drugs

    if not cyp_drug_map:
        print("  Nessun dato CYP disponibile su KEGG per queste molecole.")
        print("  [?] Impossibile valutare la competizione metabolica.")
    elif conflicts:
        print(f"\n  [!] ATTENZIONE: {len(conflicts)} isoenzima/i con competizione critica!")
        print("      Rischio di inibizione competitiva -> accumulo plasmatico.")
        print("      Si raccomanda verifica con database DrugBank o consulto farmacologico.")
    else:
        print(f"\n  [OK] Nessuna competizione metabolica critica rilevata.")
        print("      Il cocktail ha un profilo metabolico favorevole.")

    return {
        "rank": rank,
        "drug_cyp_map": drug_cyp_map,
        "cyp_drug_map": cyp_drug_map,
        "conflicts": conflicts,
        "n_conflicts": len(conflicts),
    }


# ---------- Main ----------
print("============================================================")
print(" FASE 7: Check Competizione Metabolica CYP450 (KEGG API)")
print("============================================================")

try:
    df = pd.read_csv(RESULTS / "validated_combinations.csv")
    if df.empty:
        print("Nessun candidato da validare (file CSV vuoto).")
        exit(0)
    candidates = df["molecules"].tolist()
except Exception as e:
    print(f"Errore nel leggere il file results/validated_combinations.csv: {e}")
    exit(1)

all_reports = []
for i, cocktail_str in enumerate(candidates):
    molecules = ast.literal_eval(cocktail_str)
    report = analyze_cocktail(molecules, rank=i + 1)
    all_reports.append(report)
    print("\n" + "=" * 80 + "\n")

# ---------- Riepilogo finale ----------
print("[RIEPILOGO CYP450 GLOBALE]")
for r in all_reports:
    status = "RISCHIO" if r["n_conflicts"] > 0 else "OK"
    print(f"  Rank {r['rank']}: {r['n_conflicts']} conflitti CYP  [{status}]")

print("\nDone.")
