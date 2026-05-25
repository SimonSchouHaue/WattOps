from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from src.utils.config import Settings
from src.models.models import Command, PlannedAction, Reason, Target, Window


class Planner:
    def __init__(
        self,
        settings: Settings,
        price_provider,
        forecast_provider,
    ) -> None:
        self._settings = settings
        self._price_provider = price_provider
        self._forecast_provider = forecast_provider

    def create_plan(self, planning_date: date) -> list[PlannedAction]:
        correlation_id = f"plan-{planning_date.isoformat()}"
        target = Target(
            site_id=self._settings.site_id, device_id=self._settings.device_id
        )

        prices = self._price_provider.get_prices(planning_date)
        forecast_kwh = self._forecast_provider.get_forecast_kwh(planning_date)

        actions: list[PlannedAction] = []
        actions.extend(
            self._build_export_limit_actions(
                prices=prices,
                forecast_kwh=forecast_kwh,
                target=target,
                correlation_id=correlation_id,
            )
        )

        grid_first_action = self._build_grid_first_action(
            planning_date=planning_date,
            forecast_kwh=forecast_kwh,
            target=target,
            correlation_id=correlation_id,
        )
        if grid_first_action:
            actions.append(grid_first_action)

        return actions

    def _build_export_limit_actions(
        self,
        prices: list[tuple[datetime, float]],
        forecast_kwh: float,
        target: Target,
        correlation_id: str,
    ) -> list[PlannedAction]:
        expensive_hours = [
            item for item in prices if item[1] > self._settings.price_threshold
        ]
        windows = _group_into_hour_windows(expensive_hours)
        actions: list[PlannedAction] = []

        for start, end, peak_price in windows:
            actions.append(
                PlannedAction(
                    command=Command(name="set_export_limit", value=0, unit="percent"),
                    window=Window(start=start.isoformat(), end=end.isoformat()),
                    reason=Reason(
                        type="high_price",
                        details={
                            "peak_price": peak_price,
                            "threshold": self._settings.price_threshold,
                            "forecast_kwh": forecast_kwh,
                        },
                    ),
                    target=target,
                    correlation_id=correlation_id,
                )
            )

        return actions

    def _build_grid_first_action(
        self,
        planning_date: date,
        forecast_kwh: float,
        target: Target,
        correlation_id: str,
    ) -> PlannedAction | None:
        if forecast_kwh <= self._settings.solar_output_threshold_kwh:
            return None

        # Duration scales with expected overproduction while staying within configured bounds.
        overflow_kwh = forecast_kwh - self._settings.solar_output_threshold_kwh
        computed_minutes = int(overflow_kwh * 15)
        duration_minutes = max(
            self._settings.grid_first_min_minutes,
            min(self._settings.grid_first_max_minutes, computed_minutes),
        )

        start = datetime.combine(
            planning_date,
            time(hour=self._settings.grid_first_start_hour, tzinfo=timezone.utc),
        )
        end = start + timedelta(minutes=duration_minutes)

        return PlannedAction(
            command=Command(name="set_operating_mode", value="grid_first", unit="mode"),
            window=Window(start=start.isoformat(), end=end.isoformat()),
            reason=Reason(
                type="high_solar_forecast",
                details={
                    "forecast_kwh": forecast_kwh,
                    "threshold_kwh": self._settings.solar_output_threshold_kwh,
                    "duration_minutes": duration_minutes,
                },
            ),
            target=target,
            correlation_id=correlation_id,
        )


def _group_into_hour_windows(
    hourly_prices: list[tuple[datetime, float]],
) -> list[tuple[datetime, datetime, float]]:
    if not hourly_prices:
        return []

    sorted_prices = sorted(hourly_prices, key=lambda item: item[0])
    windows: list[tuple[datetime, datetime, float]] = []

    start = sorted_prices[0][0]
    previous = sorted_prices[0][0]
    peak_price = sorted_prices[0][1]

    for timestamp, price in sorted_prices[1:]:
        if timestamp - previous == timedelta(hours=1):
            previous = timestamp
            peak_price = max(peak_price, price)
            continue

        windows.append((start, previous + timedelta(hours=1), peak_price))
        start = timestamp
        previous = timestamp
        peak_price = price

    windows.append((start, previous + timedelta(hours=1), peak_price))
    return windows
