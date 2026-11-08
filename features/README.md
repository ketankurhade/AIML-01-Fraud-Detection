# Features Store (Feast)

This directory defines the **Feast Feature Store** entities, feature views, and transformations for the fraud detection platform.

## Key Responsibilities
- **Entities**: `user` (`nameOrig`), `merchant` / `recipient` (`nameDest`).
- **Feature Views**:
  - `user_transaction_stats`: Rolling transaction velocity, mean amount, balance depletion ratio.
  - `recipient_risk_stats`: Degree centrality, in-degree count, cyclic hop flags.
- **Offline Store**: Parquet / CSV historical tables for training XGBoost & PyG models with point-in-time correctness (avoiding data leakage).
- **Online Store**: SQLite / Redis low-latency key-value store for real-time sub-millisecond feature retrieval in the FastAPI inference service.

## Configuration
- `feature_store.yaml`: Core Feast repository configuration.

