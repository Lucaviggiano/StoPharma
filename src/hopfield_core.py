import numpy as np

def energy(W, S, theta=0.0):
    """
    Calcola l'energia dello stato S nella rete di Hopfield.
    Includendo theta, la formula e': E = -0.5 * S^T * W * S + theta * sum(S)
    """
    return -0.5 * S @ W @ S + theta * np.sum(S)

def update_sync(W, S, theta=0.0):
    """Aggiornamento deterministico sincrono con tie-break a -1 (sparsita')."""
    raw = W @ S - theta
    result = np.sign(raw)
    result[result == 0] = -1
    return result

def glauber_step(W, S, T, theta=0.0):
    """Singolo step di aggiornamento stocastico (Glauber dynamics) per un nodo random."""
    i = np.random.randint(len(S))
    local_field = (W[i] @ S) - theta
    # Evita overflow se T e' molto piccolo
    with np.errstate(over='ignore'):
        exp_val = np.exp(-2.0 * local_field / T)
    prob_up = 1.0 / (1.0 + exp_val)
    
    S_new = S.copy()
    S_new[i] = 1.0 if np.random.rand() < prob_up else -1.0
    return S_new

def overlap(S1, S2):
    """Misura la similarita' tra due stati (1.0 = identici, -1.0 = opposti)."""
    return float(S1 @ S2) / len(S1)

def corrupt(pattern, noise=0.15):
    """Inverte una percentuale 'noise' di nodi in un pattern."""
    s = pattern.copy()
    n_flip = max(1, int(noise * len(s)))
    idx = np.random.choice(len(s), n_flip, replace=False)
    s[idx] *= -1
    return s

def recall(W, S_init, theta=0.0, max_iter=50):
    """Esegue l'aggiornamento deterministico fino a convergenza o max_iter."""
    S = S_init.copy()
    for step in range(max_iter):
        S_new = update_sync(W, S, theta=theta)
        if np.array_equal(S_new, S):
            return S, step
        S = S_new
    return S, max_iter
