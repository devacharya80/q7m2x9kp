from pathlib import Path
import sys

import pandas as pd

# Add the backend directory to Python's import path.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.analysis import build_hourly_actuals, select_forecasts

DATA_DIR = BACKEND_DIR / "data"


def main():
    actuals = pd.read_csv(DATA_DIR / "actuals.csv")
    forecasts = pd.read_csv(DATA_DIR / "forecasts.csv")

    # Build hourly actuals and select forecasts using the
    # same decision rule as the main analysis.
    hourly_actuals = build_hourly_actuals(actuals)

    selected = select_forecasts(
        forecasts,
        cutoff_hour=9,
        cutoff_minute=20,
    )

    # Compare the same selected forecasts against actuals
    # at different target-hour alignments.
    for shift in [-1, 0, 1]:
        comparison = selected.copy()

        # Shift the forecast target timestamps for this experiment.
        comparison["actual_target"] = (
            comparison["targetTime"]
            + pd.Timedelta(hours=shift)
        )

        comparison = comparison.merge(
            hourly_actuals[["targetTime", "actual"]],
            left_on="actual_target",
            right_on="targetTime",
            how="left",
            suffixes=("_forecast", "_actual"),
        )

        valid = comparison.dropna(
            subset=["forecast", "actual"]
        )

        if valid.empty:
            print(
                f"Shift {shift:+d}: no overlapping valid observations"
            )
            continue

        errors = valid["forecast"] - valid["actual"]

        mae = errors.abs().mean()

        print(
            f"Shift {shift:+d} hour | "
            f"Rows evaluated: {len(valid)} | "
            f"MAE: {mae:,.2f}"
        )


if __name__ == "__main__":
    main()