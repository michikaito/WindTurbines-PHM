"""
main.py - Entry Point Orchestratore per il sistema KARE applicato
alla Manutenzione Predittiva di Turbine Eoliche.
"""

import sys
import time
import pandas as pd
from pathlib import Path

# Moduli interni del framework KARE
import wt_config
import scada_preprocessor
import logic_engine
import bayesian_learner
import csp_scheduler


def print_banner():
    banner = """
    ======================================================================
       KARE: Knowledge-Aware & Probabilistic Reasoning for Wind Turbines
       Predictive Maintenance, Bayesian Inference & CSP Scheduling
    ======================================================================
    """
    print(banner)


def run_pipeline():
    start_time = time.time()
    print_banner()

    # ------------------------------------------------------------------
    # FASE 1: Caricamento Dati e Preprocessing SCADA
    # ------------------------------------------------------------------
    print("[1/4] Caricamento e preprocessing delle serie temporali SCADA...")
    df = scada_preprocessor.load_dataset()
    print(f"      - Record totali: {len(df)}")
    print(f"      - Turbine monitorate: {df[wt_config.ID_COL].nunique()}")
    print(f"      - Orizzonte temporale max: {df[wt_config.TIME_COL].max()} ore\n")

    # ------------------------------------------------------------------
    # FASE 2: Inferenza Basata su Conoscenza (Logic Engine)
    # ------------------------------------------------------------------
    print("[2/4] Esecuzione Motore di Inferenza Logico (Knowledge Base)...")
    engine = logic_engine.LogicEngine()
    df_logic = engine.evaluate_dataframe(df)
    
    state_counts = df_logic["kb_state_name"].value_counts().to_dict()
    print(f"      - Diagnosi KB aggregate: {state_counts}")
    num_critical_events = (df_logic["kb_predicted_state"] == wt_config.HEALTH_STATES["CRITICAL"]).sum()
    print(f"      - Eventi di allarme critico individuati: {num_critical_events}\n")

    # ------------------------------------------------------------------
    # FASE 3: Apprendimento ed Inferenza Bayesiana
    # ------------------------------------------------------------------
    print("[3/4] Addestramento e inferenza Rete Bayesiana...")
    bayes_net = bayesian_learner.WindTurbineBayesianLearner()
    bayes_net.fit(df)
    df_bayes = bayes_net.evaluate_dataframe(df)
    
    avg_risk = df_bayes["failure_risk_score"].mean()
    high_risk_count = (df_bayes["failure_risk_score"] >= 0.5).sum()
    print(f"      - Punteggio medio rischio guasto: {avg_risk:.4f}")
    print(f"      - Campioni ad alto rischio probabilistico (Score >= 0.5): {high_risk_count}\n")

    # Unione risultati per l'ottimizzatore
    df_combined = df.merge(df_logic, on=[wt_config.ID_COL, wt_config.TIME_COL])
    df_combined["failure_risk_score"] = df_bayes["failure_risk_score"]
    df_combined["prob_healthy"] = df_bayes["prob_healthy"]
    df_combined["prob_warning"] = df_bayes["prob_warning"]
    df_combined["prob_critical"] = df_bayes["prob_critical"]

    # ------------------------------------------------------------------
    # FASE 4: Pianificazione Manutenzione CSP (Constraint Programming)
    # ------------------------------------------------------------------
    print("[4/4] Risoluzione Constraint Satisfaction Problem (CSP)...")
    optimizer = csp_scheduler.WindFarmMaintenanceOptimizer(
        planning_days=wt_config.CSP_CONFIG["planning_horizon_days"],
        max_crews=wt_config.CSP_CONFIG["max_crews_available"]
    )
    plan_result = optimizer.plan_maintenance(df_combined)

    print(f"      - Stato solver CSP: {plan_result['status']}")
    if plan_result.get("total_cost") is not None:
        print(f"      - Costo complessivo stimato intervento: € {plan_result['total_cost']:,}")
    
    schedule = plan_result.get("schedule", [])
    print(f"      - Interventi programmati con successo: {len(schedule)}\n")

    # Stampa Piano Operativo
    print("-" * 70)
    print("PIANO DI MANUTENZIONE OTTIMIZZATO (GANTT OPERATIVO)")
    print("-" * 70)
    if schedule:
        df_sched = pd.DataFrame(schedule)
        print(df_sched.to_string(index=False))
    else:
        print("Nessun intervento necessario o condizioni meteo completamente non permissive.")
    print("-" * 70 + "\n")

    # ------------------------------------------------------------------
    # SALVATAGGIO REPORT COMPLETO
    # ------------------------------------------------------------------
    output_csv = wt_config.RESULTS_DIR / "pipeline_execution_summary.csv"
    df_combined.to_csv(output_csv, index=False)
    
    if schedule:
        schedule_csv = wt_config.RESULTS_DIR / "maintenance_schedule_plan.csv"
        pd.DataFrame(schedule).to_csv(schedule_csv, index=False)
        print(f"[OK] Piano operativo esportato in: {schedule_csv}")

    print(f"[OK] Risultati completi esportati in: {output_csv}")
    elapsed = time.time() - start_time
    print(f"[OK] Pipeline KARE completata con successo in {elapsed:.2f} secondi.")


if __name__ == "__main__":
    run_pipeline()