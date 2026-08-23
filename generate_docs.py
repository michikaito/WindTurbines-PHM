"""
generate_docs.py - Generatore automatico di figure e grafici 
ad alta risoluzione per la documentazione tecnica e la relazione di KARE 
applicato alla Manutenzione Predittiva di Turbine Eoliche.

per generare i documenti basta mandare il comando da terminale:
    python generate_docs.py
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path

import wt_config
import scada_preprocessor
import logic_engine
import bayesian_learner
import csp_scheduler

# Stile e formattazione globale per le figure
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams.update({
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.titlesize': 14,
    'figure.autolayout': True,
    'savefig.dpi': 300
})

def save_fig(fig, filename: str):
    out_path = wt_config.FIGURES_DIR / filename
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)
    print(f"  [+] Generato: {out_path.name}")


def generate_all_figures():
    print("======================================================================")
    print("   GENERAZIONE ASSET GRAFICI DOCUMENTAZIONE KARE (Turbine Eoliche)")
    print("======================================================================\n")
    
    # Caricamento ed esecuzione modelli per estrarre i dati reali
    df = scada_preprocessor.load_dataset()
    
    le = logic_engine.LogicEngine()
    df_logic = le.evaluate_dataframe(df)
    
    bl = bayesian_learner.WindTurbineBayesianLearner()
    bl.fit(df)
    df_bayes = bl.evaluate_dataframe(df)
    
    df_merged = df.merge(df_logic, on=[wt_config.ID_COL, wt_config.TIME_COL])
    df_merged["failure_risk_score"] = df_bayes["failure_risk_score"]

    # -------------------------------------------------------------
    # F1: Architettura di Sistema KARE
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axis('off')
    
    boxes = [
        {"text": "1. Telemetria SCADA\n& Ingegnerizzazione Dati\n(scada_preprocessor.py)", "xy": (0.1, 0.5), "color": "#dbeafe", "edge": "#2563eb"},
        {"text": "2. Diagnosi Logica\nKnowledge Base\n(logic_engine.py)", "xy": (0.38, 0.72), "color": "#fef3c7", "edge": "#d97706"},
        {"text": "3. Stima Rischio RUL\nRete Bayesiana (BN)\n(bayesian_learner.py)", "xy": (0.38, 0.28), "color": "#e0e7ff", "edge": "#4f46e5"},
        {"text": "4. Ottimizzatore CSP\nPianificazione Risorse\n(csp_scheduler.py)", "xy": (0.75, 0.5), "color": "#dcfce7", "edge": "#16a34a"},
    ]
    
    for b in boxes:
        ax.text(b["xy"][0], b["xy"][1], b["text"], ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.8", facecolor=b["color"], edgecolor=b["edge"], lw=2),
                fontsize=11, weight='bold')
        
    # Frecce di flusso
    arrow_props = dict(arrowstyle="->", lw=2, color="#334155")
    ax.annotate("", xy=(0.26, 0.72), xytext=(0.20, 0.55), arrowprops=arrow_props)
    ax.annotate("", xy=(0.26, 0.28), xytext=(0.20, 0.45), arrowprops=arrow_props)
    ax.annotate("", xy=(0.63, 0.55), xytext=(0.50, 0.72), arrowprops=arrow_props)
    ax.annotate("", xy=(0.63, 0.45), xytext=(0.50, 0.28), arrowprops=arrow_props)
    
    ax.set_title("KARE Architecture: Integrazione Ibrida Knowledge-Based, Bayes e CSP", pad=20, weight='bold')
    save_fig(fig, "F1_architecture_kare.png")

    # -------------------------------------------------------------
    # F2: Pipeline di Estrazione Evidenze Sensoriali
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4.5))
    sensors_sample = ["gearbox_oil_temp_c", "gearbox_bearing_temp_c", "hydraulic_pressure_bar", "active_power_kw"]
    corr = df[sensors_sample].corr()
    sns.heatmap(corr, annot=True, cmap="YlGnBu", fmt=".2f", ax=ax, cbar=True)
    ax.set_title("Correlazione tra Parametri SCADA e Variabili di Stato")
    save_fig(fig, "F2_evidence_pipeline.png")

    # -------------------------------------------------------------
    # F3: Distribuzione RUL e Transizioni di Stato
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.histplot(df["RUL"], bins=30, kde=True, color="#0284c7", ax=ax)
    ax.axvline(wt_config.CRITICAL_RUL_THRESHOLD, color="red", linestyle="--", label="Soglia Critica (100h)")
    ax.axvline(wt_config.WARNING_RUL_THRESHOLD, color="orange", linestyle="--", label="Soglia Warning (300h)")
    ax.set_xlabel("Ore di Vita Residua (RUL - Ore)")
    ax.set_ylabel("Frequenza Campioni")
    ax.set_title("Distribuzione della RUL e Zonizzazione degli Stati di Salute")
    ax.legend()
    save_fig(fig, "F3_rul_failure_distribution.png")

    # -------------------------------------------------------------
    # F4: Curve di Degrado RUL su Più Turbine
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4.5))
    sample_turbines = df[wt_config.ID_COL].unique()[:5]
    for t_id in sample_turbines:
        sub = df[df[wt_config.ID_COL] == t_id]
        ax.plot(sub[wt_config.TIME_COL], sub["RUL"], label=t_id, lw=1.8)
    ax.set_xlabel("Ore di Funzionamento (h)")
    ax.set_ylabel("RUL (Ore Residue)")
    ax.set_title("Traiettorie di Consumo Vita Residua per Flotta di Turbine")
    ax.legend(title="Turbina")
    save_fig(fig, "F4_rul_curves_multiple_engines.png")

    # -------------------------------------------------------------
    # F5: Deriva Termica e Rolling Z-Score
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    single_t = df[df[wt_config.ID_COL] == sample_turbines[0]]
    
    ax1.plot(single_t[wt_config.TIME_COL], single_t["gearbox_oil_temp_c"], color="#e11d48", label="Temp Olio (°C)")
    ax1.axhline(wt_config.PHYSICAL_THRESHOLDS["gearbox_oil_max_safe"], color="orange", linestyle=":", label="Soglia Safe")
    ax1.axhline(wt_config.PHYSICAL_THRESHOLDS["gearbox_oil_alarm"], color="red", linestyle="--", label="Allarme Critico")
    ax1.set_ylabel("Temperatura (°C)")
    ax1.set_title(f"Monitoraggio Termico e Z-Score Anomalie ({sample_turbines[0]})")
    ax1.legend(loc="upper left")
    
    ax2.plot(single_t[wt_config.TIME_COL], single_t["gearbox_oil_temp_c_zscore"], color="#7c3aed", label="Rolling Z-Score")
    ax2.axhline(wt_config.ZSCORE_THRESHOLD, color="black", linestyle="--", label=f"Soglia Anomalia ({wt_config.ZSCORE_THRESHOLD}σ)")
    ax2.set_xlabel("Ore di Funzionamento (h)")
    ax2.set_ylabel("Z-Score")
    ax2.legend(loc="upper left")
    save_fig(fig, "F5_sensor_rolling_zscore.png")

    # -------------------------------------------------------------
    # F6: Grafo Regole Motore Logico (KB Rule Graph)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4.5))
    rule_counts = df_merged["fault_details"].value_counts().head(5)
    rule_counts.plot(kind="barh", color="#f59e0b", ax=ax)
    ax.set_xlabel("Numero di Attivazioni Regola")
    ax.set_ylabel("Diagnosi Inferita")
    ax.set_title("Frequenza di Inferenza delle Regole della Knowledge Base")
    save_fig(fig, "F6_kb_rule_graph.png")

    # -------------------------------------------------------------
    # F7: Topologia Rete Bayesiana (DAG)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.axis('off')
    nodes = {
        "Vento": (0.2, 0.75), "Efficienza": (0.5, 0.85),
        "Temp_Olio": (0.2, 0.45), "Stress_Cuscinetti": (0.5, 0.45),
        "Pressione_Pitch": (0.5, 0.15), "Health_State": (0.8, 0.5)
    }
    for name, (x, y) in nodes.items():
        ax.text(x, y, name, ha='center', va='center',
                bbox=dict(boxstyle="circle,pad=0.5", facecolor="#ede9fe", edgecolor="#6d28d9", lw=2),
                fontsize=9, weight='bold')
        
    edges = [
        ("Vento", "Temp_Olio"), ("Vento", "Efficienza"),
        ("Temp_Olio", "Stress_Cuscinetti"), ("Temp_Olio", "Health_State"),
        ("Stress_Cuscinetti", "Health_State"), ("Pressione_Pitch", "Health_State"),
        ("Efficienza", "Health_State")
    ]
    for src, dst in edges:
        p1, p2 = nodes[src], nodes[dst]
        ax.annotate("", xy=p2, xytext=p1, arrowprops=dict(arrowstyle="->", lw=1.5, color="#4c1d95"))
        
    ax.set_title("Topologia Causale della Rete Bayesiana (DAG)", weight='bold')
    save_fig(fig, "F7_bayesian_network_structure.png")

    # -------------------------------------------------------------
    # F8: Confronto Probabilistico vs Ground Truth
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4.5))
    single_res = df_merged[df_merged[wt_config.ID_COL] == sample_turbines[0]]
    ax.plot(single_res[wt_config.TIME_COL], single_res["failure_risk_score"], label="Failure Risk Score (BN)", color="#ef4444", lw=2)
    ax.plot(single_res[wt_config.TIME_COL], single_res["health_state"] / 2.0, label="Stato Reale Normalizzato", color="#3b82f6", linestyle="--")
    ax.set_xlabel("Ore di Funzionamento (h)")
    ax.set_ylabel("Indice di Rischio [0, 1]")
    ax.set_title(f"Evoluzione del Rischio di Guasto Bayesiano ({sample_turbines[0]})")
    ax.legend()
    save_fig(fig, "F8_bayes_comparison.png")

    # -------------------------------------------------------------
    # F9: Schema Vincoli CSP
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.axis('off')
    csp_text = (
        "VINCOLI DI OTTIMIZZAZIONE CSP (Constraint Programming)\n"
        "------------------------------------------------------------------------\n"
        "• Hard Constraint 1 (Unicità): sum_{d,c} X[t,d,c] <= 1\n"
        "• Hard Constraint 2 (Scadenza Critica): sum_{d<=Deadline, c} X[t,d,c] == 1\n"
        "• Hard Constraint 3 (Capacità): sum_{t} X[t,d,c] <= 1 per ogni giorno d e squadra c\n"
        "• Hard Constraint 4 (Sicurezza Vento): X[t,d,c] == 0 se Vento_Previs[d] > 12 m/s\n\n"
        "OBIETTIVO: Minimizzare (Costi Fissi + Penali di Fermo Impianto + Rischio Residuo)"
    )
    ax.text(0.5, 0.5, csp_text, ha='center', va='center', family='monospace', fontsize=10,
            bbox=dict(boxstyle="square,pad=1.0", facecolor="#f8fafc", edgecolor="#94a3b8", lw=1.5))
    ax.set_title("Modellazione Matematica e Vincoli CSP", weight='bold')
    save_fig(fig, "F9_csp_schema.png")

    # -------------------------------------------------------------
    # F10: Diagramma di Gantt Schedulazione CSP
    # -------------------------------------------------------------
    opt = csp_scheduler.WindFarmMaintenanceOptimizer(planning_days=10, max_crews=3)
    plan = opt.plan_maintenance(df_merged)
    schedule = plan.get("schedule", [])
    
    fig, ax = plt.subplots(figsize=(9, 4.5))
    if schedule:
        df_sched = pd.DataFrame(schedule)
        for _, row in df_sched.iterrows():
            crew_num = int(row["crew_id"].split("_")[-1])
            color = "#ef4444" if row["is_critical"] else "#3b82f6"
            ax.barh(crew_num, 0.8, left=row["day"] - 0.4, color=color, edgecolor="black")
            ax.text(row["day"], crew_num, row["turbine_id"], ha='center', va='center', color='white', weight='bold', fontsize=9)
        
        ax.set_yticks([1, 2, 3])
        ax.set_yticklabels(["Squadra 1", "Squadra 2", "Squadra 3"])
        ax.set_xlabel("Giorno di Pianificazione")
        ax.set_title("Gantt Operativo: Assegnazione Turni e Squadre (CSP Solver)")
    else:
        ax.text(0.5, 0.5, "Nessun intervento programmato", ha='center', va='center')
    save_fig(fig, "F10_csp_comparison.png")

    # -------------------------------------------------------------
    # F11: Schema GroupKFold Cross-Validation
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4))
    folds = ["Fold 1", "Fold 2", "Fold 3", "Fold 4", "Fold 5"]
    for i, fold in enumerate(folds):
        # 4 train folds, 1 val fold
        for j in range(5):
            col = "#ef4444" if j == i else "#22c55e"
            label_t = "Val (Test)" if j == i else "Train"
            ax.barh(i, 1, left=j, color=col, edgecolor="white")
            ax.text(j + 0.5, i, label_t, ha='center', va='center', color='white', weight='bold', fontsize=8)
            
    ax.set_yticks(range(5))
    ax.set_yticklabels(folds)
    ax.set_xlabel("Gruppi di Turbine Eoliche")
    ax.set_title("Schema GroupKFold: Prevenzione Data Leakage tra Turbine")
    save_fig(fig, "F11_groupkfold_schema.png")
    
    print("\n[OK] Tutti gli asset grafici sono stati generati con successo in 'outputs/'.")

if __name__ == "__main__":
    generate_all_figures()