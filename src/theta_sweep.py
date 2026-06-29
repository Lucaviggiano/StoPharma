# theta_sweep.py — Calibrazione empirica del bias theta
# Sweep sui dati reali per trovare il theta ottimale (matching the data statistics).
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

patterns = np.load(DATA / "patterns.npy").astype(np.float64)
W        = np.load(DATA / "W.npy")
P, N     = patterns.shape

def update_sync(W, S, theta):
    raw = W @ S - theta
    result = np.sign(raw)
    result[result == 0] = -1   # tie-break verso -1
    return result

def recall(W, S_init, theta, max_iter=100):
    S = S_init.copy()
    for _ in range(max_iter):
        S_new = update_sync(W, S, theta)
        if np.array_equal(S_new, S):
            return S
        S = S_new
    return S

def overlap(S1, S2):
    return float(S1 @ S2) / len(S1)

THETAS = [0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 1.00,
          1.20, 1.40, 1.60, 1.80, 2.00, 2.50, 3.00]
N_TRIALS = 200

print(f"{'theta':>6} | {'N attivi (media)':>17} | {'N attivi (min-max)':>18} | "
      f"{'Tutti -1 (%)':>13} | {'Overlap max medio':>18}")
print("-"*82)

best_theta = None
best_score = float('inf')

for theta in THETAS:
    n_actives, max_ovs, all_dead = [], [], 0

    for _ in range(N_TRIALS):
        S0 = np.random.choice([-1.0, 1.0], N)
        S  = recall(W, S0, theta)
        na = int((S == 1).sum())
        n_actives.append(na)
        if na == 0:
            all_dead += 1
            max_ovs.append(0.0)
        else:
            max_ovs.append(max(overlap(S, patterns[mu]) for mu in range(P)))

    mean_na  = np.mean(n_actives)
    min_na   = min(n_actives)
    max_na   = max(n_actives)
    dead_pct = all_dead / N_TRIALS * 100
    mean_ov  = np.mean(max_ovs)

    # Score: vuoi media tra 2 e 6, e pochi stati "tutti -1"
    score = abs(mean_na - 3) + dead_pct * 0.1
    marker = " <- TARGET" if 2 <= mean_na <= 6 and dead_pct < 30 else ""
    if score < best_score and dead_pct < 50:
        best_score = score
        best_theta = theta

    print(f"{theta:>6.2f} | {mean_na:>10.1f} nodi  | "
          f"{min_na:>6}-{max_na:<10} | {dead_pct:>10.1f}%  | "
          f"{mean_ov:>16.3f}{marker}")

print(f"\ntheta ottimale stimato: {best_theta}")
print(f"Salva con: np.save('data/theta.npy', np.array({best_theta}))")
