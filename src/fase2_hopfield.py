# fase2_hopfield.py — Hebbian Learning e test di recall
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from hopfield_core import energy, update_sync, overlap, corrupt, recall

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

patterns  = np.load(DATA / "patterns.npy").astype(np.float64)
molecules = pd.read_csv(DATA / "molecules.csv")
P, N = patterns.shape
names = molecules["name"].tolist()

# ── Costruzione W & Calibrazione theta ─────────────────────────────────────
def hebbian_weights_centered(patterns):
    """
    Hebb rule centrata: rimuove il bias 'entrambi assenti'.
    Equivalente alla matrice di covarianza normalizzata.
    Produce pesi negativi per coppie mai co-occorrenti.
    """
    P, N = patterns.shape
    mu = patterns.mean(axis=0)           # bias medio per nodo, shape (N,)
    X = patterns - mu[np.newaxis, :]     # pattern centrati, shape (P, N)
    W = (X.T @ X) / N                   # covarianza, shape (N, N)
    np.fill_diagonal(W, 0)
    return W

W = hebbian_weights_centered(patterns)

# Calibrazione theta: percentile dei pesi positivi
# Vogliamo che circa density% dei nodi siano attivi all'equilibrio
density = 0.053          # dal CHECK 1: media 2.3/43
pos_weights = W[W > 0].flatten()
THETA = np.quantile(pos_weights, 0.30)

# (Le funzioni di base sono state spostate in hopfield_core.py)

# ── Salvataggio e Stampa W ────────────────────────────────────────────────────
print(f"[W] Shape: {W.shape} | range [{W.min():.4f}, {W.max():.4f}]")
print(f"[W] Pesi negativi: {(W<0).sum()/(N*N-N)*100:.1f}%")
print(f"[theta] Soglia di attivazione: {THETA:.4f}")
print(f"    (calibrata su densità target {density*100:.1f}%)")
np.save(DATA / "W.npy", W)
np.save(DATA / "theta.npy", np.array(THETA))   # salvalo - serve anche alla Fase 3

# ── Heatmap W ─────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 9))
im = ax.imshow(W, cmap="RdBu_r", vmin=-W.max(), vmax=W.max())
ax.set_xticks(range(N)); ax.set_xticklabels(names, rotation=90, fontsize=7)
ax.set_yticks(range(N)); ax.set_yticklabels(names, fontsize=7)
plt.colorbar(im, ax=ax, label="Peso W_ij")
ax.set_title("Matrice dei pesi W (Hopfield - Regola di Hebb)")
plt.tight_layout()
plt.savefig(RESULTS / "W_heatmap.png", dpi=150)
plt.close()
print("Salvato results/W_heatmap.png")

# ── Recall test ───────────────────────────────────────────────────────────────
print(f"\n[Recall test] - regime saturo atteso (P={P} >> cap={0.14*N:.1f})")
print(f"  {'Noise':>6} | {'Successi':>10} | {'Overlap medio':>14}")
for noise in [0.05, 0.10, 0.15, 0.20, 0.30]:
    successes, ovs = 0, []
    for mu in range(P):
        S_c = corrupt(patterns[mu], noise)
        S_r, _ = recall(W, S_c, theta=THETA)
        ov = overlap(S_r, patterns[mu])
        ovs.append(ov)
        if ov > 0.85: successes += 1
    print(f"  {noise*100:>5.0f}% | {successes:>4}/{P:<5} ({successes/P*100:4.0f}%) | "
          f"{np.mean(ovs):>13.3f}")

# ── Analisi stati spuri ───────────────────────────────────────────────────────
print(f"\n[Stati spuri con init random - 500 trial]")
spurs = []
for _ in range(500):
    S0 = np.random.choice([-1.0, 1.0], N)
    S_conv, _ = recall(W, S0, theta=THETA)
    max_ov = max(overlap(S_conv, patterns[mu]) for mu in range(P))
    n_active = (S_conv == 1).sum()
    spurs.append((S_conv, max_ov, n_active, energy(W, S_conv, theta=THETA)))

genuine = [s for s in spurs if s[1] < 0.50]
print(f"  Stati spuri genuini (overlap<0.50): {len(genuine)}/500 ({len(genuine)/5:.0f}%)")
print(f"  Principi attivi medi negli spuri: "
      f"{np.mean([s[2] for s in genuine]):.1f}")

# Mostra i 3 stati spuri con energia più bassa (i più "stabili")
genuine.sort(key=lambda x: x[3])
print(f"\n  Top 3 stati spuri piu' stabili (energia minima):")
for rank, (S, ov, na, E) in enumerate(genuine[:3], 1):
    active_mols = [names[i] for i in range(N) if S[i] == 1]
    print(f"\n  [{rank}] Energia={E:.4f} | overlap_max={ov:.3f} | "
          f"{na} principi attivi:")
    for mol in active_mols:
        print(f"       + {mol}")