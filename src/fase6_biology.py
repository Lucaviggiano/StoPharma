# fase6_biology.py — Validazione biologica ADMET via PubChem
import pandas as pd
import pubchempy as pcp
import time
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

def check_lipinski(mw, logp, hbd, hba):
    """Calcola le violazioni della Regola del 5 di Lipinski (assorbimento orale)"""
    violations = 0
    if mw == 0.0 or mw > 500: violations += 1
    if logp > 5: violations += 1
    if hbd > 5: violations += 1
    if hba > 10: violations += 1
    return violations

print("============================================================")
print(" FASE 6: Validazione Biologica ADMET (PubChem API)")
print("============================================================\n")

try:
    df = pd.read_csv(RESULTS / "validated_combinations.csv")
    if df.empty:
        print("Nessun candidato da validare (file CSV vuoto).")
        exit(0)
    candidates = df["molecules"].tolist()
except Exception as e:
    print(f"Errore nel leggere il file results/validated_combinations.csv: {e}")
    exit(1)

for i, cocktail_str in enumerate(candidates):
    molecules = ast.literal_eval(cocktail_str)
    print(f"Analisi del Rank {i+1} Cocktail ({len(molecules)} principi attivi):")
    print(f"-> {molecules}\n")

    total_mw = 0.0
    total_violations = 0

    print(f"{'Molecola':<18} | {'MW (Da)':<8} | {'LogP':<6} | {'HBD':<3} | {'HBA':<3} | {'Violazioni Lipinski'}")
    print("-" * 76)

    for mol in molecules:
        try:
            # Pausa per non intasare l'API di NCBI
            time.sleep(0.5)
            
            # Interroga PubChem
            compounds = pcp.get_compounds(mol, 'name')
            if not compounds:
                print(f"{mol:<18} | --- NON TROVATO SU PUBCHEM ---")
                continue
                
            c = compounds[0]
            
            # Estrazione proprieta'
            mw = float(c.molecular_weight) if c.molecular_weight else 0.0
            logp = float(c.xlogp) if c.xlogp is not None else 0.0
            hbd = int(c.h_bond_donor_count) if c.h_bond_donor_count is not None else 0
            hba = int(c.h_bond_acceptor_count) if c.h_bond_acceptor_count is not None else 0
            
            # Calcolo Lipinski
            violations = check_lipinski(mw, logp, hbd, hba)
            total_violations += violations
            total_mw += mw
            
            # Se c'e' piu' di 1 violazione, l'assorbimento orale e' compromesso
            status = "[OK]" if violations <= 1 else "[X]"
            
            print(f"{mol:<18} | {mw:<8.2f} | {logp:<6.2f} | {hbd:<3} | {hba:<3} | {violations} {status}")
            
        except Exception as e:
            print(f"{mol:<18} | Errore API: {str(e)[:30]}")

    print("-" * 76)
    print(f"\n[REPORT GLOBALE DEL COCKTAIL RANK {i+1}]")
    print(f"-> Carico metabolico totale (Somma pesi molecolari): {total_mw:.2f} Da")

    # Un carico totale troppo alto (>2000-3000 Da) implica fatica renale/epatica per smaltire il cocktail
    if total_mw > 2000:
        print("   [!] ATTENZIONE: Il carico molecolare totale e' molto alto (possibile affaticamento epatico/renale).")
    else:
        print("   [OK] Il carico molecolare totale e' entro limiti ragionevoli.")

    if total_violations > 2:
        print("   [!] ATTENZIONE: Diverse molecole violano le regole di assorbimento orale.")
        print("       Questo cocktail potrebbe richiedere somministrazione endovenosa.")
    else:
        print("   [OK] Ottima biodisponibilita' orale prevista per il cocktail.")
    print("\n" + "="*76 + "\n")

print("Done.")
