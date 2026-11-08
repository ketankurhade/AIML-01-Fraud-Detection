"""
Background Kafka Transaction Stream Consumer
============================================
Listens for incoming transactions on Kafka topic `transactions`,
processes them with the hybrid ScoringEngine, stores alerts in memory,
and broadcasts results to WebSocket subscribers.
"""

import asyncio
import json
import os
import socket
import sys
import threading
import time
from typing import Callable, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.api.schemas import TransactionPayload


def check_kafka_socket(host: str, port: int, timeout: float = 0.2) -> bool:
    """Quick socket check to verify broker is listening before calling KafkaConsumer."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class KafkaConsumerWorker:
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "transactions",
        on_message_callback: Optional[Callable] = None
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.on_message_callback = on_message_callback
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.consumer = None
        self.is_connected = False

    def start(self):
        # Only start if explicitly enabled in environment or docker-compose
        if os.environ.get("ENABLE_KAFKA_CONSUMER", "false").lower() != "true":
            self.is_connected = False
            print("[*] Note: Kafka consumer disabled (ENABLE_KAFKA_CONSUMER!=true). Operating in HTTP/API mode.")
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        # Parse host and port
        host = "localhost"
        port = 9092
        if ":" in self.bootstrap_servers:
            parts = self.bootstrap_servers.split(":")
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                port = 9092

        # Fast socket probe
        if not check_kafka_socket(host, port, timeout=0.2):
            self.is_connected = False
            print(f"[*] Note: Kafka broker not active on {self.bootstrap_servers}. Background consumer operating in standby mode.")
            return

        try:
            from kafka import KafkaConsumer
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                group_id="fraud-scoring-group",
                consumer_timeout_ms=1000,
                request_timeout_ms=2000
            )
            self.is_connected = True
            print(f"[+] Kafka Consumer listening on topic: {self.topic} ({self.bootstrap_servers})")

            while self.is_running:
                for message in self.consumer:
                    if not self.is_running:
                        break
                    try:
                        tx_data = message.value
                        tx = TransactionPayload(**tx_data)
                        if self.on_message_callback:
                            self.on_message_callback(tx)
                    except Exception as e:
                        print(f"[!] Error processing Kafka message: {e}")

        except Exception as e:
            self.is_connected = False
            print(f"[*] Note: Kafka broker unavailable ({e}). Background consumer in standby mode.")

    def stop(self):
        self.is_running = False
        if self.consumer:
            try:
                self.consumer.close()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
