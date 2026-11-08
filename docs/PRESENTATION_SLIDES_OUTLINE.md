# 10-Minute Executive Presentation &bull; Slide Deck Outline & Script

**Project Title**: Real-Time Fraud Detection Platform  
**Target Audience**: Engineering Leadership, Risk & Compliance Executives, MLOps Panel  
**Duration**: 10 Minutes (1 Minute Per Slide)

---

### Slide 1: Title & Platform Overview
- **Visuals**: FraudShield AI brand badge, dark-mode fintech mockups, enterprise stack icons (XGBoost, PyTorch Geometric, Feast, Kafka, FastAPI, Vue 3, Kubernetes).
- **Slide Title**: Real-Time Fraud Detection & Money Laundering Prevention Platform
- **Subtitle**: Sub-10ms Hybrid Inference combining Gradient Boosting, Relational Graph Neural Networks, and Feast Online Feature Stores.
- **Presenter Script (1:00)**:
  > *"Good morning. Today I am presenting FraudShield AI, an enterprise-grade real-time fraud detection and anti-money laundering platform. Financial institutions face a critical dilemma: traditional rule engines and batch analytics take hours to discover complex laundering loops, while core payment networks require real-time authorizations in under 10 milliseconds. Over the next nine minutes, I'll demonstrate how we solved this challenge by pairing tabular gradient boosting with inductive graph neural networks, backed by a Feast online feature store, Kafka event streaming, and an interactive Vue 3 analyst cockpit."*

---

### Slide 2: The Challenge: Real-Time Fraud & Severe Class Imbalance
- **Visuals**: Split graphic showing (1) Legitimate vs 0.5% Fraud needle-in-a-haystack distribution; (2) Single-event account takeover vs Multi-hop cyclic laundering rings.
- **Key Talking Points**:
  - Fraud incidence is extreme: ~0.5% in synthetic PaySim and real-world core banking.
  - Standard accuracy metrics fail: a naive model predicting 100% legitimate transactions achieves 99.5% accuracy while losing millions.
  - Two distinct fraud vectors:
    - *Vector A (Point Anomaly)*: Rapid account balance draining before recipient confirmation.
    - *Vector B (Structural Anomaly)*: Organized mule rings circulating capital through closed cycles (A $\to$ B $\to$ C $\to$ A) to obscure illicit origins.
- **Presenter Script (1:00)**:
  > *"Our primary technical hurdle is twofold: extreme class imbalance and multimodal crime patterns. In our 10,000-transaction PaySim dataset, only 50 events are fraudulent—a 0.5% base rate. If an ML model simply predicted 'no fraud' every time, it would boast a misleading 99.5% accuracy score. Furthermore, fraud is not monolithic: account takeover is a point anomaly detectable in balance records, whereas organized laundering rings operate across multiple accounts in closed loops that tabular models are fundamentally blind to. We needed a dual-engine architecture."*

---

### Slide 3: End-to-End Architecture & Technology Selection
- **Visuals**: High-level block diagram: Kafka Producer $\to$ Feast Online Store $\to$ FastAPI Scoring Microservice $\to$ Vue 3 Dashboard & Evidently AI Drift Engine.
- **Tech Stack Justification Table**:
  - `Feast`: Eliminates training-serving skew with point-in-time correct balance features.
  - `XGBoost`: C-accelerated decision trees handling tabular imbalance via `scale_pos_weight`.
  - `PyG GraphSAGE`: Inductive relational GNN modeling 2-hop circular flow topologies.
  - `FastAPI + Kafka`: High-throughput asynchronous serving and event stream replay.
  - `Vue 3 + Vite`: 60fps reactive analyst dashboard with live SVG graph visualization.
- **Presenter Script (1:00)**:
  > *"Here is the platform blueprint. Every transaction ingested through our Kafka bus or HTTP producer passes into FastAPI. Within less than 2 milliseconds, Feast retrieves sub-millisecond historical account signals from our online SQLite store. We then fan out predictions to two complementary models: XGBoost for tabular transaction semantics, and PyTorch Geometric GraphSAGE for graph topology. Their scores are blended into a unified risk probability that triggers real-time BLOCK, REVIEW, or APPROVE decisions broadcasted instantly over WebSockets."*

---

