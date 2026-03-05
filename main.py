import argparse
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime

from src.models import DeclineCurve
from src.eur import calculate_eur
from src.plotting import (
    plot_production_history,
    plot_decline_fits,
    plot_forecast,
    plot_model_comparison,
)


def load_production_data(filepath):
    df = pd.read_csv(filepath, parse_dates=['date'])
    df = df.sort_values('date').reset_index(drop=True)
    return df


def print_results(results, eur_results, best_model_name):
    print("\n" + "=" * 70)
    print("           DECLINE CURVE ANALYSIS RESULTS")
    print("=" * 70)

    for model_name, params in results.items():
        print(f"\n--- {model_name.upper()} DECLINE ---")
        print(f"  Initial Rate (qi):     {params['qi']:.1f} BOPD")
        print(f"  Decline Rate (di):     {params['di']:.6f} /month")
        print(f"  Nominal Annual (Di):   {params['di_annual']:.4f} /year")
        if 'b' in params:
            print(f"  Hyperbolic Exponent (b): {params['b']:.4f}")
        print(f"  R-squared:             {params['r_squared']:.6f}")

    print(f"\n{'=' * 70}")
    print(f"  BEST FIT MODEL: {best_model_name.upper()}")
    print(f"  R-squared: {results[best_model_name]['r_squared']:.6f}")
    print(f"{'=' * 70}")

    print("\n--- ESTIMATED ULTIMATE RECOVERY (EUR) ---")
    for model_name, eur in eur_results.items():
        print(f"\n  {model_name.upper()}:")
        print(f"    EUR:                 {eur['eur_bbl']:,.0f} bbl ({eur['eur_mbbl']:.1f} Mbbl)")
        print(f"    Time to Econ Limit:  {eur['time_to_econ_limit_months']:.0f} months "
              f"({eur['time_to_econ_limit_years']:.1f} years)")
        print(f"    Abandonment Rate:    {eur['abandonment_rate_bopd']:.1f} BOPD")
        print(f"    Economic Limit:      {eur['economic_limit_bopd']:.1f} BOPD")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Decline Curve Analysis Tool")
    parser.add_argument('--input', '-i', default='data/sample_production.csv',
                        help='Path to production CSV file (default: data/sample_production.csv)')
    parser.add_argument('--output-dir', '-o', default='output',
                        help='Output directory for plots (default: output)')
    parser.add_argument('--rate-column', '-r', default='oil_rate_bopd',
                        help='Column name for production rate (default: oil_rate_bopd)')
    parser.add_argument('--forecast-years', '-f', type=float, default=10,
                        help='Number of years to forecast (default: 10)')
    parser.add_argument('--economic-limit', '-e', type=float, default=10.0,
                        help='Economic limit in BOPD (default: 10.0)')
    parser.add_argument('--no-plots', action='store_true',
                        help='Skip generating plots')
    args = parser.parse_args()

    # Load data
    print(f"\nLoading production data from: {args.input}")
    df = load_production_data(args.input)
    print(f"  Records loaded: {len(df)}")
    print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  Rate column: {args.rate_column}")

    dates = df['date'].values
    rates = df[args.rate_column].values

    # Create time array (months from start)
    t = np.arange(len(rates), dtype=float)

    # Fit decline curves
    print("\nFitting decline curves...")
    dc = DeclineCurve()
    results = dc.fit_all(t, rates)

    if not results:
        print("ERROR: No models could be fitted to the data.")
        sys.exit(1)

    # Best fit
    best_model_name, best_params = dc.get_best_fit()

    # Calculate EUR for each model
    eur_results = {}
    for model_name, params in results.items():
        eur_results[model_name] = calculate_eur(
            model_name, params,
            economic_limit=args.economic_limit
        )

    # Print results
    print_results(results, eur_results, best_model_name)

    # Generate plots
    if not args.no_plots:
        os.makedirs(args.output_dir, exist_ok=True)
        dates_plt = pd.to_datetime(df['date'])

        print("\nGenerating plots...")

        plot_production_history(
            dates_plt, rates,
            title="Well Production History",
            output_path=os.path.join(args.output_dir, "01_production_history.png")
        )

        plot_decline_fits(
            dates_plt, rates, t, results,
            title="Decline Curve Analysis - Model Fits",
            output_path=os.path.join(args.output_dir, "02_decline_fits.png")
        )

        plot_forecast(
            dates_plt, rates, t, None, results, best_model_name,
            forecast_years=args.forecast_years,
            economic_limit=args.economic_limit,
            title=f"Production Forecast ({best_model_name.capitalize()} Model)",
            output_path=os.path.join(args.output_dir, "03_forecast.png")
        )

        plot_model_comparison(
            results, eur_results,
            output_path=os.path.join(args.output_dir, "04_model_comparison.png")
        )

        print(f"\nAll plots saved to: {args.output_dir}/")

    print("\nDone!")


if __name__ == '__main__':
    main()
