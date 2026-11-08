"""
PyTorch Geometric (PyG) Fraud Ring Graph Neural Network Training
================================================================
Constructs a transaction graph where:
  - Nodes: Bank accounts (nameOrig and nameDest)
  - Directed Edges: Financial transactions (source -> destination)
  - Node Features: Transacted volume (log1p), out-degree, in-degree
  - Node Labels: 1 if account participated in a fraudulent transaction, 0 otherwise
  - Loss: Weighted BCEWithLogitsLoss to handle severe imbalance (~1% fraud nodes)
  - Artifacts:
      * models/artifacts/gnn_model.pt
      * models/artifacts/node_mapping.json
"""

import json
import os
import sys
import time
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score, f1_score
import torch
import torch.nn as nn

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from models.gnn_architecture import FraudGraphSAGE, HAS_PYG
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "paysim_sample.csv")
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "models", "artifacts")
MODEL_OUTPUT_PATH = os.path.join(ARTIFACTS_DIR, "gnn_model.pt")
MAPPING_OUTPUT_PATH = os.path.join(ARTIFACTS_DIR, "node_mapping.json")


def build_fraud_graph(df: pd.DataFrame):
    """
    Constructs node feature tensors, directed edge index, and node labels from transactions.
    """
    print("[*] Extracting accounts and building directed transaction graph...")

    # Unique accounts across origin and destination
    all_accounts = sorted(list(set(df["nameOrig"].unique()).union(set(df["nameDest"].unique()))))
    account_to_idx = {acc: i for i, acc in enumerate(all_accounts)}
    num_nodes = len(all_accounts)

    print(f"[+] Total unique graph nodes (accounts): {num_nodes:,}")

    # Initialize node feature accumulators
    volumes = np.zeros(num_nodes, dtype=np.float32)
    out_degrees = np.zeros(num_nodes, dtype=np.float32)
    in_degrees = np.zeros(num_nodes, dtype=np.float32)
    fraud_labels = np.zeros(num_nodes, dtype=np.float32)

    # Edge list
    src_indices = []
    dst_indices = []

    for _, row in df.iterrows():
        orig = row["nameOrig"]
        dest = row["nameDest"]
        amount = float(row["amount"])
        is_fraud = int(row["isFraud"])

        src_idx = account_to_idx[orig]
        dst_idx = account_to_idx[dest]

        src_indices.append(src_idx)
        dst_indices.append(dst_idx)

        volumes[src_idx] += amount
        volumes[dst_idx] += amount
        out_degrees[src_idx] += 1
        in_degrees[dst_idx] += 1

        if is_fraud == 1:
            fraud_labels[src_idx] = 1.0
            fraud_labels[dst_idx] = 1.0

    # Log1p transform volume for stable gradient propagation
    log_volumes = np.log1p(volumes)

    # Node features: [transacted_volume, out_degree, in_degree]
    x_matrix = np.stack([log_volumes, out_degrees, in_degrees], axis=1)

    x = torch.tensor(x_matrix, dtype=torch.float32)
    edge_index = torch.tensor([src_indices, dst_indices], dtype=torch.long)
    y = torch.tensor(fraud_labels, dtype=torch.float32).unsqueeze(1)

    fraud_node_count = int(fraud_labels.sum())
    print(f"[+] Total directed edges: {edge_index.size(1):,}")
    print(f"[+] Flagged fraud nodes : {fraud_node_count} ({fraud_node_count / num_nodes * 100:.2f}%)")

    return x, edge_index, y, account_to_idx, all_accounts