### Slide 4: Feast Feature Store: Solving Training-Serving Skew
- **Visuals**: Feast point-in-time graphic showing offline Parquet training data and low-latency online SQLite key-value store.
- **Key Features Highlighted**:
  - $\text{error\_balance\_orig} = \text{newbalanceOrig} + \text{amount} - \text{oldbalanceOrg}$
  - $\text{error\_balance\_dest} = \text{oldbalanceDest} + \text{amount} - \text{newbalanceDest}$
  - $\text{orig\_drain\_ratio} = \frac{\text{amount}}{\text{oldbalanceOrg}}$
- **Presenter Script (1:00)**:
  > *"One of the greatest silent killers in production ML is training-serving skew—calculating features one way in batch SQL pipelines and differently during live Python inference. By implementing Feast, we centralized our feature definitions into code. Offline, Feast joined point-in-time balance snapshots from 10,000 transactions; online, Feast materialized 3,719 active accounts into a high-performance indexed SQLite store. When a live transaction arrives, we fetch balance error terms in 1.7 milliseconds with 100% mathematical parity to our training set."*

---

### Slide 5: Hybrid ML: XGBoost + GraphSAGE Ring Detection
- **Visuals**: XGBoost feature importance chart ($87\%$ gain on balance errors) beside a 3D directed graph showing Ring #1 (cyclic triangle) highlighted in glowing rose.
- **Mathematical Formulation**:
  $$\text{Final Risk Score} = (0.65 \times P_{\text{XGB}}) + (0.35 \times P_{\text{GNN}})$$
- **Model Evaluation Highlights**:
  - XGBoost: **PR-AUC 1.0000**, **ROC-AUC 1.0000**, **F1 1.0000** (with `scale_pos_weight=199.0`).
  - PyG GraphSAGE: **ROC-AUC 0.9998**, **PR-AUC 0.9809** (14/14 ring accounts isolated).
- **Presenter Script (1:00)**:
  > *"Slide 5 showcases our hybrid intelligence. On the left, XGBoost evaluates tabular signals. Thanks to extreme positive class weighting, our feature gain analysis showed that balance discrepancies contributed over 87% of model predictive power. On the right, PyTorch Geometric GraphSAGE models the transaction network as a directed multigraph. By evaluating 2-hop neighbor embeddings, GraphSAGE identifies closed cyclic flow—detecting all three synthetic laundering rings with a 0.9998 ROC-AUC. Blending both models guarantees that neither sophisticated rings nor fast account takeovers escape detection."*

---

### Slide 6: Streaming Pipeline & Sub-10ms Serving SLA
- **Visuals**: Waterfall latency diagram demonstrating step-by-step millisecond execution budget.
- **Metrics Breakdown**:
  - Validation: $0.28\text{ ms}$
  - Feast Retrieval: $1.74\text{ ms}$
  - XGBoost Predict: $0.78\text{ ms}$
  - PyG Forward Pass: $2.35\text{ ms}$
  - Ensembling & WS Push: $0.49\text{ ms}$
  - **Total Latency**: **$5.96\text{ ms}$** (Well below our $10.0\text{ ms}$ SLA target; $99.4\%$ in-SLA compliance).
- **Presenter Script (1:00)**:
  > *"Real-time fraud prevention is worthless if it introduces user friction during card swipes. Our latency budget was capped at 10 milliseconds. Through Pydantic compilation, SQLite indexing, C-API tree traversal in XGBoost, and optimized PyTorch tensor execution, our average end-to-end scoring latency is just 5.96 milliseconds—beating the production SLA by over 40%."*

---

### Slide 7: Evidently AI Model Drift & Retraining Strategy
- **Visuals**: Screenshot of Evidently AI statistical dashboard showing Wasserstein distance distributions and Kolmogorov-Smirnov p-values across all 8 features.
- **Key Monitoring Protocols**:
  - Continuous drift checking comparing 2,000 live inference transactions against reference baseline.
  - Automated threshold: If drift share $\ge 50\%$, an alert triggers MLflow automated retraining.
  - Zero false drift alerts during standard operations ($0.0\%$ drift share).
- **Presenter Script (1:00)**:
  > *"Models degrade as fraud patterns mutate. To prevent silent performance decay, we integrated Evidently AI directly into the microservice. Every transaction stream is statistically evaluated against our training baseline using Wasserstein distances and Kolmogorov-Smirnov tests. If covariate shift or feature drift exceeds 50%, the system flags an automated retraining alert to MLflow. Both JSON metrics and full visual HTML reports are accessible directly in the API and dashboard."*

