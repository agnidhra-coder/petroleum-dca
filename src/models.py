"""
Decline Curve Analysis Models
Implements Arps' decline curve equations:
- Exponential decline (b = 0)
- Hyperbolic decline (0 < b < 1)
- Harmonic decline (b = 1)
"""

import numpy as np
from scipy.optimize import curve_fit


def exponential_rate(t, qi, di):
    """Exponential decline: q(t) = qi * exp(-di * t)"""
    return qi * np.exp(-di * t)


def hyperbolic_rate(t, qi, di, b):
    """Hyperbolic decline: q(t) = qi / (1 + b * di * t)^(1/b)"""
    return qi / (1 + b * di * t) ** (1 / b)


def harmonic_rate(t, qi, di):
    """Harmonic decline (b=1): q(t) = qi / (1 + di * t)"""
    return qi / (1 + di * t)


def exponential_cumulative(t, qi, di):
    """Cumulative production for exponential decline: Np(t) = (qi - q(t)) / di"""
    q_t = exponential_rate(t, qi, di)
    return (qi - q_t) / di


def hyperbolic_cumulative(t, qi, di, b):
    """Cumulative production for hyperbolic decline:
    Np(t) = (qi^b / ((1-b) * di)) * (qi^(1-b) - q(t)^(1-b))
    """
    q_t = hyperbolic_rate(t, qi, di, b)
    return (qi ** b / ((1 - b) * di)) * (qi ** (1 - b) - q_t ** (1 - b))


def harmonic_cumulative(t, qi, di):
    """Cumulative production for harmonic decline: Np(t) = (qi / di) * ln(1 + di * t)"""
    return (qi / di) * np.log(1 + di * t)


class DeclineCurve:

    def __init__(self):
        self.results = {}

    def fit_exponential(self, t, q):
        try:
            popt, pcov = curve_fit(
                exponential_rate, t, q,
                p0=[q[0], 0.01],
                bounds=([0, 0], [np.inf, np.inf]),
                maxfev=10000
            )
            qi, di = popt
            q_fit = exponential_rate(t, qi, di)
            residuals = q - q_fit
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((q - np.mean(q)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            self.results['exponential'] = {
                'qi': qi,
                'di': di,
                'di_annual': di * 12,  # monthly to annual
                'r_squared': r_squared,
                'params': popt,
            }
            return self.results['exponential']
        except RuntimeError as e:
            print(f"Exponential fit failed: {e}")
            return None

    def fit_hyperbolic(self, t, q):
        try:
            popt, pcov = curve_fit(
                hyperbolic_rate, t, q,
                p0=[q[0], 0.01, 0.5],
                bounds=([0, 0, 0.01], [np.inf, np.inf, 0.99]),
                maxfev=10000
            )
            qi, di, b = popt
            q_fit = hyperbolic_rate(t, qi, di, b)
            residuals = q - q_fit
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((q - np.mean(q)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            self.results['hyperbolic'] = {
                'qi': qi,
                'di': di,
                'b': b,
                'di_annual': di * 12,
                'r_squared': r_squared,
                'params': popt,
            }
            return self.results['hyperbolic']
        except RuntimeError as e:
            print(f"Hyperbolic fit failed: {e}")
            return None

    def fit_harmonic(self, t, q):
        try:
            popt, pcov = curve_fit(
                harmonic_rate, t, q,
                p0=[q[0], 0.01],
                bounds=([0, 0], [np.inf, np.inf]),
                maxfev=10000
            )
            qi, di = popt
            q_fit = harmonic_rate(t, qi, di)
            residuals = q - q_fit
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((q - np.mean(q)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            self.results['harmonic'] = {
                'qi': qi,
                'di': di,
                'di_annual': di * 12,
                'r_squared': r_squared,
                'params': popt,
            }
            return self.results['harmonic']
        except RuntimeError as e:
            print(f"Harmonic fit failed: {e}")
            return None

    def fit_all(self, t, q):
        self.fit_exponential(t, q)
        self.fit_hyperbolic(t, q)
        self.fit_harmonic(t, q)
        return self.results

    def get_best_fit(self):
        """Return the model with the highest R-squared."""
        if not self.results:
            return None
        return max(self.results.items(), key=lambda x: x[1]['r_squared'])

    def forecast(self, model_name, t_forecast):
        """Generate forecast for a given model over future time array."""
        if model_name not in self.results:
            raise ValueError(f"Model '{model_name}' not fitted yet.")

        params = self.results[model_name]
        if model_name == 'exponential':
            return exponential_rate(t_forecast, params['qi'], params['di'])
        elif model_name == 'hyperbolic':
            return hyperbolic_rate(t_forecast, params['qi'], params['di'], params['b'])
        elif model_name == 'harmonic':
            return harmonic_rate(t_forecast, params['qi'], params['di'])

    def cumulative(self, model_name, t):
        """Calculate cumulative production for a given model."""
        if model_name not in self.results:
            raise ValueError(f"Model '{model_name}' not fitted yet.")

        params = self.results[model_name]
        if model_name == 'exponential':
            return exponential_cumulative(t, params['qi'], params['di'])
        elif model_name == 'hyperbolic':
            return hyperbolic_cumulative(t, params['qi'], params['di'], params['b'])
        elif model_name == 'harmonic':
            return harmonic_cumulative(t, params['qi'], params['di'])
