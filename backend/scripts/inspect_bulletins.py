from pathlib import Path

import pandas as pd


# Locate the forecast CSV
BACKEND_DIR = Path(__file__).resolve().parent.parent
FORECASTS_FILE = BACKEND_DIR / "data" / "forecasts.csv"


def main():
    # 1. Read the forecast data
    df = pd.read_csv(FORECASTS_FILE)

    # Convert timestamps into timezone-aware datetimes
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)

    # 2. Select the target delivery hour: 15 Jan 2026, 12:00 UTC
    target_time = pd.Timestamp("2026-01-15 12:00:00", tz="UTC")

    target_df = df[df["startTime"] == target_time].copy()

    # 3. Sort bulletins by publication time, oldest first
    target_df = target_df.sort_values("publishTime")

    # 4. Calculate how many hours before the target each forecast was published
    target_df["hours_before_target"] = (
        target_df["startTime"] - target_df["publishTime"]
    ).dt.total_seconds() / 3600

    # 5. Print the results
    print(f"Target delivery hour: {target_time}")
    print(f"Number of bulletin rows: {len(target_df)}")

    print("\nForecast bulletins, oldest first:\n")

    columns = [
        "publishTime",
        "generation",
        "hours_before_target",
    ]

    print(target_df[columns].to_string(index=False))


if __name__ == "__main__":
    main()