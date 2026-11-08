# Kubernetes Deployment Manifests

Production-ready Kubernetes configurations for running the end-to-end fraud platform on cloud clusters (GKE, EKS, AKS, or local Minikube/Kind).

## Components
- `kafka/`: Strimzi Kafka operator or self-hosted Kafka cluster manifests.
- `api/`: FastAPI scoring deployment, Service, HorizontalPodAutoscaler (HPA), and ConfigMaps.
- `monitoring/`: Evidently cronjob drift runner and Prometheus ServiceMonitors.
- `frontend/`: Nginx-backed Vue 3 container deployment and Ingress controller.

