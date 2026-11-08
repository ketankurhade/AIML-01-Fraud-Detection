# Transaction Replay Simulator (Kafka Producer)

High-throughput, configurable event streaming simulator that replays synthetic PaySim transaction streams into Kafka to simulate live traffic.

## Features
- Replays `data/paysim_sample.csv` or streaming bursts at controlled rates (e.g., 10 to 500 tx/sec).
- Supports real-time speed factors (1x, 5x, 10x, or burst stress test).
- Intersperses periodic fraud ring attack sequences to test real-time alert triggers.

