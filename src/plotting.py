"""
Plotting module for Decline Curve Analysis.
Generates production history, forecast curves, and EUR visualizations.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

from .models import exponential_rate, hyperbolic_rate, harmonic_rate


def plot_production_history(dates, rates, title="Production History", output_path=None):
    """Plot raw production data."""
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(dates, rates, 'ko-', markersize=4, label='Actual Production')
    ax.set_xlabel('Date')
    ax.set_ylabel('Oil Rate (BOPD)')
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    fig.autofmt_xdate()
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {output_path}")
    return fig, ax


def plot_decline_fits(dates, rates, t, results, title="Decline Curve Fits", output_path=None):
    """Plot production data with all fitted decline curves."""
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(dates, rates, 'ko', markersize=5, label='Actual Production', zorder=5)

    colors = {'exponential': '#e74c3c', 'hyperbolic': '#2ecc71', 'harmonic': '#3498db'}
    labels = {'exponential': 'Exponential', 'hyperbolic': 'Hyperbolic', 'harmonic': 'Harmonic'}

    for model_name, params in results.items():
        color = colors[model_name]
        label = f"{labels[model_name]} (R² = {params['r_squared']:.4f})"

        if model_name == 'exponential':
            q_fit = exponential_rate(t, params['qi'], params['di'])
        elif model_name == 'hyperbolic':
            q_fit = hyperbolic_rate(t, params['qi'], params['di'], params['b'])
        elif model_name == 'harmonic':
            q_fit = harmonic_rate(t, params['qi'], params['di'])

        ax.plot(dates, q_fit, color=color, linewidth=2, label=label)

    ax.set_xlabel('Date')
    ax.set_ylabel('Oil Rate (BOPD)')
    ax.set_title(title)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    fig.autofmt_xdate()
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {output_path}")
    return fig, ax


def plot_forecast(dates, rates, t_hist, t_forecast, results, best_model,
                  forecast_years=10, economic_limit=10.0,
                  title="Production Forecast", output_path=None):
    """Plot production history with forecast from the best-fit model."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[2, 1])

    params = results[best_model]

    # Generate forecast dates
    last_date = dates.iloc[-1]
    forecast_months = int(forecast_years * 12)
    forecast_dates = [last_date + timedelta(days=30.44 * i) for i in range(1, forecast_months + 1)]
    t_forecast_arr = np.arange(len(t_hist) + 1, len(t_hist) + forecast_months + 1, dtype=float)

    # Generate forecast rates
    if best_model == 'exponential':
        q_hist_fit = exponential_rate(t_hist, params['qi'], params['di'])
        q_forecast = exponential_rate(t_forecast_arr, params['qi'], params['di'])
    elif best_model == 'hyperbolic':
        q_hist_fit = hyperbolic_rate(t_hist, params['qi'], params['di'], params['b'])
        q_forecast = hyperbolic_rate(t_forecast_arr, params['qi'], params['di'], params['b'])
    elif best_model == 'harmonic':
        q_hist_fit = harmonic_rate(t_hist, params['qi'], params['di'])
        q_forecast = harmonic_rate(t_forecast_arr, params['qi'], params['di'])

    # --- Top plot: Rate vs Time ---
    ax1.plot(dates, rates, 'ko', markersize=5, label='Actual Production', zorder=5)
    ax1.plot(dates, q_hist_fit, 'b-', linewidth=2, label=f'{best_model.capitalize()} Fit')
    ax1.plot(forecast_dates, q_forecast, 'r--', linewidth=2, label='Forecast')
    ax1.axhline(y=economic_limit, color='gray', linestyle=':', linewidth=1,
                label=f'Economic Limit ({economic_limit} BOPD)')

    ax1.set_xlabel('Date')
    ax1.set_ylabel('Oil Rate (BOPD)')
    ax1.set_title(title)
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.set_ylim(bottom=0)

    # --- Bottom plot: Cumulative production ---
    all_t = np.concatenate([t_hist, t_forecast_arr])
    all_dates = list(dates) + forecast_dates

    if best_model == 'exponential':
        from .models import exponential_cumulative
        cum = exponential_cumulative(all_t, params['qi'], params['di']) * 30.44
    elif best_model == 'hyperbolic':
        from .models import hyperbolic_cumulative
        cum = hyperbolic_cumulative(all_t, params['qi'], params['di'], params['b']) * 30.44
    elif best_model == 'harmonic':
        from .models import harmonic_cumulative
        cum = harmonic_cumulative(all_t, params['qi'], params['di']) * 30.44

    n_hist = len(dates)
    ax2.plot(all_dates[:n_hist], cum[:n_hist] / 1000, 'b-', linewidth=2, label='Historical Cumulative')
    ax2.plot(all_dates[n_hist:], cum[n_hist:] / 1000, 'r--', linewidth=2, label='Forecast Cumulative')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Cumulative Production (Mbbl)')
    ax2.set_title('Cumulative Production')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax2.xaxis.set_major_locator(mdates.YearLocator())

    fig.autofmt_xdate()
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {output_path}")
    return fig, (ax1, ax2)


def plot_model_comparison(results, eur_results, output_path=None):
    """Bar chart comparing R-squared and EUR across models."""
    models = list(results.keys())
    r2_values = [results[m]['r_squared'] for m in models]
    eur_values = [eur_results[m]['eur_mbbl'] for m in models]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    colors = {'exponential': '#e74c3c', 'hyperbolic': '#2ecc71', 'harmonic': '#3498db'}
    bar_colors = [colors[m] for m in models]
    model_labels = [m.capitalize() for m in models]

    # R-squared comparison
    bars1 = ax1.bar(model_labels, r2_values, color=bar_colors, edgecolor='black', linewidth=0.5)
    ax1.set_ylabel('R-squared')
    ax1.set_title('Model Fit Comparison')
    ax1.set_ylim(min(r2_values) - 0.01, 1.0)
    for bar, val in zip(bars1, r2_values):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.001,
                 f'{val:.4f}', ha='center', va='bottom', fontsize=10)

    # EUR comparison
    bars2 = ax2.bar(model_labels, eur_values, color=bar_colors, edgecolor='black', linewidth=0.5)
    ax2.set_ylabel('EUR (Mbbl)')
    ax2.set_title('Estimated Ultimate Recovery')
    for bar, val in zip(bars2, eur_values):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{val:.1f}', ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {output_path}")
    return fig, (ax1, ax2)
