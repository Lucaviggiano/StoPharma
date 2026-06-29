# StoPharma: AI-Driven Polypharmacology con Reti di Hopfield

**StoPharma** è un sistema di intelligenza artificiale basato su Reti Neurali di Hopfield e Simulated Annealing, progettato per esplorare il vasto spazio chimico delle combinazioni farmacologiche e suggerire nuovi cocktail terapeutici (polifarmacologia) a partire da dataset di prescrizioni esistenti.

Il sistema memorizza associazioni virtuose tra farmaci noti, per poi utilizzare la termodinamica stocastica per allucinare nuovi stati (cocktail creativi) stabili, che vengono infine filtrati tramite regole farmacologiche e database medici reali (RxNorm).

## Architettura in 5 Step

1. **Ingestion & Builder**: Prende in input dataset FDA, estrae combinazioni di farmaci valide e le mappa in vettori binari.
2. **Motore Deterministico (Hopfield)**: Apprende una matrice dei pesi $W$ usando la Regola di Hebb Centrata per catturare associazioni positive e negative tra farmaci. Una calibrazione fine del bias termodinamico ($\theta$) garantisce sparsità biologica (cocktail piccoli, es. 3-8 molecole).
3. **Motore Creativo (Simulated Annealing)**: Invece di recuperare memorie esatte, il sistema inietta "temperatura" (rumore) e la fa scendere lentamente, forzando la rete a stabilizzarsi in *minimi locali spuri genuini* (le nostre combinazioni innovative).
4. **Validazione e Triage**: I candidati generati passano attraverso un filtro di sicurezza locale (es. anti-conflitto per i FANS) e vengono interrogati contro l'API del governo USA (RxNorm) per scovare interazioni chimiche controindicate.
5. **Output**: Un report dettagliato di cocktail sicuri e creativi pronti per la validazione in laboratorio.

## Installazione e Avvio

### Requisiti
- Python 3.10+
- `numpy`, `pandas`, `matplotlib`, `requests`

```bash
# Esempio di esecuzione della pipeline completa:
python builder.py
python fase1_validate.py
python fase2_hopfield.py
python theta_sweep.py           # Calibrazione empirica
python fase3_annealing.py       # Generazione creativa
python fase4_validation.py      # Triage finale
```

## Esempio di Output Generato

Cocktail originale validato senza interazioni note (Target: dolore acuto):
- **Molecole**: `acetaminophen, aspirin, butalbital, caffeine, carisoprodol, codeine, dihydrocodeine, propoxyphene`
- **Energia di Hopfield**: `-14.04`
- **Overlap con il dataset noto**: `81.4%` (Nuovo al ~19%)

---
*StoPharma è un proof of concept computazionale. Le combinazioni farmaceutiche generate non sostituiscono un trial clinico o il consulto di un medico.*
