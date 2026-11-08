"""
Streaming PaySim Transaction Producer & Replay Simulator
========================================================
Streams synthetic transactions into:
  1. Apache Kafka topic: `transactions`
  2. HTTP Push fallback directly to FastAPI: `POST /api/v1/score`
     (Enables end-to-end real-time scoring without requiring local Kafka broker)

CLI Arguments:
  --rate     : Transactions per second (default: 5.0)
  --mode     : 'kafka' or 'http' (default: 'http' if broker offline)
  --limit    : Max transactions to replay (default: 100, 0 = unlimited)
  --target-url : FastAPI endpoint URL for HTTP push mode
"""

import argparse
import csv
import json
import os
import sys
import time
from typing import Generator, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "paysim_sample.csv")


def parse_args():
    parser = argparse.ArgumentParser(description="Real-time PaySim Transaction Stream Simulator")
    parser.add_argument("--rate", type=float, default=float(os.getenv("PRODUCER_RATE", "5.0")), help="Transactions per second (default: 5.0)")
    parser.add_argument("--mode", type=str, choices=["kafka", "http", "auto"], default=os.getenv("PRODUCER_MODE", "auto"), help="Streaming transport mode")
    parser.add_argument("--limit", type=int, default=int(os.getenv("PRODUCER_LIMIT", "0")), help="Max transactions to stream (default: 0 for unlimited in container)")
    parser.add_argument("--target-url", type=str, default=os.getenv("PRODUCER_TARGET_URL", "http://localhost:8000/api/v1/score"), help="FastAPI scoring URL")
    parser.add_argument("--topic", type=str, default=os.getenv("KAFKA_TOPIC_TRANSACTIONS", "transactions"), help="Kafka destination topic")
    parser.add_argument("--bootstrap-servers", type=str, default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"), help="Kafka broker address")
    return parser.parse_args()


def load_transactions(csv_path: str = DATA_PATH) -> Generator[dict, None, None]:
    """Yields parsed transaction dictionaries chronologically."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset {csv_path} not found. Run data/generate_sample_paysim.py first.")

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield {
                "transaction_id": f"TX_{row.get('step', '1')}_{row.get('nameOrig', 'C0')}_{int(time.time() * 1000)}",
                "step": int(row.get("step", 1)),
                "type": row.get("type", "PAYMENT"),
                "amount": float(row.get("amount", 0.0)),
                "nameOrig": row.get("nameOrig", ""),
                "oldbalanceOrg": float(row.get("oldbalanceOrg", 0.0)),
                "newbalanceOrig": float(row.get("newbalanceOrig", 0.0)),
                "nameDest": row.get("nameDest", ""),
                "oldbalanceDest": float(row.get("oldbalanceDest", 0.0)),
                "newbalanceDest": float(row.get("newbalanceDest", 0.0)),
                "timestamp": row.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            }


class StreamSimulator:
    def __init__(self, mode: str, bootstrap_servers: str, topic: str, target_url: str):
        self.mode = mode
        self.topic = topic
        self.target_url = target_url
        self.bootstrap_servers = bootstrap_servers
        self.kafka_producer = None
        self.http_client = None

        self._initialize_transport()

    def _initialize_transport(self):
        if self.mode in ("kafka", "auto"):
            import socket
            host = "localhost"
            port = 9092
            if ":" in self.bootstrap_servers:
                parts = self.bootstrap_servers.split(":")
                host = parts[0]
                try:
                    port = int(parts[1])
                except ValueError:
                    port = 9092

            kafka_active = False
            try:
                with socket.create_connection((host, port), timeout=0.2):
                    kafka_active = True
            except OSError:
                kafka_active = False

            if kafka_active:
                try:
                    from kafka import KafkaProducer
                    self.kafka_producer = KafkaProducer(
                        bootstrap_servers=self.bootstrap_servers,
                        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                        request_timeout_ms=2000,
                        max_block_ms=2000
                    )
                    self.mode = "kafka"
                    print(f"[+] Connected to Kafka broker: {self.bootstrap_servers} (Topic: {self.topic})")
                    return
                except Exception as e:
                    print(f"[!] Warning: KafkaProducer init failed: {e}")

            if self.mode == "kafka":
                print(f"[!] Warning: Kafka broker not reachable on {self.bootstrap_servers}. Falling back to HTTP push mode.")
            self.mode = "http"

        if self.mode == "http":
            import httpx
            self.http_client = httpx.Client(timeout=3.0)
            print(f"[+] Configured HTTP push mode to FastAPI: {self.target_url}")

    def send_transaction(self, tx: dict) -> bool:
        if self.mode == "kafka" and self.kafka_producer:
            try:
                self.kafka_producer.send(self.topic, value=tx)
                return True
            except Exception as e:
                print(f"[!] Kafka send failed: {e}")
                return False
        elif self.mode == "http" and self.http_client:
            try:
                resp = self.http_client.post(self.target_url, json=tx)
                return resp.status_code == 200
            except Exception as e:
                print(f"[!] HTTP push failed ({tx['transaction_id']}): {e}")
                return False
        return False

    def close(self):
        if self.kafka_producer:
            self.kafka_producer.flush()
            self.kafka_producer.close()
        if self.http_client:
            self.http_client.close()


def run_producer():
    args = parse_args()
    print("=" * 70)
    print(" REAL-TIME TRANSACTION STREAM SIMULATOR")
    print("=" * 70)
    print(f"Target Mode       : {args.mode}")
    print(f"Stream Rate       : {args.rate:.1f} tx/sec")
    print(f"Transaction Limit : {args.limit if args.limit > 0 else 'Unlimited'}")
    print("-" * 70)

    simulator = StreamSimulator(
        mode=args.mode,
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        target_url=args.target_url
    )

    interval = 1.0 / max(0.1, args.rate)
    count = 0
    start_time = time.time()

    try:
        for tx in load_transactions():
            t0 = time.perf_counter()
            success = simulator.send_transaction(tx)
            elapsed = time.perf_counter() - t0

            count += 1
            status = "SENT" if success else "FAIL"
            print(f"[{status}] TX #{count:04d} | Type: {tx['type']:8} | Amt: ${tx['amount']:10,.2f} | {tx['nameOrig']} -> {tx['nameDest']}")

            if args.limit > 0 and count >= args.limit:
                break

            sleep_time = max(0.0, interval - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[*] Simulator interrupted by user.")
    finally:
        total_time = time.time() - start_time
        simulator.close()
        print("-" * 70)
        print(f"[+] Total transactions replayed: {count:,}")
        print(f"[+] Total duration: {total_time:.2f} seconds ({count / max(0.01, total_time):.1f} tx/sec)")
        print("=" * 70)


if __name__ == "__main__":
    run_producer()
