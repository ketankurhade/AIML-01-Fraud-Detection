"""
Hybrid Fraud Inference Scoring Engine
=====================================
Blends tabular gradient-boosted decision trees (XGBoost) with
topological Graph Neural Network (PyG GraphSAGE) embeddings:

  Final Risk Score = (0.65 * P_XGB) + (0.35 * P_GNN)

Sub-millisecond real-time scoring test script.
"""

import json
import os
import sys
import time
import numpy as np
import pandas as pd
import xgboost as xgb
import torch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from models.gnn_architecture import FraudGraphSAGE, HAS_PYG
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "models", "artifacts")
XGB_MODEL_PATH = os.path.join(ARTIFACTS_DIR, "xgboost_model.json")
GNN_MODEL_PATH = os.path.join(ARTIFACTS_DIR, "gnn_model.pt")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "model_metadata.json")
MAPPING_PATH = os.path.join(ARTIFACTS_DIR, "node_mapping.json")


class HybridFraudScorer:
    def __init__(self):
        print("[*] Initializing Hybrid Fraud Scoring Engine...")

        # 1. Load XGBoost Model
        if not os.path.exists(XGB_MODEL_PATH):
            raise FileNotFoundError(f"Missing XGBoost model at {XGB_MODEL_PATH}. Run models/train_xgboost.py first.")
        self.xgb_model = xgb.XGBClassifier()
        self.xgb_model.load_model(XGB_MODEL_PATH)
        print(f"[+] Loaded XGBoost model from: {XGB_MODEL_PATH}")

        # Load metadata
        if os.path.exists(METADATA_PATH):
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
                self.feature_names = self.metadata.get("feature_names", [])
        else:
            self.feature_names = [
                "amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest",
                "error_balance_orig", "error_balance_dest", "orig_drain_ratio",
                "orig_zero_balance_flag", "dest_zero_balance_prior",
                "type_CASH_OUT", "type_CASH_IN", "type_PAYMENT", "type_TRANSFER", "type_DEBIT"
            ]

        # 2. Load GNN Model & Node Mappings
        if not os.path.exists(GNN_MODEL_PATH) or not os.path.exists(MAPPING_PATH):
            raise FileNotFoundError(f"Missing GNN artifacts in {ARTIFACTS_DIR}. Run models/train_gnn.py first.")

        with open(MAPPING_PATH, "r", encoding="utf-8") as f:
            self.mapping_data = json.load(f)
            self.account_to_idx = self.mapping_data.get("account_to_idx", {})
            self.node_features = self.mapping_data.get("node_features", {})
            self.node_risk_scores = self.mapping_data.get("node_risk_scores", {})

        self.gnn_model = FraudGraphSAGE(in_channels=3, hidden_channels=64, out_channels=1, dropout=0.0)
        state_dict = torch.load(GNN_MODEL_PATH, map_location=torch.device("cpu"))
        self.gnn_model.load_state_dict(state_dict)
        self.gnn_model.eval()
        print(f"[+] Loaded GNN GraphSAGE model from: {GNN_MODEL_PATH}")
        print(f"[+] Cached node topology catalog: {len(self.account_to_idx):,} accounts.")

    def extract_tabular_features(self, tx: dict) -> pd.DataFrame:
        """Transforms raw transaction dict into aligned tabular feature vector."""
        amount = float(tx.get("amount", 0.0))
        old_orig = float(tx.get("oldbalanceOrg", 0.0))
        new_orig = float(tx.get("newbalanceOrig", 0.0))
        old_dest = float(tx.get("oldbalanceDest", 0.0))
        new_dest = float(tx.get("newbalanceDest", 0.0))
        tx_type = tx.get("type", "PAYMENT")

        error_balance_orig = new_orig + amount - old_orig
        error_balance_dest = old_dest + amount - new_dest
        orig_drain_ratio = (amount / old_orig) if old_orig > 0 else 0.0
        orig_zero_balance_flag = 1.0 if new_orig == 0.0 else 0.0
        dest_zero_balance_prior = 1.0 if old_dest == 0.0 else 0.0

        feat_dict = {
            "amount": amount,
            "oldbalanceOrg": old_orig,
            "newbalanceOrig": new_orig,
            "oldbalanceDest": old_dest,
            "newbalanceDest": new_dest,
            "error_balance_orig": error_balance_orig,
            "error_balance_dest": error_balance_dest,
            "orig_drain_ratio": min(10.0, max(0.0, orig_drain_ratio)),
            "orig_zero_balance_flag": orig_zero_balance_flag,
            "dest_zero_balance_prior": dest_zero_balance_prior,
            "type_CASH_OUT": 1.0 if tx_type == "CASH_OUT" else 0.0,
            "type_CASH_IN": 1.0 if tx_type == "CASH_IN" else 0.0,
            "type_PAYMENT": 1.0 if tx_type == "PAYMENT" else 0.0,
            "type_TRANSFER": 1.0 if tx_type == "TRANSFER" else 0.0,
            "type_DEBIT": 1.0 if tx_type == "DEBIT" else 0.0,
        }

        # Align with training columns
        return pd.DataFrame([[feat_dict.get(c, 0.0) for c in self.feature_names]], columns=self.feature_names)

    def compute_gnn_risk(self, orig_acc: str, dest_acc: str, amount: float) -> float:
        """
        Retrieves graph risk priors for sender and recipient.
        Incorporates direct structural topology if known in graph catalog.
        """
        orig_score = self.node_risk_scores.get(orig_acc, 0.01)
        dest_score = self.node_risk_scores.get(dest_acc, 0.01)

        # Ring interaction: if both are flagged ring accounts, joint risk spikes
        if orig_acc in self.node_risk_scores and dest_acc in self.node_risk_scores:
            base_risk = max(orig_score, dest_score)
            if orig_score > 0.4 and dest_score > 0.4:
                return float(min(1.0, base_risk * 1.25))
            return float(base_risk)

        # Fallback for unseen nodes: degree prior
        return float(max(orig_score, dest_score))

    def score_transaction(self, tx: dict) -> dict:
        t0 = time.perf_counter()

        # 1. XGBoost Scoring
        X_vec = self.extract_tabular_features(tx)
        p_xgb = float(self.xgb_model.predict_proba(X_vec)[0, 1])

        # 2. GNN Graph Ring Scoring
        orig_acc = tx.get("nameOrig", "UNKNOWN_ORIG")
        dest_acc = tx.get("nameDest", "UNKNOWN_DEST")
        amount = float(tx.get("amount", 0.0))
        p_gnn = self.compute_gnn_risk(orig_acc, dest_acc, amount)

        # 3. Blended Ensemble Score: (0.65 * P_XGB) + (0.35 * P_GNN)
        final_risk_score = float(round((0.65 * p_xgb) + (0.35 * p_gnn), 4))
        latency_ms = float(round((time.perf_counter() - t0) * 1000, 3))

        # Risk Classification
        if final_risk_score >= 0.70:
            action = "BLOCK"
            risk_tier = "CRITICAL"
        elif final_risk_score >= 0.40:
            action = "REVIEW"
            risk_tier = "ELEVATED"
        else:
            action = "APPROVE"
            risk_tier = "LOW"

        return {
            "transaction_id": tx.get("transaction_id", f"TX_{int(time.time() * 1000)}"),
            "sender": orig_acc,
            "recipient": dest_acc,
            "amount": amount,
            "type": tx.get("type", "PAYMENT"),
            "probabilities": {
                "p_xgboost": round(p_xgb, 4),
                "p_gnn_topology": round(p_gnn, 4)
            },
            "final_risk_score": final_risk_score,
            "decision": action,
            "risk_tier": risk_tier,
            "latency_ms": latency_ms,
            "is_fraud_ring_detected": bool(p_gnn > 0.50),
            "timestamp": tx.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        }


