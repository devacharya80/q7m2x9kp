from pathlib import Path

import pandas as pd


# Define file paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"

ACTUALS_FILE = DATA_DIR / "actuals.csv"
FORECASTS_FILE = DATA_DIR / "forecasts.csv"


def inspect_dataset(file_path: Path, dataset_name: str) -> pd.DataFrame:
    """Inspect a CSV file and print basic statistics."""

    print("\n" + "=" * 60)
    print(f"DATASET: {dataset_name}")
    print("=" * 60)

    # Read the CSV file
    df = pd.read_csv(file_path)

    # 1. Number of rows and column names
    print(f"\nNumber of rows: {len(df):,}")
    print(f"Column names: {list(df.columns)}")

    # 2. Earliest and latest startTime
    df["startTime"] = pd.to_datetime(
        df["startTime"],
        utc=True,
    )

    print(f"\nEarliest startTime: {df['startTime'].min()}")
    print(f"Latest startTime:   {df['startTime'].max()}")

    # 3a. Missing values
    missing_values = int(df.isna().sum().sum())
    print(f"\nTotal missing values: {missing_values:,}")

    # 3b. Duplicated rows
    duplicate_rows = int(df.duplicated().sum())
    print(f"Duplicate rows: {duplicate_rows:,}")

    # 3c. Negative generation values
    if "generation" in df.columns:
        generation = pd.to_numeric(
            df["generation"],
            errors="coerce",
        )

        negative_generation = int((generation < 0).sum())
        print(f"Negative generation values: {negative_generation:,}")
    else:
        print("Negative generation values: No 'generation' column found.")

    return df


def main():
    # Inspect actual generation data
    actuals_df = inspect_dataset(
        ACTUALS_FILE,
        "ACTUALS (FUELHH)",
    )

    # Inspect wind forecast data
    forecasts_df = inspect_dataset(
        FORECASTS_FILE,
        "FORECASTS (WINDFOR)",
    )

    # Forecast-specific checks
    print("\n" + "=" * 60)
    print("FORECAST-SPECIFIC ANALYSIS")
    print("=" * 60)

    # 4. Number of distinct publishTime values
    forecasts_df["publishTime"] = pd.to_datetime(
        forecasts_df["publishTime"],
        utc=True,
    )

    unique_publish_times = forecasts_df["publishTime"].nunique()

    print(f"\nDistinct publishTime values: {unique_publish_times:,}")

    # 5. Forecasts published after their delivery hour started
    junk_forecasts = (
        forecasts_df["startTime"] < forecasts_df["publishTime"]
    )

    junk_count = int(junk_forecasts.sum())

    print(
        "Rows where startTime < publishTime: "
        f"{junk_count:,}"
    )

    print("\nSample junk forecast rows:")

    columns_to_show = [
        column
        for column in [
            "startTime",
            "publishTime",
            "generation",
        ]
        if column in forecasts_df.columns
    ]

    print(
        forecasts_df.loc[junk_forecasts, columns_to_show]
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()