import logging
from datetime import datetime

from utils.config import Settings
from services.growatt.growatt_service import GrowattService
from models.result import Result
from models.planned_action import PlannedAction, CommandName

logger = logging.getLogger("wattops.executor")


def apply_planned_action(action: PlannedAction, settings: Settings) -> Result[None]:
    growatt_api_key = settings.growatt_api_key
    device_sn = settings.growatt_device_serial_number

    if settings.dry_run:
        logger.info(
            f"DRY RUN action: {action.command.name} on device: {device_sn} "
            f"value: {action.command.value} {action.command.unit} "
            f"window: [{action.window.start} -> {action.window.end}] "
            f"reason: {action.reason.type} correlation_id={action.correlation_id}"
        )
        return Result.ok(None)

    growatt_service = GrowattService(api_key=growatt_api_key, device_sn=device_sn)

    match action.command.name:
        case CommandName.SET_EXPORT_LIMIT:
            return growatt_service.set_export_limit(percent=action.command.value)

        case CommandName.DISABLE_EXPORT_LIMIT:
            return growatt_service.disable_export_limit()

        case CommandName.SET_AC_CHARGE_WINDOW:
            start_time = datetime.fromisoformat(action.window.start).strftime("%H:%M")
            end_time = datetime.fromisoformat(action.window.end).strftime("%H:%M")
            return growatt_service.set_ac_charge_window(
                start_time=start_time, end_time=end_time
            )

        case CommandName.DISABLE_AC_CHARGE_WINDOW:
            return growatt_service.disable_ac_charge_window()

        case CommandName.ENABLE_GRID_FIRST:
            start_time = datetime.fromisoformat(action.window.start).strftime("%H:%M")
            end_time = datetime.fromisoformat(action.window.end).strftime("%H:%M")
            return growatt_service.set_ac_discharge_window(
                start_time=start_time,
                end_time=end_time,
                discharge_power=settings.growatt_discharge_power_percent,
                stop_soc=settings.growatt_stop_soc_percent,
            )

        case CommandName.DISABLE_GRID_FIRST:
            return growatt_service.disable_ac_discharge_window()

        case _:
            return Result.fail(f"Unsupported command: {action.command.name}")
