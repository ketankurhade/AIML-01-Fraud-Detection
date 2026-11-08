"""
FastAPI Data Schemas and Validation Models
=========================================
Pydantic schemas for transactions, Feast features, real-time fraud scoring,
analyst alert actions, and graph ring visualizations.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class TransactionPayload(BaseModel):
    """Raw transaction payload from payment gateway, simulator, or Kafka stream."""
    transaction_id: Optional[str] = Field(default=None, description="Unique transaction ID")
    step: Optional[int] = Field(default=1, description="Simulation step / hour offset")
    type: Literal["PAYMENT", "TRANSFER", "CASH_OUT", "CASH_IN", "DEBIT"] = Field(
        ..., description="Transaction type"
    )
    amount: float = Field(..., gt=0, description="Transaction monetary amount")
    nameOrig: str = Field(..., description="Originating customer account identifier")
    oldbalanceOrg: float = Field(..., ge=0, description="Origin account initial balance")
    newbalanceOrig: float = Field(..., ge=0, description="Origin account balance post-transaction")
    nameDest: str = Field(..., description="Recipient identifier (Customer or Merchant)")
    oldbalanceDest: float = Field(default=0.0, ge=0, description="Recipient initial balance")
    newbalanceDest: float = Field(default=0.0, ge=0, description="Recipient balance post-transaction")
    timestamp: Optional[str] = Field(default=None, description="ISO-8601 UTC timestamp")


class ProbabilitiesBreakdown(BaseModel):
    p_xgboost: float = Field(..., description="Tabular fraud probability from XGBoost [0, 1]")
    p_gnn_topology: float = Field(..., description="Graph laundering ring probability from GNN [0, 1]")


class FraudScoreResponse(BaseModel):
    """Unified fraud decision response returned in sub-millisecond latency."""
    transaction_id: str
    sender: str
    recipient: str
    amount: float
    type: str
    probabilities: ProbabilitiesBreakdown
    final_risk_score: float = Field(..., description="Ensemble score: 0.65 * P_XGB + 0.35 * P_GNN")
    decision: Literal["APPROVE", "REVIEW", "BLOCK"]
    risk_tier: Literal["LOW", "ELEVATED", "CRITICAL"]
    is_fraud_ring_detected: bool
    feast_features: Dict[str, Optional[float]]
    latency_ms: float
    timestamp: str


class AlertCase(BaseModel):
    """Flagged alert record for analyst review queue."""
    alert_id: str
    transaction_id: str
    timestamp: str
    sender: str
    recipient: str
    amount: float
    type: str
    risk_score: float
    risk_tier: str
    decision: str
    is_fraud_ring: bool
    status: Literal["PENDING", "APPROVE", "CONFIRM_FRAUD", "FLAG_KYC"] = "PENDING"
    notes: Optional[str] = None
    updated_at: Optional[str] = None


class AlertActionPayload(BaseModel):
    """Analyst update payload for a flagged alert."""
    action: Literal["APPROVE", "CONFIRM_FRAUD", "FLAG_KYC"]
    notes: Optional[str] = Field(default=None, description="Investigator notes")


class GraphRingNode(BaseModel):
    id: str
    label: str
    risk_score: float
    transacted_volume: float
    is_ring_member: bool


class GraphRingEdge(BaseModel):
    source: str
    target: str
    amount: float
    type: str
    is_fraud: bool


class GraphRingResponse(BaseModel):
    nodes: List[GraphRingNode]
    edges: List[GraphRingEdge]
    total_rings: int
    active_ring_nodes: int


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    models_loaded: Dict[str, bool]
    feast_online_store_ready: bool
    kafka_connected: bool


class DriftMetricSummary(BaseModel):
    is_drift_detected: bool
    drift_share: float
    number_of_drifted_features: int
    total_features_evaluated: int
    drifted_features: List[str]
    report_html_path: str
    generated_at: str
