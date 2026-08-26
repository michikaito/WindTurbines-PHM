"""
experiment_runner.py - Orchestratore degli esperimenti e benchmark comparativo
tra i tre moduli del framework KARE (Knowledge Base vs Bayes vs CSP).

Script che fa partire l'esecuzione dei seguenti componenti:
1. kb_evaluation.py: Valutazione della Knowledge Base (motore logico) con metriche di classificazione.
2. cv_bayes.py: Cross-Validation della rete Bayesiana con metriche di accuratezza e F1-score.
3. csp_evaluation.py: Benchmarking e stress test del modulo CSP
4. generazione del report finale comparativo in formato CSV nella cartella outputs.

"""

import time
import pandas as pd
import wt_config
import kb_evaluation
import cv_bayes
import csp_evaluation

def run_all_experiments():
    print("======================================================================")
    print("   AVVIO SUITE COMPLETA ESPERIMENTI KARE (Wind Turbine PHM)")
    print("======================================================================\n")
    
    start_total = time.time()
    
    # 1. Benchmark Motore Logico
    print("[STEP 1/3] Valutazione Knowledge Base...")
    kb_report = kb_evaluation.evaluate_knowledge_base()
    print("-" * 70)
    
    # 2. Benchmark Cross-Validation Bayesiana
    print("\n[STEP 2/3] GroupKFold Cross-Validation Rete Bayesiana...")
    bayes_cv = cv_bayes.cross_validate_bayes(n_splits=5)
    print("-" * 70)
    
    # 3. Benchmark Ottimizzazione CSP
    print("\n[STEP 3/3] Stress Test e Benchmark CSP...")
    csp_bench = csp_evaluation.run_csp_benchmarks()
    print("-" * 70)
    
    # 4. Sintesi dei risultati comparativi
    summary_data = {
        "Metric": [
            "KB Weighted F1-Score",
            "KB Critical Recall",
            "Bayesian CV Mean Accuracy",
            "Bayesian CV Mean F1-Macro",
            "CSP Optimal Feasibility Rate (%)",
            "CSP Avg Solver Time (ms)"
        ],
        "Value": [
            round(kb_report.loc["weighted avg", "f1-score"], 4),
            round(kb_report.loc["CRITICAL", "recall"], 4),
            round(bayes_cv["accuracy"].mean(), 4),
            round(bayes_cv["f1_macro"].mean(), 4),
            round((csp_bench["status"].isin(["OPTIMAL", "FEASIBLE", "HEURISTIC_SOLVED"])).mean() * 100, 2),
            round(csp_bench["solver_time_ms"].mean(), 2)
        ]
    }
    
    summary_df = pd.DataFrame(summary_data)
    print("\n======================================================================")
    print("   RIEPILOGO COMPARATIVO FINALE ESPERIMENTI")
    print("======================================================================")
    print(summary_df.to_string(index=False))
    print("======================================================================")
    
    summary_path = wt_config.RESULTS_DIR / "model_comparison_wind_turbines.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"\n[OK] Sintesi finale esportata in: {summary_path}")
    print(f"[OK] Suite completata in {time.time() - start_total:.2f} secondi.")

if __name__ == "__main__":
    run_all_experiments()