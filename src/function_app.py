import json
import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage

from src.utils.config import Settings
from src.functions.executor import apply_planned_action
from src.functions.planner import Planner
from src.services.electric_pricing_api import ElectricityPriceProvider
from src.services.solar_power_output_api import SolarForecastProvider
from src.models.models import PlannedAction

app = func.FunctionApp()
logger = logging.getLogger("wattops")


@app.timer_trigger(
    schedule="0 0 23 * * *", arg_name="timer", run_on_startup=False, use_monitor=True
)
def planner_timer(timer: func.TimerRequest) -> None:
    _ = timer
    settings = Settings.from_env()
    planning_date = (datetime.now(timezone.utc) + timedelta(days=1)).date()

    planner = Planner(
        settings=settings,
        price_provider=ElectricityPriceProvider(settings),
        forecast_provider=SolarForecastProvider(settings),
    )
    actions = planner.create_plan(planning_date)

    if not actions:
        logger.info("Planner produced no actions for %s", planning_date.isoformat())
        return

    _publish_actions(actions, settings)
    logger.info(
        "Planner published %s actions for %s", len(actions), planning_date.isoformat()
    )


@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="%PLANNER_QUEUE_NAME%",
    connection="SERVICE_BUS_CONNECTION",
)
def executor_queue(msg: func.ServiceBusMessage) -> None:
    settings = Settings.from_env()

    payload = msg.get_body().decode("utf-8")
    action = PlannedAction.from_message(json.loads(payload))

    api_key = _get_growatt_api_key(settings)
    apply_planned_action(action, settings, api_key)
    logger.info(
        "Executor applied command '%s' for site '%s'",
        action.command.name,
        action.target.site_id,
    )


def _publish_actions(actions: list[PlannedAction], settings: Settings) -> None:
    if not settings.service_bus_connection:
        raise ValueError("SERVICE_BUS_CONNECTION is required")

    with ServiceBusClient.from_connection_string(
        settings.service_bus_connection
    ) as client:
        sender = client.get_queue_sender(queue_name=settings.planner_queue_name)
        with sender:
            messages = [
                ServiceBusMessage(json.dumps(action.to_message())) for action in actions
            ]
            sender.send_messages(messages)


@lru_cache(maxsize=1)
def _get_growatt_api_key(settings: Settings) -> str:
    if settings.growatt_api_key:
        return settings.growatt_api_key

    if not settings.key_vault_url:
        raise ValueError(
            "Set GROWATT_API_KEY or KEY_VAULT_URL + GROWATT_API_SECRET_NAME"
        )

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=settings.key_vault_url, credential=credential)
    return client.get_secret(settings.growatt_api_secret_name).value
