"""
Comprehensive Verification Test Suite for Step 3
================================================
Validates all Step 3 components:
  1. FastAPI Health Probe (GET /health)
  2. Live WebSocket Handler (/ws/transactions) with mock connection
  3. Synchronous Hybrid Fraud Scoring (POST /api/v1/score)
  4. Analyst Case Management (GET /api/v1/alerts, POST /api/v1/alerts/{id}/action)
  5. Interactive Graph Ring Topology API (GET /api/v1/rings)
  6. Evidently AI Data Drift Generation (GET /api/v1/monitoring/drift)
  7. Operational System Stats (GET /api/v1/stats)
"""

import json
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.api.main import (
    active_connections,
    alerts_db,
    broadcast_transaction,
    get_alerts,
    get_drift_metrics,
    get_fraud_rings,
    get_health,
    get_system_stats,
    score_transaction,
    update_alert_action,
)
from services.api.schemas import AlertActionPayload, TransactionPayload


class MockWebSocket:
    """Mock WebSocket for testing live event streaming and broadcasting."""
    def __init__(self):
        self.accepted = True
        self.sent_messages = []

    def send_text_sync(self, text: str):
        self.sent_messages.append(text)


def run_all_tests():
    print("=" * 70)
    print(" STEP 3 END-TO-END VERIFICATION TEST SUITE")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # TEST 1: Service Healthcheck
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing Health Endpoint: GET /health")
    health = get_health()
    print(f"[+] Health Response:")
    print(json.dumps(health.model_dump(), indent=2))
    assert health.status == "healthy", f"Health status unhealthy: {health.status}"
    assert health.models_loaded["xgboost"] is True, "XGBoost model not loaded"
    assert health.models_loaded["gnn"] is True, "GNN model not loaded"
    assert health.feast_online_store_ready is True, "Feast online store not ready"

    # -------------------------------------------------------------------------
    # TEST 2: WebSocket Broadcasting
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing WebSocket Handler & Broadcast: /ws/transactions")
    mock_ws = MockWebSocket()
    active_connections.add(mock_ws)

    # Broadcast test event
    test_event = {"event": "TEST_ALERT", "risk": 0.99, "action": "BLOCK"}
    broadcast_transaction(test_event)
    assert len(mock_ws.sent_messages) > 0, "WebSocket broadcast failed to deliver message"
    received_event = json.loads(mock_ws.sent_messages[-1])
    assert received_event["event"] == "TEST_ALERT"
    print(f"[+] WebSocket broadcast verified. Delivered event: {received_event}")

    # -------------------------------------------------------------------------
    # TEST 3: Real-Time Fraud Scoring Engine (5 Scenarios)
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing Real-Time Scoring: POST /api/v1/score")
    test_scenarios = [
        {
            "description": "Legitimate Retail Payment",
            "payload": TransactionPayload(
                transaction_id="TX_TEST_001_LEGIT_PAYMENT",
                type="PAYMENT",
                amount=24.50,
                nameOrig="C2654343",
                oldbalanceOrg=5000.00,
                newbalanceOrig=4975.50,
                nameDest="M18230536",
                oldbalanceDest=0.0,
                newbalanceDest=0.0,
                timestamp="2026-01-01T09:00:00Z"
            ),
            "expected_decision": "APPROVE"
        },
        {
            "description": "Legitimate ATM Cash-Out",
            "payload": TransactionPayload(
                transaction_id="TX_TEST_002_LEGIT_CASHOUT",
                type="CASH_OUT",
                amount=150.00,
                nameOrig="C1029384",
                oldbalanceOrg=2000.00,
                newbalanceOrig=1850.00,
                nameDest="C9988776",
                oldbalanceDest=10000.00,
                newbalanceDest=10150.00,
                timestamp="2026-01-01T10:15:00Z"
            ),
            "expected_decision": "APPROVE"
        },
        {
            "description": "Organized Laundering Ring 1 - Mule Hop 1->2",
            "payload": TransactionPayload(
                transaction_id="TX_TEST_003_RING1_HOP1",
                type="TRANSFER",
                amount=185000.00,
                nameOrig="C_RING1_MULE_101",
                oldbalanceOrg=185000.00,
                newbalanceOrig=0.00,
                nameDest="C_RING1_MULE_102",
                oldbalanceDest=1200.00,
                newbalanceDest=186200.00,
                timestamp="2026-01-01T11:30:00Z"
            ),
            "expected_decision": "BLOCK"
        },
        {
            "description": "Organized Laundering Ring 1 - Exit Cash-Out",
            "payload": TransactionPayload(
                transaction_id="TX_TEST_004_RING1_EXIT",
                type="CASH_OUT",
                amount=185000.00,
                nameOrig="C_RING1_MULE_103",
                oldbalanceOrg=185000.00,
                newbalanceOrig=0.00,
                nameDest="C_RING1_CASHOUT_AGENT",
                oldbalanceDest=50000.00,
                newbalanceDest=235000.00,
                timestamp="2026-01-01T12:00:00Z"
            ),
            "expected_decision": "BLOCK"
        },
        {
            "description": "Victim Account Complete Balance Drain (TRANSFER)",
            "payload": TransactionPayload(
                transaction_id="TX_TEST_005_ACCOUNT_DRAIN",
                type="TRANSFER",
                amount=310000.00,
                nameOrig="C_VICTIM_0001",
                oldbalanceOrg=310000.00,
                newbalanceOrig=0.00,
                nameDest="C_MULE_0001",
                oldbalanceDest=0.00,
                newbalanceDest=310000.00,
                timestamp="2026-01-01T13:45:00Z"
            ),
            "expected_decision": "BLOCK"
        }
    ]

    scored_outputs = []
    for item in test_scenarios:
        desc = item["description"]
        payload = item["payload"]
        expected = item["expected_decision"]

        res = score_transaction(payload)
        scored_outputs.append(res)

        print(f"  [{res.decision:7}] {desc:48} | Risk: {res.final_risk_score:.4f} | Ring: {str(res.is_fraud_ring_detected):5} | Latency: {res.latency_ms:.2f}ms")
        assert res.decision == expected, f"Decision mismatch for {desc}: expected {expected}, got {res.decision}"

    # Clean up mock ws
    active_connections.discard(mock_ws)

    # -------------------------------------------------------------------------
    # TEST 4: Analyst Alert Queue
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing Alerts Queue: GET /api/v1/alerts")
    alerts = get_alerts()
    print(f"[+] Total flagged alerts in triage queue: {len(alerts)}")
    assert len(alerts) >= 3, "Expected at least 3 flagged alerts"
    for a in alerts[:3]:
        print(f"  - Alert: {a.alert_id} | Status: {a.status} | Risk: {a.risk_score:.4f} | Amount: ${a.amount:,.2f}")

    # -------------------------------------------------------------------------
    # TEST 5: Analyst Action Update
    # -------------------------------------------------------------------------
    target_alert = alerts[0]
    print(f"\n[TEST 5] Updating Alert Case: POST /api/v1/alerts/{target_alert.alert_id}/action")
    action_payload = AlertActionPayload(
        action="CONFIRM_FRAUD",
        notes="Verified cyclic mule laundering loop on Ring 1. Accounts frozen."
    )
    updated_case = update_alert_action(target_alert.alert_id, action_payload)
    print(f"[+] Case Updated: ID={updated_case.alert_id} | Status={updated_case.status} | Notes='{updated_case.notes}'")
    assert updated_case.status == "CONFIRM_FRAUD"

    # -------------------------------------------------------------------------
    # TEST 6: Fraud Ring Graph Analytics API
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing Graph Ring Topology API: GET /api/v1/rings")
    rings = get_fraud_rings()
    print(f"[+] Graph Topology Extracted:")
    print(f"  * Total Active Rings : {rings.total_rings}")
    print(f"  * Active Ring Nodes  : {rings.active_ring_nodes}")
    print(f"  * Total Graph Nodes  : {len(rings.nodes)}")
    print(f"  * Total Directed Edges: {len(rings.edges)}")
    assert len(rings.nodes) > 0
    assert len(rings.edges) > 0
    sample_edge = rings.edges[0]
    print(f"  * Sample Edge: {sample_edge.source} -> {sample_edge.target} (${sample_edge.amount:,.2f}, {sample_edge.type})")

    # -------------------------------------------------------------------------
    # TEST 7: Evidently AI Drift Monitoring
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Testing Evidently AI Drift Monitor: GET /api/v1/monitoring/drift")
    drift = get_drift_metrics()
    print(f"[+] Drift Monitoring Results:")
    print(f"  * Drift Detected     : {drift.is_drift_detected}")
    print(f"  * Drift Share        : {drift.drift_share * 100:.1f}%")
    print(f"  * Drifted Features   : {drift.drifted_features}")
    print(f"  * Monitored Features : {drift.total_features_evaluated}")
    print(f"  * Report HTML File   : {drift.report_html_path}")
    assert os.path.exists(drift.report_html_path), "HTML drift report not found"

    # -------------------------------------------------------------------------
    # TEST 8: System Statistics & Percentiles
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Testing Operational System Stats: GET /api/v1/stats")
    stats = get_system_stats()
    print(f"[+] Operational Metrics:")
    print(f"  * Total Scored         : {stats['total_scored']}")
    print(f"  * Total Approved       : {stats['total_approved']}")
    print(f"  * Total Blocked        : {stats['total_blocked']}")
    print(f"  * Fraud Ring Detections: {stats['fraud_ring_detections']}")
    print(f"  * Average Latency      : {stats['average_latency_ms']:.3f} ms")
    print(f"  * P95 Latency          : {stats['p95_latency_ms']:.3f} ms")
    assert stats["total_scored"] >= 5

    print("\n" + "=" * 70)
    print(" ALL STEP 3 INTEGRATION & VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
