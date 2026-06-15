from datetime import time

from growattServer import GrowattV1ApiError, OpenApiV1

from models.result import Result

DISABLED_PERIOD = {"start_time": time(0, 0), "end_time": time(0, 0), "enabled": False}


class GrowattService:
    def __init__(self, api_key: str, device_sn: str) -> None:
        self.device_sn = device_sn
        self._api = OpenApiV1(token=api_key)

    def set_export_limit(self, percent: float) -> Result[None]:
        """Set the inverter export limit to the grid.

        Args:
            percent: Export limit as % of rated power (0-100).
        """
        if not (0 <= percent <= 100):
            return Result.fail(
                f"Export limit percent must be between 0 and 100, got {percent}"
            )
        try:
            self._api.sph_write_parameter(
                self.device_sn,
                "backflow_setting",
                ["1", str(int(percent))],
            )
            return Result.ok(None)
        except GrowattV1ApiError as e:
            return Result.fail(f"API error details: {e.error_msg} {e.error_code}")

    def disable_export_limit(self) -> Result[None]:
        """Disable export limit to the grid and set export limit to 0%."""
        try:
            self._api.sph_write_parameter(
                self.device_sn,
                "backflow_setting",
                ["0", "0"],
            )
            return Result.ok(None)
        except GrowattV1ApiError as e:
            return Result.fail(f"API error details: {e.error_msg} {e.error_code}")

    def disable_ac_charge_window(self) -> Result[None]:
        """Disable all AC charge windows (grid → battery)."""
        try:
            self._api.sph_write_ac_charge_times(
                self.device_sn,
                50,
                25,
                mains_enabled=False,
                periods=[DISABLED_PERIOD, DISABLED_PERIOD, DISABLED_PERIOD],
            )
            return Result.ok(None)
        except GrowattV1ApiError as e:
            return Result.fail(f"API error details: {e.error_msg} {e.error_code}")

    def set_ac_charge_window(
        self,
        start_time: str,
        end_time: str,
        charge_power: int = 50,
        stop_soc: int = 90,
    ) -> Result[None]:
        """Schedule grid → battery charging in a time window.

        Args:
            start_time: Window start in "HH:MM" format.
            end_time:   Window end in "HH:MM" format.
            charge_power: Charge power as % of rated (0-100).
            stop_soc:   Stop charging at this battery SOC % (0-100).
        """
        if not (0 <= charge_power <= 100):
            return Result.fail(
                f"Charge power percent must be between 0 and 100, got {charge_power}"
            )
        if not (0 <= stop_soc <= 100):
            return Result.fail(
                f"Stop SOC percent must be between 0 and 100, got {stop_soc}"
            )
        try:
            sh, sm = (int(x) for x in start_time.split(":"))
            eh, em = (int(x) for x in end_time.split(":"))
            self._api.sph_write_ac_charge_times(
                self.device_sn,
                charge_power,
                stop_soc,
                mains_enabled=True,
                periods=[
                    {
                        "start_time": time(sh, sm),
                        "end_time": time(eh, em),
                        "enabled": True,
                    },
                    DISABLED_PERIOD,
                    DISABLED_PERIOD,
                ],
            )
            return Result.ok(None)
        except GrowattV1ApiError as e:
            return Result.fail(f"API error details: {e.error_msg} {e.error_code}")

    def disable_ac_discharge_window(self) -> Result[None]:
        """Disable all AC discharge windows (battery → grid/load)."""
        try:
            self._api.sph_write_ac_discharge_times(
                self.device_sn,
                50,
                25,
                periods=[DISABLED_PERIOD, DISABLED_PERIOD, DISABLED_PERIOD],
            )
            return Result.ok(None)
        except GrowattV1ApiError as e:
            return Result.fail(f"API error details: {e.error_msg} {e.error_code}")

    def set_ac_discharge_window(
        self,
        start_time: str,
        end_time: str,
        discharge_power: int = 50,
        stop_soc: int = 25,
    ) -> Result[None]:
        """Schedule battery → grid/load discharging in a time window.

        Args:
            start_time:      Window start in "HH:MM" format.
            end_time:        Window end in "HH:MM" format.
            discharge_power: Discharge power as % of rated (0-100).
            stop_soc:        Stop discharging at this battery SOC % (0-100).
        """
        if not (0 <= discharge_power <= 100):
            return Result.fail(
                f"Discharge power percent must be between 0 and 100, got {discharge_power}"
            )
        if not (10 <= stop_soc <= 100):
            return Result.fail(
                f"Stop SOC percent must be between 10 and 100, got {stop_soc}"
            )
        try:
            sh, sm = (int(x) for x in start_time.split(":"))
            eh, em = (int(x) for x in end_time.split(":"))
            self._api.sph_write_ac_discharge_times(
                self.device_sn,
                discharge_power,
                stop_soc,
                periods=[
                    {
                        "start_time": time(sh, sm),
                        "end_time": time(eh, em),
                        "enabled": True,
                    },
                    DISABLED_PERIOD,
                    DISABLED_PERIOD,
                ],
            )
            return Result.ok(None)
        except GrowattV1ApiError as e:
            return Result.fail(f"API error details: {e.error_msg} {e.error_code}")
