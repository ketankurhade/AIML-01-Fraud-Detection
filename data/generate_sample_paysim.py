"""
Synthetic PaySim Dataset Generator
===================================
Generates a realistic 10,000-row synthetic PaySim financial transaction dataset
specifically structured for:
  1. XGBoost tabular classification (balance deltas, transaction amounts, types).
  2. PyTorch Geometric (PyG) Graph Neural Networks (fraud ring cycles, mule hops).
  3. Feast feature store point-in-time lookups (ISO-8601 timestamps).

Schema Matches Standard PaySim:
  - step: Unit of time in hours (1..720)
  - type: CASH_OUT, PAYMENT, CASH_IN, TRANSFER, DEBIT
  - amount: Transaction value
  - nameOrig: Originating customer ID (C...)
  - oldbalanceOrg: Sender initial balance
  - newbalanceOrig: Sender final balance
  - nameDest: Destination recipient ID (C... or M...)
  - oldbalanceDest: Recipient initial balance
  - newbalanceDest: Recipient final balance
  - isFraud: Ground-truth label (1 = fraudulent, 0 = legitimate)
  - isFlaggedFraud: Rule-based benchmark flag (>200,000 threshold)
  - timestamp: ISO-8601 UTC timestamp for Feast feature joins
"""

import argparse
import csv
from datetime import datetime, timedelta, timezone
import math
import os
import random
import sys


