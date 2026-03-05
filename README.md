# DCA - Decline Curve Analysis

A web-based and CLI tool for petroleum production decline curve analysis using Arps' decline models. Fits exponential, hyperbolic, and harmonic decline curves to production data and calculates Estimated Ultimate Recovery (EUR).

## Features

- **Three Arps' Decline Models** — Exponential, Hyperbolic, and Harmonic
- **Automatic Best-Fit Selection** — based on R-squared comparison
- **EUR Calculation** — with configurable economic limit and forecast period
- **Multi-Phase Support** — analyze oil (BOPD), gas (MCFD), or water (BWPD) rates
- **Interactive Web Dashboard** — upload CSV, visualize fits, forecasts, and cumulative production
- **CLI Mode** — run analysis from the command line with plot export

## Quick Start

### Web App

```bash
pip install -r requirements.txt
python app.py
```

Open [this link](https://petroleum-dca.onrender.com/) in your browser. Upload a CSV or use the built-in sample data.

### CLI

```bash
python main.py --input data/sample_production.csv --rate-column oil_rate_bopd
```

**CLI Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `-i, --input` | Path to production CSV | `data/sample_production.csv` |
| `-r, --rate-column` | Column name for rate data | `oil_rate_bopd` |
| `-f, --forecast-years` | Forecast duration (years) | `10` |
| `-e, --economic-limit` | Economic limit rate | `10.0` |
| `-o, --output-dir` | Directory for plot output | `output` |
| `--no-plots` | Skip plot generation | — |

## CSV Format

The input CSV must have a `date` column and one or more rate columns:

```csv
date,oil_rate_bopd,gas_rate_mcfd,water_rate_bwpd
2020-01-01,1200,3600,150
2020-02-01,1150,3450,160
```

## Project Structure

```
dca/
├── app.py              # Flask web application
├── main.py             # CLI entry point
├── src/
│   ├── models.py       # Arps' decline curve models and fitting
│   ├── eur.py          # EUR calculation
│   └── plotting.py     # Matplotlib plotting (CLI)
├── static/
│   ├── app.js          # Frontend chart rendering (Chart.js)
│   └── style.css       # Dashboard styles
├── templates/
│   └── index.html      # Web UI
├── data/
│   └── sample_production.csv
├── requirements.txt
└── render.yaml         # Render deployment config
```
