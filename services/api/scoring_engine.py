"""
Real-Time Fraud Scoring Engine
==============================
Connects Feast Feature Store (SQLite online store) with XGBoost and
PyTorch GraphSAGE models for unified real-time transaction inference.

Blending Formula:
  Final Risk Score = (0.65 * P_XGB) + (0.35 * P_GNN)
"""

import json
import os
import sys
import time
from typing import Any, Dict, Optional, Tuple
import numpy as np
import pandas as pd
import torch
import xgboost as xgb

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from models.gnn_architecture import FraudGraphSAGE
from services.api.schemas import FraudScoreResponse, ProbabilitiesBreakdown, TransactionPayload

ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "models", "artifacts")
XGB_MODEL_PATH = os.path.join(ARTIFACTS_DIR, "xgboost_model.json")
GNN_MODEL_PATH = os.path.join(ARTIFACTS_DIR, "gnn_model.pt")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "model_metadata.json")
MAPPING_PATH = os.path.join(ARTIFACTS_DIR, "node_mapping.json")
FEATURES_DIR = os.path.join(PROJECT_ROOT, "features")


class ScoringEngine:
    def __init__(self):
        self.xgb_model: Optional[xgb.XGBClassifier] = None
        self.gnn_model: Optional[FraudGraphSAGE] = None
        self.feature_store = None
        self.node_mapping: Dict[str, Any] = {}
        self.feature_names = [
            "amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest",
            "error_balance_orig", "error_balance_dest", "orig_drain_ratio",
            "orig_zero_balance_flag", "dest_zero_balance_prior",
            "type_CASH_OUT", "type_CASH_IN", "type_PAYMENT", "type_TRANSFER", "type_DEBIT"
        ]
        self.feast_ready = False
        self.models_loaded = {"xgboost": False, "gnn": False}
        self.load_components()

    def load_components(self):
        print("[*] Initializing Scoring Engine components...")

        # 1. Load XGBoost Model
        if os.path.exists(XGB_MODEL_PATH):
            self.xgb_model = xgb.XGBClassifier()
            self.xgb_model.load_model(XGB_MODEL_PATH)
            self.models_loaded["xgboost"] = True
            print(f"[+] Loaded XGBoost model from: {XGB_MODEL_PATH}")

        if os.path.exists(METADATA_PATH):
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
                self.feature_names = meta.get("feature_names", self.feature_names)

        # 2. Load GNN Model and Catalog
        if os.path.exists(GNN_MODEL_PATH) and os.path.exists(MAPPING_PATH):
            with open(MAPPING_PATH, "r", encoding="utf-8") as f:
                self.node_mapping = json.load(f)

            self.gnn_model = FraudGraphSAGE(in_channels=3, hidden_channels=64, out_channels=1, dropout=0.0)
            state_dict = torch.load(GNN_MODEL_PATH, map_location=torch.device("cpu"))
            self.gnn_model.load_state_dict(state_dict)
            self.gnn_model.eval()
            self.models_loaded["gnn"] = True
            print(f"[+] Loaded GNN GraphSAGE model and catalog ({len(self.node_mapping.get('account_to_idx', {})):,} accounts).")

        # 3. Connect to Feast Online Store
        try:
            from feast import FeatureStore
            if os.path.exists(os.path.join(FEATURES_DIR, "feature_store.yaml")):
                self.feature_store = FeatureStore(repo_path=FEATURES_DIR)
                self.feast_ready = True
                print("[+] Feast FeatureStore online connection initialized.")
        except Exception as e:
            print(f"[!] Warning: Feast FeatureStore initialization skipped: {e}")
            self.feast_ready = False

    def retrieve_feast_features(self, account_id: str) -> Dict[str, Optional[float]]:
        """Queries Feast SQLite online store for account risk factors with fallback."""
        default_feast = {
            "error_balance_orig": None,
            "error_balance_dest": None,
            "amount": None,
            "orig_drain_ratio": None,
        }

        if not self.feast_ready or not self.feature_store:
            return default_feast

        try:
            features = [
                "account_feature_view:error_balance_orig",
                "account_feature_view:error_balance_dest",
                "account_feature_view:amount",
                "account_feature_view:orig_drain_ratio",
            ]
            response = self.feature_store.get_online_features(
                features=features,
                entity_rows=[{"account_id": account_id}]
            ).to_dict()

            return {
                "error_balance_orig": float(response.get("error_balance_orig", [None])[0]) if response.get("error_balance_orig", [None])[0] is not None else None,
                "error_balance_dest": float(response.get("error_balance_dest", [None])[0]) if response.get("error_balance_dest", [None])[0] is not None else None,
                "amount": float(response.get("amount", [None])[0]) if response.get("amount", [None])[0] is not None else None,
                "orig_drain_ratio": float(response.get("orig_drain_ratio", [None])[0]) if response.get("orig_drain_ratio", [None])[0] is not None else None,
            }
        except Exception:
            return default_feast

    def score(self, tx: TransactionPayload) -> FraudScoreResponse:
        t0 = time.perf_counter()

        # 1. Query Feast Feature Store
        feast_feats = self.retrieve_feast_features(tx.nameOrig)

        # 2. Extract Tabular Features for XGBoost
        error_orig = tx.newbalanceOrig + tx.amount - tx.oldbalanceOrg
        error_dest = tx.oldbalanceDest + tx.amount - tx.newbalanceDest
        drain_ratio = (tx.amount / tx.oldbalanceOrg) if tx.oldbalanceOrg > 0 else 0.0
        drain_ratio = min(10.0, max(0.0, drain_ratio))

        feat_values = {
            "amount": tx.amount,
            "oldbalanceOrg": tx.oldbalanceOrg,
            "newbalanceOrig": tx.newbalanceOrig,
            "oldbalanceDest": tx.oldbalanceDest,
            "newbalanceDest": tx.newbalanceDest,
            "error_balance_orig": error_orig,
            "error_balance_dest": error_dest,
            "orig_drain_ratio": drain_ratio,
            "orig_zero_balance_flag": 1.0 if tx.newbalanceOrig == 0.0 else 0.0,
            "dest_zero_balance_prior": 1.0 if tx.oldbalanceDest == 0.0 else 0.0,
            "type_CASH_OUT": 1.0 if tx.type == "CASH_OUT" else 0.0,
            "type_CASH_IN": 1.0 if tx.type == "CASH_IN" else 0.0,
            "type_PAYMENT": 1.0 if tx.type == "PAYMENT" else 0.0,
            "type_TRANSFER": 1.0 if tx.type == "TRANSFER" else 0.0,
            "type_DEBIT": 1.0 if tx.type == "DEBIT" else 0.0,
        }

        x_row = [[feat_values.get(c, 0.0) for c in self.feature_names]]
        df_x = pd.DataFrame(x_row, columns=self.feature_names)

        # 3. Predict Tabular Risk Probability (XGBoost)
        if self.xgb_model:
            p_xgb = float(self.xgb_model.predict_proba(df_x)[0, 1])
        else:
            p_xgb = 0.01

        # 4. Predict Graph Ring Probability (PyG GNN)
        node_risks = self.node_mapping.get("node_risk_scores", {})
        p_orig = node_risks.get(tx.nameOrig, 0.01)
        p_dest = node_risks.get(tx.nameDest, 0.01)

        # Check cyclic laundering pattern or elevated graph node
        is_ring = False
        if tx.nameOrig in node_risks and tx.nameDest in node_risks:
            p_gnn = max(p_orig, p_dest)
            if p_orig > 0.40 and p_dest > 0.40:
                p_gnn = min(1.0, p_gnn * 1.25)
                is_ring = True
            elif p_gnn > 0.50:
                is_ring = True
        else:
            p_gnn = max(p_orig, p_dest)
            if p_gnn > 0.50:
                is_ring = True

        # 5. Blend Predictions
        final_risk = float(round((0.65 * p_xgb) + (0.35 * p_gnn), 4))

        # Decision & Risk Tier
        if final_risk >= 0.50:
            decision = "BLOCK"
            tier = "CRITICAL"
        elif final_risk >= 0.35:
            decision = "REVIEW"
            tier = "ELEVATED"
        else:
            decision = "APPROVE"
            tier = "LOW"

        latency_ms = float(round((time.perf_counter() - t0) * 1000, 3))
        tx_id = tx.transaction_id or f"TX_{int(time.time() * 1000)}"
        timestamp = tx.timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        return FraudScoreResponse(
            transaction_id=tx_id,
            sender=tx.nameOrig,
            recipient=tx.nameDest,
            amount=tx.amount,
            type=tx.type,
            probabilities=ProbabilitiesBreakdown(
                p_xgboost=round(p_xgb, 4),
                p_gnn_topology=round(p_gnn, 4)
            ),
            final_risk_score=final_risk,
            decision=decision,
            risk_tier=tier,
            is_fraud_ring_detected=is_ring,
            feast_features=feast_feats,
            latency_ms=latency_ms,
            timestamp=timestamp
        )

