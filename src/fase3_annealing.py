# fase3_annealing.py — Generazione creativa via Simulated Annealing
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from hopfield_core import energy, glauber_step, overlap, corrupt

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

print("[Info] Caricamento dati...")
patterns  = np.load(DATA / "patterns.npy").astype(np.float64)
W         = np.load(DATA / "W.npy").astype(np.float64)
THETA     = float(np.load(DATA / "theta.npy"))
molecules = pd.read_csv(DATA / "molecules.csv")
P, N = patterns.shape
names = molecules["name"].tolist()

print(f"       W shape: {W.shape}, theta: {THETA:.4f}")

# ── Motore SA (Simulated Annealing) ───────────────────────────────────────────
def simulated_annealing(W, S_init, theta, T_start=2.0, T_end=0.05,
                         cooling=0.995, steps_per_T=50):
    S = S_init.copy()
    T = T_start
    history = []

    while T > T_end:
        for _ in range(steps_per_T):
            S = glauber_step(W, S, T, theta=theta)
        history.append({
            'T': T,
            'energy': energy(W, S, theta=theta),
            'S': S.copy()
        })
        T *= cooling

    return S, history

# ── Grid Search su parametri di cooling ───────────────────────────────────────
configs = [
    {'name': 'Veloce', 'T_start': 3.0, 'T_end': 0.05, 'cooling': 0.99},
    {'name': 'Medio',  'T_start': 2.0, 'T_end': 0.05, 'cooling': 0.995},
    {'name': 'Lento',  'T_start': 1.0, 'T_end': 0.01, 'cooling': 0.999},
]

print("\n[Grid Search] Avvio test sui parametri di cooling...")
n_trials = 10
saved_history = None
final_states = []

for conf in configs:
    print(f"\n>> Test configurazione: {conf['name']} (cooling={conf['cooling']})")
    n_spurious = 0
    n_memory = 0
    
    for trial in range(n_trials):
        # Inizializzazione Random come base per la Grid Search
        S_init = np.random.choice([-1.0, 1.0], N)
        
        S_final, history = simulated_annealing(
            W, S_init, THETA,
            T_start=conf['T_start'], 
            T_end=conf['T_end'], 
            cooling=conf['cooling'], 
            steps_per_T=50
        )
        
        # Salviamo la prima history per il plot
        if saved_history is None:
            saved_history = history
            
        # Controlliamo overlap
        max_ov = max(overlap(S_final, p) for p in patterns)
        if max_ov >= 0.85:
            n_memory += 1
        else:
            n_spurious += 1
            
        final_states.append(S_final)
            
    print(f"   Risultati su {n_trials} trial:")
    print(f"     - Convergenza a Pattern Noti (memoria): {n_memory}")
    print(f"     - Convergenza a Stati Spuri (creatività): {n_spurious}")

# ── Plot della curva termodinamica ────────────────────────────────────────────
print("\n[Plot] Generazione curva di raffreddamento (T vs Energia)...")
temps = [h['T'] for h in saved_history]
energies = [h['energy'] for h in saved_history]

plt.figure(figsize=(10, 6))
plt.plot(temps, energies, marker='.', linestyle='-', color='b', alpha=0.7)
plt.gca().invert_xaxis()  # Temperatura decrescente
plt.title('Curva Termodinamica (Simulated Annealing)')
plt.xlabel('Temperatura (T)')
plt.ylabel('Energia (E)')
plt.grid(True)
plt.tight_layout()
plt.savefig(RESULTS / 'sa_cooling_curve.png', dpi=150)
plt.close()
print("       Salvato in 'results/sa_cooling_curve.png'")

# ── Strategie di Inizializzazione ─────────────────────────────────────────────
print("\n[Test Strategie di Inizializzazione]")
print("  Confronto usando la configurazione 'Medio'...")

conf = configs[1] # Medio
init_strategies = {
    'Random': lambda: np.random.choice([-1.0, 1.0], N),
    'Corrotto (40% noise)': lambda: corrupt(patterns[np.random.randint(P)], noise=0.40),
    'Complementare': lambda: -1.0 * patterns[np.random.randint(P)]
}

for name, init_fn in init_strategies.items():
    S_init = init_fn()
    S_final, _ = simulated_annealing(
        W, S_init, THETA,
        T_start=conf['T_start'], T_end=conf['T_end'], cooling=conf['cooling'], steps_per_T=50
    )
    max_ov = max(overlap(S_final, p) for p in patterns)
    E_final = energy(W, S_final, theta=THETA)
    tipo = "Pattern Noto" if max_ov >= 0.85 else "Stato Spurio"
    print(f"  > Init: {name:20s} -> {tipo} (Overlap Max: {max_ov:.2f}, Energia: {E_final:.2f})")
    final_states.append(S_final)

np.save(RESULTS / "sa_states.npy", np.array(final_states))
print(f"\n[Info] Salvati {len(final_states)} stati finali in 'results/sa_states.npy'")
