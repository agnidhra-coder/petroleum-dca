"""
Flask web application for Decline Curve Analysis.
"""

import os
import io
import json
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from datetime import timedelta

from src.models import (
    DeclineCurve,
    exponential_rate, hyperbolic_rate, harmonic_rate,
    exponential_cumulative, hyperbolic_cumulative, harmonic_cumulative,
)
from src.eur import calculate_eur

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze():
    forecast_years = float(request.form.get('forecast_years', 10))
    economic_limit = float(request.form.get('economic_limit', 10.0))
    rate_column = request.form.get('rate_column', 'oil_rate_bopd')

    # Load CSV
    if 'file' in request.files and request.files['file'].filename:
        file = request.files['file']
        content = file.read().decode('utf-8')
        df = pd.read_csv(io.StringIO(content), parse_dates=['date'])
    else:
        df = pd.read_csv('data/sample_production.csv', parse_dates=['date'])

    df = df.sort_values('date').reset_index(drop=True)

    # Validate rate column
    if rate_column not in df.columns:
        available = [c for c in df.columns if c != 'date']
        return jsonify({'error': f"Column '{rate_column}' not found. Available: {available}"}), 400

    dates = df['date']
    rates = df[rate_column].values
    t = np.arange(len(rates), dtype=float)

    # Fit models
    dc = DeclineCurve()
    results = dc.fit_all(t, rates)
    if not results:
        return jsonify({'error': 'Could not fit any decline model to the data.'}), 400

    best_model_name, _ = dc.get_best_fit()

    # EUR
    eur_results = {}
    for model_name, params in results.items():
        eur_results[model_name] = calculate_eur(model_name, params, economic_limit=economic_limit)

    # Build response data for charts
    date_strings = [d.strftime('%Y-%m-%d') for d in dates]

    # Fitted curves over historical period
    fits = {}
    for model_name, params in results.items():
        if model_name == 'exponential':
            q_fit = exponential_rate(t, params['qi'], params['di'])
        elif model_name == 'hyperbolic':
            q_fit = hyperbolic_rate(t, params['qi'], params['di'], params['b'])
        elif model_name == 'harmonic':
            q_fit = harmonic_rate(t, params['qi'], params['di'])
        fits[model_name] = [round(float(v), 2) for v in q_fit]

    # Forecast from best model
    best_params = results[best_model_name]
    forecast_months = int(forecast_years * 12)
    t_forecast = np.arange(len(t), len(t) + forecast_months, dtype=float)
    last_date = dates.iloc[-1]
    forecast_dates = [(last_date + timedelta(days=30.44 * (i + 1))).strftime('%Y-%m-%d')
                      for i in range(forecast_months)]

    if best_model_name == 'exponential':
        q_forecast = exponential_rate(t_forecast, best_params['qi'], best_params['di'])
    elif best_model_name == 'hyperbolic':
        q_forecast = hyperbolic_rate(t_forecast, best_params['qi'], best_params['di'], best_params['b'])
    elif best_model_name == 'harmonic':
        q_forecast = harmonic_rate(t_forecast, best_params['qi'], best_params['di'])

    # Cumulative production (historical + forecast)
    all_t = np.concatenate([t, t_forecast])
    if best_model_name == 'exponential':
        cum = exponential_cumulative(all_t, best_params['qi'], best_params['di']) * 30
    elif best_model_name == 'hyperbolic':
        cum = hyperbolic_cumulative(all_t, best_params['qi'], best_params['di'], best_params['b']) * 30
    elif best_model_name == 'harmonic':
        cum = harmonic_cumulative(all_t, best_params['qi'], best_params['di']) * 30

    n_hist = len(t)

    # Serialize model results (strip numpy arrays)
    model_results = {}
    for name, params in results.items():
        model_results[name] = {
            'qi': round(float(params['qi']), 2),
            'di': round(float(params['di']), 6),
            'di_annual': round(float(params['di_annual']), 4),
            'r_squared': round(float(params['r_squared']), 6),
        }
        if 'b' in params:
            model_results[name]['b'] = round(float(params['b']), 4)

    eur_serialized = {}
    for name, eur in eur_results.items():
        eur_serialized[name] = {
            'eur_bbl': round(float(eur['eur_bbl']), 0),
            'eur_mbbl': round(float(eur['eur_mbbl']), 1),
            'time_to_econ_limit_months': round(float(eur['time_to_econ_limit_months']), 0),
            'time_to_econ_limit_years': round(float(eur['time_to_econ_limit_years']), 1),
            'abandonment_rate_bopd': round(float(eur['abandonment_rate_bopd']), 1),
            'economic_limit_bopd': float(eur['economic_limit_bopd']),
        }

    # Available columns for the frontend
    available_columns = [c for c in df.columns if c != 'date']

    return jsonify({
        'dates': date_strings,
        'rates': [round(float(v), 2) for v in rates],
        'fits': fits,
        'forecast_dates': forecast_dates,
        'forecast_rates': [round(float(v), 2) for v in q_forecast],
        'cumulative_dates': date_strings + forecast_dates,
        'cumulative_hist': [round(float(v), 0) for v in cum[:n_hist]],
        'cumulative_forecast': [round(float(v), 0) for v in cum[n_hist:]],
        'models': model_results,
        'eur': eur_serialized,
        'best_model': best_model_name,
        'economic_limit': economic_limit,
        'available_columns': available_columns,
        'rate_column': rate_column,
    })


if __name__ == '__main__':
    app.run(debug=True, port=5050)
