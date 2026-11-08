# Evidently AI Drift & Quality Monitoring

Automated continuous monitoring service for data drift, feature distribution shifts, and model decay.

## Key Functions
- **Data Drift Detection**: Compares sliding inference window against baseline reference dataset (`data/paysim_sample.csv`) using Kolmogorov-Smirnov and Wasserstein distance tests.
- **Concept Drift & Target Drift**: Monitors prediction score distributions and alert trigger ratios.
- **Report Generation**: Automatically exports interactive Evidently HTML reports and Prometheus drift metrics.

