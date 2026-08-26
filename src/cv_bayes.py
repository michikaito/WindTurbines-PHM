# ==============================================================================
# cv_bayes.py - GroupKFold Cross-Validation per la Rete Bayesiana
# ==============================================================================
"""
cv_bayes.py - Esegue la validazione incrociata raggruppando per turbina (GroupKFold)
per garantire generalizzazione a macchine mai viste nel training set.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.metrics import accuracy_score, f1_score, log_loss
import wt_config
import scada_preprocessor
import bayesian_learner

def cross_validate_bayes(n_splits: int = 5):
    print(f"--- GroupKFold Cross-Validation Rete Bayesiana ({n_splits} Folds) ---")
    df = scada_preprocessor.load_dataset()
    
    gkf = GroupKFold(n_splits=n_splits)
    groups = df[wt_config.ID_COL]
    
    fold_metrics = []
    
    for fold, (train_idx, val_idx) in enumerate(gkf.split(df, groups=groups), 1):
        df_train = df.iloc[train_idx].copy()
        df_val = df.iloc[val_idx].copy()
        
        learner = bayesian_learner.WindTurbineBayesianLearner()
        learner.fit(df_train)
        
        val_preds = learner.evaluate_dataframe(df_val)
        
        y_true = df_val["health_state"].values
        y_pred = val_preds["bayes_pred_state"].values
        
        acc = accuracy_score(y_true, y_pred)
        f1_macro = f1_score(y_true, y_pred, average="macro")
        
        fold_metrics.append({
            "fold": fold,
            "train_turbines": df_train[wt_config.ID_COL].nunique(),
            "val_turbines": df_val[wt_config.ID_COL].nunique(),
            "accuracy": round(acc, 4),
            "f1_macro": round(f1_macro, 4)
        })
        print(f"  Fold {fold}: Accuracy = {acc:.4f} | F1-Macro = {f1_macro:.4f}")
        
    df_res = pd.DataFrame(fold_metrics)
    print("\nMetriche Medie Cross-Validation:")
    print(f"  Accuracy Media: {df_res['accuracy'].mean():.4f} +/- {df_res['accuracy'].std():.4f}")
    print(f"  F1-Macro Medio: {df_res['f1_macro'].mean():.4f} +/- {df_res['f1_macro'].std():.4f}")
    
    out_path = wt_config.RESULTS_DIR / "bayes_cv_wind_turbines.csv"
    df_res.to_csv(out_path, index=False)
    print(f"[OK] Risultati salvati in: {out_path}")
    return df_res

if __name__ == "__main__":
    cross_validate_bayes()