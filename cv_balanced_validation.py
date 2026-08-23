"""
cv_balanced_validation.py - Baseline supervisionate per KARE (Wind Turbines PHM).

Valuta modelli supervisionati standard (Logistic Regression, Decision Tree, Naive Bayes) 
come confronto esterno rispetto al sistema KARE (KB + Bayes + CSP).

"""

from __future__ import annotations

import argparse
import os
import time

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.model_selection import GroupKFold
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

import wt_config
import scada_preprocessor
import logic_engine


def _one_hot_encoder_dense():
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def _format_mean_std(values):
    return f"{np.mean(values):.3f} ± {np.std(values, ddof=1):.3f}"


def _make_pipeline(model, feature_cols):
    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", _one_hot_encoder_dense(), feature_cols),
        ],
        remainder="drop",
    )

    return Pipeline([
        ("preprocess", preprocessor),
        ("clf", model),
    ])


def annotate_with_kb_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Arricchisce il dataset SCADA con i fatti booleani inferiti dalla Knowledge Base.
    """
    engine = logic_engine.LogicEngine()
    kb_records = []
    
    for _, row in df.iterrows():
        facts = engine.kb.evaluate_telemetry_facts(row)
        kb_records.append({
            "kb_oil_overheat": facts["gearbox_oil_high"] or facts["gearbox_oil_critical"],
            "kb_bearing_stress": facts["bearing_temp_critical"],
            "kb_hydraulic_low": facts["hydraulic_pressure_low"] or facts["hydraulic_pressure_critical"],
            "kb_thermal_runaway": facts["thermal_runaway_detected"],
            "kb_power_underperformance": facts["power_curve_underperformance"]
        })
        
    df_kb_facts = pd.DataFrame(kb_records, index=df.index)
    return pd.concat([df, df_kb_facts], axis=1)


def run_model_comparison(
    k: int = 5,
    max_rows: int | None = None,
    skip_kb: bool = False,
):
    total_start = time.perf_counter()

    print("=" * 90)
    print("KARE - BASELINE SUPERVISIONATE CON GROUPKFOLD (WIND TURBINES)")
    print("=" * 90)
    print(f"k fold: {k}")
    print(f"max_rows: {max_rows if max_rows else 'nessun limite'}")
    print(f"skip_kb: {skip_kb}")
    print("-" * 90, flush=True)

    print("[1/6] Caricamento dataset SCADA...", flush=True)
    df = scada_preprocessor.load_dataset()

    if df is None or df.empty:
        raise ValueError("Dataset non caricato o vuoto.")

    print(f"Dataset caricato: {df.shape[0]} righe, {df.shape[1]} colonne", flush=True)
    print(f"Turbine uniche: {df[wt_config.ID_COL].nunique()}", flush=True)

    if max_rows is not None and len(df) > max_rows:
        print(f"[INFO] Campionamento veloce: tengo {max_rows} righe su {len(df)}", flush=True)
        df = df.sort_values([wt_config.ID_COL, wt_config.TIME_COL]).groupby(wt_config.ID_COL, group_keys=False).head(
            max(1, max_rows // df[wt_config.ID_COL].nunique())
        )
        print(f"Dataset dopo campionamento: {df.shape[0]} righe", flush=True)

    print("[2/6] Annotazione con Knowledge Base...", flush=True)
    if skip_kb:
        print("[INFO] skip_kb=True: creo colonne KB a False per test veloce.", flush=True)
        for col in [
            "kb_oil_overheat",
            "kb_bearing_stress",
            "kb_hydraulic_low",
            "kb_thermal_runaway",
            "kb_power_underperformance",
        ]:
            if col not in df.columns:
                df[col] = False
    else:
        kb_start = time.perf_counter()
        df = annotate_with_kb_features(df)
        kb_time = time.perf_counter() - kb_start
        print(f"Annotazione KB completata in {kb_time:.2f}s", flush=True)

    target = "health_state"
    if target not in df.columns:
        raise ValueError(f"Colonna target mancante: {target}")

    if df[target].nunique() < 2:
        raise ValueError("Target con una sola classe: confronto non significativo.")

    # Discretizzazione/Binning qualitativo per le baseline supervisionate
    df["wind_regime"] = pd.cut(df["wind_speed_ms"], bins=[-np.inf, 6.0, 13.0, np.inf], labels=[0, 1, 2]).astype(str)
    df["gearbox_state"] = pd.cut(df["gearbox_oil_temp_c"], bins=[-np.inf, 80.0, 95.0, np.inf], labels=[0, 1, 2]).astype(str)
    df["hydraulic_state"] = (df["hydraulic_pressure_bar"] < wt_config.PHYSICAL_THRESHOLDS["hydraulic_min_safe"]).astype(str)

    feature_cols = [
        "wind_regime",
        "gearbox_state",
        "hydraulic_state",
        "kb_oil_overheat",
        "kb_bearing_stress",
        "kb_hydraulic_low",
        "kb_thermal_runaway",
        "kb_power_underperformance",
    ]

    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colonne feature mancanti: {missing}")

    X = df[feature_cols].astype(str)
    y = df[target].astype(int).values
    groups = df[wt_config.ID_COL].values

    print("[3/6] Statistiche dataset finale...", flush=True)
    print(f"Righe usate: {len(df)}", flush=True)
    print(f"Feature usate: {len(feature_cols)} -> {feature_cols}", flush=True)
    print("Distribuzione target (Health States 0=Healthy, 1=Warning, 2=Critical):", flush=True)
    print(df[target].value_counts().to_string(), flush=True)
    print("Turbine per GroupKFold:", len(np.unique(groups)), flush=True)

    n_groups = len(np.unique(groups))
    if n_groups < k:
        raise ValueError(f"Impossibile usare k={k}: turbine disponibili={n_groups}")

    cv = GroupKFold(n_splits=k)

    models = {
        "Baseline Most Frequent": DummyClassifier(strategy="most_frequent"),
        "Logistic Regression": LogisticRegression(
            max_iter=400,
            class_weight="balanced",
            random_state=42,
            solver="lbfgs",
        ),
        "Decision Tree": DecisionTreeClassifier(
            random_state=42,
            class_weight="balanced",
            max_depth=6,
            min_samples_leaf=5,
        ),
        "Gaussian Naive Bayes": GaussianNB(),
    }

    results = {}

    print("[4/6] Inizio cross-validation con GroupKFold...", flush=True)
    print("-" * 90, flush=True)

    for model_idx, (name, model) in enumerate(models.items(), start=1):
        model_start = time.perf_counter()

        print(f"\n[{model_idx}/{len(models)}] Modello: {name}", flush=True)

        fold_accuracy = []
        fold_balanced_accuracy = []
        fold_f1_macro = []

        for fold_idx, (train_idx, test_idx) in enumerate(cv.split(X, y, groups=groups), start=1):
            fold_start = time.perf_counter()

            X_train = X.iloc[train_idx]
            X_test = X.iloc[test_idx]
            y_train = y[train_idx]
            y_test = y[test_idx]

            train_groups = len(np.unique(groups[train_idx]))
            test_groups = len(np.unique(groups[test_idx]))

            print(
                f"  Fold {fold_idx}/{k} | "
                f"train={len(train_idx)} righe ({train_groups} turbine), "
                f"test={len(test_idx)} righe ({test_groups} turbine)...",
                flush=True,
            )

            pipeline = _make_pipeline(model, feature_cols)
            pipeline.fit(X_train, y_train)
            y_pred = pipeline.predict(X_test)

            acc = accuracy_score(y_test, y_pred)
            bal_acc = balanced_accuracy_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)

            fold_accuracy.append(acc)
            fold_balanced_accuracy.append(bal_acc)
            fold_f1_macro.append(f1)

            fold_time = time.perf_counter() - fold_start

            print(
                f"    -> acc={acc:.3f}, bal_acc={bal_acc:.3f}, "
                f"f1_macro={f1:.3f} | {fold_time:.2f}s",
                flush=True,
            )

        model_time = time.perf_counter() - model_start

        results[name] = {
            "accuracy_mean": float(np.mean(fold_accuracy)),
            "accuracy_std": float(np.std(fold_accuracy, ddof=1)),
            "balanced_accuracy_mean": float(np.mean(fold_balanced_accuracy)),
            "balanced_accuracy_std": float(np.std(fold_balanced_accuracy, ddof=1)),
            "f1_macro_mean": float(np.mean(fold_f1_macro)),
            "f1_macro_std": float(np.std(fold_f1_macro, ddof=1)),
            "runtime_seconds": float(model_time),
        }

        print(
            f"  COMPLETATO {name} in {model_time:.2f}s | "
            f"F1={_format_mean_std(fold_f1_macro)}, "
            f"Balanced Accuracy={_format_mean_std(fold_balanced_accuracy)}, "
            f"Accuracy={_format_mean_std(fold_accuracy)}",
            flush=True,
        )

    print("\n[5/6] Tabella finale comparativa", flush=True)
    print("=" * 90)
    print("| Modello | F1-Macro | Balanced Accuracy | Accuracy | Runtime |")
    print("|---|---:|---:|---:|---:|")

    rows = []
    for name, stats in results.items():
        f1_str = f"{stats['f1_macro_mean']:.3f} ± {stats['f1_macro_std']:.3f}"
        bal_str = f"{stats['balanced_accuracy_mean']:.3f} ± {stats['balanced_accuracy_std']:.3f}"
        acc_str = f"{stats['accuracy_mean']:.3f} ± {stats['accuracy_std']:.3f}"
        runtime_str = f"{stats['runtime_seconds']:.2f}s"

        print(f"| {name} | {f1_str} | {bal_str} | {acc_str} | {runtime_str} |")

        rows.append({
            "model": name,
            "f1_macro": f1_str,
            "balanced_accuracy": bal_str,
            "accuracy": acc_str,
            "f1_macro_mean": stats["f1_macro_mean"],
            "f1_macro_std": stats["f1_macro_std"],
            "balanced_accuracy_mean": stats["balanced_accuracy_mean"],
            "balanced_accuracy_std": stats["balanced_accuracy_std"],
            "accuracy_mean": stats["accuracy_mean"],
            "accuracy_std": stats["accuracy_std"],
            "runtime_seconds": stats["runtime_seconds"],
        })

    print("\n[6/6] Salvataggio CSV...", flush=True)
    wt_config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    out_df = pd.DataFrame(rows)
    out_path = wt_config.RESULTS_DIR / "model_comparison_wind_turbines.csv"
    out_df.to_csv(out_path, index=False)

    total_time = time.perf_counter() - total_start

    print(f"CSV salvato in: {out_path}", flush=True)
    print(f"Tempo totale: {total_time:.2f}s", flush=True)
    print("=" * 90)

    return results


def main():
    parser = argparse.ArgumentParser(description="KARE - Confronto baseline supervisionate (Wind Turbines)")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Usa solo un sottoinsieme di righe per test veloce. Non usare per risultati finali.",
    )
    parser.add_argument(
        "--skip-kb",
        action="store_true",
        help="Salta annotazione KB per test veloce. Non usare per risultati finali.",
    )

    args = parser.parse_args()

    run_model_comparison(
        k=args.k,
        max_rows=args.max_rows,
        skip_kb=args.skip_kb,
    )


if __name__ == "__main__":
    main()