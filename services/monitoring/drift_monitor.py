"""
Evidently AI Drift Monitoring Engine
===================================
Compares real-time streaming transaction distributions against baseline PaySim
reference data (first 2,000 transactions) to detect data drift and model degradation.

Outputs:
  - Interactive HTML report: services/monitoring/drift_report.html
  - Structured Drift Summary JSON for FastAPI endpoint: GET /api/v1/monitoring/drift
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "paysim_sample.csv")
MONITORING_DIR = os.path.join(PROJECT_ROOT, "services", "monitoring")
REPORT_HTML_PATH = os.path.join(MONITORING_DIR, "drift_report.html")
REPORT_JSON_PATH = os.path.join(MONITORING_DIR, "drift_summary.json")

# Statistical features monitored for drift
MONITORED_FEATURES = [
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "error_balance_orig",
    "error_balance_dest",
    "orig_drain_ratio"
]


class DriftMonitor:
    def __init__(self, reference_path: str = DATA_PATH):
        self.reference_path = reference_path
        self.reference_df: Optional[pd.DataFrame] = None
        self.latest_summary: Optional[Dict[str, Any]] = None
        self.load_reference_data()

    def load_reference_data(self):
        """Loads first 2,000 baseline records as reference dataset."""
        if not os.path.exists(self.reference_path):
            print(f"[!] Warning: Reference dataset {self.reference_path} not found.")
            return

        df = pd.read_csv(self.reference_path, nrows=2000)
        # Ensure engineered terms exist
        if "error_balance_orig" not in df.columns:
            df["error_balance_orig"] = df["newbalanceOrig"] + df["amount"] - df["oldbalanceOrg"]
        if "error_balance_dest" not in df.columns:
            df["error_balance_dest"] = df["oldbalanceDest"] + df["amount"] - df["newbalanceDest"]
        if "orig_drain_ratio" not in df.columns:
            df["orig_drain_ratio"] = np.where(df["oldbalanceOrg"] > 0, df["amount"] / df["oldbalanceOrg"], 0.0)

        # Select monitored columns
        available_cols = [c for c in MONITORED_FEATURES if c in df.columns]
        self.reference_df = df[available_cols].copy()
        print(f"[+] Loaded Evidently reference baseline: {len(self.reference_df):,} records.")

    def run_statistical_drift_test(self, current_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates Kolmogorov-Smirnov statistical two-sample tests per feature."""
        from scipy.stats import ks_2samp

        drifted_features = []
        feature_metrics = {}

        for col in self.reference_df.columns:
            if col in current_df.columns:
                ref_vals = pd.to_numeric(self.reference_df[col], errors="coerce").dropna().values
                curr_vals = pd.to_numeric(current_df[col], errors="coerce").dropna().values

                if len(curr_vals) >= 5 and len(ref_vals) >= 5:
                    res = ks_2samp(ref_vals, curr_vals)
                    p_val = float(res.pvalue)
                    stat = float(res.statistic)
                    is_drifted = bool(p_val < 0.05)
                else:
                    p_val = 1.0
                    stat = 0.0
                    is_drifted = False

                if is_drifted:
                    drifted_features.append(col)

                feature_metrics[col] = {
                    "p_value": round(p_val, 4),
                    "statistic": round(stat, 4),
                    "is_drifted": is_drifted
                }

        total_cols = len(self.reference_df.columns)
        drift_share = float(len(drifted_features) / total_cols) if total_cols > 0 else 0.0
        is_drift_detected = drift_share >= 0.30

        return {
            "is_drift_detected": is_drift_detected,
            "drift_share": round(drift_share, 4),
            "number_of_drifted_features": len(drifted_features),
            "total_features_evaluated": total_cols,
            "drifted_features": drifted_features,
            "feature_metrics": feature_metrics,
            "current_sample_count": len(current_df),
            "reference_sample_count": len(self.reference_df),
            "report_html_path": REPORT_HTML_PATH,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    def generate_drift_report(
        self,
        current_data: Any,
        output_html: str = REPORT_HTML_PATH
    ) -> Dict[str, Any]:
        """
        Generates interactive Evidently HTML report and JSON summary.
        Accepts DataFrame, list of transaction dicts, or CSV path.
        """
        os.makedirs(os.path.dirname(output_html), exist_ok=True)

        # 1. Parse current data
        if isinstance(current_data, str) and os.path.exists(current_data):
            curr_df = pd.read_csv(current_data)
        elif isinstance(current_data, list):
            curr_df = pd.DataFrame(current_data)
        elif isinstance(current_data, pd.DataFrame):
            curr_df = current_data.copy()
        else:
            # Fallback to sample
            curr_df = pd.read_csv(self.reference_path).tail(200)

        # Ensure engineered terms
        if "error_balance_orig" not in curr_df.columns and "amount" in curr_df.columns:
            curr_df["error_balance_orig"] = curr_df["newbalanceOrig"] + curr_df["amount"] - curr_df["oldbalanceOrg"]
        if "error_balance_dest" not in curr_df.columns and "amount" in curr_df.columns:
            curr_df["error_balance_dest"] = curr_df["oldbalanceDest"] + curr_df["amount"] - curr_df["newbalanceDest"]
        if "orig_drain_ratio" not in curr_df.columns and "amount" in curr_df.columns:
            curr_df["orig_drain_ratio"] = np.where(curr_df["oldbalanceOrg"] > 0, curr_df["amount"] / curr_df["oldbalanceOrg"], 0.0)

        cols = [c for c in MONITORED_FEATURES if c in curr_df.columns and c in self.reference_df.columns]
        curr_clean = curr_df[cols].copy()

        # 2. Try Evidently Report
        evidently_success = False
        try:
            from evidently.report import Report
            from evidently.metric_preset import DataDriftPreset

            report = Report(metrics=[DataDriftPreset()])
            report.run(reference_data=self.reference_df[cols], current_data=curr_clean)
            report.save_html(output_html)
            evidently_success = True
            print(f"[+] Saved Evidently HTML report to: {output_html}")
        except Exception as e:
            print(f"[!] Warning: Evidently preset run failed ({e}). Generating standalone HTML report.")

        # 3. Compute detailed statistical summary
        summary = self.run_statistical_drift_test(curr_clean)

        # If evidently didn't write HTML, generate an interactive dashboard HTML
        if not evidently_success or not os.path.exists(output_html):
            self._write_html_report(summary, output_html)

        # Save summary JSON
        with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        self.latest_summary = summary
        return summary

    def _write_html_report(self, summary: Dict[str, Any], output_path: str):
        """Generates clean standalone HTML report visualizing feature drift."""
        rows_html = ""
        for feat, data in summary.get("feature_metrics", {}).items():
            status_badge = '<span style="color:#ef4444;font-weight:bold;">DRIFTED</span>' if data["is_drifted"] else '<span style="color:#10b981;font-weight:bold;">STABLE</span>'
            rows_html += f"""
            <tr style="border-bottom:1px solid #e2e8f0;">
                <td style="padding:10px 14px;font-family:monospace;font-weight:600;">{feat}</td>
                <td style="padding:10px 14px;">{data['p_value']}</td>
                <td style="padding:10px 14px;">{data['statistic']}</td>
                <td style="padding:10px 14px;">{status_badge}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Evidently AI Drift Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }}
        .card {{ background: #1e293b; border-radius: 10px; padding: 24px; max-width: 900px; margin: 0 auto; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }}
        h1 {{ color: #38bdf8; margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #334155; text-align: left; padding: 10px 14px; color: #94a3b8; font-size: 13px; }}
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Evidently AI Model & Data Drift Monitor</h1>
        <p style="color:#94a3b8;">Real-Time Financial Transaction Distribution Comparison against 2,000 Baseline Samples</p>
        <div style="display:flex;gap:16px;margin:20px 0;">
            <div style="background:#0f172a;padding:14px;border-radius:8px;flex:1;">
                <div style="color:#94a3b8;font-size:12px;">Drift Detected</div>
                <div style="font-size:22px;font-weight:700;color:{'#ef4444' if summary['is_drift_detected'] else '#10b981'};">
                    {'YES' if summary['is_drift_detected'] else 'NO'}
                </div>
            </div>
            <div style="background:#0f172a;padding:14px;border-radius:8px;flex:1;">
                <div style="color:#94a3b8;font-size:12px;">Drift Share</div>
                <div style="font-size:22px;font-weight:700;">{summary['drift_share'] * 100:.1f}%</div>
            </div>
            <div style="background:#0f172a;padding:14px;border-radius:8px;flex:1;">
                <div style="color:#94a3b8;font-size:12px;">Drifted Features</div>
                <div style="font-size:22px;font-weight:700;">{summary['number_of_drifted_features']} / {summary['total_features_evaluated']}</div>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Feature</th>
                    <th>p-value (KS-test)</th>
                    <th>KS Statistic</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        <p style="color:#64748b;font-size:12px;margin-top:20px;">Generated At: {summary['generated_at']}</p>
    </div>
</body>
</html>"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)


if __name__ == "__main__":
    monitor = DriftMonitor()
    summary = monitor.generate_drift_report(current_data=DATA_PATH)
    print(json.dumps(summary, indent=2))

