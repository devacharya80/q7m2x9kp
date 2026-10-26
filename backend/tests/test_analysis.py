import pandas as pd
import pytest

from app.analysis import (
    build_hourly_actuals,
    build_hourly_comparison,
    calculate_metrics,
    select_forecasts,
)


def test_selects_latest_forecast_available_before_deadline():
    forecasts = pd.DataFrame(
        [
            {
                "startTime": "2026-01-15T12:00:00Z",
                "publishTime": "2026-01-12T09:30:00Z",
                "generation": 11938,
            },
            {
                "startTime": "2026-01-15T12:00:00Z",
                "publishTime": "2026-01-14T07:30:00Z",
                "generation": 11049,
            },
            {
                "startTime": "2026-01-15T12:00:00Z",
                "publishTime": "2026-01-14T09:30:00Z",
                "generation": 10503,
            },
            {
                "startTime": "2026-01-15T12:00:00Z",
                "publishTime": "2026-01-15T09:30:00Z",
                "generation": 10000,
            },
        ]
    )

    selected = select_forecasts(
        forecasts,
        cutoff_hour=9,
        cutoff_minute=20,
    )

    target = selected[
        selected["targetTime"]
        == pd.Timestamp("2026-01-15T12:00:00Z")
    ]

    assert len(target) == 1

    row = target.iloc[0]

    assert row["forecast"] == 11049

    assert row["forecastPublishTime"] == pd.Timestamp(
        "2026-01-14T07:30:00Z"
    )

    assert row["decisionDeadline"] == pd.Timestamp(
        "2026-01-14T09:20:00Z"
    )


def test_hourly_actual_is_average_of_two_half_hours():
    actuals = pd.DataFrame(
        [
            {
                "startTime": "2026-01-15T12:00:00Z",
                "generation": 9500,
            },
            {
                "startTime": "2026-01-15T12:30:00Z",
                "generation": 10081,
            },
        ]
    )

    hourly = build_hourly_actuals(actuals)

    assert len(hourly) == 1
    assert hourly.iloc[0]["actual"] == pytest.approx(9790.5)


def test_comparison_error_matches_hand_checked_example():
    actuals = pd.DataFrame(
        [
            {
                "startTime": "2026-01-15T12:00:00Z",
                "generation": 9500,
            },
            {
                "startTime": "2026-01-15T12:30:00Z",
                "generation": 10081,
            },
        ]
    )

    forecasts = pd.DataFrame(
        [
            {
                "startTime": "2026-01-15T12:00:00Z",
                "publishTime": "2026-01-14T07:30:00Z",
                "generation": 11049,
            },
            {
                "startTime": "2026-01-15T12:00:00Z",
                "publishTime": "2026-01-14T09:30:00Z",
                "generation": 10503,
            },
        ]
    )

    comparison = build_hourly_comparison(actuals, forecasts)

    target = comparison[
        comparison["targetTime"]
        == pd.Timestamp("2026-01-15T12:00:00Z")
    ]

    row = target.iloc[0]

    assert row["forecast"] == 11049
    assert row["actual"] == pytest.approx(9790.5)
    assert row["error"] == pytest.approx(1258.5)



def test_metrics_use_forecast_minus_actual():
    comparison = pd.DataFrame(
        {
            "forecast": [110.0, 90.0, 120.0],
            "actual": [100.0, 100.0, 100.0],
        }
    )

    metrics = calculate_metrics(comparison)

    assert metrics["hours_evaluated"] == 3
    assert metrics["MAE"] == pytest.approx(40 / 3)
    assert metrics["bias"] == pytest.approx(20 / 3)
    assert metrics["RMSE"] == pytest.approx((200) ** 0.5)
    assert metrics["average_actual"] == pytest.approx(100.0)
    assert metrics["MAE_percent_of_average_actual"] == pytest.approx(
        100 * (40 / 3) / 100
    )


