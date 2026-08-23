# KARE: Knowledge-Aware Reasoning Engine for Wind Turbine PHM

**Creatore:** Michele Carbonara
**Matricola:** 802895
**Insegnamento:** Ingegneria della Conoscenza - anno accademico 2025/2026


**KARE** è una piattaforma in Python per la **Manutenzione Predittiva (PHM)** di parchi eolici industriali. Il framework combina tre approcci complementari dell'Intelligenza Artificiale:

1. **Knowledge Base Deterministica (`logic_engine.py`):** applica regole fisiche (norma IEC 61400) sui sensori SCADA per rilevare derive termiche e guasti imminenti.
2. **Rete Bayesiana Causale (`bayesian_learner.py`):** gestisce il rumore dei sensori e calcola la distribuzione di probabilità del rischio di rottura (Failure Risk Score).
3. **Ottimizzazione a Vincoli CSP (`csp_scheduler.py`):** schedula i turni dei tecnici con il solutore Google OR-Tools CP-SAT, bloccando gli interventi nei giorni con vento oltre i 12 m/s.

---

##  Requisiti e Installazione

### 1. Clonazione del repository
```bash
git clone [https://github.com/michikaito/WindTurbines-PHM.git](https://github.com/michikaito/WindTurbines-PHM.git)
cd WindTurbines
```

### 2. Installazione delle dipendenze
```bash
pip install -r requirements.txt
```

### 3. Esecuzione della pipeline principale
```bash
python main.py
```

#### Cosa succede durante l'esecuzione?
- Caricamento e Preprocessing SCADA: Carica o autogenera il dataset in dataset/WindTurbineData/train_wind_turbines.csv, calcola le medie mobili e la Remaining Useful Life (RUL).
- Motore Logico (KB): Valuta i fatti atomici termici/meccanici e genera le diagnosi con le scadenze operative.
- Rete Bayesiana: Addestra la rete con stima Dirichlet (BDeu) ed esegue l'inferenza esatta per produrre il failure_risk_score $[0, 1]$.
- Risoluzione CSP: Risolve il problema combinatorio con Google OR-Tools CP-SAT, assegnando le squadre nei giorni consentiti dal meteo.

### 4. Esecuzione Suite di Validazione e Benchmark (`experiment_runner.py`)
Lancia l'intera batteria di test comparativi in validazione incrociata:
```bash
python experiment_runner.py
```

Il comando manda in esecuzione i seguenti file:
- kb_evaluation.py: Calcola Confusion Matrix, Precision, Recall e F1 del motore a regole rispetto alla RUL reale.
- cv_bayes.py: Esegue 5-Fold GroupKFold per la Rete Bayesiana raggruppando per turbine_id (prevenzione data leakage).
- csp_evaluation.py: Stress-test del risolutore CSP su orizzonti di 7, 14, 21 e 30 giorni e con 1-4 squadre.

#### Output generato
Genera i report quantitativi esportati in outputs/:

- outputs/kb_evaluation_wind_turbines.csv

- outputs/bayes_cv_wind_turbines.csv

- outputs/csp_evaluation_wind_turbines.csv

- outputs/model_comparison_wind_turbines.csv


### 5. Valutazione Baseline Supervisionate Esterne (`cv_balanced_validation.py`)
Confronta KARE contro i classificatori standard di machine learning:

```bash
python cv_balanced_validation.py
```

Il confronto avviene con DummyClassifier, Logistic Regression, Decision Tree e Gaussian Naive Bayes sullo stesso split GroupKFold, calcolando F1-Macro e Balanced Accuracy mediate con deviazione standard.


### 6. Generazione Figure per la Documentazione (`generate_docs.py`)
Genera tutti gli 11 grafici in formato PNG:

```bash
python generate_docs_assets.py
```

I grafici vengono salvati in outputs/:

- F1_architecture_kare.png (Architettura del sistema)

- F2_evidence_pipeline.png (Matrice di correlazione SCADA)

- F3_rul_failure_distribution.png (Distribuzione RUL per classi)

- F4_rul_curves_multiple_engines.png (Curve di degrado della flotta)

- F5_sensor_rolling_zscore.png (Deriva termica e Z-Score mobile)

- F6_kb_rule_graph.png (Grafo attivazione regole KB)

- F7_bayesian_network_structure.png (Topologia causale del DAG Bayesiano)

- F8_bayes_comparison.png (Andamento temporale del Failure Risk Score)

- F9_csp_schema.png (Schema dei vincoli e funzione di costo CSP)

- F10_csp_comparison.png (Diagramma di Gantt operativo delle squadre)

- F11_groupkfold_schema.png (Schema GroupKFold anti-leakage)

