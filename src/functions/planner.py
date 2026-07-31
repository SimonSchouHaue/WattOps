import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from utils.config import Settings
from models.result import Result
from models.planned_action import Command, CommandName, PlannedAction, Reason, Window
from services.price.base.electricity_price_service import ElectricityPriceService
from services.forecast.base.solar_forecast_service import SolarForecastService
from services.sunrise.base.sunrise_service import SunriseService
from services.growatt.growatt_service import GrowattService

logger = logging.getLogger("wattops.planner")


class Planner:
    def __init__(
        self,
        settings: Settings,
        price_provider: ElectricityPriceService,
        forecast_providers: list[SolarForecastService],
        sunrise_provider: SunriseService,
        growatt_service: GrowattService,
    ) -> None:
        self.settings = settings
        self.price_provider = price_provider
        self.forecast_providers = forecast_providers
        self.sunrise_provider = sunrise_provider
        self.growatt_service = growatt_service
        self.timezone = ZoneInfo(settings.local_timezone)

    def create_plan(self, planning_date: date) -> Result[list[PlannedAction]]:
        correlation_id = f"plan-{planning_date.isoformat()}"

        prices_result = self.price_provider.get_prices(planning_date)
        if not prices_result.success:
            return Result.fail(
                f"Could not fetch electricity prices: {prices_result.error}"
            )

        forecast_values: list[float] = []
        for provider in self.forecast_providers:
            result = provider.get_forecast_kwh(planning_date)
            if result.success:
                logger.info(
                    f"Provider {type(provider).__name__} forecast: {result.value:.1f} kWh"
                )
                forecast_values.append(result.value)
            else:
                logger.warning(
                    f"Provider {type(provider).__name__} failed: {result.error}"
                )

        if not forecast_values:
            return Result.fail(f"Could not fetch solar forecast for any provider")

        forecast_kwh = sum(forecast_values) / len(forecast_values)

        # Apply performance ratio to get more realistic usable energy estimate
        forecast_kwh *= self.settings.solar_performance_ratio

        electricity_prices = prices_result.value

        actions: list[PlannedAction] = []

        actions.extend(
            self._build_export_limit_actions(
                planning_date=planning_date,
                prices=electricity_prices,
                correlation_id=correlation_id,
            )
        )

        grid_first_actions = self._build_grid_first_action(
            planning_date=planning_date,
            forecast_kwh=forecast_kwh,
            prices=electricity_prices,
            correlation_id=correlation_id,
        )
        if grid_first_actions:
            actions.extend(grid_first_actions)
        else:
            midnight = datetime.combine(planning_date, time(0, 0, tzinfo=timezone.utc))
            actions.append(
                PlannedAction(
                    command=Command(
                        name=CommandName.DISABLE_GRID_FIRST,
                        value=0,
                        unit="disable",
                    ),
                    window=Window(
                        start=midnight.astimezone(self.timezone).isoformat(),
                        end=(midnight + timedelta(days=1))
                        .astimezone(self.timezone)
                        .isoformat(),
                    ),
                    reason=Reason(
                        type="low_solar_forecast",
                        details={
                            "forecast_kwh": forecast_kwh,
                            "threshold_kwh": self.settings.solar_output_export_threshold_kwh,
                        },
                    ),
                    correlation_id=correlation_id,
                    scheduled_at=midnight.isoformat(),
                )
            )

        actions.extend(
            self._build_ac_charge_action(
                forecast_kwh=forecast_kwh,
                prices=electricity_prices,
                correlation_id=correlation_id,
            )
        )

        return Result.ok(actions)

    def _build_export_limit_actions(
        self,
        planning_date: date,
        prices: list[tuple[datetime, float]],
        correlation_id: str,
    ) -> list[PlannedAction]:
        cheap_hours = sorted(
            [
                item
                for item in prices
                if item[1] < self.settings.price_stop_export_threshold_dkk_kwh
            ],
            key=lambda item: item[0],
        )

        if not cheap_hours:
            return []

        window_start = cheap_hours[0][0]
        window_end = cheap_hours[-1][0] + timedelta(minutes=15)
        lowest_price = min(item[1] for item in cheap_hours)
        end_of_day = datetime.combine(
            planning_date + timedelta(days=1), time(0, 0, tzinfo=timezone.utc)
        )
        prices_after = [
            p for dt, p in sorted(prices, key=lambda x: x[0]) if dt > cheap_hours[-1][0]
        ]
        trigger_price = (
            prices_after[0]
            if prices_after
            else self.settings.price_stop_export_threshold_dkk_kwh
        )

        return [
            PlannedAction(
                command=Command(
                    name=CommandName.SET_EXPORT_LIMIT,
                    value=0,
                    unit="percent",
                ),
                window=Window(
                    start=window_start.astimezone(self.timezone).isoformat(),
                    end=window_end.astimezone(self.timezone).isoformat(),
                ),
                reason=Reason(
                    type="low_price",
                    details={
                        "lowest_price_in_window": lowest_price,
                        "threshold_price": self.settings.price_stop_export_threshold_dkk_kwh,
                    },
                ),
                correlation_id=correlation_id,
                scheduled_at=window_start.isoformat(),
            ),
            PlannedAction(
                command=Command(
                    name=CommandName.DISABLE_EXPORT_LIMIT,
                    value=100,
                    unit="percent",
                ),
                window=Window(
                    start=window_end.astimezone(self.timezone).isoformat(),
                    end=end_of_day.astimezone(self.timezone).isoformat(),
                ),
                reason=Reason(
                    type="high_price",
                    details={
                        "enable_export_trigger_price": trigger_price,
                        "threshold_price": self.settings.price_stop_export_threshold_dkk_kwh,
                    },
                ),
                correlation_id=correlation_id,
                scheduled_at=window_end.isoformat(),
            ),
        ]

    def _build_ac_charge_action(
        self,
        forecast_kwh: float,
        prices: list[tuple[datetime, float]],
        correlation_id: str,
    ) -> list[PlannedAction]:
        if forecast_kwh >= self.settings.solar_output_import_threshold_kwh:
            logger.info(
                f"Forecast kWh {forecast_kwh:.1f} is at or above import threshold {self.settings.solar_output_import_threshold_kwh:.1f}, skipping AC charge action"
            )
            return []

        soc_result = self.growatt_service.get_battery_soc()
        if not soc_result.success:
            logger.warning(
                f"Could not fetch battery SOC: {soc_result.error}, skipping AC charge action"
            )
            return []

        battery_soc = soc_result.value
        if battery_soc >= self.settings.growatt_start_charge_soc_percent:
            logger.info(
                f"Battery SOC {battery_soc} % is at or above threshold {self.settings.growatt_start_charge_soc_percent} %, skipping AC charge action"
            )
            return []

        cheap_hours = sorted(
            [
                item
                for item in prices
                if item[1] < self.settings.price_start_import_threshold_dkk_kwh
            ],
            key=lambda item: item[0],
        )

        if len(cheap_hours) < 4:
            logger.info(
                f"Only {len(cheap_hours)} price slot(s) below import threshold found, "
                "need at least 4, skipping AC charge action"
            )
            return []

        window_start = cheap_hours[0][0]
        window_end = cheap_hours[-1][0] + timedelta(minutes=15)
        lowest_price = min(item[1] for item in cheap_hours)

        return [
            PlannedAction(
                command=Command(
                    name=CommandName.SET_AC_CHARGE_WINDOW,
                    value=battery_soc,
                    unit="battery_soc_percent",
                ),
                window=Window(
                    start=window_start.astimezone(self.timezone).isoformat(),
                    end=window_end.astimezone(self.timezone).isoformat(),
                ),
                reason=Reason(
                    type="low_soc_low_forecast",
                    details={
                        "battery_soc_percent": battery_soc,
                        "soc_threshold_percent": self.settings.growatt_start_charge_soc_percent,
                        "forecast_kwh": forecast_kwh,
                        "forecast_threshold_kwh": self.settings.solar_output_import_threshold_kwh,
                        "lowest_price_in_window": lowest_price,
                        "threshold_price": self.settings.price_start_import_threshold_dkk_kwh,
                    },
                ),
                correlation_id=correlation_id,
                scheduled_at=(window_start - timedelta(minutes=5)).isoformat(),
            )
        ]

    def _build_grid_first_action(
        self,
        planning_date: date,
        forecast_kwh: float,
        prices: list[tuple[datetime, float]],
        correlation_id: str,
    ) -> list[PlannedAction]:
        if forecast_kwh <= self.settings.solar_output_export_threshold_kwh:
            logger.info(
                f"Forecast kWh {forecast_kwh:.1f} is below threshold {self.settings.solar_output_export_threshold_kwh:.1f}, skipping grid-first action"
            )
            return []

        # Duration scales with expected overproduction.
        overflow_kwh = forecast_kwh - self.settings.solar_output_export_threshold_kwh

        logger.info(
            f"Average forecast kWh: {forecast_kwh}, calculated overflow kWh: {overflow_kwh}"
        )
        duration_minutes = int(overflow_kwh * 15)

        sunrise_result = self.sunrise_provider.get_sunrise(planning_date)

        if not sunrise_result.success:
            fallback_sunrise = datetime.combine(
                planning_date,
                time(
                    self.settings.grid_first_sunrise_fallback_hour,
                    0,
                    tzinfo=timezone.utc,
                ),
            )
            logger.warning(
                f"Could not fetch sunrise for {planning_date}: {sunrise_result.error}, "
                f"using fallback sunrise time {fallback_sunrise.isoformat()}"
            )
            sunrise = fallback_sunrise
        else:
            sunrise = sunrise_result.value

        start = sunrise + timedelta(
            minutes=self.settings.grid_first_minutes_after_sunrise
        )
        end = start + timedelta(minutes=duration_minutes)

        # Cap end at the first slot within the window where price drops below threshold.
        cheap_in_window = sorted(
            [
                dt
                for dt, price in prices
                if start <= dt < end
                and price < self.settings.price_stop_export_threshold_dkk_kwh
            ]
        )
        if cheap_in_window:
            end = cheap_in_window[0]
            logger.info(
                f"Grid-first window capped at {end.isoformat()} due to price below threshold"
            )

        result_actions: list[PlannedAction] = []

        if end <= start:
            logger.info(
                "Grid-first window collapsed due to immediate high price, skipping"
            )
        else:
            result_actions.append(
                PlannedAction(
                    command=Command(
                        name=CommandName.ENABLE_GRID_FIRST,
                        value=30,
                        unit="discharge_stop_soc_percent",
                    ),
                    window=Window(
                        start=start.astimezone(self.timezone).isoformat(),
                        end=end.astimezone(self.timezone).isoformat(),
                    ),
                    reason=Reason(
                        type="high_solar_forecast",
                        details={
                            "forecast_kwh": forecast_kwh,
                            "threshold_kwh": self.settings.solar_output_export_threshold_kwh,
                            "duration_minutes": duration_minutes,
                        },
                    ),
                    correlation_id=correlation_id,
                    scheduled_at=(start - timedelta(minutes=5)).isoformat(),
                )
            )

        # Enable grid-first during high-price windows
        high_price_entries = [
            (dt, price)
            for dt, price in prices
            if price > self.settings.price_start_export_threshold_dkk_kwh
        ]

        if high_price_entries:
            high_price_slots = sorted(dt for dt, _ in high_price_entries)
            hp_start = high_price_slots[0]
            hp_end = high_price_slots[-1] + timedelta(minutes=15)
            max_price_in_window = max(price for _, price in high_price_entries)

            logger.info(
                f"High price peak at {max_price_in_window:.4f} DKK/kWh, {len(high_price_slots)} price slots above threshold {self.settings.price_start_export_threshold_dkk_kwh:.4f} DKK/kWh"
            )

            # Avoid overlapping with the high-solar-forecast window above by
            # shortening the high-price window rather than the solar one.
            solar_first_active = end > start
            if solar_first_active and hp_start < end and hp_end > start:
                if hp_start < start:
                    hp_end = min(hp_end, start)
                else:
                    hp_start = max(hp_start, end)
                logger.info(
                    f"High-price window overlapped high-solar-forecast window, shortened to {hp_start.isoformat()} - {hp_end.isoformat()}"
                )

            if hp_end <= hp_start:
                logger.info(
                    "High-price grid-first window fully overlapped by high-solar-forecast window, skipping"
                )
            else:
                result_actions.append(
                    PlannedAction(
                        command=Command(
                            name=CommandName.ENABLE_GRID_FIRST,
                            value=50,
                            unit="discharge_stop_soc_percent",
                        ),
                        window=Window(
                            start=hp_start.astimezone(self.timezone).isoformat(),
                            end=hp_end.astimezone(self.timezone).isoformat(),
                        ),
                        reason=Reason(
                            type="high_price",
                            details={
                                "high_price_dkk_kwh": max_price_in_window,
                                "threshold_price_dkk_kwh": self.settings.price_start_export_threshold_dkk_kwh,
                                "slots_above_threshold": len(high_price_slots),
                            },
                        ),
                        correlation_id=correlation_id,
                        scheduled_at=(hp_start - timedelta(minutes=5)).isoformat(),
                    )
                )

        return result_actions
