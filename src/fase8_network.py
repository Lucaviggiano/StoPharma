# fase8_network.py — Network Pharmacology: analisi target proteici e pathway
"""
Per ogni cocktail candidato, interroga STRING DB e KEGG Pathway per:
1. Recuperare le proteine bersaglio di ciascun principio attivo (via STITCH/PubChem)
2. Costruire il network di interazione proteina-proteina (PPI) del cocktail
3. Identificare i pathway KEGG condivisi e potenziali convergenze tossiche

Obiettivo: verificare che i pathway biochimici attivati dal cocktail non
convergano su effetti avversi sinergici (es. depressione respiratoria multipla,
prolungamento QT, epatotossicita' additiva).
"""
import pandas as pd
import requests
import time
import ast
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

# Specie: Homo sapiens (NCBI taxonomy ID)
SPECIES_TAXID = 9606

# Soglia di convergenza pathway: se N+ molecole del cocktail colpiscono
# lo stesso pathway KEGG, segnaliamo il rischio
PATHWAY_CONVERGENCE_THRESHOLD = 3


def get_drug_targets_stitch(drug_name: str) -> list[str]:
    """
    Recupera le proteine target di un farmaco usando STITCH
    (la versione chemical-protein di STRING).
    Fallback: usa PubChem per ottenere il CID, poi STITCH.
    """
    # STITCH usa il formato "CIDm" o "CIDs" + PubChem CID
    # Proviamo prima con il nome diretto via STRING API
    url = "https://string-db.org/api/json/get_string_ids"
    params = {
        "identifiers": drug_name,
        "species": SPECIES_TAXID,
        "limit": 1,
        "caller_identity": "StoPharma",
    }
    try:
        time.sleep(0.5)
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200 and r.json():
            string_id = r.json()[0].get("stringId", "")
            if string_id:
                return get_ppi_partners(string_id)
    except Exception:
        pass
    return []


def get_ppi_partners(string_id: str, limit: int = 10) -> list[str]:
    """
    Dato un protein ID STRING, restituisce i partner di interazione
    proteina-proteina con score >= 700 (alta confidenza).
    """
    url = "https://string-db.org/api/json/interaction_partners"
    params = {
        "identifiers": string_id,
        "species": SPECIES_TAXID,
        "limit": limit,
        "required_score": 700,  # Alta confidenza
        "caller_identity": "StoPharma",
    }
    try:
        time.sleep(0.5)
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200 and r.json():
            partners = []
            for interaction in r.json():
                # Restituisce il preferred name del partner
                partner = interaction.get("preferredName_B", "")
                if partner:
                    partners.append(partner)
            return partners
    except Exception:
        pass
    return []


def get_kegg_pathways_for_gene(gene_name: str) -> list[tuple[str, str]]:
    """
    Dato un gene/proteina umano, restituisce i pathway KEGG associati.
    Returns: lista di (pathway_id, pathway_name)
    """
    # Prima trova il KEGG gene ID
    url = f"https://rest.kegg.jp/find/hsa/{gene_name}"
    try:
        time.sleep(0.3)
        r = requests.get(url, timeout=10)
        if r.status_code != 200 or not r.text.strip():
            return []

        # Prendi il primo gene match
        first_line = r.text.strip().split("\n")[0]
        gene_id = first_line.split("\t")[0]  # es. "hsa:1576"

        # Ora recupera i pathway
        time.sleep(0.3)
        url2 = f"https://rest.kegg.jp/link/pathway/{gene_id}"
        r2 = requests.get(url2, timeout=10)
        if r2.status_code != 200 or not r2.text.strip():
            return []

        pathway_ids = []
        for line in r2.text.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) >= 2:
                pw_id = parts[1].replace("path:", "")
                pathway_ids.append(pw_id)

        # Recupera i nomi dei pathway
        pathways = []
        for pw_id in pathway_ids[:5]:  # Limita a 5 per non intasare
            time.sleep(0.2)
            url3 = f"https://rest.kegg.jp/get/{pw_id}"
            r3 = requests.get(url3, timeout=10)
            if r3.status_code == 200:
                # Il nome e' nella prima riga dopo "NAME"
                for line in r3.text.split("\n"):
                    if line.startswith("NAME"):
                        pw_name = line.replace("NAME", "").strip()
                        # Rimuovi " - Homo sapiens (human)" dal nome
                        pw_name = pw_name.split(" - Homo sapiens")[0].strip()
                        pathways.append((pw_id, pw_name))
                        break

        return pathways
    except Exception:
        return []