def train_gnn_model():
    print("=" * 70)
    print(" PYTORCH FRAUD RING GRAPH NEURAL NETWORK TRAINING")
    print(f" Engine: {'PyTorch Geometric (PyG)' if HAS_PYG else 'PyTorch Native GraphSAGE'}")
    print("=" * 70)

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    # 1. Load Data & Build Graph
    df = pd.read_csv(DATA_PATH)
    x, edge_index, y, account_to_idx, all_accounts = build_fraud_graph(df)

    num_nodes = x.size(0)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Training device: {device}")

    x = x.to(device)
    edge_index = edge_index.to(device)
    y = y.to(device)

    # 2. Train / Test Node Mask (80/20 stratified split)
    np.random.seed(42)
    rand_perm = np.random.permutation(num_nodes)
    split_idx = int(num_nodes * 0.8)

    train_mask = torch.zeros(num_nodes, dtype=torch.bool)
    test_mask = torch.zeros(num_nodes, dtype=torch.bool)
    train_mask[rand_perm[:split_idx]] = True
    test_mask[rand_perm[split_idx:]] = True

    # 3. Model & Loss Definition
    model = FraudGraphSAGE(in_channels=3, hidden_channels=64, out_channels=1, dropout=0.2).to(device)

    # Class weighting for BCEWithLogitsLoss
    pos_count = (y[train_mask] == 1).sum().item()
    neg_count = (y[train_mask] == 0).sum().item()
    pos_weight_val = max(1.0, float(neg_count / max(1, pos_count)))
    pos_weight = torch.tensor([pos_weight_val], device=device)

    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)

    print(f"[*] Node training samples : {train_mask.sum().item():,}")
    print(f"[*] Node testing samples  : {test_mask.sum().item():,}")
    print(f"[*] Loss pos_weight factor: {pos_weight_val:.2f}")

    # 4. Training Loop
    epochs = 60
    print(f"\n[*] Training GraphSAGE for {epochs} epochs...")
    t_start = time.perf_counter()

    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        out = model(x, edge_index)
        loss = criterion(out[train_mask], y[train_mask])
        loss.backward()
        optimizer.step()

        if epoch % 10 == 0 or epoch == epochs:
            model.eval()
            with torch.no_grad():
                val_out = model(x, edge_index)
                val_probs = torch.sigmoid(val_out[test_mask]).cpu().numpy().flatten()
                val_true = y[test_mask].cpu().numpy().flatten()

                val_pr_auc = average_precision_score(val_true, val_probs) if val_true.sum() > 0 else 0.0
                val_roc_auc = roc_auc_score(val_true, val_probs) if val_true.sum() > 0 else 0.0

            print(f"  Epoch {epoch:02d}/{epochs:02d} | Loss: {loss.item():.4f} | Val PR-AUC: {val_pr_auc:.4f} | Val ROC-AUC: {val_roc_auc:.4f}")

    train_time = time.perf_counter() - t_start
    print(f"[+] Graph training finished in {train_time:.2f} seconds.")

    # 5. Final Evaluation on Test Mask
    model.eval()
    with torch.no_grad():
        all_logits = model(x, edge_index)
        all_probs = torch.sigmoid(all_logits).cpu().numpy().flatten()
        test_probs = all_probs[test_mask.cpu().numpy()]
        test_true = y[test_mask].cpu().numpy().flatten()

        test_pr_auc = float(average_precision_score(test_true, test_probs)) if test_true.sum() > 0 else 0.0
        test_roc_auc = float(roc_auc_score(test_true, test_probs)) if test_true.sum() > 0 else 0.0
        test_preds = (test_probs >= 0.5).astype(int)
        test_f1 = float(f1_score(test_true, test_preds, zero_division=0))

    # 6. Save Model Artifacts
    torch.save(model.state_dict(), MODEL_OUTPUT_PATH)
    print(f"[+] Saved PyG/Graph model weights to: {MODEL_OUTPUT_PATH}")

    # Build node mapping with cached features and risk priors for online inference
    node_mapping = {
        "account_to_idx": {acc: int(idx) for acc, idx in account_to_idx.items()},
        "num_nodes": num_nodes,
        "input_features": ["log_volume", "out_degree", "in_degree"],
        "node_features": {
            acc: [float(v) for v in x.cpu().numpy()[idx]]
            for acc, idx in account_to_idx.items()
        },
        "node_risk_scores": {
            acc: float(round(float(all_probs[idx]), 4))
            for acc, idx in account_to_idx.items()
        },
        "metrics": {
            "test_pr_auc": test_pr_auc,
            "test_roc_auc": test_roc_auc,
            "test_f1": test_f1
        }
    }

    with open(MAPPING_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(node_mapping, f, indent=2)

    print(f"[+] Saved node mapping & graph priors to: {MAPPING_OUTPUT_PATH}")

    print("-" * 70)
    print(" GNN MODEL TEST EVALUATION:")
    print("-" * 70)
    print(f"  * Test PR-AUC  : {test_pr_auc:.4f}")
    print(f"  * Test ROC-AUC : {test_roc_auc:.4f}")
    print(f"  * Test F1-Score: {test_f1:.4f}")
    print("=" * 70)

    return model, node_mapping


if __name__ == "__main__":
    train_gnn_model()
