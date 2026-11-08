"""
XGBoost Fraud Classification Model Training with MLflow Tracking
================================================================
- Stratified 80/20 train/test split preserving ~0.5% fraud distribution.
- Advanced tabular feature engineering:
  * Transaction type one-hot encoding
  * Balance error terms:
      error_balance_orig = newbalanceOrig + amount - oldbalanceOrg
      error_balance_dest = oldbalanceDest + amount - newbalanceDest
  * Balance drain ratio (amount / oldbalanceOrg)
  * Account emptied indicator (newbalanceOrig == 0)
- scale_pos_weight optimization for extreme class imbalance (~199:1).
- MLflow experiment tracking: params, metrics (PR-AUC, ROC-AUC, F1, Recall), and model registration.
- Saves model artifact to `models/artifacts/xgboost_model.json`.
"""

import json
import os
import time
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    f1_score,
    recall_score,
    precision_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
import xgboost as xgb
import mlflow
import mlflow.xgboost

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "paysim_sample.csv")
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "models", "artifacts")
MODEL_OUTPUT_PATH = os.path.join(ARTIFACTS_DIR, "xgboost_model.json")
METADATA_OUTPUT_PATH = os.path.join(ARTIFACTS_DIR, "model_metadata.json")


def engineer_features(df: pd.DataFrame):
    """
    Computes domain-specific fraud indicators and encodes transaction types.
    """
    df = df.copy()

    # Numeric conversions
    numeric_cols = ["amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest", "isFraud"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # 1. Balance Error Terms
    # In legitimate transactions, old - amount = new (so new + amount - old == 0)
    # Fraudsters or errors deviate significantly from 0
    df["error_balance_orig"] = df["newbalanceOrig"] + df["amount"] - df["oldbalanceOrg"]
    df["error_balance_dest"] = df["oldbalanceDest"] + df["amount"] - df["newbalanceDest"]

    # 2. Origin Drain Ratio (Fraction of origin balance transferred)
    df["orig_drain_ratio"] = np.where(
        df["oldbalanceOrg"] > 0,
        np.clip(df["amount"] / df["oldbalanceOrg"], 0.0, 10.0),
        0.0
    )

    # 3. Account Completely Emptied Flag
    df["orig_zero_balance_flag"] = (df["newbalanceOrig"] == 0.0).astype(int)

    # 4. Destination Zero Balance Prior to Transfer Flag
    df["dest_zero_balance_prior"] = (df["oldbalanceDest"] == 0.0).astype(int)

    # 5. One-Hot Encode Transaction Types
    # Standard PaySim types: CASH_OUT, PAYMENT, CASH_IN, TRANSFER, DEBIT
    type_dummies = pd.get_dummies(df["type"], prefix="type", dtype=float)
    expected_types = ["type_CASH_OUT", "type_CASH_IN", "type_PAYMENT", "type_TRANSFER", "type_DEBIT"]
    for t_col in expected_types:
        if t_col not in type_dummies.columns:
            type_dummies[t_col] = 0.0

    df = pd.concat([df, type_dummies[expected_types]], axis=1)

    feature_cols = [
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
        "error_balance_orig",
        "error_balance_dest",
        "orig_drain_ratio",
        "orig_zero_balance_flag",
        "dest_zero_balance_prior",
        "type_CASH_OUT",
        "type_CASH_IN",
        "type_PAYMENT",
        "type_TRANSFER",
        "type_DEBIT"
    ]

    return df, feature_cols


def train_xgboost_model():
    print("=" * 70)
    print(" XGBOOST FRAUD CLASSIFICATION TRAINING (MLFLOW INTEGRATION)")
    print("=" * 70)

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    # 1. Load Data
    print(f"[*] Loading transaction dataset: {DATA_PATH}")
    df_raw = pd.read_csv(DATA_PATH)
    print(f"[+] Loaded {len(df_raw):,} records. Total Frauds: {df_raw['isFraud'].sum()} ({df_raw['isFraud'].mean() * 100:.2f}%)")

    # 2. Feature Engineering
    df, feature_cols = engineer_features(df_raw)
    X = df[feature_cols]
    y = df["isFraud"].astype(int)

    # 3. Stratified 80/20 Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    total_neg = (y_train == 0).sum()
    total_pos = (y_train == 1).sum()
    scale_pos_weight = float(total_neg / total_pos) if total_pos > 0 else 1.0

    print(f"[*] Training samples: {len(X_train):,} (Frauds: {total_pos})")
    print(f"[*] Testing samples : {len(X_test):,} (Frauds: {(y_test == 1).sum()})")
    print(f"[*] Calculated scale_pos_weight: {scale_pos_weight:.2f}")

    # 4. Configure MLflow Tracking
    # Using modern SQLite database backend as recommended by MLflow 3.x
    mlflow_db_path = os.path.join(PROJECT_ROOT, "data", "mlflow.db").replace("\\", "/")
    mlflow.set_tracking_uri(f"sqlite:///{mlflow_db_path}")
    experiment_name = "Fraud_Detection_XGBoost"
    mlflow.set_experiment(experiment_name)

    hyperparams = {
        "n_estimators": 120,
        "max_depth": 5,
        "learning_rate": 0.08,
        "scale_pos_weight": scale_pos_weight,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "eval_metric": "logloss",
        "random_state": 42
    }

    print("\n[*] Starting MLflow run and training XGBClassifier...")
    with mlflow.start_run(run_name="xgboost_baseline_run") as run:
        # Log Hyperparameters
        mlflow.log_params(hyperparams)
        mlflow.log_param("train_samples", len(X_train))
        mlflow.log_param("test_samples", len(X_test))
        mlflow.log_param("feature_count", len(feature_cols))

        # Model Initialization & Training
        model = xgb.XGBClassifier(**hyperparams)
        t_train_start = time.perf_counter()
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        train_duration = time.perf_counter() - t_train_start
        print(f"[+] Model training completed in {train_duration:.2f} seconds.")

        # 5. Model Evaluation
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        y_pred = (y_pred_proba >= 0.5).astype(int)

        pr_auc = float(average_precision_score(y_test, y_pred_proba))
        roc_auc = float(roc_auc_score(y_test, y_pred_proba))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        recall = float(recall_score(y_test, y_pred, zero_division=0))
        precision = float(precision_score(y_test, y_pred, zero_division=0))

        # Log Metrics
        metrics = {
            "pr_auc": pr_auc,
            "roc_auc": roc_auc,
            "f1_score": f1,
            "recall": recall,
            "precision": precision,
            "train_duration_sec": train_duration
        }
        mlflow.log_metrics(metrics)

        # 6. Save Model Artifact locally & MLflow
        model.save_model(MODEL_OUTPUT_PATH)
        mlflow.xgboost.log_model(
            xgb_model=model,
            artifact_path="xgboost_model"
        )

        # Save Feature Metadata for Inference Gateway
        metadata = {
            "model_type": "xgboost",
            "feature_names": feature_cols,
            "num_features": len(feature_cols),
            "scale_pos_weight": scale_pos_weight,
            "optimal_threshold": 0.50,
            "metrics": metrics,
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        with open(METADATA_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        print("-" * 70)
        print(" EVALUATION RESULTS (TEST SET):")
        print("-" * 70)
        print(f"  * Precision-Recall AUC (PR-AUC) : {pr_auc:.4f}")
        print(f"  * ROC-AUC                       : {roc_auc:.4f}")
        print(f"  * F1-Score                      : {f1:.4f}")
        print(f"  * Recall                        : {recall:.4f}")
        print(f"  * Precision                     : {precision:.4f}")
        print("-" * 70)
        print("Confusion Matrix:")
        print(confusion_matrix(y_test, y_pred))
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, digits=4, zero_division=0))
        print(f"[+] Saved model artifact to: {MODEL_OUTPUT_PATH}")
        print(f"[+] Saved metadata to      : {METADATA_OUTPUT_PATH}")
        print(f"[+] MLflow Run ID          : {run.info.run_id}")
        print("=" * 70)

    return model, metrics


if __name__ == "__main__":
    train_xgboost_model()
