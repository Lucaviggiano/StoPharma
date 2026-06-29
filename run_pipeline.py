#!/usr/bin/env python
"""
run_pipeline.py — Entry point per l'intera pipeline StoPharma.
Esegue le fasi in sequenza dalla root del progetto.

Uso:
    python run_pipeline.py          # Esegue tutte le fasi (1-6)
    python run_pipeline.py 3 4      # Esegue solo le fasi 3 e 4
"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC  = ROOT / "src"

PHASES = {
    "1": ("builder.py",         "Fase 1: Parsing prescrizioni FDA"),
    "1v": ("fase1_validate.py", "Fase 1v: Quality Assurance dataset"),
    "2": ("fase2_hopfield.py",  "Fase 2: Hebbian Learning (W)"),
    "2b": ("theta_sweep.py",    "Fase 2b: Calibrazione theta"),
    "3": ("fase3_annealing.py", "Fase 3: Simulated Annealing"),
    "4": ("fase4_validation.py","Fase 4: Triage FANS + RxNorm"),
    "6": ("fase6_biology.py",   "Fase 6: Check ADMET (Lipinski)"),
}

ALL_ORDER = ["1", "1v", "2", "2b", "3", "4", "6"]

def run_phase(key):
    script, desc = PHASES[key]
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, str(SRC / script)],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print(f"\n[ERRORE] {script} terminato con codice {result.returncode}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    selected = sys.argv[1:] if len(sys.argv) > 1 else ALL_ORDER
    for key in selected:
        if key not in PHASES:
            print(f"[!] Fase '{key}' sconosciuta. Disponibili: {list(PHASES.keys())}")
            sys.exit(1)
        run_phase(key)
    print(f"\n{'='*60}")
    print("  Pipeline completata con successo!")
    print(f"{'='*60}")
