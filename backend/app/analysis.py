from pathlib import Path

import numpy as np
import pandas as pd


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load a CSV file into a DataFrame."""
    return pd.read_csv(path)


def build_hourly_actuals(
    actuals: pd.DataFrame,
    start_date: str = "2026-01-01",
    end_date: str = "2026-02-01",
) -> pd.DataFrame:
    """
    Convert half-hourly actual generation into hourly averages.

    The date interval is start-inclusive and end-exclusive.
    The default interval covers January 2026 in UTC.
    """
    df = actuals.copy()

    df["startTime"] = pd.to_datetime(
        df["startTime"],
        utc=True,
        errors="raise",
    )

    df["generation"] = pd.to_numeric(
        df["generation"],
        errors="raise",
    )

    start = pd.Timestamp(start_date, tz="UTC")
    end = pd.Timestamp(end_date, tz="UTC")

    df = df[
        (df["startTime"] >= start)
        & (df["startTime"] < end)
    ].copy()

    # Each half-hour belongs to the hour in which it starts.
    df["targetTime"] = df["startTime"].dt.floor("h")

    hourly = (
        df.groupby("targetTime")
        .agg(
            actual=("generation", "mean"),
            half_hour_count=("generation", "count"),
        )
        .reset_index()
    )

    # Only accept complete hours with both half-hour observations.
    hourly.loc[
        hourly["half_hour_count"] != 2,
        "actual",
    ] = np.nan

    return hourly


def select_forecasts(
    forecasts: pd.DataFrame,
    cutoff_hour: int = 9,
    cutoff_minute: int = 20,
) -> pd.DataFrame:
    """
    Select the newest eligible forecast for each target hour.

    The deadline is cutoff_hour:cutoff_minute UTC on the
    calendar day before the target hour.

    Forecasts published exactly at the deadline are eligible.
    """
    if not 0 <= cutoff_hour <= 23:
        raise ValueError("cutoff_hour must be between 0 and 23.")

    if not 0 <= cutoff_minute <= 59:
        raise ValueError("cutoff_minute must be between 0 and 59.")

    df = forecasts.copy()

    df["startTime"] = pd.to_datetime(
        df["startTime"],
        utc=True,
        errors="raise",
    )

    df["publishTime"] = pd.to_datetime(
        df["publishTime"],
        utc=True,
        errors="raise",
    )

    df["generation"] = pd.to_numeric(
        df["generation"],
        errors="raise",
    )

    # Target is the delivery-hour start.
    df["targetTime"] = df["startTime"].dt.floor("h")

    # Construct the decision deadline separately for each target.
    previous_day = df["targetTime"].dt.normalize() - pd.Timedelta(days=1)

    df["decisionDeadline"] = (
        previous_day
        + pd.Timedelta(hours=cutoff_hour)
        + pd.Timedelta(minutes=cutoff_minute)
    )

    # Only bulletins available by the deadline can be selected.
    eligible = df[
        df["publishTime"].notna()
        & (df["publishTime"] <= df["decisionDeadline"])
    ].copy()

    # Sort oldest to newest. For duplicate publication timestamps,
    # keep the last record in the sorted input order.
    eligible = eligible.sort_values(
        ["targetTime", "publishTime"],
        kind="stable",
    )

    selected = eligible.drop_duplicates(
        subset=["targetTime"],
        keep="last",
    )

    return selected[
        [
            "targetTime",
            "publishTime",
            "decisionDeadline",
            "generation",
        ]
    ].rename(
        columns={
            "publishTime": "forecastPublishTime",
            "generation": "forecast",
        }
    ).reset_index(drop=True)


def build_hourly_comparison(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    cutoff_hour: int = 9,
    cutoff_minute: int = 20,
) -> pd.DataFrame:
    """
    Build one row per January delivery hour.

    Missing actuals or eligible forecasts remain missing.
    Forecast error is forecast minus actual.
    """
    hourly_actuals = build_hourly_actuals(actuals)

    selected_forecasts = select_forecasts(
        forecasts,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
    )

    # Generate all 744 hourly targets for January 2026.
    january_hours = pd.date_range(
        start="2026-01-01 00:00:00",
        end="2026-01-31 23:00:00",
        freq="h",
        tz="UTC",
        name="targetTime",
    )

    result = pd.DataFrame(
        {"targetTime": january_hours}
    )

    result = result.merge(
        hourly_actuals.drop(columns=["half_hour_count"]),
        on="targetTime",
        how="left",
        validate="one_to_one",
    )

    result = result.merge(
        selected_forecasts,
        on="targetTime",
        how="left",
        validate="one_to_one",
    )

    result["error"] = result["forecast"] - result["actual"]

    result["absolute_error"] = result["error"].abs()

    return result


def calculate_metrics(
    comparison: pd.DataFrame,
) -> dict[str, float | int]:
    """
    Calculate MAE, bias, RMSE and MAE as a percentage
    of average actual generation.
    """
    valid = comparison.dropna(subset=["forecast", "actual"])

    if valid.empty:
        return {
            "hours_evaluated": 0,
            "MAE": float("nan"),
            "bias": float("nan"),
            "RMSE": float("nan"),
            "average_actual": float("nan"),
            "MAE_percent_of_average_actual": float("nan"),
        }

    errors = (
        valid["forecast"].to_numpy(dtype=float)
        - valid["actual"].to_numpy(dtype=float)
    )

    average_actual = float(valid["actual"].mean())
    mae = float(np.mean(np.abs(errors)))

    if average_actual == 0:
        mae_percent = float("nan")
    else:
        mae_percent = float(mae / abs(average_actual) * 100)

    return {
        "hours_evaluated": len(valid),
        "MAE": mae,
        "bias": float(np.mean(errors)),
        "RMSE": float(np.sqrt(np.mean(errors ** 2))),
        "average_actual": average_actual,
        "MAE_percent_of_average_actual": mae_percent,
    }


def run_analysis(
    actuals_path: str | Path,
    forecasts_path: str | Path,
    cutoff_hour: int = 9,
    cutoff_minute: int = 20,
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Load both datasets, build the comparison, and calculate metrics."""
    actuals = load_csv(actuals_path)
    forecasts = load_csv(forecasts_path)

    comparison = build_hourly_comparison(
        actuals,
        forecasts,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
    )

    metrics = calculate_metrics(comparison)

    return comparison, metrics

def count_junk_forecasts(
    forecasts: pd.DataFrame,
    start_date: str = "2026-01-01",
    end_date: str = "2026-02-01",
) -> int:
    """
    Count forecasts published after their target hour began,
    restricted to target hours in [start_date, end_date).
    """
    df = forecasts.copy()

    df["startTime"] = pd.to_datetime(
        df["startTime"],
        utc=True,
        errors="raise",
    )

    df["publishTime"] = pd.to_datetime(
        df["publishTime"],
        utc=True,
        errors="raise",
    )

    start = pd.Timestamp(start_date, tz="UTC")
    end = pd.Timestamp(end_date, tz="UTC")

    in_scope = (
        (df["startTime"] >= start)
        & (df["startTime"] < end)
    )

    published_too_late = (
        df["startTime"] < df["publishTime"]
    )

    return int((in_scope & published_too_late).sum())