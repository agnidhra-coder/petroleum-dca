"""
Estimated Ultimate Recovery (EUR) Calculator
Calculates EUR by integrating decline curves to an economic limit.
"""

import numpy as np
from .models import (
    exponential_rate, hyperbolic_rate, harmonic_rate,
    exponential_cumulative, hyperbolic_cumulative, harmonic_cumulative,
)


def calculate_eur(model_name, params, economic_limit=10.0, max_months=600):
    """
    Calculate EUR (Estimated Ultimate Recovery) for a decline model.

    Args:
        model_name: 'exponential', 'hyperbolic', or 'harmonic'
        params: dict with model parameters (qi, di, and optionally b)
        economic_limit: minimum economic production rate (bopd)
        max_months: maximum forecast horizon in months

    Returns:
        dict with EUR (bbl), time to economic limit (months), and abandonment rate
    """
    qi = params['qi']
    di = params['di']
    b = params.get('b', None)

    t = np.arange(1, max_months + 1, dtype=float)

    if model_name == 'exponential':
        rates = exponential_rate(t, qi, di)
    elif model_name == 'hyperbolic':
        rates = hyperbolic_rate(t, qi, di, b)
    elif model_name == 'harmonic':
        rates = harmonic_rate(t, qi, di)
    else:
        raise ValueError(f"Unknown model: {model_name}")

    # Find time when rate drops below economic limit
    below_limit = np.where(rates < economic_limit)[0]
    if len(below_limit) > 0:
        t_econ = t[below_limit[0]]
    else:
        t_econ = max_months

    # Calculate cumulative production up to economic limit
    if model_name == 'exponential':
        eur_daily_rate = exponential_cumulative(t_econ, qi, di)
    elif model_name == 'hyperbolic':
        eur_daily_rate = hyperbolic_cumulative(t_econ, qi, di, b)
    elif model_name == 'harmonic':
        eur_daily_rate = harmonic_cumulative(t_econ, qi, di)

    # Convert daily cumulative to total EUR in barrels
    days_per_month = 30
    eur_bbl = eur_daily_rate * days_per_month

    # Abandonment rate
    if model_name == 'exponential':
        q_abandon = exponential_rate(t_econ, qi, di)
    elif model_name == 'hyperbolic':
        q_abandon = hyperbolic_rate(t_econ, qi, di, b)
    elif model_name == 'harmonic':
        q_abandon = harmonic_rate(t_econ, qi, di)

    return {
        'eur_bbl': eur_bbl,
        'eur_mbbl': eur_bbl / 1000,
        'time_to_econ_limit_months': t_econ,
        'time_to_econ_limit_years': t_econ / 12,
        'abandonment_rate_bopd': q_abandon,
        'economic_limit_bopd': economic_limit,
    }
