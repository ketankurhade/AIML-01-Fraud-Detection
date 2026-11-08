# Scoring Service & Streaming Consumers (FastAPI + Kafka)

Real-time inference microservice responsible for sub-millisecond fraud scoring, Kafka stream consumption, and alert publication.

## Capabilities
- **REST Endpoints**:
  - `POST /score`: Synchronous fraud inference endpoint for payments gateway.
  - `GET /health`: Health and readiness probe for Kubernetes.
  - `GET /metrics`: Prometheus operational metrics (scoring latency, request rates, fraud detection counters).
- **Kafka Stream Consumer**:
  - Consumes incoming streaming transactions from `fraud.transactions.raw`.
  - Enriches payload with online features from Feast.
  - Predicts fraud score using ensemble (XGBoost + PyG).
  - Emits high-risk alerts to `fraud.alerts.detected` topic.
- **WebSocket Streaming**:
  - Live broadcast channel for the Vue 3 analyst dashboard.