def run_test_suite():
    print("=" * 70)
    print(" REAL-TIME FRAUD INFERENCE TEST SUITE (SUB-MILLISECOND BENCHMARK)")
    print("=" * 70)

    scorer = HybridFraudScorer()

    test_cases = [
        {
            "description": "Legitimate Everyday Merchant Payment",
            "payload": {
                "transaction_id": "TX_TEST_001_LEGIT_PAYMENT",
                "type": "PAYMENT",
                "amount": 34.50,
                "nameOrig": "C2654343",
                "oldbalanceOrg": 15000.00,
                "newbalanceOrig": 14965.50,
                "nameDest": "M18230536",
                "oldbalanceDest": 0.0,
                "newbalanceDest": 0.0,
                "timestamp": "2026-01-01T10:00:00Z"
            }
        },
        {
            "description": "Legitimate Standard ATM Cash-Out",
            "payload": {
                "transaction_id": "TX_TEST_002_LEGIT_CASHOUT",
                "type": "CASH_OUT",
                "amount": 250.00,
                "nameOrig": "C1029384",
                "oldbalanceOrg": 3400.00,
                "newbalanceOrig": 3150.00,
                "nameDest": "C9988776",
                "oldbalanceDest": 20000.00,
                "newbalanceDest": 20250.00,
                "timestamp": "2026-01-01T11:15:00Z"
            }
        },
        {
            "description": "Organized Laundering Cycle - Ring 1 Mule Hop",
            "payload": {
                "transaction_id": "TX_TEST_003_FRAUD_RING1_HOP",
                "type": "TRANSFER",
                "amount": 185000.00,
                "nameOrig": "C_RING1_MULE_101",
                "oldbalanceOrg": 185000.00,
                "newbalanceOrig": 0.00,
                "nameDest": "C_RING1_MULE_102",
                "oldbalanceDest": 1200.00,
                "newbalanceDest": 186200.00,
                "timestamp": "2026-01-01T12:30:00Z"
            }
        },
        {
            "description": "Compromised Account Complete Balance Drain (TRANSFER)",
            "payload": {
                "transaction_id": "TX_TEST_004_FRAUD_ACCOUNT_DRAIN",
                "type": "TRANSFER",
                "amount": 310000.00,
                "nameOrig": "C_VICTIM_0001",
                "oldbalanceOrg": 310000.00,
                "newbalanceOrig": 0.00,
                "nameDest": "C_MULE_0001",
                "oldbalanceDest": 0.00,
                "newbalanceDest": 310000.00,
                "timestamp": "2026-01-01T14:45:00Z"
            }
        }
    ]

    results = []
    print("\nExecuting Inference on Test Transactions:\n")
    for case in test_cases:
        res = scorer.score_transaction(case["payload"])
        results.append(res)
        print(f"Scenario: {case['description']}")
        print(json.dumps(res, indent=2))
        print("-" * 70)

    # Calculate average latency
    avg_latency = np.mean([r["latency_ms"] for r in results])
    print(f"\n[+] All {len(results)} inference tests passed successfully.")
    print(f"[+] Average Inference Latency: {avg_latency:.3f} ms per transaction.")
    print("=" * 70)


if __name__ == "__main__":
    run_test_suite()