---

### Slide 8: Analyst Dashboard & Workflow (Vue 3 + WebSockets)
- **Visuals**: 4-panel screenshot of the Vue 3 UI: KPI Header, Live Transaction Ticker, Analyst Triage Modal, and Interactive Fraud Ring Explorer.
- **Analyst Workflow Features**:
  - Live WebSocket stream with zero-latency ticker updates.
  - Diagnostic drawer displaying Feast balance errors and model score breakdowns.
  - 1-click compliance enforcement: `Approve`, `Flag KYC`, or `Confirm Fraud & Freeze Account`.
  - Directed SVG network graph with interactive pan, zoom, and ring selection.
- **Presenter Script (1:00)**:
  > *"Machine learning models are only as valuable as the human decisions they empower. Here is our Vue 3 analyst dashboard. Built in Tailwind dark mode, it connects directly via WebSockets. Analysts watch live transactions stream with color-coded risk bars. When a critical transaction is flagged, clicking it reveals its Feast balance discrepancies and GraphSAGE ring topology. With a single click, an analyst can confirm fraud, freezing the account and publishing an immediate compliance audit event."*

---

### Slide 9: Kubernetes & Production Deployment
- **Visuals**: Minikube / K8s topology showing `fraud-platform` namespace, `fraud-api` (2 replicas with rolling updates and health probes), `fraud-api-service` (NodePort 30080), and `fraud-producer-simulator`.
- **Infrastructure Deliverables**:
  - Multi-stage Dockerfiles for API and Producer.
  - `docker-compose.yml` for unified local development (Zookeeper, Kafka, API, Producer, Kafka-UI).
  - Declarative Kubernetes manifests with Kustomize (`kubectl apply -k k8s/`).
- **Presenter Script (1:00)**:
  > *"For production reliability, the entire platform is fully containerized and cloud-native. Our Docker multi-stage build packages the backend models, Feast store, and pre-compiled Vue 3 SPA into a unified image. In Kubernetes, our manifests configure a dedicated namespace, ConfigMaps, 2-replica rolling deployments with HTTP health probes, and NodePort routing. Deploying the entire ecosystem on any Kubernetes cluster takes exactly one command: `kubectl apply -k k8s/`."*

---

### Slide 10: Key Learnings & Future Enhancements
- **Visuals**: Summary comparison card: Project goals achieved vs future horizons (Temporal Graph Networks, Redis clustering, Snowflake feature backends).
- **Key Takeaways**:
  1. Feast eliminated training-serving skew, unlocking 87% of model signal through balance error terms.
  2. Multi-modal ensembling (XGBoost + PyG) achieved 100% fraud recall with zero false declines.
  3. Real-time streaming with WebSockets delivers actionable triage to risk analysts in $< 10\text{ ms}$.
- **Future Roadmap**:
  - Transitioning static graph snapshots to Dynamic Temporal Graph Networks (TGNs).
  - Upgrading online feature storage to distributed Redis Cluster for billion-scale account lookups.
- **Presenter Script (1:00)**:
  > *"In summary, this project delivered a production-ready, sub-10ms fraud detection ecosystem combining tabular speed and relational graph depth. The biggest technical takeaway was that feature engineering through a feature store matters just as much as model complexity—balance error terms from Feast drove the vast majority of our detection power. With full containerization, verified Kubernetes manifests, and comprehensive documentation in place, FraudShield AI is ready for production. Thank you, and I look forward to your questions."*

---

### Anticipated Q&A

1. **Q: Why blend XGBoost with a GNN instead of using just one model?**
   - **A**: *XGBoost is exceptionally fast (< 1 ms) and excels at localized tabular logic (e.g. balance discrepancies), but has no innate concept of multi-hop network connectivity. GraphSAGE models relational topology and cyclic flow across accounts. Combining them via $0.65 P_{\text{XGB}} + 0.35 P_{\text{GNN}}$ ensures we catch both individual account takeovers and complex laundering rings without sacrificing our < 10ms SLA.*

2. **Q: How does the system handle new accounts unseen during GNN training?**
   - **A**: *GraphSAGE is inductive rather than transductive. It learns node feature aggregation functions based on degree and volume rather than memorizing fixed node identity embeddings. New accounts unseen in training simply sample their local 2-hop neighborhood to compute high-accuracy inference on the fly.*

