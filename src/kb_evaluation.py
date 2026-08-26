# ==============================================================================
# kb_evaluation.py - Valutazione quantitativa delle prestazioni del Motore Logico
# ==============================================================================
"""
kb_evaluation.py - Valuta l'accuratezza diagnostica del sistema a regole
confrontando lo stato inferito rispetto allo stato di salute reale (RUL ground truth).
"""

import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
import wt_config
import scada_preprocessor
import logic_engine

def evaluate_knowledge_base():
    print("--- Valutazione Prestazioni Motore Logico (KB) ---")
    df = scada_preprocessor.load_dataset()
    
    engine = logic_engine.LogicEngine()
    df_kb = engine.evaluate_dataframe(df)
    
    # Unione con ground truth
    df_eval = df.merge(df_kb, on=[wt_config.ID_COL, wt_config.TIME_COL])
    
    y_true = df_eval["health_state"]
    y_pred = df_eval["kb_predicted_state"]
    
    target_names = ["HEALTHY", "WARNING", "CRITICAL"]
    report = classification_report(y_true, y_pred, target_names=target_names, output_dict=True)
    report_df = pd.DataFrame(report).transpose()
    
    print("\nReport di Classificazione Diagnostica:")
    print(classification_report(y_true, y_pred, target_names=target_names))
    
    cm = confusion_matrix(y_true, y_pred)
    print("Matrice di Confusione:")
    print(cm)
    
    out_path = wt_config.RESULTS_DIR / "kb_evaluation_wind_turbines.csv"
    report_df.to_csv(out_path)
    print(f"\n[OK] Risultati salvati in: {out_path}")
    return report_df

if __name__ == "__main__":
    evaluate_knowledge_base()