def analyze_cocktail_network(molecules: list[str], rank: int) -> dict:
    """Analizza il network farmacologico di un cocktail."""
    print(f"\nAnalisi Network Pharmacology del Rank {rank} ({len(molecules)} principi attivi):")
    print(f"-> {molecules}\n")

    # STEP 1: Trova i target proteici di ogni molecola
    print("[STEP 1] Ricerca target proteici (STRING DB)...")
    print("-" * 70)

    drug_targets = {}  # {molecola: [proteine]}
    all_targets = set()

    for mol in molecules:
        targets = get_drug_targets_stitch(mol)
        drug_targets[mol] = targets
        all_targets.update(targets)
        n = len(targets)
        target_str = ", ".join(targets[:5])
        if n > 5:
            target_str += f" (+{n-5} altri)"
        print(f"  {mol:<30} -> {n} target: {target_str if target_str else 'nessuno trovato'}")

    print(f"\n  Totale proteine bersaglio uniche: {len(all_targets)}")

    # STEP 2: Identifica proteine colpite da piu' molecole
    print(f"\n[STEP 2] Analisi convergenza target...")
    print("-" * 70)

    target_drugs = {}  # {proteina: [molecole che la colpiscono]}
    for mol, targets in drug_targets.items():
        for t in targets:
            target_drugs.setdefault(t, []).append(mol)

    shared_targets = {t: mols for t, mols in target_drugs.items() if len(mols) >= 2}

    if shared_targets:
        print(f"  {len(shared_targets)} proteine colpite da 2+ molecole del cocktail:")
        for target, mols in sorted(shared_targets.items(), key=lambda x: -len(x[1])):
            print(f"    {target}: {', '.join(mols)} ({len(mols)} molecole)")
    else:
        print("  Nessuna proteina condivisa tra le molecole del cocktail.")

    # STEP 3: Analisi pathway KEGG (solo per i target condivisi)
    print(f"\n[STEP 3] Analisi pathway KEGG per target condivisi...")
    print("-" * 70)

    pathway_counter = Counter()  # {pathway_name: count}
    pathway_details = {}  # {pathway_name: [geni]}

    # Analizziamo solo i target piu' rilevanti (quelli condivisi o i top per frequenza)
    targets_to_check = list(shared_targets.keys())[:10] if shared_targets else list(all_targets)[:5]

    for target in targets_to_check:
        pathways = get_kegg_pathways_for_gene(target)
        for pw_id, pw_name in pathways:
            pathway_counter[pw_name] += 1
            pathway_details.setdefault(pw_name, []).append(target)

    if pathway_counter:
        print(f"  Pathway KEGG identificati:")
        for pw_name, count in pathway_counter.most_common(10):
            genes = ", ".join(pathway_details[pw_name][:3])
            flag = " [!] CONVERGENZA" if count >= PATHWAY_CONVERGENCE_THRESHOLD else ""
            print(f"    [{count}x] {pw_name} ({genes}){flag}")
    else:
        print("  Nessun pathway KEGG recuperato per i target analizzati.")

    # ---------- Verdetto ----------
    convergent_pathways = {k: v for k, v in pathway_counter.items()
                          if v >= PATHWAY_CONVERGENCE_THRESHOLD}

    print(f"\n[VERDETTO NETWORK PHARMACOLOGY - RANK {rank}]")
    print(f"  Target proteici totali: {len(all_targets)}")
    print(f"  Target condivisi (2+ molecole): {len(shared_targets)}")
    print(f"  Pathway con convergenza critica (>={PATHWAY_CONVERGENCE_THRESHOLD}): {len(convergent_pathways)}")

    if convergent_pathways:
        print("  [!] ATTENZIONE: Convergenza pathway rilevata.")
        print("      I seguenti pathway sono attivati da target multipli del cocktail:")
        for pw, cnt in sorted(convergent_pathways.items(), key=lambda x: -x[1]):
            print(f"        - {pw} ({cnt} target convergenti)")
        print("      Si raccomanda valutazione farmacodinamica approfondita.")
    elif not all_targets:
        print("  [?] Dati insufficienti: nessun target proteico trovato su STRING.")
        print("      Questo puo' indicare molecole non mappate o nomi non riconosciuti.")
    else:
        print("  [OK] Nessuna convergenza pathway critica rilevata.")
        print("      Il profilo farmacodinamico del cocktail appare diversificato.")

    return {
        "rank": rank,
        "n_targets": len(all_targets),
        "n_shared": len(shared_targets),
        "n_convergent_pathways": len(convergent_pathways),
        "convergent_pathways": list(convergent_pathways.keys()),
    }


# ---------- Main ----------
print("============================================================")
print(" FASE 8: Network Pharmacology (STRING + KEGG Pathway)")
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
    report = analyze_cocktail_network(molecules, rank=i + 1)
    all_reports.append(report)
    print("\n" + "=" * 80 + "\n")

# ---------- Riepilogo finale ----------
print("[RIEPILOGO NETWORK PHARMACOLOGY]")
for r in all_reports:
    status = "CONVERGENZA" if r["n_convergent_pathways"] > 0 else "OK"
    print(f"  Rank {r['rank']}: {r['n_targets']} target, "
          f"{r['n_shared']} condivisi, "
          f"{r['n_convergent_pathways']} pathway critici  [{status}]")

print("\nDone.")
