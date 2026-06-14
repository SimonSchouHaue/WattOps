import json
import logging
from datetime import datetime, timedelta, timezone

import azure.functions as func

from services.forecast.pvnode_forcast_service import PVnodeForecastService
from utils.config import Settings
from utils.service_bus import publish_scheduled_actions
from functions.executor import apply_planned_action
from functions.planner import Planner
from services.price.energi_data_price_service import EnergiDataPriceService
from services.forecast.open_meteo_forecast_service import OpenMeteoForecastService
from services.forecast.solcast_forecast_service import SolcastForecastService
from services.sunrise.sunrise_sunset_service import SunriseSunsetService
from models.planned_action import PlannedAction

app = func.FunctionApp()

# Suppress third-party library logging except for our own wattops.* logs
logging.getLogger().setLevel(logging.ERROR)
logging.getLogger("wattops").setLevel(logging.INFO)

logger = logging.getLogger("wattops")


@app.function_name(name="planner")
@app.timer_trigger(
    schedule="0 0 23 * * *", arg_name="timer", run_on_startup=True, use_monitor=True
)
def planner(timer: func.TimerRequest) -> None:
    _ = timer
    settings = Settings.from_env()
    planning_date = (datetime.now(timezone.utc) + timedelta(days=1)).date()

    planner = Planner(
        settings=settings,
        price_provider=EnergiDataPriceService(settings),
        forecast_providers=[
            OpenMeteoForecastService(settings),
            SolcastForecastService(settings),
            PVnodeForecastService(settings),
        ],
        sunrise_provider=SunriseSunsetService(settings),
    )
    result = planner.create_plan(planning_date)

    if not result.success:
        logger.error(f"Planner failed for {planning_date.isoformat()}: {result.error}")
        return

    actions = result.value

    if not actions:
        logger.warning(f"Planner produced no actions for {planning_date.isoformat()}")
        return

    for action in actions:
        logger.info(
            f"Planner created action '{action.command.name}' for window {action.window.start} - {action.window.end} "
            f"because of {action.reason.type}: {action.reason.details}"
        )

    # publish_scheduled_actions(
    #     actions,
    #     settings.service_bus_fully_qualified_namespace,
    #     settings.planner_queue_name,
    # )


# @app.function_name(name="executor")
# @app.service_bus_queue_trigger(
#     arg_name="msg",
#     queue_name="planed-commands",
#     connection="ServiceBusConnection",
# )
# def executor(msg: func.ServiceBusMessage) -> None:
#     settings = Settings.from_env()

#     payload = msg.get_body().decode("utf-8")
#     action = PlannedAction.from_message(json.loads(payload))

#     planed_action_result = apply_planned_action(action, settings)

#     if not planed_action_result.success:
#         logger.error(
#             f"Executor failed applying command '{action.command.name}' on device '{settings.growatt_device_serial_number}': {planed_action_result.error}"
#         )
#         return
#     if not settings.dry_run:
#         logger.info(
#             f"Executor applied command '{action.command.name}' for device '{settings.growatt_device_serial_number}' successfully"
#         )
