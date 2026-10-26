
from pathlib import Path
import sys

import pandas as pd

# Add the backend directory to Python's import path.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.analysis import run_analysis, count_junk_forecasts


DATA_DIR = BACKEND_DIR / "data"
OUTPUT_DIR = BACKEND_DIR / "outputs"


def main():
    actuals_path = DATA_DIR / "actuals.csv"
    forecasts_path = DATA_DIR / "forecasts.csv"

    # Run the hourly analysis and calculate metrics.
    comparison, metrics = run_analysis(
        actuals_path=actuals_path,
        forecasts_path=forecasts_path,
        cutoff_hour=9,
        cutoff_minute=20,
    )

    # Count forecast records published after their target hour began.
    forecasts = pd.read_csv(forecasts_path)
    junk_count = count_junk_forecasts(forecasts)

    # Create output directory and save hourly results.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / "hourly_comparison.csv"
    comparison.to_csv(output_path, index=False)

    print("=" * 60)
    print("JANUARY 2026 WIND FORECAST ANALYSIS")
    print("=" * 60)

    print(f"\nTotal target hours: {len(comparison)}")
    print(f"Hours evaluated: {metrics['hours_evaluated']}")
    print(f"Hours missing actual: {comparison['actual'].isna().sum()}")
    print(
        "Hours missing eligible forecast: "
        f"{comparison['forecast'].isna().sum()}"
    )
    print(f"Junk forecast rows: {junk_count:,}")

    print("\nSummary metrics:")

    for name in ["MAE", "bias", "RMSE"]:
        print(f"{name}: {metrics[name]:,.2f}")

    print(f"Average actual: {metrics['average_actual']:,.2f}")
    print(
        "MAE (% of average actual): "
        f"{metrics['MAE_percent_of_average_actual']:.2f}%"
    )

    print(f"\nHourly results saved to: {output_path}")

    # Display the hand-checked target hour.
    target_time = pd.Timestamp("2026-01-15 12:00:00", tz="UTC")
    target = comparison[comparison["targetTime"] == target_time]

    print("\nHand-checked target hour:")
    print(target.to_string(index=False))


if __name__ == "__main__":
    main()
