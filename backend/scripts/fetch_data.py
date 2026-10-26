from pathlib import Path

import httpx
import pandas as pd


# Project paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"

# Elexon API
BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

ACTUALS_URL = f"{BASE_URL}/datasets/FUELHH/stream"
FORECASTS_URL = f"{BASE_URL}/datasets/WINDFOR/stream"


def fetch_data(
    client: httpx.Client,
    url: str,
    params: dict,
    dataset_name: str,
) -> pd.DataFrame:
    """Fetch a dataset from the Elexon API and return a DataFrame."""

    print(f"\nFetching {dataset_name}...")

    response = client.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        raise ValueError(
            f"Expected a list from {dataset_name}, "
            f"but received {type(data).__name__}."
        )

    df = pd.DataFrame(data)

    print(f"Successfully fetched {len(df):,} rows.")
    print(f"Columns: {list(df.columns)}")

    return df


def main():
    # Create the data directory if it doesn't exist.
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Request parameters for actual wind generation.
    actuals_params = {
        "settlementDateFrom": "2026-01-01",
        "settlementDateTo": "2026-01-31",
        "fuelType": "WIND",
    }

    # Request parameters for wind forecasts.
    forecasts_params = {
        "publishDateTimeFrom": "2025-12-25T00:00:00Z",
        "publishDateTimeTo": "2026-02-02T00:00:00Z",
    }

    # Set a timeout so the requests do not hang indefinitely.
    timeout = httpx.Timeout(120.0, connect=20.0)

    # Reuse one HTTP client for both API requests.
    with httpx.Client(timeout=timeout) as client:

        # Fetch actual wind generation.
        actuals_df = fetch_data(
            client=client,
            url=ACTUALS_URL,
            params=actuals_params,
            dataset_name="Actual wind generation (FUELHH)",
        )

        # Fetch wind forecasts.
        forecasts_df = fetch_data(
            client=client,
            url=FORECASTS_URL,
            params=forecasts_params,
            dataset_name="Wind forecasts (WINDFOR)",
        )

    # Save the data as CSV files.
    actuals_path = DATA_DIR / "actuals.csv"
    forecasts_path = DATA_DIR / "forecasts.csv"

    actuals_df.to_csv(actuals_path, index=False)
    forecasts_df.to_csv(forecasts_path, index=False)

    print("\n" + "=" * 50)
    print("DATA FETCH COMPLETE")
    print("=" * 50)

    print(f"Actuals saved to: {actuals_path}")
    print(f"Actuals rows: {len(actuals_df):,}")

    print(f"\nForecasts saved to: {forecasts_path}")
    print(f"Forecast rows: {len(forecasts_df):,}")


if __name__ == "__main__":
    main()