def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate synthetic PaySim dataset for fraud detection.")
    parser.add_argument("--rows", type=int, default=10000, help="Total number of transaction rows to generate (default: 10000)")
    parser.add_argument("--fraud-rate", type=float, default=0.005, help="Target fraud rate (default: 0.005, i.e. 0.5%%)")
    parser.add_argument("--output", type=str, default=os.path.join("data", "paysim_sample.csv"), help="Output CSV path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    return parser.parse_args()


def format_timestamp(dt):
    """Format datetime as standard ISO-8601 UTC timestamp."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_account_id(prefix="C", index_range=(1000000, 9999999)):
    return f"{prefix}{random.randint(index_range[0], index_range[1])}"


def generate_fraud_rings(num_fraud_target, start_time):
    """
    Generates interconnected fraud rings with cyclic sender-receiver graph topology.
    Crucial for PyTorch Geometric (PyG) graph fraud detection.
    """
    fraud_transactions = []

    # Ring 1: Triangular Laundering Cycle (3 accounts)
    # C_RING1_A -> C_RING1_B -> C_RING1_C -> C_RING1_A
    ring1_nodes = ["C_RING1_MULE_101", "C_RING1_MULE_102", "C_RING1_MULE_103"]
    ring1_amount = 185000.00
    for i in range(len(ring1_nodes)):
        sender = ring1_nodes[i]
        dest = ring1_nodes[(i + 1) % len(ring1_nodes)]
        step = 10 + (i * 2)
        tx_time = start_time + timedelta(hours=step, minutes=random.randint(5, 50))
        fraud_transactions.append({
            "step": step,
            "type": "TRANSFER",
            "amount": ring1_amount,
            "nameOrig": sender,
            "oldbalanceOrg": ring1_amount,
            "newbalanceOrig": 0.0,
            "nameDest": dest,
            "oldbalanceDest": 1200.0,
            "newbalanceDest": 1200.0 + ring1_amount,
            "isFraud": 1,
            "isFlaggedFraud": 0,
            "timestamp": format_timestamp(tx_time),
            "_ring": "Ring 1 (Triangle Cycle)"
        })

    # Add Ring 1 Cash-out exit
    step_exit = 18
    fraud_transactions.append({
        "step": step_exit,
        "type": "CASH_OUT",
        "amount": ring1_amount,
        "nameOrig": ring1_nodes[-1],
        "oldbalanceOrg": ring1_amount,
        "newbalanceOrig": 0.0,
        "nameDest": "C_RING1_CASHOUT_AGENT",
        "oldbalanceDest": 50000.0,
        "newbalanceDest": 50000.0 + ring1_amount,
        "isFraud": 1,
        "isFlaggedFraud": 0,
        "timestamp": format_timestamp(start_time + timedelta(hours=step_exit, minutes=30)),
        "_ring": "Ring 1 Cashout Exit"
    })

    # Ring 2: 4-Node Circular Wash Ring
    # C_RING2_A -> C_RING2_B -> C_RING2_C -> C_RING2_D -> C_RING2_A
    ring2_nodes = [f"C_RING2_MULE_{i}" for i in range(201, 205)]
    ring2_amount = 310000.00
    for i in range(len(ring2_nodes)):
        sender = ring2_nodes[i]
        dest = ring2_nodes[(i + 1) % len(ring2_nodes)]
        step = 40 + (i * 3)
        tx_time = start_time + timedelta(hours=step, minutes=random.randint(10, 45))
        fraud_transactions.append({
            "step": step,
            "type": "TRANSFER",
            "amount": ring2_amount,
            "nameOrig": sender,
            "oldbalanceOrg": ring2_amount,
            "newbalanceOrig": 0.0,
            "nameDest": dest,
            "oldbalanceDest": 0.0,
            "newbalanceDest": ring2_amount,
            "isFraud": 1,
            "isFlaggedFraud": 1 if ring2_amount > 200000 else 0,
            "timestamp": format_timestamp(tx_time),
            "_ring": "Ring 2 (4-Node Cycle)"
        })

    # Ring 3: Hub-and-Spoke Smurfing with Circular Kickback (Fan-out then Fan-in)
    # Master mule distributes to 4 sub-mules, sub-mules consolidate into accumulator,
    # and accumulator kicks funds back to master mule
    master_mule = "C_RING3_MASTER_300"
    spoke_mules = [f"C_RING3_SPOKE_{i}" for i in range(301, 305)]
    accumulator = "C_RING3_ACCUMULATOR_399"
    smurf_amount = 75000.00

    # Step 1: Master splits into spokes
    for i, spoke in enumerate(spoke_mules):
        step = 80 + i
        tx_time = start_time + timedelta(hours=step, minutes=random.randint(2, 25))
        fraud_transactions.append({
            "step": step,
            "type": "TRANSFER",
            "amount": smurf_amount,
            "nameOrig": master_mule,
            "oldbalanceOrg": (len(spoke_mules) - i) * smurf_amount,
            "newbalanceOrig": (len(spoke_mules) - i - 1) * smurf_amount,
            "nameDest": spoke,
            "oldbalanceDest": 0.0,
            "newbalanceDest": smurf_amount,
            "isFraud": 1,
            "isFlaggedFraud": 0,
            "timestamp": format_timestamp(tx_time),
            "_ring": "Ring 3 (Fan-Out)"
        })

    # Step 2: Spokes funnel into accumulator
    for i, spoke in enumerate(spoke_mules):
        step = 86 + i
        tx_time = start_time + timedelta(hours=step, minutes=random.randint(5, 55))
        fraud_transactions.append({
            "step": step,
            "type": "TRANSFER",
            "amount": smurf_amount,
            "nameOrig": spoke,
            "oldbalanceOrg": smurf_amount,
            "newbalanceOrig": 0.0,
            "nameDest": accumulator,
            "oldbalanceDest": i * smurf_amount,
            "newbalanceDest": (i + 1) * smurf_amount,
            "isFraud": 1,
            "isFlaggedFraud": 0,
            "timestamp": format_timestamp(tx_time),
            "_ring": "Ring 3 (Fan-In)"
        })

    # Step 3: Accumulator kicks back partial return to master completing the cycle
    step_kickback = 92
    fraud_transactions.append({
        "step": step_kickback,
        "type": "TRANSFER",
        "amount": smurf_amount * 3,
        "nameOrig": accumulator,
        "oldbalanceOrg": smurf_amount * len(spoke_mules),
        "newbalanceOrig": smurf_amount,
        "nameDest": master_mule,
        "oldbalanceDest": 0.0,
        "newbalanceDest": smurf_amount * 3,
        "isFraud": 1,
        "isFlaggedFraud": 1,
        "timestamp": format_timestamp(start_time + timedelta(hours=step_kickback, minutes=15)),
        "_ring": "Ring 3 (Kickback Loop)"
    })

    # Fill remaining fraud quota with realistic PaySim TRANSFER + CASH_OUT drain pairs
    remaining = num_fraud_target - len(fraud_transactions)
    pair_count = max(0, remaining // 2)

    for p in range(pair_count):
        drain_amount = round(random.uniform(50000.0, 500000.0), 2)
        victim = f"C_VICTIM_{p:04d}"
        mule = f"C_MULE_{p:04d}"
        cashout_agent = f"C_CASHOUT_AGENT_{p:04d}"

        step_t = random.randint(100, 700)
        t_time = start_time + timedelta(hours=step_t, minutes=random.randint(0, 30))

        # 1. Compromised Account Drain (TRANSFER)
        fraud_transactions.append({
            "step": step_t,
            "type": "TRANSFER",
            "amount": drain_amount,
            "nameOrig": victim,
            "oldbalanceOrg": drain_amount,
            "newbalanceOrig": 0.0,
            "nameDest": mule,
            "oldbalanceDest": 0.0,
            "newbalanceDest": drain_amount,
            "isFraud": 1,
            "isFlaggedFraud": 1 if drain_amount > 200000 else 0,
            "timestamp": format_timestamp(t_time),
            "_ring": "Drain Transfer"
        })

        # 2. Mule Instant Cash-Out (CASH_OUT)
        step_c = step_t + random.randint(0, 2)
        c_time = start_time + timedelta(hours=step_c, minutes=random.randint(31, 59))
        fraud_transactions.append({
            "step": step_c,
            "type": "CASH_OUT",
            "amount": drain_amount,
            "nameOrig": mule,
            "oldbalanceOrg": drain_amount,
            "newbalanceOrig": 0.0,
            "nameDest": cashout_agent,
            "oldbalanceDest": round(random.uniform(10000, 100000), 2),
            "newbalanceDest": round(random.uniform(10000, 100000) + drain_amount, 2),
            "isFraud": 1,
            "isFlaggedFraud": 0,
            "timestamp": format_timestamp(c_time),
            "_ring": "Drain CashOut"
        })

    # If an odd single transaction remains to reach exact target
    if len(fraud_transactions) < num_fraud_target:
        drain_amount = 250000.00
        step_extra = random.randint(120, 600)
        fraud_transactions.append({
            "step": step_extra,
            "type": "TRANSFER",
            "amount": drain_amount,
            "nameOrig": "C_VICTIM_EXTRA_9999",
            "oldbalanceOrg": drain_amount,
            "newbalanceOrig": 0.0,
            "nameDest": "C_MULE_EXTRA_9999",
            "oldbalanceDest": 0.0,
            "newbalanceDest": drain_amount,
            "isFraud": 1,
            "isFlaggedFraud": 1,
            "timestamp": format_timestamp(start_time + timedelta(hours=step_extra, minutes=10)),
            "_ring": "Drain Transfer Standalone"
        })

    return fraud_transactions

    return fraud_transactions


def generate_legitimate_transaction(step, start_time, customer_pool, merchant_pool):
    """
    Generates a realistic legitimate PaySim transaction adhering to normal banking behaviors.
    """
    # Distribution of types in PaySim:
    # PAYMENT (~35%), CASH_OUT (~34%), CASH_IN (~22%), TRANSFER (~8%), DEBIT (~1%)
    tx_type = random.choices(
        population=["PAYMENT", "CASH_OUT", "CASH_IN", "TRANSFER", "DEBIT"],
        weights=[0.35, 0.34, 0.22, 0.08, 0.01],
        k=1
    )[0]

    orig_customer = random.choice(customer_pool)
    orig_balance = round(random.expovariate(1 / 40000.0) + random.uniform(100.0, 5000.0), 2)

    tx_time = start_time + timedelta(
        hours=step,
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59)
    )

    if tx_type == "PAYMENT":
        # Merchant payment: dest starts with 'M'
        dest = random.choice(merchant_pool)
        amount = round(random.uniform(1.50, min(orig_balance, 5000.0)), 2)
        new_orig = max(0.0, round(orig_balance - amount, 2))
        old_dest = 0.0  # In PaySim, merchant balances are 0.0
        new_dest = 0.0
    elif tx_type == "CASH_IN":
        dest = random.choice(customer_pool)
        amount = round(random.uniform(100.0, 50000.0), 2)
        new_orig = round(orig_balance + amount, 2)
        old_dest = round(random.uniform(100.0, 50000.0), 2)
        new_dest = max(0.0, round(old_dest - amount, 2))
    elif tx_type == "CASH_OUT":
        dest = random.choice(customer_pool)
        # Normal cashouts usually don't drain 100% of the account
        fraction = random.uniform(0.05, 0.70)
        amount = round(orig_balance * fraction, 2)
        if amount < 10.0:
            amount = round(random.uniform(10.0, 500.0), 2)
            orig_balance = amount + round(random.uniform(50.0, 1000.0), 2)
        new_orig = round(orig_balance - amount, 2)
        old_dest = round(random.uniform(1000.0, 150000.0), 2)
        new_dest = round(old_dest + amount, 2)
    elif tx_type == "TRANSFER":
        dest = random.choice(customer_pool)
        while dest == orig_customer:
            dest = random.choice(customer_pool)
        fraction = random.uniform(0.05, 0.60)
        amount = round(orig_balance * fraction, 2)
        if amount < 20.0:
            amount = round(random.uniform(20.0, 1000.0), 2)
            orig_balance = amount + round(random.uniform(100.0, 2000.0), 2)
        new_orig = round(orig_balance - amount, 2)
        old_dest = round(random.uniform(500.0, 100000.0), 2)
        new_dest = round(old_dest + amount, 2)
    else:  # DEBIT
        dest = random.choice(customer_pool)
        amount = round(random.uniform(10.0, 2000.0), 2)
        if orig_balance < amount:
            orig_balance = amount + 500.0
        new_orig = round(orig_balance - amount, 2)
        old_dest = round(random.uniform(500.0, 20000.0), 2)
        new_dest = round(old_dest + amount, 2)

    return {
        "step": step,
        "type": tx_type,
        "amount": amount,
        "nameOrig": orig_customer,
        "oldbalanceOrg": orig_balance,
        "newbalanceOrig": new_orig,
        "nameDest": dest,
        "oldbalanceDest": old_dest,
        "newbalanceDest": new_dest,
        "isFraud": 0,
        "isFlaggedFraud": 0,
        "timestamp": format_timestamp(tx_time),
        "_ring": "None"
    }


def generate_dataset(total_rows=10000, fraud_rate=0.005, output_path="data/paysim_sample.csv", seed=42):
    random.seed(seed)
    start_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    num_fraud = max(10, int(round(total_rows * fraud_rate)))
    num_legit = total_rows - num_fraud

    print("=" * 70)
    print(" PAY-SIM SYNTHETIC DATA GENERATOR (MLOPS & GRAPH PIPELINE)")
    print("=" * 70)
    print(f"Target Total Rows     : {total_rows:,}")
    print(f"Target Fraud Rows     : {num_fraud} ({fraud_rate * 100:.2f}%)")
    print(f"Target Legit Rows     : {num_legit:,}")
    print(f"Random Seed           : {seed}")
    print(f"Output File           : {output_path}")

    # Generate customer and merchant pools
    num_customers = int(total_rows * 0.4)
    num_merchants = int(total_rows * 0.08)
    customer_pool = [generate_account_id("C", (1000000, 9999999)) for _ in range(num_customers)]
    merchant_pool = [generate_account_id("M", (1000000, 9999999)) for _ in range(num_merchants)]

    print(f"Customer Account Pool : {len(customer_pool):,} accounts")
    print(f"Merchant Account Pool : {len(merchant_pool):,} accounts")

    # 1. Generate fraud rings & laundering patterns
    fraud_records = generate_fraud_rings(num_fraud, start_time)

    # 2. Generate legitimate transactions across 720 hours (30 simulated days)
    legit_records = []
    for _ in range(num_legit):
        step = random.randint(1, 720)
        legit_records.append(generate_legitimate_transaction(step, start_time, customer_pool, merchant_pool))

    # Combine and sort strictly by timestamp / step for realistic time-series streaming
    all_records = fraud_records + legit_records

    # Ensure exact row count matches total_rows
    if len(all_records) > total_rows:
        non_fraud = [r for r in all_records if r["isFraud"] == 0]
        fraud = [r for r in all_records if r["isFraud"] == 1]
        non_fraud = non_fraud[:total_rows - len(fraud)]
        all_records = fraud + non_fraud
    elif len(all_records) < total_rows:
        deficit = total_rows - len(all_records)
        for _ in range(deficit):
            step = random.randint(1, 720)
            all_records.append(generate_legitimate_transaction(step, start_time, customer_pool, merchant_pool))

    all_records.sort(key=lambda r: (r["step"], r["timestamp"]))

    # Prepare output directory
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    fieldnames = [
        "step",
        "type",
        "amount",
        "nameOrig",
        "oldbalanceOrg",
        "newbalanceOrig",
        "nameDest",
        "oldbalanceDest",
        "newbalanceDest",
        "isFraud",
        "isFlaggedFraud",
        "timestamp"
    ]

    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in all_records:
            writer.writerow(row)

    # Calculate summary metrics
    fraud_count = sum(1 for r in all_records if r["isFraud"] == 1)
    type_counts = {}
    for r in all_records:
        t = r["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    file_size_kb = os.path.getsize(output_path) / 1024.0

    print("-" * 70)
    print(" GENERATION COMPLETED SUCCESSFULLY")
    print("-" * 70)
    print(f"Generated Rows        : {len(all_records):,}")
    print(f"Actual Fraud Rows     : {fraud_count} ({(fraud_count / len(all_records)) * 100:.2f}%)")
    print(f"Actual Legit Rows     : {len(all_records) - fraud_count:,}")
    print(f"Transaction Breakdown : {type_counts}")
    print(f"Output File Size      : {file_size_kb:.2f} KB")
    print("=" * 70)

    return output_path


if __name__ == "__main__":
    args = parse_arguments()
    generate_dataset(
        total_rows=args.rows,
        fraud_rate=args.fraud_rate,
        output_path=args.output,
        seed=args.seed
    )
