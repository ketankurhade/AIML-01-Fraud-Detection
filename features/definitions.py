"""
Feast Feature Definitions for Fraud Detection Platform
======================================================
Defines entities, batch sources, and feature views for real-time
sub-millisecond account risk scoring.
"""

from datetime import timedelta
import os
import feast
from feast import (
    Entity,
    Field,
    FeatureView,
    FileSource,
    ValueType,
)
from feast.types import Float32, String

# Current file path to ensure absolute correctness across platforms
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
PARQUET_SOURCE_PATH = os.path.join(PROJECT_ROOT, "data", "paysim_sample.parquet").replace("\\", "/")

# 1. Define Entity
# Primary key for account-level feature retrieval
account_id = Entity(
    name="account_id",
    join_keys=["account_id"],
    value_type=ValueType.STRING,
    description="Bank customer or merchant account identifier (mapped from nameOrig/nameDest)"
)

# 2. Define Batch Source
# Points to historical Parquet snapshot generated from data/paysim_sample.csv
account_features_source = FileSource(
    name="account_features_source",
    path=PARQUET_SOURCE_PATH,
    timestamp_field="timestamp",
    created_timestamp_column="created_timestamp"
)

# 3. Define Account Feature View
# Exposes key fraud indicators to the Feast online store (SQLite)
account_feature_view = FeatureView(
    name="account_feature_view",
    entities=[account_id],
    ttl=timedelta(days=365),
    schema=[
        Field(name="error_balance_orig", dtype=Float32),
        Field(name="error_balance_dest", dtype=Float32),
        Field(name="amount", dtype=Float32),
        Field(name="orig_drain_ratio", dtype=Float32),
    ],
    online=True,
    source=account_features_source,
)
