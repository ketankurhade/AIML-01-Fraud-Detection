"""
Feast Feature Materialization Pipeline
======================================
1. Enriches `data/paysim_sample.csv` with calculated online feature indicators:
   - `account_id` (mapped from nameOrig)
   - `created_timestamp` (ISO timestamp)
   - `error_balance_orig` (newbalanceOrig + amount - oldbalanceOrg)
   - `error_balance_dest` (oldbalanceDest + amount - newbalanceDest)
   - `orig_drain_ratio` (amount / oldbalanceOrg)
2. Exports Parquet snapshot `data/paysim_sample.parquet` with typed datetime fields for Feast offline store.
3. Applies Feast definitions to the local registry (data/registry.db).
4. Materializes features to the low-latency SQLite online store (data/online_store.db).
5. Tests sub-millisecond online retrieval.
"""

from datetime import datetime, timezone
import os
import sys
import time
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

CSV_PATH = os.path.join(PROJECT_ROOT, "data", "paysim_sample.csv")
PARQUET_PATH = os.path.join(PROJECT_ROOT, "data", "paysim_sample.parquet")
FEATURES_DIR = os.path.join(PROJECT_ROOT, "features")


def enrich_dataset_for_feast():
    """
    Ensures data/paysim_sample.csv has all fields expected by Feast FeatureView
    and exports a strongly-typed parquet version for the Feast offline store.
    """
    print(f"[*] Reading and enriching dataset: {CSV_PATH}")
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Source file {CSV_PATH} not found. Run data/generate_sample_paysim.py first.")

    df = pd.read_csv(CSV_PATH)

    # 1. Ensure required columns are computed
    df["account_id"] = df["nameOrig"].astype(str)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["created_timestamp"] = df["timestamp"]

    amount = df["amount"].astype(float)
    old_orig = df["oldbalanceOrg"].astype(float)
    new_orig = df["newbalanceOrig"].astype(float)
    old_dest = df["oldbalanceDest"].astype(float)
    new_dest = df["newbalanceDest"].astype(float)

    df["error_balance_orig"] = (new_orig + amount - old_orig).astype("float32")
    df["error_balance_dest"] = (old_dest + amount - new_dest).astype("float32")
    df["amount"] = amount.astype("float32")

    drain_ratio = (amount / old_orig).fillna(0.0)
    drain_ratio = drain_ratio.replace([float("inf"), float("-inf")], 0.0)
    df["orig_drain_ratio"] = drain_ratio.clip(lower=0.0, upper=10.0).astype("float32")

    # 2. Save enriched CSV (timestamps as ISO string)
    df_csv = df.copy()
    df_csv["timestamp"] = df_csv["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df_csv["created_timestamp"] = df_csv["timestamp"]
    df_csv.to_csv(CSV_PATH, index=False)
    print(f"[+] Successfully enriched CSV: {CSV_PATH}")

    # 3. Save Feast offline Parquet source
    # Keep only the latest record per account to prevent duplicate entity keys in online store
    df_sorted = df.sort_values(by="timestamp").groupby("account_id", as_index=False).last()
    df_sorted.to_parquet(PARQUET_PATH, index=False)
    print(f"[+] Generated Feast Parquet source with {len(df_sorted):,} unique accounts: {PARQUET_PATH}")


def run_materialization():
    print("=" * 70)
    print(" FEAST FEATURE STORE MATERIALIZATION")
    print("=" * 70)

    enrich_dataset_for_feast()

    from feast import FeatureStore
    from features.definitions import account_id, account_feature_view

    # Initialize store pointing to features directory
    store = FeatureStore(repo_path=FEATURES_DIR)

    print("[*] Applying feature definitions to Feast registry...")
    store.apply([account_id, account_feature_view])
    print("[+] Feast definitions applied successfully.")

    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2027, 1, 1, tzinfo=timezone.utc)

    print(f"[*] Materializing features into SQLite online store: {start_date.date()} -> {end_date.date()}...")
    t_start = time.perf_counter()
    store.materialize(start_date=start_date, end_date=end_date)
    duration = time.perf_counter() - t_start
    print(f"[+] Materialization completed in {duration:.2f} seconds.")

    # Test sub-millisecond retrieval
    print("\n[*] Testing Feast Online Feature Retrieval...")
    test_entities = [
        {"account_id": "C_RING1_MULE_101"},
        {"account_id": "C_RING1_MULE_102"},
        {"account_id": "C2654343"}
    ]

    features_to_fetch = [
        "account_feature_view:error_balance_orig",
        "account_feature_view:error_balance_dest",
        "account_feature_view:amount",
        "account_feature_view:orig_drain_ratio",
    ]

    t0 = time.perf_counter()
    online_response = store.get_online_features(
        features=features_to_fetch,
        entity_rows=test_entities
    ).to_dict()
    latency_ms = (time.perf_counter() - t0) * 1000

    print(f"[+] Retrieved {len(test_entities)} entity records in {latency_ms:.3f} ms.")
    print("Online Features Response Sample:")
    for i, entity in enumerate(test_entities):
        acc = entity["account_id"]
        amt = online_response.get("amount", [])[i] if i < len(online_response.get("amount", [])) else None
        drain = online_response.get("orig_drain_ratio", [])[i] if i < len(online_response.get("orig_drain_ratio", [])) else None
        err_orig = online_response.get("error_balance_orig", [])[i] if i < len(online_response.get("error_balance_orig", [])) else None
        print(f"  - Account: {acc:20} | Amount: {amt} | Drain Ratio: {drain} | Error Orig: {err_orig}")
    print("=" * 70)


if __name__ == "__main__":
    run_materialization()
