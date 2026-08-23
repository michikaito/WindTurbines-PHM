"""
csp_evaluation.py - Benchmark e valutazione delle prestazioni del solver CSP
su diversi scenari operativi, orizzonti temporali e disponibilità delle squadre.

Questo modulo stressa l'ottimizzatore CSP su diversi orizzonti temporali (7, 14, 21, 30 giorni) e diversi numeri di squadre disponibili, calcolando:
-Tasso di successo e fattibilità della pianificazione (Feasibility Rate).
-Costo totale dell'orizzonte di manutenzione.
-Tempo medio di risoluzione del solver OR-Tools CP-SAT
"""

import time
import pandas as pd
import numpy as np
import wt_config
import scada_preprocessor
import logic_engine
import bayesian_learner
import csp_scheduler

def run_csp_benchmarks():
    print("--- Benchmark e Valutazione Modulo CSP (csp_scheduler) ---")
    
    # 1. Carica dati e genera predizioni integrate
    df = scada_preprocessor.load_dataset()
    
    le = logic_engine.LogicEngine()
    df_logic = le.evaluate_dataframe(df)
    
    bl = bayesian_learner.WindTurbineBayesianLearner()
    bl.fit(df)
    df_bayes = bl.evaluate_dataframe(df)
    
    df_combined = df.merge(df_logic, on=[wt_config.ID_COL, wt_config.TIME_COL])
    df_combined["failure_risk_score"] = df_bayes["failure_risk_score"]
    
    # 2. Matrice di esperimenti (Orizzonti temporali x Squadre disponibili)
    horizons = [7, 14, 21, 30]
    crews_list = [1, 2, 3, 4]
    
    results = []
    
    for h in horizons:
        for c in crews_list:
            opt = csp_scheduler.WindFarmMaintenanceOptimizer(planning_days=h, max_crews=c)
            
            start_t = time.time()
            res = opt.plan_maintenance(df_combined)
            elapsed_ms = (time.time() - start_t) * 1000
            
            schedule = res.get("schedule", [])
            total_cost = res.get("total_cost", 0)
            status = res.get("status", "UNKNOWN")
            
            critical_serviced = sum(1 for item in schedule if item["is_critical"])
            
            results.append({
                "planning_horizon_days": h,
                "crews_available": c,
                "status": status,
                "scheduled_interventions": len(schedule),
                "critical_repaired": critical_serviced,
                "total_cost_eur": total_cost,
                "solver_time_ms": round(elapsed_ms, 2)
            })
            
            print(f"  Orizzonte: {h:2d} gg | Squadre: {c} -> Stato: {status:<10} | Interventi: {len(schedule):2d} | Tempo: {elapsed_ms:6.2f} ms")

    df_res = pd.DataFrame(results)
    
    out_path = wt_config.RESULTS_DIR / "csp_evaluation_wind_turbines.csv"
    df_res.to_csv(out_path, index=False)
    print(f"\n[OK] Report benchmark CSP salvato in: {out_path}")
    return df_res

if __name__ == "__main__":
    run_csp_benchmarks()