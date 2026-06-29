import numpy as np
import pandas as pd

patterns  = np.load("data/patterns.npy")
molecules = pd.read_csv("data/molecules.csv")
P, N = patterns.shape
names = molecules["name"].tolist()

print(f"Shape: {patterns.shape}  |  Valori unici: {np.unique(patterns)}")

# CHECK 1: sparsità per pattern
active_per_pattern = (patterns == 1).sum(axis=1)
print(f"\n[CHECK 1] Principi attivi per combinazione:")
print(f"  min={active_per_pattern.min()}  max={active_per_pattern.max()}  "
      f"media={active_per_pattern.mean():.1f}  mediana={np.median(active_per_pattern):.1f}")
suspicious_big  = np.where(active_per_pattern > 6)[0]
suspicious_small = np.where(active_per_pattern < 2)[0]
if len(suspicious_big):
    print(f"  (!)  Pattern con >6 attivi ({len(suspicious_big)}):")
    for i in suspicious_big:
        mols = [names[j] for j in range(N) if patterns[i,j]==1]
        print(f"     [{i}] {mols}")
if len(suspicious_small):
    print(f"  (!)  Pattern con <2 attivi: indice {suspicious_small}")

# CHECK 2: coppie mai co-occorrenti
print(f"\n[CHECK 2] Coppie mai co-occorrenti (W_ij sarà negativo):")
never_together = []
for i in range(N):
    for j in range(i+1, N):
        both = ((patterns[:,i]==1) & (patterns[:,j]==1)).sum()
        ni, nj = (patterns[:,i]==1).sum(), (patterns[:,j]==1).sum()
        if both == 0 and ni >= 2 and nj >= 2:
            never_together.append((names[i], names[j], ni, nj))
print(f"  Trovate {len(never_together)} coppie esclusive")
never_together.sort(key=lambda x: -(x[2]+x[3]))
for a, b, na, nb in never_together[:15]:
    print(f"    {a:20s} x {b:20s}  (freq: {na}, {nb})")

# CHECK 3: FANS exclusivity
FANS = ["ibuprofen","naproxen","diclofenac","meloxicam","ketorolac","celecoxib"]
fans_in_data = [f for f in FANS if f in names]
print(f"\n[CHECK 3] FANS nel dataset: {fans_in_data}")
found_conflict = False
for i, fa in enumerate(fans_in_data):
    for fb in fans_in_data[i+1:]:
        cooc = ((patterns[:,names.index(fa)]==1) & (patterns[:,names.index(fb)]==1)).sum()
        if cooc > 0:
            print(f"  [X] {fa} + {fb}: {cooc} co-occorrenze")
            found_conflict = True
if not found_conflict:
    print("  (OK) Nessun conflitto FANS")

# CHECK 4 + 5
keys = ["|".join(map(str, row)) for row in patterns]
print(f"\n[CHECK 4] Duplicati: {'(OK) nessuno' if len(set(keys))==P else f'(!) {P-len(set(keys))} trovati'}")
dead = [names[i] for i in range(N) if (patterns[:,i]==1).sum()==0]
print(f"[CHECK 5] Nodi morti: {'(OK) nessuno' if not dead else dead}")

print(f"\n  N={N}, P={P} - densita' media {active_per_pattern.mean()/N*100:.1f}% - pronti per Fase 2")