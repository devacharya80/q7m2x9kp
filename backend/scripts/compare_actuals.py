from pathlib import Path

import pandas as pd


# Locate the actuals CSV
BACKEND_DIR = Path(__file__).resolve().parent.parent
ACTUALS_FILE = BACKEND_DIR / "data" / "actuals.csv"


def main():
    # Read actual wind generation data
    df = pd.read_csv(ACTUALS_FILE)

    # Convert startTime to timezone-aware datetime
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)

    # Target delivery hour: 15 January 2026, 12:00–13:00 UTC
    target_start = pd.Timestamp("2026-01-15 12:00:00", tz="UTC")
    target_end = pd.Timestamp("2026-01-15 13:00:00", tz="UTC")

    # Select the two half-hour periods
    hourly_actuals = df[
        (df["startTime"] >= target_start)
        & (df["startTime"] < target_end)
    ].copy()

    if len(hourly_actuals) != 2:
        raise ValueError(
            f"Expected 2 half-hour actuals, "
            f"but found {len(hourly_actuals)}."
        )

    # Convert generation to numeric values
    hourly_actuals["generation"] = pd.to_numeric(
        hourly_actuals["generation"],
        errors="raise",
    )

    # Calculate hourly actual as the average of both half-hours
    hourly_actual = hourly_actuals["generation"].mean()

    print("=" * 55)
    print("ACTUAL WIND GENERATION")
    print("=" * 55)

    print("\nHalf-hour actuals:")
    print(
        hourly_actuals[["startTime", "generation"]]
        .sort_values("startTime")
        .to_string(index=False)
    )

    print(f"\nHourly actual: {hourly_actual:,.2f}")

    # Forecast values from the previous bulletin inspection
    forecasts = {
        "First forecast": 11938,
        "09:30 forecast": 10503,
        "Selected forecast": 11049,
    }

    # Calculate forecast errors
    print("\n" + "=" * 55)
    print("FORECAST COMPARISON")
    print("=" * 55)

    results = []

    for name, forecast in forecasts.items():
        error = forecast - hourly_actual

        results.append({
            "forecast_name": name,
            "forecast": forecast,
            "actual": hourly_actual,
            "error": error,
            "absolute_error": abs(error),
        })

    results_df = pd.DataFrame(results)

    print(
        results_df.to_string(
            index=False,
            formatters={
                "forecast": "{:,.2f}".format,
                "actual": "{:,.2f}".format,
                "error": "{:+,.2f}".format,
                "absolute_error": "{:,.2f}".format,
            },
        )
    )

    closest = results_df.sort_values("absolute_error").iloc[0]

    print("\nClosest forecast:")
    print(f"{closest['forecast_name']}: {closest['forecast']:,.2f}")

    print(f"Absolute error: {closest['absolute_error']:,.2f}")


if __name__ == "__main__":
    main()