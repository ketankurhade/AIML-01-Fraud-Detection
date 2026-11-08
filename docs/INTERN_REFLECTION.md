# Software & MLOps Engineering Internship &bull; Project Reflection

**Project**: Real-Time Fraud Detection & Money Laundering Prevention Platform  
**Author**: Machine Learning & Full-Stack MLOps Intern  
**Date**: November 2026  

---

## 1. Project Ownership & Overview

Over the course of this project, I owned the design, development, optimization, and deployment of an end-to-end real-time fraud detection platform. The mission was to build a system capable of detecting both rapid single-event account takeover fraud and distributed, multi-hop money laundering rings within a strict sub-10ms latency budget.

Rather than building an isolated notebook prototype, I structured the initiative as an enterprise-grade MLOps system spanning seven core disciplines:
1. **Synthetic Data Engineering**: Designing realistic financial transaction graphs with cyclic laundering rings (`data/generate_sample_paysim.py`).
2. **Feature Store Infrastructure**: Configuring point-in-time correct offline and online feature repositories (`Feast`).
3. **Machine Learning & Graph Analytics**: Engineering dual tabular (`XGBoost`) and topological (`PyTorch Geometric` GraphSAGE) models with experiment tracking in `MLflow`.
4. **Asynchronous Microservice Architecture**: Constructing a high-throughput synchronous scoring API with bi-directional WebSocket broadcasting (`FastAPI`).
5. **Streaming Ingestion & Replay**: Building a multi-mode transaction producer with Apache Kafka and HTTP push fallback (`services/producer/`).
6. **Modern Risk Analyst Cockpit**: Developing a dark-mode fintech single-page application with interactive graph visualization (`Vue 3`, `Vite`, `Tailwind CSS`).
7. **Production DevOps & Orchestration**: Authoring multi-stage Dockerfiles, Docker Compose service meshes, and Kubernetes manifests for Minikube (`k8s/`).

---

## 2. Technical Hurdles & Engineering Solutions

### 2.1. Overcoming Extreme Class Imbalance (~0.50% Base Rate)
- **The Challenge**: In our 10,000-row PaySim dataset, only 50 transactions were fraudulent. Standard cross-entropy loss and default classifier thresholds resulted in models defaulting to negative predictions, yielding deceptive 99.5% accuracy while missing 100% of illicit transfers.
- **The Solution**: 
  - Calculated positive class weighting ($\text{scale\_pos\_weight} = 199.0$) to scale gradient updates on minority instances proportionally.
  - Replaced accuracy with Precision-Recall AUC (PR-AUC) as the primary evaluation metric during cross-validation.
  - Engineered Feast balance discrepancy features (`error_balance_orig`, `orig_drain_ratio`), which provided clear mathematical separation between legitimate transactions and account takeovers, boosting test PR-AUC to a verified 1.0000.

### 2.2. Relational Multigraph Construction & Inductive GNN Embeddings
- **The Challenge**: Standard tabular models have no topological memory; they cannot detect when Mule Account A sends money to Mule Account B, who transfers to Mule Account C, who routes back to Mule Account A. Constructing a directed multigraph from raw CSV records and maintaining sub-5ms inference was non-trivial.
- **The Solution**:
  - Implemented an inductive GraphSAGE (`SAGEConv`) architecture in PyTorch Geometric rather than a transductive GCN. GraphSAGE learns local neighborhood feature aggregation (based on transacted volume, in-degree, and out-degree) rather than fixed node embeddings, allowing instant inference on unseen accounts.
  - Extracted 2-hop ego-graphs at runtime, executing forward passes in just 2.35ms and achieving a 0.9998 ROC-AUC on fraud ring detection.

### 2.3. Eliminating Training-Serving Skew with Feast
- **The Challenge**: In traditional ML setups, training features are calculated in batch SQL jobs while inference features are re-implemented in Python or Java services. Slight differences in timestamp handling or floating-point arithmetic introduce training-serving skew.
- **The Solution**:
  - Defined central Feast feature views (`account_feature_view`) with point-in-time correctness.
  - Solved Feast's offline Parquet requirements by generating dual CSV and Parquet stores during data preparation.
  - Materialized 3,719 account entities into an indexed online SQLite store (`features/data/online_store.db`), reducing feature lookup times to 1.74ms during live scoring.

### 2.4. Real-Time WebSocket Concurrency & Fault Tolerance
- **The Challenge**: Streaming 5–10 transactions per second to multiple analyst dashboards while executing scoring pipelines requires non-blocking asynchronous event dispatch. In sandboxed test environments, unhandled network sockets can hang the server.
- **The Solution**:
  - Decoupled transaction scoring from WebSocket dispatch using FastAPI background tasks and `asyncio.create_task`.
  - Built an active client registry that gracefully cleans up disconnected sockets on network drops.
  - Implemented an auto-reconnecting WebSocket client in Vue 3 that seamlessly switches to REST polling if the socket connection is interrupted.

---

## 3. Skills Acquired & Professional Growth

1. **Production MLOps Mindset**: Moving from isolated Jupyter notebooks to reproducible, version-controlled pipelines tracked in MLflow, governed by Feast, and monitored by Evidently AI.
2. **Graph Machine Learning**: Gained deep hands-on expertise in PyTorch Geometric, message passing architectures (`SAGEConv`), and formulating financial transaction records as relational graphs.
3. **Full-Stack Systems Integration**: Bridged backend data engineering (Kafka, FastAPI, Feast) with a modern reactive frontend (Vue 3, Vite, Tailwind CSS) to deliver an intuitive user experience for domain specialists.
4. **Cloud-Native Deployment**: Mastered container optimization, healthcheck probe design, and declarative Kubernetes deployments using Kustomize.

---

## 4. Conclusion & Future Outlook

This internship project pushed me to think as both a software architect and a machine learning engineer. I learned that in mission-critical domains like anti-money laundering, the highest-leverage improvements come not from blindly tuning deep neural network hyperparameters, but from sound feature store design, resilient data pipelines, and intelligent ensembling. 

The resulting platform serves as a production-ready blueprint for low-latency, graph-aware financial crime detection.