def test_forecast_published_exactly_at_deadline_is_selected():
    forecasts = pd.DataFrame([
        {
            "startTime": "2026-01-15T12:00:00Z",
            "publishTime": "2026-01-14T09:20:00Z",
            "generation": 11049,
        },
        {
            "startTime": "2026-01-15T12:00:00Z",
            "publishTime": "2026-01-14T09:21:00Z",
            "generation": 10503,
        },
    ])

    selected = select_forecasts(forecasts)

    assert len(selected) == 1
    assert selected.iloc[0]["forecast"] == 11049


def test_target_without_eligible_forecast_is_not_selected():
    forecasts = pd.DataFrame([
        {
            "startTime": "2026-01-15T12:00:00Z",
            "publishTime": "2026-01-14T09:21:00Z",
            "generation": 10503,
        },
    ])

    selected = select_forecasts(forecasts)

    assert selected.empty


def test_hour_with_one_half_hour_actual_is_missing():
    actuals = pd.DataFrame([
        {
            "startTime": "2026-01-15T12:00:00Z",
            "generation": 9500,
        },
    ])

    hourly = build_hourly_actuals(actuals)

    assert len(hourly) == 1
    assert pd.isna(hourly.iloc[0]["actual"])

def test_junk_forecast_count_includes_only_january_targets():
    from app.analysis import count_junk_forecasts

    forecasts = pd.DataFrame([
        # December target published after its delivery time:
        # junk, but outside the January scope.
        {
            "startTime": "2025-12-31T12:00:00Z",
            "publishTime": "2025-12-31T12:30:00Z",
            "generation": 100,
        },
        # January target published after its delivery time:
        # count this.
        {
            "startTime": "2026-01-15T12:00:00Z",
            "publishTime": "2026-01-15T12:30:00Z",
            "generation": 200,
        },
        # February target published after its delivery time:
        # junk, but outside the January scope.
        {
            "startTime": "2026-02-01T12:00:00Z",
            "publishTime": "2026-02-01T12:30:00Z",
            "generation": 300,
        },
        # January target published before delivery:
        # not junk.
        {
            "startTime": "2026-01-16T12:00:00Z",
            "publishTime": "2026-01-15T09:30:00Z",
            "generation": 400,
        },
    ])

    assert count_junk_forecasts(forecasts) == 1

def test_changing_cutoff_changes_selected_forecast():
    forecasts = pd.DataFrame([
        {
            "startTime": "2026-01-15T12:00:00Z",
            "publishTime": "2026-01-14T07:30:00Z",
            "generation": 11049,
        },
        {
            "startTime": "2026-01-15T12:00:00Z",
            "publishTime": "2026-01-14T09:30:00Z",
            "generation": 10503,
        },
    ])

    early = select_forecasts(
        forecasts,
        cutoff_hour=9,
        cutoff_minute=20,
    )

    late = select_forecasts(
        forecasts,
        cutoff_hour=9,
        cutoff_minute=50,
    )

    assert early.iloc[0]["forecast"] == 11049
    assert late.iloc[0]["forecast"] == 10503

def test_comparison_keeps_hour_with_no_eligible_forecast():
    actuals = pd.DataFrame([
        {
            "startTime": "2026-01-15T12:00:00Z",
            "generation": 9500,
        },
        {
            "startTime": "2026-01-15T12:30:00Z",
            "generation": 10081,
        },
    ])

    forecasts = pd.DataFrame([
        {
            "startTime": "2026-01-15T12:00:00Z",
            "publishTime": "2026-01-14T09:30:00Z",
            "generation": 10503,
        },
    ])

    comparison = build_hourly_comparison(
        actuals,
        forecasts,
        cutoff_hour=9,
        cutoff_minute=20,
    )

    target = comparison[
        comparison["targetTime"]
        == pd.Timestamp("2026-01-15T12:00:00Z")
    ]

    assert len(target) == 1
    assert pd.isna(target.iloc[0]["forecast"])
    assert pd.isna(target.iloc[0]["error"])