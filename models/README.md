# Models & Training Pipelines

This module manages offline training, evaluation, and experiment tracking with MLflow.

## Architectures Supported
1. **XGBoost Classifier**:
   - Tabular features (amount, balance deltas, transaction type one-hot encoding, velocity features).
   - Tuned for extreme class imbalance (scale_pos_weight, focal loss / PR-AUC optimization).
2. **PyTorch Geometric (PyG) Graph Neural Network**:
   - Graph representation: Nodes represent accounts (`nameOrig`, `nameDest`), directed edges represent transactions.
   - Architectures: Relational Graph Convolutional Network (R-GCN), Graph Attention Network (GAT), or GraphSAGE.
   - Detects topological fraud patterns: triangular laundering rings, high fan-in mule accumulators, and smurfing loops.
3. **Hybrid Ensemble Scorer**:
   - Stacks tabular XGBoost probability with graph structural embedding risk score for maximum recall at low false positive rates.

## Experiment Tracking
- All runs, hyperparameters, ROC-AUC, PR-AUC, confusion matrices, and model artifacts are registered to **MLflow Model Registry**.

